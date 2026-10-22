#!/usr/bin/env python3
"""深海アンビエント BGM の 30 分版ジェネレーター.

make_ocean.py の音作り (楽器・効果音) をそのまま使い、
「海面 → 浅瀬 → 潜水 → 中層 → 深海 → 深淵 → 浮上 → 海面へ」の 8 章で
約 30 分かけて潜って戻ってくる 1 曲を作る. 章ごとにコード進行・楽器・深さ・
効果音の頻度を変えて、長く聴いても単調にならないようにしている.

使い方:
    python3 make_ocean_long.py               # 音声 + YouTube 用 MP4
    python3 make_ocean_long.py --no-video    # 音声だけ
    python3 make_ocean_long.py --seed 5      # 別テイク

出力: ocean_long.mid / ocean_long.wav / ocean_long.mp3 / ocean_long.mp4 / ocean_cover.png
"""
import argparse
import random
import subprocess
from pathlib import Path

import numpy as np
import pretty_midi
from scipy.io import wavfile
from scipy.signal import butter, sosfiltfilt

from make_bgm import SR, render_wav
from make_ocean import (CHORDS, DEEP_LOWPASS_HZ, SFX_BUBBLES, SFX_ENGINE,
                        SFX_REVERB, SFX_SLAPS, SFX_SONAR, SFX_WAVES,
                        SOUNDFONT, SURFACE_LOWPASS_HZ, VIBES_SCALE,
                        bubble_cluster, circular_reverb, pan, place,
                        ship_engine, sonar, water_slap, wrap_tail)

# ---------------------------------------------------------------------------
# パラメータ
# ---------------------------------------------------------------------------
BPM = 60
SEED = 11
TRANSPOSE = 0
HUMANIZE_MS = 25
BARS_PER_CHORD = 2

PROG_PAD = 94          # Pad 7 (halo)
PROG_BASS = 35         # Fretless Bass
PROG_VIBES = 11        # Vibraphone
PROG_CELESTA = 8       # Celesta (浅瀬のきらめき)
PROG_CHOIR = 52        # Choir Aahs
PROG_DRONE = 89        # Pad 2 (warm) (深淵の低いうなり)

VEL_PAD = 50
VEL_BASS = 70
VEL_VIBES = 58
VEL_CELESTA = 50
VEL_CHOIR = 36
VEL_DRONE = 44

# 3 分版のコードに、浅瀬用の明るいコードを追加
CHORDS = dict(CHORDS, **{
    "Fmaj9": (41, [52, 57, 60, 67]),
    "Cadd9": (36, [50, 55, 60, 64]),
    "Am9":   (33, [55, 59, 60, 64]),
})

PROG_SURFACE = ["Dm9", "Bbmaj7#11", "Gm9", "A7sus4b9"]
PROG_SHALLOW = ["Fmaj9", "Cadd9", "Gm9", "Dm9"]
PROG_MID = ["Dm9", "Bbmaj7#11", "Ebmaj7#11", "A7sus4b9"]
PROG_DEEP = ["Ebmaj7#11", "Dm9", "Cmaj7#11", "Bbmaj7"]
PROG_ABYSS = ["Dm9", "Ebmaj7#11", "Bbmaj7#11", "Ebmaj7#11"]
PROG_ASCENT = ["Bbmaj7#11", "Cmaj7#11", "Dm9", "Am9"]
PROG_END = ["Dm9", "A7sus4b9"]   # 冒頭の Dm9 に戻るつなぎ

