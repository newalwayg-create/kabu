#!/usr/bin/env python3
"""コンセプト設定 (concepts.py) から、動画 1 本分の素材をまとめて作る.

    MIDI → FluidSynth で音声化 → 深さ (こもり具合) の演出 → 効果音を重ねる
    → WAV / MP3 / MP4 (静止画 + 音声) / サムネイル / タイトルと説明文 (meta.md)

数時間の長尺でもメモリに収まるよう、音声は 30 秒ずつ区切って処理する.

使い方:
    python3 make_room.py rain                 # concepts.py の RAIN を作る
    python3 make_room.py ocean_sleep --minutes 10 --no-video   # 短く試す
出力: out/<名前>/
"""
import argparse
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pretty_midi
from PIL import Image
from scipy.io import wavfile
from scipy.signal import butter, oaconvolve, sosfilt

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "youtube")]

from make_bgm import SR, add_note  # noqa: E402
from make_ocean import bubble_cluster, pan  # noqa: E402
from make_thumbnails import SANS_BOLD, SANS_LIGHT, SANS_MED, SERIF, draw_text  # noqa: E402

from concepts import CONCEPTS  # noqa: E402
from scenes import SCENES  # noqa: E402

SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
CHUNK = SR * 30
HUMANIZE_MS = 25


# ---------------------------------------------------------------------------
# 1. 曲 (MIDI)
# ---------------------------------------------------------------------------
def build_midi(cfg, minutes, seed):
    rng = random.Random(seed)
    beat = 60.0 / cfg["bpm"]
    clen = cfg["bars_per_chord"] * 4 * beat
    hum = HUMANIZE_MS / 1000.0
    pm = pretty_midi.PrettyMIDI(initial_tempo=cfg["bpm"])
    insts = {}

    def inst(name):
        if name not in insts:
            insts[name] = pretty_midi.Instrument(cfg["parts"][name]["prog"], name=name)
        return insts[name]

    last = {}

    def add(name, pitch, start, dur, vel, jitter=hum):
        start = max(0.0, start + rng.uniform(-jitter, jitter))
        vel = int(np.clip(vel + rng.randint(-6, 6), 1, 127))
        add_note(inst(name), pretty_midi.Note(vel, int(pitch), start, start + dur), last)

    total_w = sum(ch["weight"] for ch in cfg["chapters"])
    t = 0.0
    chapters, dark_points = [], []
    for ch in cfg["chapters"]:
        cycle = len(ch["prog"]) * clen
        reps = max(1, round(minutes * 60 * ch["weight"] / total_w / cycle))
        start = t
        total = reps * len(ch["prog"])
        for i in range(total):
            root, voicing = cfg["chords"][ch["prog"][i % len(ch["prog"])]]
            late = i >= total // 2
            for token in ch["parts"]:
                name, _, when = token.partition("@")
                if when == "late" and not late:
                    continue
                p = cfg["parts"][name]
                kind, vel, octv = p["kind"], p["vel"], p.get("octave", 0)
                if kind == "sustain":
                    notes = voicing[1:] if p.get("drop_root") else voicing
                    for n in notes:
                        add(name, n + octv, t, clen + 0.3, vel, jitter=0)
                elif kind == "bass":
                    add(name, root + octv, t + 0.05, clen * 0.95, vel)
                elif kind == "drone":
                    for n in (root + 12, root + 19):
                        add(name, n + octv, t, clen + 0.3, vel, jitter=0)
                elif kind == "arp":
                    step = p.get("step", 1.0) * beat
                    seq = voicing + voicing[-2:0:-1]
                    k, pos = 0, 0.0
                    while pos < clen - step * 0.5:
                        if rng.random() > 0.15:  # たまに休んで息をつく
                            accent = 6 if k % len(seq) == 0 else 0
                            add(name, seq[k % len(seq)] + octv, t + pos, step * 2.5, vel + accent)
                        k += 1
                        pos += step
                elif kind == "comp":
                    for j, n in enumerate(voicing):
                        add(name, n + octv, t + beat * 0.06 + j * 0.02, clen * 0.6, vel)
                    if rng.random() < 0.5:
                        for j, n in enumerate(voicing[1:]):
                            add(name, n + octv, t + clen * 0.625 + j * 0.02, clen * 0.3, vel - 12)
                elif kind == "sprinkle":
                    if rng.random() > p.get("prob", 1.0):
                        continue
                    count = rng.choice(p["counts"])
                    pcs = {n % 12 for n in voicing}
                    scale = cfg["scale"]
                    pool = [n for n in scale if n % 12 in pcs] or scale
                    slots = cfg["bars_per_chord"] * 4
                    for s in sorted(rng.sample(range(slots), min(count, slots))):
                        pitch = rng.choice(pool if rng.random() < 0.7 else scale)
                        add(name, pitch + octv, t + s * beat + 0.1, beat * p.get("dur", 3), vel)
            t += clen
        chapters.append((ch["label"], start, t))
        dark_points += [(start, ch["dark"][0]), (t, ch["dark"][1])]

    pm.instruments.extend(insts.values())
    return pm, t, chapters, dark_points


