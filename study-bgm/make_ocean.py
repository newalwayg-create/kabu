#!/usr/bin/env python3
"""深海イメージのアンビエント BGM ジェネレーター.

MIDI を打ち込み (pretty_midi) → FluidSynth で WAV 化 → 深さに合わせてこもらせ、
numpy で合成した海の効果音 (波・水面をたたく音・泡・船のエンジン・ソナー) を重ねる.
曲は「海面 → 潜水 → 深海 → 浮上 → 海面」と進み、継ぎ目なくループする.

使い方:
    python3 make_ocean.py                 # デフォルト設定で生成
    python3 make_ocean.py --bpm 56 --seed 3

出力: ocean_bgm.mid / ocean_bgm.wav / ocean_bgm.mp3 / ocean_sfx.wav (効果音だけのステム)
"""
import argparse
import random
import subprocess
from pathlib import Path

import numpy as np
import pretty_midi
from scipy.io import wavfile
from scipy.signal import butter

from make_bgm import SR, circular_filter, render_wav

# ---------------------------------------------------------------------------
# パラメータ (ここを変えると雰囲気が変わる)
# ---------------------------------------------------------------------------
BPM = 60
SEED = 11
TRANSPOSE = 0
HUMANIZE_MS = 25

# GM プログラム番号 (0 始まり)
PROG_PAD = 94          # Pad 7 (halo)
PROG_BASS = 35         # Fretless Bass
PROG_VIBES = 11        # Vibraphone
PROG_CHOIR = 52        # Choir Aahs

VEL_PAD = 50
VEL_BASS = 70
VEL_VIBES = 58
VEL_CHOIR = 36

# 深さの演出: 深いほど音楽をこもらせる
SURFACE_LOWPASS_HZ = 6000
DEEP_LOWPASS_HZ = 700

# 効果音の音量 (0 で無効)
SFX_WAVES = 0.025      # 海面の波
SFX_SLAPS = 0.18       # 水面をたたく音
SFX_BUBBLES = 0.09     # 泡
SFX_ENGINE = 0.30      # 船のエンジン
SFX_SONAR = 0.05       # ソナー
SFX_REVERB = 0.35      # 効果音にかける残響の量

SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"

# ---------------------------------------------------------------------------
# 和声: (ベースのルート, ボイシング)
# ---------------------------------------------------------------------------
CHORDS = {
    "Dm9":       (38, [53, 57, 60, 64]),
    "Bbmaj7#11": (34, [50, 53, 57, 64]),
    "Gm9":       (43, [53, 57, 58, 62]),
    "A7sus4b9":  (33, [55, 58, 62, 64]),
    "Ebmaj7#11": (39, [55, 58, 62, 69]),
    "Cmaj7#11":  (36, [52, 55, 59, 66]),
    "Bbmaj7":    (34, [53, 57, 62, 65]),
}
BARS_PER_CHORD = 2

PROG_A = ["Dm9", "Bbmaj7#11", "Gm9", "A7sus4b9"]
PROG_B = ["Ebmaj7#11", "Dm9", "Cmaj7#11", "Bbmaj7"]
PROG_END = ["Dm9", "A7sus4b9"]   # 冒頭の Dm9 に戻るためのつなぎ

# 構成: (セクション名, 進行, 使うパート, 深さ 開始→終了 (0=海面, 1=深海))
SECTIONS = [
    ("surface", PROG_A,   {"pad", "vibes"},                   (0.0, 0.0)),
    ("descent", PROG_A,   {"pad", "bass", "vibes"},           (0.0, 1.0)),
    ("deep",    PROG_B,   {"pad", "bass", "vibes_low"},       (1.0, 1.0)),
    ("abyss",   PROG_B,   {"pad", "bass", "choir"},           (1.0, 1.0)),
    ("ascent",  PROG_A,   {"pad", "bass", "vibes", "choir"},  (1.0, 0.0)),
    ("end",     PROG_END, {"pad", "vibes"},                   (0.0, 0.0)),
]

# ヴィブラフォンの音階 (D ドリアン)
VIBES_SCALE = [62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81]