# 章: (名前, 進行, 繰り返し, パート, 深さ 開始→終了 (0=海面, 1=深海))
# 1 周 = 4 コード × 2 小節 × 4 秒 = 32 秒 (60 BPM)
CHAPTERS = [
    ("surface", PROG_SURFACE, 5, {"pad", "vibes"},                      (0.0, 0.0)),
    ("shallow", PROG_SHALLOW, 7, {"pad", "bass", "celesta", "vibes_sparse"}, (0.0, 0.25)),
    ("descent", PROG_SURFACE, 5, {"pad", "bass", "vibes"},              (0.25, 0.6)),
    ("mid",     PROG_MID,     8, {"pad", "bass", "vibes", "choir_late"}, (0.6, 0.6)),
    ("deep",    PROG_DEEP,    9, {"pad", "bass", "vibes_low"},          (0.6, 1.0)),
    ("abyss",   PROG_ABYSS,   9, {"pad", "bass", "drone", "choir", "vibes_sparse_low"}, (1.0, 1.0)),
    ("ascent",  PROG_ASCENT,  7, {"pad", "bass", "vibes", "choir"},     (1.0, 0.2)),
    ("return",  PROG_SURFACE, 5, {"pad", "vibes", "celesta"},           (0.2, 0.0)),
    ("end",     PROG_END,     1, {"pad", "vibes"},                      (0.0, 0.0)),
]


def build_midi(bpm, seed, transpose):
    rng = random.Random(seed)
    beat = 60.0 / bpm
    bar = beat * 4
    clen = BARS_PER_CHORD * bar
    hum = HUMANIZE_MS / 1000.0

    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    pad = pretty_midi.Instrument(PROG_PAD, name="Pad")
    bass = pretty_midi.Instrument(PROG_BASS, name="Fretless Bass")
    vibes = pretty_midi.Instrument(PROG_VIBES, name="Vibraphone")
    celesta = pretty_midi.Instrument(PROG_CELESTA, name="Celesta")
    choir = pretty_midi.Instrument(PROG_CHOIR, name="Choir")
    drone = pretty_midi.Instrument(PROG_DRONE, name="Drone")

    def add(inst, pitch, start, dur, vel, jitter=hum):
        start = max(0.0, start + rng.uniform(-jitter, jitter))
        vel = int(np.clip(vel + rng.randint(-6, 6), 1, 127))
        inst.notes.append(
            pretty_midi.Note(vel, pitch + transpose, start, start + dur))

    def sprinkle(inst, t, voicing, counts, octave, vel, dur):
        # コードの構成音寄りに、まばらに音を置く
        count = rng.choice(counts)
        chord_pcs = {p % 12 for p in voicing}
        pool = [p for p in VIBES_SCALE if (p % 12) in chord_pcs] or VIBES_SCALE
        for s in sorted(rng.sample(range(BARS_PER_CHORD * 4), count)):
            pitch = rng.choice(pool if rng.random() < 0.7 else VIBES_SCALE)
            add(inst, pitch + octave, t + s * beat + 0.1, dur, vel)

    t = 0.0
    depth_points = []
    chapters = []
    for name, prog, reps, parts, (d0, d1) in CHAPTERS:
        start = t
        total = reps * len(prog)
        for i in range(total):
            cname = prog[i % len(prog)]
            root, voicing = CHORDS[cname]
            late = i >= total // 2  # 章の後半

            if "pad" in parts:
                for p in voicing:
                    add(pad, p, t, clen + 0.3, VEL_PAD, jitter=0)
            if "bass" in parts:
                add(bass, root, t + 0.05, clen * 0.95, VEL_BASS)
            if "drone" in parts:
                for p in (root + 12, root + 19):
                    add(drone, p, t, clen + 0.3, VEL_DRONE, jitter=0)
            if "choir" in parts or ("choir_late" in parts and late):
                for p in voicing[1:]:
                    add(choir, p + 12, t, clen + 0.3, VEL_CHOIR, jitter=0)

            if "vibes" in parts:
                sprinkle(vibes, t, voicing, [1, 2, 2, 3], 0, VEL_VIBES, beat * 3)
            if "vibes_sparse" in parts and rng.random() < 0.5:
                sprinkle(vibes, t, voicing, [1, 2], 0, VEL_VIBES - 6, beat * 3)
            if "vibes_low" in parts:
                sprinkle(vibes, t, voicing, [1, 1, 2], -12, VEL_VIBES - 10, beat * 3)
            if "vibes_sparse_low" in parts and rng.random() < 0.35:
                sprinkle(vibes, t, voicing, [1], -12, VEL_VIBES - 12, beat * 4)
            if "celesta" in parts:
                sprinkle(celesta, t, voicing, [0, 1, 2, 3], 12, VEL_CELESTA, beat * 2)
            t += clen
        depth_points += [(start, d0), (t, d1)]
        chapters.append((name, start, t))

    pm.instruments.extend([pad, bass, vibes, celesta, choir, drone])
    return pm, t, depth_points, chapters


