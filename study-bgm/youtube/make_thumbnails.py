#!/usr/bin/env python3
"""YouTube 用サムネイルのバリエーションと、表示イメージのプレビューを作る.

比較したい要素 (背景・文字の太さ・文字の有無) が 1 つずつ違うように作ってあるので、
テストで差が出たときに「何が効いたか」を特定しやすい.

    T1 情景 + 細いセリフ体「Ocean.」          ← 推奨 (データとあなたの好みの折衷)
    T2 情景 (暗め) + 細いサンセリフ「THE DEEP」 ← 物語・場所型 (⑤ DARK AQUARIUM 型)
    T3 情景 + 太いサンセリフ「Ocean.」          ← 小さく表示されても読める型 (③⑥⑦ 型)
    T4 情景のみ (文字なし)                      ← 雰囲気型 (⑪ 型)
    T5 単色グラデーション + 細いセリフ体「Ocean.」 ← 当初案 (T1 と背景だけが違う対照)

使い方:
    python3 make_thumbnails.py            # thumbnails/ と preview_*.png を出力
    python3 make_thumbnails.py --seed 3   # 情景の乱数を変える
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

W, H = 1280, 720
OUT = Path(__file__).resolve().parent

SERIF = "/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf"
SANS_THIN = "/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf"
SANS_LIGHT = "/usr/share/fonts/opentype/inter/Inter-Light.otf"
SANS_BOLD = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
SANS_MED = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
SANS_REG = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"


# ---------------------------------------------------------------------------
# 背景
# ---------------------------------------------------------------------------
def underwater_scene(seed, darkness=0.0):
    """海面から光が差し込む水中の情景 (0..1 の float RGB)."""
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]

    # 深さのグラデーション
    stops = np.array([[24, 104, 132], [10, 52, 76], [4, 20, 36], [1, 6, 14]]) / 255
    pos = np.array([0.0, 0.35, 0.7, 1.0])
    img = np.stack([np.interp(y[:, 0], pos, stops[:, c]) for c in range(3)], axis=1)
    img = np.repeat(img[:, None, :], W, axis=1)

    # 海面のゆらめき (コースティクス): 網目状の光 = ボロノイ境界を
    # ゆがませ、奥ほど縦につぶして見上げた海面の遠近感を出す
    band = int(H * 0.42)
    yy, xx = np.mgrid[0:band, 0:W].astype(float)
    depth_scale = 1 + 5 * (yy / band)
    u = xx + gaussian_filter(rng.normal(0, 1, (band, W)), 18) * 900
    v = (yy * depth_scale) + gaussian_filter(rng.normal(0, 1, (band, W)), 18) * 900
    pts = np.column_stack([rng.uniform(-50, W + 50, 900),
                           rng.uniform(-50, band * 6 + 50, 900)])
    dist, _ = cKDTree(pts).query(np.column_stack([u.ravel(), v.ravel()]), k=2)
    edge = (dist[:, 1] - dist[:, 0]).reshape(band, W)
    caustic = np.exp(-edge / (2.2 * depth_scale)) * np.exp(-yy / (band * 0.3))
    caustic = gaussian_filter(caustic, 0.8)
    img[:band] += caustic[..., None] * np.array([0.30, 0.60, 0.66])

    # 光の筋 (海面の 1 点から扇状に広がる)
    x0, y0 = rng.uniform(0.4, 0.6), -0.35
    theta = np.arctan2(x - x0, (y - y0) * H / W)
    rays = np.zeros((H, W))
    for _ in range(14):
        c = rng.uniform(-0.55, 0.55)
        wdt = rng.uniform(0.006, 0.03)
        rays += np.exp(-((theta - c) / wdt) ** 2) * rng.uniform(0.3, 1.0)
    flicker = gaussian_filter(rng.normal(0, 1, (H, W)), 40)
    flicker = 0.75 + 0.25 * flicker / (np.abs(flicker).max() + 1e-9)
    rays = gaussian_filter(rays * flicker, 3) * np.exp(-y / 0.42)
    img += rays[..., None] * np.array([0.10, 0.22, 0.24])

    # マリンスノー (漂う微粒子)
    snow = np.zeros((H, W))
    for _ in range(900):
        px, py = rng.integers(0, W), rng.integers(0, H)
        snow[py, px] += rng.uniform(0.2, 1.0)
    snow = gaussian_filter(snow, 0.9) * 2.2 + gaussian_filter(snow, 3) * 3
    img += snow[..., None] * np.array([0.5, 0.7, 0.75]) * 0.5

    # 奥行きの霧と周辺減光
    vign = 1 - 0.55 * (((x - 0.5) / 0.75) ** 2 + ((y - 0.45) / 0.9) ** 2)
    img *= np.clip(vign, 0, 1)[..., None]
    img *= 1 - darkness
    img += rng.normal(0, 0.008, img.shape)  # フィルムの粒子
    return np.clip(img, 0, 1)


def add_bubbles(img, seed, count=26):
    rng = np.random.default_rng(seed + 7)
    yy, xx = np.mgrid[0:H, 0:W]
    cx = rng.uniform(0.72, 0.82) * W
    for _ in range(count):
        by = rng.uniform(0.25, 1.0) * H
        bx = cx + rng.normal(0, 18 + (H - by) * 0.05)
        r = rng.uniform(2, 8) * (0.6 + 0.6 * by / H)
        d = np.hypot(xx - bx, yy - by)
        ring = np.exp(-((d - r) / 1.1) ** 2) + 0.6 * np.exp(-(np.hypot(xx - bx + r * 0.35, yy - by + r * 0.35) / (r * 0.25 + 0.5)) ** 2)
        img += ring[..., None] * np.array([0.35, 0.55, 0.6]) * (0.4 + 0.6 * (1 - by / H))
    return np.clip(img, 0, 1)


def flat_gradient():
    """当初案: 青の単色グラデーション."""
    y = np.linspace(0, 1, H)[:, None, None]
    top = np.array([31, 111, 165]) / 255
    bottom = np.array([9, 33, 66]) / 255
    return np.broadcast_to(top * (1 - y) + bottom * y, (H, W, 3)).copy()


# ---------------------------------------------------------------------------
# 文字
# ---------------------------------------------------------------------------
def draw_text(im, text, font_path, size, cy, spacing=0.0, alpha=235, glow=True):
    """中央揃えで文字を描く。spacing は文字サイズに対する字間の比率."""
    font = ImageFont.truetype(font_path, size)
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + spacing * size * (len(text) - 1)
    layer = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(layer)
    x = (W - total) / 2
    for ch, w in zip(text, widths):
        d.text((x, cy), ch, font=font, fill=alpha, anchor="lm")
        x += w + spacing * size
    if glow:  # 読みやすさのための薄い影
        shadow = layer.filter(ImageFilter.GaussianBlur(size * 0.12))
        im.paste(Image.new("RGB", im.size, (0, 10, 20)), mask=shadow.point(lambda v: v * 0.55))
    im.paste(Image.new("RGB", im.size, (240, 248, 250)), mask=layer)
    return im


def to_image(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))


def make_variants(seed):
    scene = add_bubbles(underwater_scene(seed), seed)
    dark = add_bubbles(underwater_scene(seed, darkness=0.35), seed)

    v = {}
    im = to_image(scene)
    draw_text(im, "Ocean.", SERIF, 150, H * 0.46, spacing=0.02)
    draw_text(im, "DEEP SEA AMBIENT", SANS_LIGHT, 22, H * 0.60, spacing=0.45, alpha=200)
    v["T1_scene_serif"] = im

    im = to_image(dark)
    draw_text(im, "A DESCENT INTO THE ABYSS", SANS_LIGHT, 22, H * 0.38, spacing=0.45, alpha=190)
    draw_text(im, "THE DEEP", SANS_THIN, 120, H * 0.50, spacing=0.28)
    v["T2_scene_thin_story"] = im

    im = to_image(scene)
    draw_text(im, "Ocean.", SANS_BOLD, 220, H * 0.45, spacing=-0.01)
    draw_text(im, "DEEP SEA AMBIENT", SANS_MED, 34, H * 0.65, spacing=0.3, alpha=220)
    v["T3_scene_bold"] = im

    v["T4_scene_notext"] = to_image(scene)

    im = to_image(flat_gradient())
    draw_text(im, "Ocean.", SERIF, 150, H * 0.46, spacing=0.02, glow=False)
    draw_text(im, "DEEP SEA AMBIENT", SANS_LIGHT, 22, H * 0.60, spacing=0.45, alpha=200, glow=False)
    v["T5_flat_serif"] = im
    return v


# ---------------------------------------------------------------------------
# 表示イメージのプレビュー (ダークモードの YouTube 風)
# ---------------------------------------------------------------------------
def wrap(text, font, width):
    lines, cur = [], ""
    for word in text.split(" "):
        test = (cur + " " + word).strip()
        if font.getlength(test) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def card(thumb, title, width=420):
    tw, th = width, int(width * 9 / 16)
    t = thumb.resize((tw, th), Image.LANCZOS)
    f_title = ImageFont.truetype(SANS_MED, 17)
    f_meta = ImageFont.truetype(SANS_REG, 13)
    lines = wrap(title, f_title, width - 8)[:2]
    if len(wrap(title, f_title, width - 8)) > 2:
        lines[1] = lines[1].rstrip() + "…"
    hgt = th + 16 + 24 * len(lines) + 26
    c = Image.new("RGB", (width, hgt), (15, 15, 15))
    c.paste(t, (0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((tw - 52, th - 26, tw - 6, th - 6), 4, fill=(0, 0, 0))
    d.text((tw - 29, th - 16), "29:36", font=f_meta, fill=(255, 255, 255), anchor="mm")
    yy = th + 12
    for ln in lines:
        d.text((4, yy), ln, font=f_title, fill=(241, 241, 241))
        yy += 24
    d.text((4, yy + 2), "Your Channel · 1.2K views · 2 days ago", font=f_meta, fill=(170, 170, 170))
    return c


def label(im, text):
    f = ImageFont.truetype(SANS_MED, 15)
    out = Image.new("RGB", (im.width, im.height + 30), (15, 15, 15))
    out.paste(im, (0, 30))
    ImageDraw.Draw(out).text((4, 6), text, font=f, fill=(120, 200, 220))
    return out


def grid(images, cols, pad=24, bg=(15, 15, 15)):
    rows = (len(images) + cols - 1) // cols
    cw = max(i.width for i in images)
    ch = max(i.height for i in images)
    g = Image.new("RGB", (cols * cw + (cols + 1) * pad, rows * ch + (rows + 1) * pad), bg)
    for k, im in enumerate(images):
        r, c = divmod(k, cols)
        g.paste(im, (pad + c * (cw + pad), pad + r * (ch + pad)))
    return g


TITLES = {
    "A": "Ocean.",
    "B": "Ocean. | Deep Sea Ambient Music for Sleep, Study & Meditation",
    "C": "The Deep | A Descent into the Abyss · Ambient Music for Sleep, Study & Meditation",
    "D": "Deep Sea Ambient Music for Sleep, Study & Meditation 🌊 Underwater Sounds (30 Min)",
}
COMBOS = [  # テストと比較 (最大 3 案) に入れる組み合わせ
    ("Combo 1 (main) T1 × B", "T1_scene_serif", "B"),
    ("Combo 2 (story) T2 × C", "T2_scene_thin_story", "C"),
    ("Combo 3 (original) T5 × A", "T5_flat_serif", "A"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--seed", type=int, default=21)
    args = ap.parse_args()

    tdir = OUT / "thumbnails"
    tdir.mkdir(exist_ok=True)
    variants = make_variants(args.seed)
    for name, im in variants.items():
        im.save(tdir / f"{name}.png")
        print(tdir / f"{name}.png")

    # 1) 組み合わせ案をスマホのホーム画面くらいの大きさで
    cards = [label(card(variants[t], TITLES[k]), lab) for lab, t, k in COMBOS]
    grid(cards, 3).save(OUT / "preview_combos.png")

    # 2) 全サムネイルを「関連動画」欄の小ささ (168x94) と通常サイズで
    small = [label(v.resize((168, 94), Image.LANCZOS), n.split("_")[0]) for n, v in variants.items()]
    mid = [label(v.resize((360, 202), Image.LANCZOS), n) for n, v in variants.items()]
    grid(small, 5, pad=16).save(OUT / "preview_small.png")
    grid(mid, 3).save(OUT / "preview_all.png")
    print(OUT / "preview_combos.png")


if __name__ == "__main__":
    main()