def build_midi(bpm, seed, transpose):
    rng = random.Random(seed)
    beat = 60.0 / bpm
    bar = beat * 4
    hum = HUMANIZE_MS / 1000.0

    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    pad = pretty_midi.Instrument(PROG_PAD, name="Pad")
    bass = pretty_midi.Instrument(PROG_BASS, name="Fretless Bass")
    vibes = pretty_midi.Instrument(PROG_VIBES, name="Vibraphone")
    choir = pretty_midi.Instrument(PROG_CHOIR, name="Choir")

    def add(inst, pitch, start, dur, vel, jitter=hum):
        start = max(0.0, start + rng.uniform(-jitter, jitter))
        vel = int(np.clip(vel + rng.randint(-6, 6), 1, 127))
        inst.notes.append(
            pretty_midi.Note(vel, pitch + transpose, start, start + dur))

    t = 0.0
    depth_points = []  # (時刻, 深さ) の折れ線
    for name, prog, parts, (d0, d1) in SECTIONS:
        sec_len = len(prog) * BARS_PER_CHORD * bar
        depth_points += [(t, d0), (t + sec_len, d1)]
        for cname in prog:
            root, voicing = CHORDS[cname]
            clen = BARS_PER_CHORD * bar

            if "pad" in parts:
                for p in voicing:
                    add(pad, p, t, clen + 0.3, VEL_PAD, jitter=0)
            if "bass" in parts:
                add(bass, root, t + 0.05, clen * 0.95, VEL_BASS)
            if "choir" in parts:
                for p in voicing[1:]:
                    add(choir, p + 12, t, clen + 0.3, VEL_CHOIR, jitter=0)

            # ヴィブラフォン: コードの構成音寄りに、まばらに
            if "vibes" in parts or "vibes_low" in parts:
                low = "vibes_low" in parts
                count = rng.choice([1, 2, 2, 3]) if not low else rng.choice([1, 1, 2])
                chord_pcs = {p % 12 for p in voicing}
                pool = [p for p in VIBES_SCALE if (p % 12) in chord_pcs] or VIBES_SCALE
                slots = sorted(rng.sample(range(BARS_PER_CHORD * 4), count))
                for s in slots:
                    pitch = rng.choice(pool if rng.random() < 0.7 else VIBES_SCALE)
                    if low:
                        pitch -= 12
                    add(vibes, pitch, t + s * beat + 0.1, beat * 3,
                        VEL_VIBES - (10 if low else 0))
            t += clen

    pm.instruments.extend([pad, bass, vibes, choir])
    return pm, t, depth_points


# ---------------------------------------------------------------------------
# 効果音の合成 (すべてループ長 n の中で巡回配置)
# ---------------------------------------------------------------------------
def place(buf, start, sig):
    n = len(buf)
    idx = (start + np.arange(len(sig))) % n
    np.add.at(buf, idx, sig)


def pan(mono, p):
    # p: -1 (左) 〜 +1 (右)。配列でも可
    a = (np.asarray(p) + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1)


def bubble(rng):
    dur = rng.uniform(0.03, 0.11)
    t = np.arange(int(dur * SR)) / SR
    f0 = rng.uniform(350, 1400)
    f = f0 * (1 + rng.uniform(0.8, 2.5) * t / dur)    # 泡は音程が上がる
    env = (1 - np.exp(-t / 0.002)) * np.exp(-t / (dur * 0.35))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env


def bubble_cluster(buf, start, rng, count, spread, level):
    p = rng.uniform(-0.6, 0.6)
    for _ in range(count):
        s = start + int(rng.uniform(0, spread) * SR)
        p = float(np.clip(p + rng.normal(0, 0.15), -0.9, 0.9))
        place(buf, s, pan(bubble(rng) * level * rng.uniform(0.4, 1.0), p))


def water_slap(rng, level):
    dur = 0.35
    t = np.arange(int(dur * SR)) / SR
    burst = rng.normal(0, 1, len(t)) * np.exp(-t / 0.035)
    burst = circular_filter(burst, butter(2, [350, 2800], "band", fs=SR,
                                          output="sos"))
    sig = burst / (np.max(np.abs(burst)) + 1e-9)
    for _ in range(rng.integers(2, 5)):  # はねたしずく
        d0 = rng.uniform(0.04, 0.25)
        tt = t[t < 0.03]
        f = rng.uniform(1500, 3200) * (1 + 1.5 * tt / 0.03)
        drop = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.008)
        i = int(d0 * SR)
        sig[i:i + len(drop)] += drop[:len(sig) - i] * 0.4
    return sig * level