def render(midi_path, wav_path):
    subprocess.run(["fluidsynth", "-ni", "-g", "0.45", "-r", str(SR), "-F", str(wav_path),
                    SOUNDFONT, str(midi_path)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------------------
# 2. 効果音 (区切って生成できるよう、フィルタの状態を持ち越す)
# ---------------------------------------------------------------------------
class Filtered:
    """ノイズやインパルスを、チャンクをまたいで連続したフィルタに通す."""

    def __init__(self, sos):
        self.sos = sos
        self.zi = np.zeros((sos.shape[0], 2, 2))

    def __call__(self, x):
        y, self.zi = sosfilt(self.sos, x, axis=0, zi=self.zi)
        return y


def bp(lo, hi, order=2):
    return butter(order, [lo, hi], "band", fs=SR, output="sos")


def lp(f, order=2):
    return butter(order, f, "low", fs=SR, output="sos")


def slow_curve(rng, periods=(37, 83, 151)):
    """ゆっくり揺れる -1..1 の曲線 (風の強弱・雨の強さなど)."""
    ph = rng.uniform(0, 2 * np.pi, len(periods))

    def f(t):
        return sum(np.sin(2 * np.pi * t / p + q) for p, q in zip(periods, ph)) / len(periods)
    return f


def noise_gain(sos, rng):
    """フィルタ後のノイズの標準偏差が 1 になる倍率."""
    return 1.0 / np.std(sosfilt(sos, rng.normal(0, 1, SR * 4)))


class Bed:
    """途切れずに鳴り続ける環境音 (雨・風・波・暖炉)."""

    def __init__(self, spec, rng, dark_fn):
        self.rng, self.level, self.dark = rng, spec["level"], dark_fn
        kind = spec["type"]
        self.kind = kind
        if kind == "rain":
            self.hiss = Filtered(bp(700, 9000)); self.g_hiss = noise_gain(bp(700, 9000), rng)
            self.pat = Filtered(bp(1500, 7000)); self.roof = Filtered(lp(380))
            self.g_roof = noise_gain(lp(380), rng)
            self.curve = slow_curve(rng, (53, 131, 307))
        elif kind == "wind":
            self.low = Filtered(bp(80, 420)); self.g_low = noise_gain(bp(80, 420), rng)
            self.mid = Filtered(bp(380, 1300)); self.g_mid = noise_gain(bp(380, 1300), rng)
            self.curve = slow_curve(rng, (17, 41, 97))
        elif kind == "fire":
            self.roar = Filtered(lp(260)); self.g_roar = noise_gain(lp(260), rng)
            self.crk = Filtered(bp(1200, 6000)); self.pop = Filtered(bp(250, 1400))
        elif kind == "waves":
            self.w = Filtered(bp(120, 1500)); self.g_w = noise_gain(bp(120, 1500), rng)
        else:
            raise ValueError(kind)

    def __call__(self, t):
        n = len(t)
        r = self.rng
        if self.kind == "rain":
            inten = 0.78 + 0.22 * self.curve(t)
            hiss = self.hiss(r.normal(0, 1, (n, 2))) * self.g_hiss
            imp = (r.random((n, 2)) < 400 / SR) * np.minimum(r.pareto(3.0, (n, 2)), 4) * 6
            patter = self.pat(imp)
            roof = self.roof(r.normal(0, 1, (n, 2))) * self.g_roof
            out = hiss * 0.55 + patter * 0.9 + roof * 0.25
            return out * (inten * self.level)[:, None]
        if self.kind == "wind":
            g = 0.5 + 0.5 * self.curve(t)
            low = self.low(r.normal(0, 1, (n, 2))) * self.g_low
            mid = self.mid(r.normal(0, 1, (n, 2))) * self.g_mid
            out = low * (0.5 + 0.5 * g)[:, None] + mid * (0.15 + 0.6 * g ** 2)[:, None]
            return out * self.level
        if self.kind == "fire":
            roar = self.roar(r.normal(0, 1, (n, 2))) * self.g_roar * 0.35
            crk = self.crk((r.random((n, 2)) < 9 / SR) * np.minimum(r.pareto(1.6, (n, 2)), 8) * 2.5)
            pop = self.pop((r.random((n, 2)) < 0.25 / SR) * r.uniform(8, 20, (n, 2)))
            return (roar + crk + pop) * self.level
        if self.kind == "waves":
            swell = 0.35 + 0.65 * np.sin(np.pi * t / 7.7) ** 2
            surface = 1 - self.dark(t)
            return self.w(r.normal(0, 1, (n, 2))) * self.g_w * (swell * surface * self.level)[:, None]


def thunder(rng, level):
    dur = rng.uniform(7, 12)
    n = int(dur * SR)
    t = np.arange(n) / SR
    rumble = np.cumsum(rng.normal(0, 1, n))
    rumble = sosfilt(bp(25, 160), rumble)
    rumble /= np.max(np.abs(rumble)) + 1e-9
    env = np.zeros(n)
    for _ in range(rng.integers(2, 5)):  # 何度か重なって転がる
        t0 = rng.uniform(0, dur * 0.4)
        env += np.clip((t - t0) / 0.6, 0, 1) * np.exp(-np.clip(t - t0, 0, None) / rng.uniform(1.5, 3.5))
    env /= env.max() + 1e-9
    return pan(rumble * env * level, rng.uniform(-0.6, 0.6))


def drip(rng, level):
    t = np.arange(int(0.25 * SR)) / SR
    f = rng.uniform(900, 1700) * (1 - 0.25 * t / 0.25)
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.03) * (1 - np.exp(-t / 0.002))
    return pan(sig * level * rng.uniform(0.5, 1.0), rng.uniform(-0.8, 0.8))


def make_events(cfg, total_n, rng, dark_fn):
    """一回きりの効果音 (雷・しずく・泡) を (開始位置, ステレオ配列) のリストで返す."""
    events = []
    total_s = total_n / SR
    for spec in cfg["sfx"]:
        kind = spec["type"]
        if kind not in ("thunder", "drips", "bubbles"):
            continue
        t = rng.uniform(*spec["every"])
        while t < total_s - 15:
            s = int(t * SR)
            if kind == "thunder":
                events.append((s, thunder(rng, spec["level"])))
            elif kind == "drips":
                events.append((s, drip(rng, spec["level"])))
            elif kind == "bubbles" and dark_fn(np.array([t]))[0] >= spec.get("min_dark", 0):
                buf = np.zeros((int(2.5 * SR), 2))
                bubble_cluster(buf, 0, rng, int(rng.integers(3, 9)), 1.2, spec["level"])
                events.append((s, buf))
            t += rng.uniform(*spec["every"])
    return sorted(events, key=lambda e: e[0])


def reverb_ir(rng, decay=1.4, length=3.0):
    m = int(length * SR)
    t = np.arange(m) / SR
    ir = rng.normal(0, 1, (m, 2)) * np.exp(-t / (decay / 6.9 * 3))[:, None]
    ir = sosfilt(lp(3000, 1), ir, axis=0)
    return ir / np.sqrt(np.sum(ir ** 2, axis=0))


# ---------------------------------------------------------------------------
# 3. 区切って処理して書き出す
# ---------------------------------------------------------------------------
TARGET_RMS_DB = -20.0
# 効果音の level は「曲の音量がこの値 (RMS) のとき」の大きさ. 曲の音量に合わせて自動で拡縮する
REF_MUSIC_RMS = 0.05


def soft_limit(x, knee=0.8):
    """knee を超えた分だけを tanh でなめらかに抑え、±1 を超えないようにする."""
    a = np.abs(x)
    over = a > knee
    y = x.copy()
    y[over] = np.sign(x[over]) * (knee + (1 - knee) * np.tanh((a[over] - knee) / (1 - knee)))
    return y


def process(cfg, raw_wav, out_wav, dark_points, seed, fade_in=4.0, fade_out=10.0):
    rng = np.random.default_rng(seed + 1000)
    _, raw = wavfile.read(raw_wav, mmap=True)
    n = len(raw)

    pts_t, pts_d = zip(*dark_points)

    def dark_fn(t):
        d = np.interp(t, pts_t, pts_d)
        return 0.5 - 0.5 * np.cos(np.pi * d)

    bright_hz, dark_hz = cfg["lowpass"]
    f_bright, f_dark = Filtered(lp(bright_hz, 2)), Filtered(lp(dark_hz, 4))
    f_hp = Filtered(butter(2, 30, "high", fs=SR, output="sos"))
    # こもらせた音の音量を、明るい音にそろえる倍率 (曲の中ほど 60 秒で測る)
    mid = n // 2
    probe = raw[mid:mid + SR * 60].astype(float) / 32768
    bright_probe = sosfilt(lp(bright_hz, 2), probe, axis=0)
    dark_gain = np.std(bright_probe) / (np.std(sosfilt(lp(dark_hz, 4), probe, axis=0)) + 1e-9) * 0.9
    sfx_scale = np.sqrt(np.mean(bright_probe ** 2)) / REF_MUSIC_RMS

    beds = [Bed(s, rng, dark_fn) for s in cfg["sfx"] if s["type"] in ("rain", "wind", "fire", "waves")]
    events = make_events(cfg, n, rng, dark_fn)
    wet = cfg.get("sfx_reverb", 0.0)
    ir = reverb_ir(rng) if wet else None
    tail = np.zeros((len(ir) - 1, 2)) if wet else None

    tmp = np.lib.format.open_memmap(str(out_wav) + ".f32.npy", mode="w+", dtype=np.float32, shape=(n, 2))
    sq = {"music": 0.0, "beds": 0.0, "events": 0.0, "mix": 0.0}
    ev_i = 0
    for s in range(0, n, CHUNK):
        e = min(s + CHUNK, n)
        t = np.arange(s, e) / SR
        x = raw[s:e].astype(float) / 32768
        d = dark_fn(t)[:, None]
        music = f_bright(x) * (1 - d) + f_dark(x) * dark_gain * d
        music = f_hp(music)

        sfx = np.zeros_like(music)
        for b in beds:
            sfx += b(t)
        sfx *= sfx_scale
        ev = np.zeros_like(music)
        while ev_i < len(events) and events[ev_i][0] + len(events[ev_i][1]) < s:
            ev_i += 1
        for st, sig in events[ev_i:]:
            if st >= e:
                break
            a, b2 = max(st, s), min(st + len(sig), e)
            if b2 > a:
                ev[a - s:b2 - s] += sig[a - st:b2 - st]
        if wet:
            # 前のチャンクの残響の続きを足し、はみ出た分を次へ持ち越す
            full = np.stack([oaconvolve(ev[:, c], ir[:, c]) for c in range(2)], axis=1)
            full[:len(tail)] += tail
            rev, tail = full[:e - s], full[e - s:].copy()
            ev = ev * (1 - wet) + rev * wet
        ev *= sfx_scale
        y = music + sfx + ev
        for k, v in (("music", music), ("beds", sfx), ("events", ev), ("mix", y)):
            sq[k] += float(np.sum(v ** 2))
        # フェードイン・アウト
        fi = np.clip(t / fade_in, 0, 1)
        fo = np.clip((n / SR - t) / fade_out, 0, 1)
        y *= (fi * fo)[:, None]
        tmp[s:e] = y
    tmp.flush()

    db = {k: 10 * np.log10(v / (2 * n) + 1e-20) for k, v in sq.items()}
    print("levels (dB, before gain): " + ", ".join(f"{k} {v:.1f}" for k, v in db.items()), flush=True)
    gain = 10 ** ((TARGET_RMS_DB - db["mix"]) / 20)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        for s in range(0, n, CHUNK):
            w.writeframes((soft_limit(tmp[s:s + CHUNK] * gain) * 32767).astype("<i2").tobytes())
    del tmp
    Path(str(out_wav) + ".f32.npy").unlink()
    return n / SR


# ---------------------------------------------------------------------------
# 4. サムネイル・動画・説明文
# ---------------------------------------------------------------------------
def to_image(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))


