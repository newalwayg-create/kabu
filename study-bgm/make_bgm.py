#!/usr/bin/env python3
"""勉強用 lo-fi hip hop BGM ジェネレーター.

MIDI を打ち込み (pretty_midi) → FluidSynth + サウンドフォントで WAV に書き出し
→ numpy/scipy で lo-fi 処理 (こもり・テープ揺れ・レコードノイズ) → MP3 化.

使い方:
    python3 make_bgm.py                     # デフォルト設定で生成
    python3 make_bgm.py --bpm 70 --seed 7   # テンポや乱数シードを変えて作り直す

必要なもの: pretty_midi, scipy, numpy, fluidsynth コマンド, ffmpeg, GM サウンドフォント
"""
import argparse
import random
import subprocess
from pathlib import Path

import numpy as np
import pretty_midi
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

# ---------------------------------------------------------------------------
# パラメータ (ここを変えると雰囲気が変わる)
# ---------------------------------------------------------------------------
BPM = 75
SEED = 42
TRANSPOSE = 0          # 半音単位でキーを移動 (例: -2 で E♭メジャー)
SWING = 0.58           # 16分音符のスウィング量 (0.5 = ストレート)
HUMANIZE_MS = 12       # タイミングのランダムなズレ (ミリ秒)

# GM プログラム番号 (0 始まり)
PROG_EPIANO = 4        # Electric Piano 1 (Rhodes 系)
PROG_BASS = 33         # Electric Bass (finger)
PROG_PAD = 89          # Pad 2 (warm)

# 音量バランス (ベロシティの基準値)
VEL_EPIANO = 62
VEL_BASS = 78
VEL_PAD = 34
VEL_DRUMS = 1.0        # ドラム全体の倍率

# lo-fi 処理
LOWPASS_HZ = 3800      # こもり具合 (低いほどこもる)
WOW_DEPTH_MS = 1.6     # テープのゆっくりした揺れの深さ
NOISE_LEVEL = 0.010    # レコードのヒスノイズ量
CRACKLE_PER_SEC = 3.0  # プチプチ音の頻度

SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
SR = 44100

# ---------------------------------------------------------------------------
# 和声: コードごとに (ベースのルート, エレピのボイシング)
# ---------------------------------------------------------------------------
CHORDS = {
    "Fmaj9":   (41, [57, 60, 64, 67]),
    "Em7b5":   (40, [55, 58, 62, 64]),
    "A7b13":   (45, [55, 61, 65]),
    "Dm9":     (38, [53, 57, 60, 64]),
    "Cm9":     (36, [51, 55, 58, 62]),
    "F13":     (41, [51, 57, 62]),
    "Bbmaj9":  (34, [57, 60, 62, 65]),
    "Am7":     (45, [55, 60, 64]),
    "Gm9":     (43, [53, 57, 58, 62]),
    "C13sus4": (36, [58, 62, 65, 69]),
}

# 1 小節 = コードのリスト (2 つなら 2 拍ずつ)
PROG_A = [["Fmaj9"], ["Em7b5", "A7b13"], ["Dm9"], ["Cm9", "F13"]]
PROG_B = [["Bbmaj9"], ["Am7"], ["Gm9"], ["C13sus4"]]
# 最後はドミナント (C13sus4) で終えて、ループ先頭の Fmaj9 に自然に戻る
PROG_END = [["Fmaj9"], ["Em7b5", "A7b13"], ["Dm9"], ["Gm9", "C13sus4"]]

# 構成: (セクション名, 進行, 繰り返し回数, 使うパート)
SECTIONS = [
    ("intro", PROG_A, 1, {"ep", "pad"}),
    ("A",     PROG_A, 2, {"ep", "pad", "bass", "drums"}),
    ("A2",    PROG_A, 2, {"ep", "pad", "bass", "drums", "melody"}),
    ("B",     PROG_B, 2, {"ep", "pad", "bass", "drums"}),
    ("A3",    PROG_A, 2, {"ep", "pad", "bass", "drums", "melody"}),
    ("B2",    PROG_B, 2, {"ep", "pad", "bass", "drums_soft"}),
    ("A4",    PROG_A, 2, {"ep", "pad", "bass", "drums"}),
    ("end",   PROG_END, 1, {"ep", "pad", "bass", "drums_fade"}),
]

# メロディ用の音階 (F メジャー・ペンタトニック, F4〜F5 周辺)
MELODY_SCALE = [60, 62, 65, 67, 69, 72, 74, 77]


