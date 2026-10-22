"""コンセプトごとの情景 (サムネイルと動画の背景). すべて 0..1 の float RGB 配列を返す."""
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

from make_thumbnails import add_bubbles, underwater_scene


def _grid(w, h):
    return np.linspace(0, 1, h)[:, None], np.linspace(0, 1, w)[None, :]


def _vignette_grain(img, rng, strength=0.5):
    h, w = img.shape[:2]
    y, x = _grid(w, h)
    v = 1 - strength * (((x - 0.5) / 0.75) ** 2 + ((y - 0.5) / 0.85) ** 2)
    img = img * np.clip(v, 0, 1)[..., None]
    return np.clip(img + rng.normal(0, 0.007, img.shape), 0, 1)


def _soft_disks(h, w, rng, count, rmin, rmax, colors, alpha, blur, yrange=(0, 1)):
    layer = np.zeros((h, w, 3))
    for _ in range(count):
        r = rng.uniform(rmin, rmax)
        cx, cy = rng.uniform(0, w), rng.uniform(*yrange) * h
        x0, x1 = int(max(cx - r - 2, 0)), int(min(cx + r + 2, w))
        y0, y1 = int(max(cy - r - 2, 0)), int(min(cy + r + 2, h))
        if x1 <= x0 or y1 <= y0:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        disk = np.clip(r + 0.5 - np.hypot(xx - cx, yy - cy), 0, 1)
        c = np.array(colors[rng.integers(len(colors))]) / 255
        layer[y0:y1, x0:x1] += disk[..., None] * c * rng.uniform(*alpha)
    return gaussian_filter(layer, (blur, blur, 0))


def rain_window(w, h, seed):
    """夜、雨粒のついた窓越しにぼやけた街の灯り."""
    rng = np.random.default_rng(seed)
    s = w / 1280
    y, x = _grid(w, h)
    top, bottom = np.array([18, 24, 34]) / 255, np.array([7, 9, 14]) / 255
    img = np.broadcast_to(top * (1 - y[..., None]) + bottom * y[..., None], (h, w, 3)).copy()

    warm, cool, white = (255, 168, 92), (96, 168, 190), (215, 225, 235)
    img += _soft_disks(h, w, rng, 70, 18 * s, 80 * s, [warm, warm, cool, white], (0.10, 0.35), 10 * s, (0.3, 1.0))
    img += _soft_disks(h, w, rng, 30, 6 * s, 20 * s, [warm, white], (0.15, 0.4), 3 * s, (0.35, 0.95))
    background = img.copy()

    # 雨の筋 (少し斜め)
    streaks = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(streaks)
    for _ in range(int(500 * s)):
        x0, y0 = rng.uniform(0, w), rng.uniform(-50, h)
        ln = rng.uniform(25, 70) * s
        d.line((x0, y0, x0 - ln * 0.15, y0 + ln), fill=int(rng.uniform(15, 45)), width=1)
    st = gaussian_filter(np.asarray(streaks, float) / 255, 0.6 * s)
    img += st[..., None] * np.array([0.6, 0.7, 0.8])

    # 窓ガラスの水滴: 背景を少し明るく映し、縁を暗く、左上に小さな光
    blurred = gaussian_filter(background, (6 * s, 6 * s, 0))
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(int(320 * s)):
        r = rng.uniform(2, 9) * s
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        x0, x1 = int(max(cx - r - 2, 0)), int(min(cx + r + 2, w))
        y0, y1 = int(max(cy - r - 2, 0)), int(min(cy + r + 2, h))
        if x1 <= x0 or y1 <= y0:
            continue
        sub_y, sub_x = yy[y0:y1, x0:x1], xx[y0:y1, x0:x1]
        dist = np.hypot(sub_x - cx, sub_y - cy)
        inside = np.clip(r + 0.5 - dist, 0, 1)[..., None]
        rim = np.exp(-((dist - r * 0.85) / (0.25 * r + 0.5)) ** 2)[..., None]
        spec = np.exp(-(np.hypot(sub_x - (cx - r * 0.35), sub_y - (cy - r * 0.35)) / (0.18 * r + 0.4)) ** 2)[..., None]
        lens = np.flip(blurred[y0:y1, x0:x1], axis=0) * 1.5
        patch = img[y0:y1, x0:x1]
        patch[:] = patch * (1 - inside) + lens * inside - rim * inside * 0.06 + spec * 0.35
        if rng.random() < 0.15:  # 流れ落ちた跡
            tl = int(rng.uniform(20, 90) * s)
            ty0 = int(max(cy - tl, 0))
            tx = int(np.clip(cx, 0, w - 1))
            img[ty0:int(cy), max(tx - 1, 0):tx + 1] += 0.05
    return _vignette_grain(img, rng)