def make_images(cfg, out, seed):
    scene = SCENES[cfg["scene"]]
    still = to_image(scene(1920, 1080, seed))
    still.save(out / "video_still.png")
    base = to_image(scene(1280, 720, seed))
    main = base.copy()
    draw_text(main, cfg["word"], SERIF, 150, 720 * 0.46, spacing=0.02)
    draw_text(main, cfg["subtitle"], SANS_LIGHT, 22, 720 * 0.60, spacing=0.45, alpha=200)
    main.save(out / "thumb_serif.png")
    bold = base.copy()
    draw_text(bold, cfg["word"], SANS_BOLD, 220, 720 * 0.45, spacing=-0.01)
    draw_text(bold, cfg["subtitle"], SANS_MED, 34, 720 * 0.65, spacing=0.3, alpha=220)
    bold.save(out / "thumb_bold.png")


SEG_SEC = 60


def make_video(out, name, wav, length):
    seg = out / "_still.mp4"
    # 静止画なので、キーフレームは区切り (60 秒) ごとに 1 枚だけにしてファイルを小さくする
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "24", "-t", str(SEG_SEC),
                    "-i", str(out / "video_still.png"), "-c:v", "libx264", "-tune", "stillimage",
                    "-crf", "26", "-g", str(SEG_SEC * 24), "-pix_fmt", "yuv420p", "-r", "24", str(seg)], check=True)
    # 区切りの静止画動画を必要な回数だけ繰り返し、音声の長さで切る
    # (-stream_loop -1 と -shortest の組み合わせは映像のコピー時に止まらないことがある)
    loops = int(np.ceil(length / SEG_SEC)) + 1
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", str(loops), "-i", str(seg),
                    "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-t", f"{length:.3f}", "-movflags", "+faststart",
                    str(out / f"{name}.mp4")], check=True)
    seg.unlink()