def build_midi(bpm, seed, transpose):
    rng = random.Random(seed)
    beat = 60.0 / bpm
    bar = beat * 4
    hum = HUMANIZE_MS / 1000.0

    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    ep = pretty_midi.Instrument(PROG_EPIANO, name="Rhodes")
    bass = pretty_midi.Instrument(PROG_BASS, name="Bass")
    pad = pretty_midi.Instrument(PROG_PAD, name="Pad")
    drums = pretty_midi.Instrument(0, is_drum=True, name="Drums")

    def add(inst, pitch, start, dur, vel, jitter=hum):
        start = max(0.0, start + rng.uniform(-jitter, jitter))
        vel = int(np.clip(vel + rng.randint(-7, 7), 1, 127))
        p = pitch if inst.is_drum else pitch + transpose
        inst.notes.append(pretty_midi.Note(vel, p, start, start + dur))

    def swung(sixteenth):
        # 16 分音符位置 (0..15) をスウィングさせた拍位置 (秒) に
        pair, odd = divmod(sixteenth, 2)
        return (pair * 2 + (2 * SWING if odd else 0)) * beat / 4

    t = 0.0
    melody_note = 4
    for name, prog, reps, parts in SECTIONS:
        for _ in range(reps):
            for bar_chords in prog:
                n = len(bar_chords)
                for ci, cname in enumerate(bar_chords):
                    root, voicing = CHORDS[cname]
                    cs = t + ci * bar / n          # コード開始
                    clen = bar / n

                    # パッド: 1 オクターブ上で白玉
                    if "pad" in parts:
                        for p in voicing:
                            add(pad, p + 12, cs, clen + 0.05, VEL_PAD, jitter=0)

                    # エレピ: 少し遅れて下から上へ軽くばらす
                    if "ep" in parts:
                        lay = beat * 0.06
                        hold = clen * (0.9 if n == 2 else 0.55)
                        for k, p in enumerate(voicing):
                            add(ep, p, cs + lay + k * 0.018, hold, VEL_EPIANO)
                        # 1 コード/小節のときは裏拍で軽く刻み直す
                        if n == 1 and rng.random() < 0.75:
                            off = rng.choice([swung(5), swung(6), swung(10)])
                            for k, p in enumerate(voicing[1:]):
                                add(ep, p, cs + off + k * 0.015,
                                    beat * 1.2, VEL_EPIANO - 16)

                    # ベース: ルート + たまに 5 度/オクターブ
                    if "bass" in parts:
                        if n == 1:
                            add(bass, root, cs, beat * 1.6, VEL_BASS)
                            add(bass, root, cs + swung(6), beat * 0.9,
                                VEL_BASS - 14)
                            add(bass, rng.choice([root + 7, root + 12, root]),
                                cs + beat * 3 + swung(2) - swung(0),
                                beat * 0.6, VEL_BASS - 18)
                        else:
                            add(bass, root, cs, clen * 0.85, VEL_BASS)

                # ドラム (1 小節単位)
                dset = parts & {"drums", "drums_soft", "drums_fade"}
                if dset:
                    kind = dset.pop()
                    d = VEL_DRUMS
                    kicks = [0, 7, 10] if rng.random() < 0.6 else [0, 10]
                    for k in kicks:
                        add(drums, 36, t + swung(k), 0.2,
                            (80 if k == 0 else 62) * d, jitter=hum * 0.6)
                    for s in (4, 12):  # 2・4 拍目にサイドスティック
                        add(drums, 37, t + swung(s), 0.2,
                            (58 if kind == "drums_soft" else 70) * d,
                            jitter=hum * 0.6)
                    if kind == "drums":
                        for h in range(0, 16, 2):
                            v = 46 if h % 4 == 0 else 34
                            add(drums, 42, t + swung(h), 0.1, v * d,
                                jitter=hum * 0.5)
                        if rng.random() < 0.3:
                            add(drums, 42, t + swung(15), 0.08, 26 * d)
                    elif kind == "drums_fade":
                        # ループ先頭 (ドラムなし) へつなぐため徐々に薄く
                        for h in range(0, 16, 4):
                            add(drums, 42, t + swung(h), 0.1, 30 * d)

                # メロディ: まばらなペンタトニックのフレーズ
                if "melody" in parts:
                    for pos in sorted(rng.sample(range(0, 16, 2), 3)):
                        if rng.random() < 0.7:
                            step = rng.choice([-2, -1, -1, 1, 1, 2])
                            melody_note = int(np.clip(melody_note + step, 0,
                                                      len(MELODY_SCALE) - 1))
                            add(ep, MELODY_SCALE[melody_note] + 12,
                                t + swung(pos) + 0.03, beat * 0.9,
                                VEL_EPIANO - 4)
                t += bar

    pm.instruments.extend([ep, bass, pad, drums])
    return pm, t  # t = ループ長 (秒)