def ship_engine(rng, dur, level):
    n = int(dur * SR)
    t = np.arange(n) / SR
    mid = dur / 2
    # 通過に合わせて回転数 (ドップラー) がわずかに下がる
    rate = 7.5 * (1 - 0.04 * np.tanh((t - mid) / 6))
    phase = np.cumsum(rate) / SR
    thump = (0.5 + 0.5 * np.cos(2 * np.pi * phase)) ** 10
    hum = sum(np.sin(2 * np.pi * k * 6 * phase) / k for k in range(1, 6))
    rumble = circular_filter(rng.normal(0, 1, n),
                             butter(2, [30, 180], "band", fs=SR, output="sos"))
    rumble /= np.std(rumble) + 1e-9
    sig = thump * 1.0 + hum * 0.25 + rumble * 0.3 * (0.6 + thump)
    sig = circular_filter(sig, butter(4, 260, "low", fs=SR, output="sos"))
    sig = circular_filter(sig, butter(2, 25, "high", fs=SR, output="sos"))
    sig /= np.max(np.abs(sig)) + 1e-9
    env = np.exp(-0.5 * ((t - mid) / (dur / 5)) ** 2)
    return pan(sig * env * level, np.linspace(-0.8, 0.8, n))


def sonar(level):
    t = np.arange(int(4.0 * SR)) / SR
    ping = np.sin(2 * np.pi * 1180 * t) * np.exp(-t / 0.25) * (1 - np.exp(-t / 0.004))
    out = ping.copy()
    for k, g in enumerate([0.45, 0.22, 0.1], start=1):  # 遠くからの反響
        d = int(k * 1.05 * SR)
        out[d:] += ping[:len(out) - d] * g
    return out * level