def snow_night(w, h, seed):
    """夜の雪景色. 遠くの丘に小さな暖かい窓明かり."""
    rng = np.random.default_rng(seed)
    s = w / 1280
    y, x = _grid(w, h)
    stops = np.array([[10, 16, 30], [30, 42, 62], [58, 72, 92], [40, 50, 66]]) / 255
    pos = np.array([0.0, 0.45, 0.66, 1.0])
    col = np.stack([np.interp(y[:, 0], pos, stops[:, c]) for c in range(3)], axis=1)
    img = np.repeat(col[:, None, :], w, axis=1)

    # 丘の重なり (奥ほど明るく霞む)
    xs = np.arange(w)
    for k, (base, amp, shade) in enumerate(((0.64, 0.035, 0.30), (0.72, 0.05, 0.24), (0.84, 0.06, 0.18))):
        ridge = gaussian_filter(rng.normal(0, 1, w), 90 * s)
        ridge = base + amp * ridge / (np.abs(ridge).max() + 1e-9)
        mask = (y > ridge[None, :]).astype(float)
        mask = gaussian_filter(mask, 1.2 * s)
        # 稜線のすぐ下が雪明かりで明るく、下へいくほど暗い
        below = np.clip((y - ridge[None, :]) / 0.25, 0, 1)
        tone = np.array([0.66, 0.74, 0.86])[None, None, :] * (shade * 2.0 * (1 - 0.55 * below))[..., None]
        img = img * (1 - mask[..., None]) + tone * mask[..., None]
        if k == 1:  # 二番目の丘の稜線に小さな窓明かり
            for _ in range(4):
                px = int(rng.uniform(0.15, 0.85) * w)
                py = int(ridge[px] * h + rng.uniform(4, 12) * s)
                glow = np.exp(-((xs[None, :] - px) ** 2 + (np.arange(h)[:, None] - py) ** 2) / (2 * (6 * s) ** 2))
                img += glow[..., None] * np.array([1.0, 0.68, 0.36]) * 0.55
                img[max(py - 2, 0):py + 2, max(px - 2, 0):px + 2] = [1.0, 0.82, 0.55]

    # 雪 (遠く小さく → 近く大きくぼけて)
    white = (235, 240, 248)
    img += _soft_disks(h, w, rng, int(900 * s), 0.6 * s, 1.3 * s, [white], (0.4, 0.8), 0.4 * s)
    img += _soft_disks(h, w, rng, int(260 * s), 1.5 * s, 3.0 * s, [white], (0.4, 0.8), 0.9 * s)
    img += _soft_disks(h, w, rng, 26, 7 * s, 16 * s, [white], (0.15, 0.35), 4 * s)
    return _vignette_grain(img, rng, 0.45)


def ocean_dark(w, h, seed):
    """睡眠向けの暗い水中 (サムネイル T1 と同じ描き方を暗くしたもの)."""
    img = add_bubbles(underwater_scene(seed, darkness=0.35), seed, count=14)
    if (w, h) != img.shape[1::-1]:
        im = Image.fromarray((img * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
        img = np.asarray(im, float) / 255
    return img


SCENES = {"rain": rain_window, "snow": snow_night, "ocean_dark": ocean_dark}