def render_wav(midi_path, wav_path, soundfont):
    subprocess.run(
        ["fluidsynth", "-ni", "-g", "0.6", "-r", str(SR), "-F", str(wav_path),
         soundfont, str(midi_path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sr, y = wavfile.read(wav_path)
    assert sr == SR
    return y.astype(np.float64) / 32768.0


def circular_filter(x, sos):
    # ループ境界でも途切れないよう、3 周分つないでフィルタして中央を取る
    n = len(x)
    y = sosfiltfilt(sos, np.concatenate([x, x, x]), axis=0)
    return y[n:2 * n]


def lofi(y, loop_sec, seed):
    rng = np.random.default_rng(seed)
    n = int(round(loop_sec * SR))
    if len(y) < n:
        y = np.pad(y, ((0, n - len(y)), (0, 0)))

    # 1. 曲末の残響を先頭に重ねる (ループの継ぎ目をなくす)
    body = y[:n].copy()
    tail = y[n:]
    while len(tail):
        m = min(len(tail), n)
        body[:m] += tail[:m]
        tail = tail[m:]

    # 2. こもり (ローパス) と低域の整理 (ハイパス)
    body = circular_filter(body, butter(4, LOWPASS_HZ, "low", fs=SR,
                                        output="sos"))
    body = circular_filter(body, butter(2, 35, "high", fs=SR, output="sos"))

    # 3. テープの揺れ (ループ長で割り切れる周期にしてつなぎ目を合わせる)
    t = np.arange(n) / SR
    wow_cycles = max(1, round(loop_sec * 0.4))
    flutter_cycles = max(1, round(loop_sec * 5.3))
    delay = (WOW_DEPTH_MS / 1000 * np.sin(2 * np.pi * wow_cycles * t / loop_sec)
             + 0.00015 * np.sin(2 * np.pi * flutter_cycles * t / loop_sec))
    idx = (np.arange(n) - delay * SR) % n
    i0 = np.floor(idx).astype(int)
    frac = (idx - i0)[:, None]
    body = body[i0] * (1 - frac) + body[(i0 + 1) % n] * frac

    # 4. やわらかいサチュレーション
    body = np.tanh(body * 1.6) / 1.6

    # 5. レコードノイズ (ヒス + プチプチ)
    hiss = rng.normal(0, 1, (n, 2))
    hiss = circular_filter(hiss, butter(1, [300, 5000], "band", fs=SR,
                                        output="sos"))
    hiss *= NOISE_LEVEL / (np.std(hiss) + 1e-9)
    crackle = np.zeros((n, 2))
    k = int(CRACKLE_PER_SEC * loop_sec)
    pos = rng.integers(0, n, k)
    crackle[pos] = rng.normal(0, 1, (k, 2)) * rng.choice([0.02, 0.06], (k, 1))
    crackle = circular_filter(crackle, butter(2, [800, 6000], "band", fs=SR,
                                              output="sos"))
    body += hiss + crackle

    # 6. 正規化 (ピーク -1 dBFS)
    body *= 10 ** (-1 / 20) / np.max(np.abs(body))
    return body


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--bpm", type=float, default=BPM)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--transpose", type=int, default=TRANSPOSE)
    ap.add_argument("--soundfont", default=SOUNDFONT)
    ap.add_argument("--out", default="study_bgm", help="出力ファイル名 (拡張子なし)")
    args = ap.parse_args()

    out_dir = Path(__file__).resolve().parent
    midi_path = out_dir / f"{args.out}.mid"
    raw_path = out_dir / f"{args.out}_raw.wav"
    wav_path = out_dir / f"{args.out}.wav"
    mp3_path = out_dir / f"{args.out}.mp3"

    pm, loop_sec = build_midi(args.bpm, args.seed, args.transpose)
    pm.write(str(midi_path))
    print(f"MIDI: {midi_path}  ({loop_sec:.1f} 秒)")

    y = render_wav(midi_path, raw_path, args.soundfont)
    raw_path.unlink()
    y = lofi(y, loop_sec, args.seed)
    wavfile.write(wav_path, SR, (y * 32767).astype(np.int16))
    print(f"WAV : {wav_path}")

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path),
                    "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3_path)],
                   check=True)
    print(f"MP3 : {mp3_path}")


if __name__ == "__main__":
    main()