def make_sfx(n, loop_sec, depth, seed):
    rng = np.random.default_rng(seed + 1000)
    sfx = np.zeros((n, 2))
    sec = lambda s: int(s * SR) % n
    surface = 1 - depth

    # 波: 帯域を絞ったノイズを、ループ長で割り切れる周期でうねらせる
    if SFX_WAVES:
        noise = rng.normal(0, 1, (n, 2))
        noise = circular_filter(noise, butter(2, [120, 1500], "band", fs=SR,
                                              output="sos"))
        noise /= np.std(noise)
        t = np.arange(n) / SR
        cycles = max(1, round(loop_sec / 7.5))
        swell = 0.35 + 0.65 * np.sin(np.pi * cycles * t / loop_sec) ** 2
        sfx += noise * (swell * surface * SFX_WAVES)[:, None]

    # 水面をたたく音: 海面にいる間だけ、ランダムに
    if SFX_SLAPS:
        for _ in range(int(loop_sec / 4)):
            s = int(rng.uniform(0, n))
            if surface[s] > 0.7 and rng.random() < 0.6:
                sig = water_slap(rng, SFX_SLAPS * rng.uniform(0.5, 1.0))
                place(sfx, s, pan(sig, rng.uniform(-0.7, 0.7)))

    # 泡: 潜る瞬間に大きなかたまり、深いところではときどき
    if SFX_BUBBLES:
        dive = np.argmax(depth > 0.05)
        bubble_cluster(sfx, dive, rng, 45, 3.5, SFX_BUBBLES)
        for _ in range(int(loop_sec / 9)):
            s = int(rng.uniform(0, n))
            if depth[s] > 0.4:
                bubble_cluster(sfx, s, rng, int(rng.integers(3, 12)),
                               rng.uniform(0.4, 1.5), SFX_BUBBLES * 0.8)

    # 船のエンジン: 深海の中ほどで頭上を一度通過
    if SFX_ENGINE:
        deep_idx = np.where(depth > 0.95)[0]
        center = deep_idx[len(deep_idx) // 2] if len(deep_idx) else n // 2
        dur = 36.0
        place(sfx, center - int(dur / 2 * SR), ship_engine(rng, dur, SFX_ENGINE))

    # ソナー: 深海で 2 回、遠くから
    if SFX_SONAR:
        deep_idx = np.where(depth > 0.95)[0]
        if len(deep_idx):
            for frac, p in ((0.2, -0.5), (0.75, 0.4)):
                s = deep_idx[int(len(deep_idx) * frac)]
                place(sfx, s, pan(sonar(SFX_SONAR), p))

    return sfx


def circular_reverb(x, seed, decay=1.4, length=4.0):
    # 指数減衰ノイズをインパルス応答にした簡易リバーブ (FFT で巡回畳み込み)
    rng = np.random.default_rng(seed)
    n = len(x)
    m = int(length * SR)
    t = np.arange(m) / SR
    ir = rng.normal(0, 1, (m, 2)) * np.exp(-t / (decay / 6.9 * 3))[:, None]
    ir = circular_filter(ir, butter(1, 3000, "low", fs=SR, output="sos"))
    ir /= np.sqrt(np.sum(ir ** 2, axis=0))
    out = np.empty_like(x)
    for ch in range(2):
        h = np.zeros(n)
        h[:m] = ir[:, ch]
        out[:, ch] = np.fft.irfft(np.fft.rfft(x[:, ch]) * np.fft.rfft(h), n)
    return out


def wrap_tail(y, n):
    if len(y) < n:
        y = np.pad(y, ((0, n - len(y)), (0, 0)))
    body = y[:n].copy()
    tail = y[n:]
    while len(tail):
        m = min(len(tail), n)
        body[:m] += tail[:m]
        tail = tail[m:]
    return body


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--bpm", type=float, default=BPM)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--transpose", type=int, default=TRANSPOSE)
    ap.add_argument("--soundfont", default=SOUNDFONT)
    ap.add_argument("--out", default="ocean_bgm", help="出力ファイル名 (拡張子なし)")
    args = ap.parse_args()

    out_dir = Path(__file__).resolve().parent
    midi_path = out_dir / f"{args.out}.mid"
    raw_path = out_dir / f"{args.out}_raw.wav"
    wav_path = out_dir / f"{args.out}.wav"
    mp3_path = out_dir / f"{args.out}.mp3"
    sfx_path = out_dir / "ocean_sfx.wav"

    pm, loop_sec, depth_points = build_midi(args.bpm, args.seed, args.transpose)
    pm.write(str(midi_path))
    print(f"MIDI: {midi_path}  ({loop_sec:.1f} 秒)")

    n = int(round(loop_sec * SR))
    music = wrap_tail(render_wav(midi_path, raw_path, args.soundfont), n)
    raw_path.unlink()

    # 深さカーブ (なめらかに)
    pts_t, pts_d = zip(*depth_points)
    tt = np.arange(n) / SR
    depth = np.interp(tt, pts_t, pts_d)
    depth = 0.5 - 0.5 * np.cos(np.pi * depth)

    # 深さに応じて「明るい音」と「こもった音」をクロスフェード
    bright = circular_filter(music, butter(2, SURFACE_LOWPASS_HZ, "low", fs=SR,
                                           output="sos"))
    dark = circular_filter(music, butter(4, DEEP_LOWPASS_HZ, "low", fs=SR,
                                         output="sos"))
    dark *= np.std(bright) / (np.std(dark) + 1e-9) * 0.9
    music = bright * (1 - depth)[:, None] + dark * depth[:, None]
    music = circular_filter(music, butter(2, 30, "high", fs=SR, output="sos"))

    sfx = make_sfx(n, loop_sec, depth, args.seed)
    sfx = sfx * (1 - SFX_REVERB) + circular_reverb(sfx, args.seed) * SFX_REVERB

    mix = music + sfx
    gain = 10 ** (-1 / 20) / np.max(np.abs(mix))
    wavfile.write(wav_path, SR, (mix * gain * 32767).astype(np.int16))
    wavfile.write(sfx_path, SR, (np.clip(sfx * gain, -1, 1) * 32767).astype(np.int16))
    print(f"WAV : {wav_path}")
    print(f"SFX : {sfx_path}")

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path),
                    "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3_path)],
                   check=True)
    print(f"MP3 : {mp3_path}")


if __name__ == "__main__":
    main()