def ts(sec):
    sec = int(sec)
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def write_meta(cfg, out, chapters, length):
    merged = []
    for label, s, _ in chapters:
        if not merged or merged[-1][0] != label:
            merged.append((label, s))
    lines = [f"# {cfg['word']}  ({ts(length)})", "",
             "## Title (main)", "", f"`{cfg['title']}`", "",
             "## Title (alternatives for Test & Compare)", ""]
    lines += [f"- `{t}`" for t in cfg["alt_titles"]]
    lines += ["", "## Thumbnails", "", "- `thumb_serif.png` (main, H1-H3 style)",
              "- `thumb_bold.png` (bold text, for H4)", "",
              "## Description", "", "```", cfg["lead"], cfg["use_line"], "", "Chapters"]
    lines += [f"{ts(s)} {label}" for label, s in merged]
    lines += ["", cfg["credits"], "", cfg["tags"], "```", ""]
    (out / "meta.md").write_text("\n".join(lines), encoding="utf-8")


def video_only(concept):
    """音声は作り直さず、out/ にある WAV と静止画から MP4 だけ作る."""
    out = HERE / "out" / concept
    wav = out / f"{concept}.wav"
    with wave.open(str(wav)) as w:
        length = w.getnframes() / w.getframerate()
    make_video(out, concept, wav, length)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("concept", choices=sorted(CONCEPTS))
    ap.add_argument("--minutes", type=float, help="長さを上書き (試し用)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--video-only", action="store_true", help="既存の WAV から MP4 だけ作る")
    args = ap.parse_args()
    if args.video_only:
        video_only(args.concept)
        return

    cfg = CONCEPTS[args.concept]
    minutes = args.minutes or cfg["minutes"]
    out = HERE / "out" / args.concept
    out.mkdir(parents=True, exist_ok=True)
    name = args.concept

    pm, music_len, chapters, dark_points = build_midi(cfg, minutes, args.seed)
    pm.write(str(out / f"{name}.mid"))
    print(f"MIDI  {music_len / 60:.1f} min", flush=True)
    raw = out / "_raw.wav"
    render(out / f"{name}.mid", raw)
    print("rendered", flush=True)
    length = process(cfg, raw, out / f"{name}.wav", dark_points, args.seed,
                     fade_out=cfg.get("fade_out", 10.0))
    raw.unlink()
    print(f"WAV   {ts(length)}", flush=True)
    if minutes <= 60:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out / f"{name}.wav"),
                        "-codec:a", "libmp3lame", "-b:a", "192k", str(out / f"{name}.mp3")], check=True)
    make_images(cfg, out, args.seed)
    write_meta(cfg, out, chapters, length)
    if not args.no_video:
        make_video(out, name, out / f"{name}.wav", length)
    print(f"done  {out}", flush=True)


if __name__ == "__main__":
    main()