# ---------------------------------------------------------------------------
# 長尺用の処理: 全体を 3 周分つなぐとメモリが足りないので、前後数秒だけ巡回させる
# ---------------------------------------------------------------------------
def wrap_filter(x, sos, pad_sec=3.0):
    p = int(pad_sec * SR)
    y = sosfiltfilt(sos, np.concatenate([x[-p:], x, x[:p]]), axis=0)
    return y[p:-p]


def make_sfx(n, loop_sec, depth, chapters, seed):
    rng = np.random.default_rng(seed + 1000)
    sfx = np.zeros((n, 2))
    at = {name: (int(s * SR), int(e * SR)) for name, s, e in chapters}
    surface = 1 - depth

    # 波 (海面にいる間だけ)
    noise = rng.normal(0, 1, (n, 2))
    noise = wrap_filter(noise, butter(2, [120, 1500], "band", fs=SR, output="sos"))
    noise /= np.std(noise)
    t = np.arange(n) / SR
    cycles = max(1, round(loop_sec / 7.5))
    swell = 0.35 + 0.65 * np.sin(np.pi * cycles * t / loop_sec) ** 2
    sfx += noise * (swell * surface * SFX_WAVES)[:, None]
    del noise, swell, t

    # 水面をたたく音
    for _ in range(int(loop_sec / 4)):
        s = int(rng.uniform(0, n))
        if surface[s] > 0.7 and rng.random() < 0.6:
            sig = water_slap(rng, SFX_SLAPS * rng.uniform(0.5, 1.0))
            place(sfx, s, pan(sig, rng.uniform(-0.7, 0.7)))

    # 泡: 潜る瞬間と浮上の瞬間に大きなかたまり、水中ではときどき
    bubble_cluster(sfx, at["descent"][0], rng, 45, 3.5, SFX_BUBBLES)
    bubble_cluster(sfx, at["ascent"][0], rng, 60, 6.0, SFX_BUBBLES * 0.9)
    for _ in range(int(loop_sec / 9)):
        s = int(rng.uniform(0, n))
        if depth[s] > 0.3 and rng.random() < 0.7:
            bubble_cluster(sfx, s, rng, int(rng.integers(3, 12)),
                           rng.uniform(0.4, 1.5), SFX_BUBBLES * 0.8)

    # 船のエンジン: 中層で遠くを 1 回、深淵で頭上を 1 回
    dur = 36.0
    for name, level in (("mid", SFX_ENGINE * 0.55), ("abyss", SFX_ENGINE)):
        s, e = at[name]
        place(sfx, (s + e) // 2 - int(dur / 2 * SR), ship_engine(rng, dur, level))

    # ソナー: 深海と深淵で 2 回ずつ
    for name in ("deep", "abyss"):
        s, e = at[name]
        for frac, p in ((0.25, -0.5), (0.7, 0.4)):
            place(sfx, s + int((e - s) * frac), pan(sonar(SFX_SONAR), p))

    return sfx


# ---------------------------------------------------------------------------
# YouTube 用の静止画 (深海のグラデーション + 光の筋 + 泡)
# ---------------------------------------------------------------------------
def make_cover(path, seed, w=1920, h=1080):
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    top = np.array([28, 92, 120]) / 255
    bottom = np.array([2, 8, 20]) / 255
    k = y ** 0.8
    img = top * (1 - k[..., None]) + bottom * k[..., None]
    img = np.broadcast_to(img, (h, w, 3)).copy()

    # 海面から差し込む光の筋
    rays = np.zeros((h, w))
    for _ in range(9):
        cx = rng.uniform(0.15, 0.85)
        slope = rng.uniform(-0.25, 0.25)
        width = rng.uniform(0.01, 0.04)
        d = np.abs(x - (cx + slope * y))
        rays += np.exp(-(d / width) ** 2) * rng.uniform(0.3, 1.0)
    rays *= np.exp(-y / 0.45)
    img += rays[..., None] * np.array([0.10, 0.22, 0.24])

    # 泡
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(40):
        bx, by = rng.uniform(0, w), rng.uniform(h * 0.25, h)
        r = rng.uniform(2, 9)
        ring = np.exp(-((np.hypot(xx - bx, yy - by) - r) / 1.2) ** 2)
        img += ring[..., None] * np.array([0.25, 0.4, 0.45]) * (1.1 - by / h)

    img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                    "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-i", "-", str(path)],
                   input=img.tobytes(), check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--bpm", type=float, default=BPM)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--transpose", type=int, default=TRANSPOSE)
    ap.add_argument("--soundfont", default=SOUNDFONT)
    ap.add_argument("--out", default="ocean_long", help="出力ファイル名 (拡張子なし)")
    ap.add_argument("--no-video", action="store_true", help="MP4 を作らない")
    args = ap.parse_args()

    out_dir = Path(__file__).resolve().parent
    midi_path = out_dir / f"{args.out}.mid"
    raw_path = out_dir / f"{args.out}_raw.wav"
    wav_path = out_dir / f"{args.out}.wav"
    mp3_path = out_dir / f"{args.out}.mp3"
    mp4_path = out_dir / f"{args.out}.mp4"
    cover_path = out_dir / "ocean_cover.png"

    pm, loop_sec, depth_points, chapters = build_midi(
        args.bpm, args.seed, args.transpose)
    pm.write(str(midi_path))
    print(f"MIDI: {midi_path}  ({loop_sec / 60:.1f} 分)")
    for name, s, e in chapters:
        print(f"  {int(s // 60):2d}:{int(s % 60):02d}  {name}")

    n = int(round(loop_sec * SR))
    music = wrap_tail(render_wav(midi_path, raw_path, args.soundfont), n)
    raw_path.unlink()

    pts_t, pts_d = zip(*depth_points)
    depth = np.interp(np.arange(n) / SR, pts_t, pts_d)
    depth = 0.5 - 0.5 * np.cos(np.pi * depth)

    bright = wrap_filter(music, butter(2, SURFACE_LOWPASS_HZ, "low", fs=SR,
                                       output="sos"))
    dark = wrap_filter(music, butter(4, DEEP_LOWPASS_HZ, "low", fs=SR,
                                     output="sos"))
    del music
    dark *= np.std(bright) / (np.std(dark) + 1e-9) * 0.9
    bright *= (1 - depth)[:, None]
    bright += dark * depth[:, None]
    del dark
    mix = wrap_filter(bright, butter(2, 30, "high", fs=SR, output="sos"))
    del bright

    sfx = make_sfx(n, loop_sec, depth, chapters, args.seed)
    sfx = sfx * (1 - SFX_REVERB) + circular_reverb(sfx, args.seed) * SFX_REVERB
    mix += sfx
    del sfx

    mix *= 10 ** (-1 / 20) / np.max(np.abs(mix))
    wavfile.write(wav_path, SR, (mix * 32767).astype(np.int16))
    del mix
    print(f"WAV : {wav_path}")

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path),
                    "-codec:a", "libmp3lame", "-b:a", "192k", str(mp3_path)],
                   check=True)
    print(f"MP3 : {mp3_path}")

    if not args.no_video:
        make_cover(cover_path, args.seed)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-loop", "1", "-framerate", "1", "-i", str(cover_path),
                        "-i", str(wav_path),
                        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium",
                        "-pix_fmt", "yuv420p", "-r", "24",
                        "-c:a", "aac", "-b:a", "256k", "-shortest",
                        "-movflags", "+faststart", str(mp4_path)], check=True)
        print(f"MP4 : {mp4_path}")


if __name__ == "__main__":
    main()
