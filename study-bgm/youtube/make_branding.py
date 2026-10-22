#!/usr/bin/env python3
"""チャンネルの周辺素材 (プロフィール画像・バナー・透かし) とプレビューを作る.

ブランドマークは「水平線の上の点」. 点は「Ocean.」の句点であり、ひと休み (pause) の印.
海に限らず Forest. / Rain. などに広げても使えるよう、特定のテーマに寄せていない.

    branding/avatar_A1_dot_horizon.png   点 + 水平線 + 水面の反射   ← 推奨
    branding/avatar_A2_monogram.png      セリフ体のモノグラム「H.」
    branding/avatar_A3_dot.png           点だけ (いちばんミニマル)
    branding/banner.png                  2560x1440 (全デバイスの安全領域 1235x338 に文字を収める)
    branding/watermark.png               150x150 透過 PNG (動画右下に出る登録ボタン用)
    preview_branding.png                 小さい表示・バナーの切り取られ方の確認用

使い方:
    python3 make_branding.py --name "Halcyon Rooms" --mono "H."
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter

OUT = Path(__file__).resolve().parent
SERIF = "/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf"
SANS_LIGHT = "/usr/share/fonts/opentype/inter/Inter-Light.otf"
SANS_MED = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"

SKY_TOP = np.array([7, 22, 38]) / 255
SKY_HORIZON = np.array([38, 86, 108]) / 255
WATER_TOP = np.array([12, 38, 56]) / 255
WATER_BOTTOM = np.array([3, 10, 20]) / 255
DOT = np.array([240, 246, 248]) / 255


def horizon_scene(w, h, horizon, dot_x, dot_y, dot_r, seed=5, reflection=True):
    """夜明け前の静かな水平線と、その上に浮かぶ点 (0..1 の float RGB)."""
    rng = np.random.default_rng(seed)
    y = np.linspace(0, 1, h)[:, None]
    hy = horizon

    sky_t = np.clip(y / hy, 0, 1) ** 1.6
    sky = SKY_TOP * (1 - sky_t[..., None]) + SKY_HORIZON * sky_t[..., None]
    wat_t = np.clip((y - hy) / (1 - hy), 0, 1) ** 0.6
    water = WATER_TOP * (1 - wat_t[..., None]) + WATER_BOTTOM * wat_t[..., None]
    img = np.where((y < hy)[..., None], sky, water)
    img = np.repeat(img, w, axis=1)

    # 水平線のにじみ
    glow = np.exp(-((y - hy) / 0.015) ** 2) * 0.10
    img += glow[..., None] * np.array([0.6, 0.85, 0.9])

    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    # 点 (やわらかい光をまとった円)
    d = np.hypot(xx - dot_x, yy - dot_y)
    disc = np.clip(dot_r + 0.8 - d, 0, 1)
    halo = np.exp(-(d / (dot_r * 2.6)) ** 2) * 0.22
    img = img * (1 - disc[..., None]) + DOT * disc[..., None]
    img += halo[..., None] * np.array([0.6, 0.85, 0.95])

    # 水面に映る点 (横長の揺らぐ線の集まり)
    if reflection:
        hpx = hy * h
        lines = np.zeros((h, w))
        for _ in range(int(h * (1 - hy) / 9)):
            ly = rng.uniform(hpx + 4, hpx + (h - hpx) * 0.8)
            k = (ly - hpx) / (h - hpx)
            half = dot_r * (1.6 + 2.5 * k) * rng.uniform(0.4, 1.1)
            cx = dot_x + rng.normal(0, dot_r * 0.25)
            seg = (np.abs(xx[int(ly)] - cx) < half).astype(float)
            lines[int(ly)] += seg * (1 - k) ** 1.5 * rng.uniform(0.3, 0.9)
        lines = gaussian_filter(lines, (0.7, 1.2))
        img += lines[..., None] * np.array([0.55, 0.75, 0.82]) * 0.8

    img += rng.normal(0, 0.006, img.shape)
    return np.clip(img, 0, 1)


def to_image(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))


def text_center(im, text, font_path, size, cy, spacing=0.0, fill=(240, 248, 250), alpha=235):
    font = ImageFont.truetype(font_path, size)
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + spacing * size * (len(text) - 1)
    layer = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(layer)
    x = (im.width - total) / 2
    for ch, w in zip(text, widths):
        d.text((x, cy), ch, font=font, fill=alpha, anchor="lm")
        x += w + spacing * size
    shadow = layer.filter(ImageFilter.GaussianBlur(size * 0.12))
    im.paste(Image.new("RGB", im.size, (0, 8, 16)), mask=shadow.point(lambda v: v * 0.5))
    im.paste(Image.new("RGB", im.size, fill), mask=layer)
    return im


def avatars(mono):
    s = 800
    a = {}
    a["avatar_A1_dot_horizon"] = to_image(
        horizon_scene(s, s, 0.60, s / 2, s * 0.42, 70))
    im = to_image(horizon_scene(s, s, 0.80, s / 2, -999, 1, reflection=False))
    text_center(im, mono, SERIF, 380, s * 0.47)
    a["avatar_A2_monogram"] = im
    a["avatar_A3_dot"] = to_image(
        horizon_scene(s, s, 1.01, s / 2, s / 2, 120, reflection=False))
    return a


def banner(name, tagline):
    w, h = 2560, 1440
    im = to_image(horizon_scene(w, h, 0.56, w / 2, h * 0.405, 16))
    text_center(im, name, SERIF, 112, h * 0.485, spacing=0.02)
    text_center(im, tagline, SANS_LIGHT, 34, h * 0.548, spacing=0.30, alpha=215)
    return im


def watermark():
    s = 150
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((6, 6, s - 6, s - 6), outline=(255, 255, 255, 210), width=5)
    d.line((26, 92, s - 26, 92), fill=(255, 255, 255, 170), width=3)
    d.ellipse((s / 2 - 13, 56 - 13, s / 2 + 13, 56 + 13), fill=(255, 255, 255, 235))
    return im


# ---------------------------------------------------------------------------
# プレビュー
# ---------------------------------------------------------------------------
def circle(im, size):
    im = im.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4, size * 4), fill=255)
    out = Image.new("RGB", (size, size), (15, 15, 15))
    out.paste(im, (0, 0), mask.resize((size, size), Image.LANCZOS))
    return out


def preview(avs, ban, name):
    bg = (15, 15, 15)
    f = ImageFont.truetype(SANS_MED, 16)
    fs = ImageFont.truetype(SANS_MED, 13)
    canvas = Image.new("RGB", (1400, 1180), bg)
    d = ImageDraw.Draw(canvas)

    # 1) アバターを 3 サイズで (チャンネルページ 176 / 動画の下 48 / コメント欄 24)
    d.text((24, 16), "Avatars at 176 / 48 / 24 px", font=f, fill=(120, 200, 220))
    x = 24
    for n, im in avs.items():
        canvas.paste(circle(im, 176), (x, 46))
        canvas.paste(circle(im, 48), (x + 190, 46))
        canvas.paste(circle(im, 24), (x + 190, 104))
        d.text((x, 230), n.replace("avatar_", ""), font=fs, fill=(170, 170, 170))
        # 動画下のチャンネル行の見え方
        canvas.paste(circle(im, 36), (x, 258))
        d.text((x + 46, 266), name, font=f, fill=(241, 241, 241))
        x += 450

    # 2) バナー全体 (安全領域の枠つき)
    d.text((24, 316), "Banner 2560x1440  (yellow = safe area 1235x338 for all devices, cyan = desktop 2560x423)",
           font=f, fill=(120, 200, 220))
    b = ban.copy()
    bd = ImageDraw.Draw(b)
    bw, bh = b.size
    bd.rectangle(((bw - 2560) / 2, (bh - 423) / 2, (bw + 2560) / 2 - 1, (bh + 423) / 2), outline=(80, 220, 240), width=6)
    bd.rectangle(((bw - 1235) / 2, (bh - 338) / 2, (bw + 1235) / 2, (bh + 338) / 2), outline=(250, 210, 60), width=6)
    canvas.paste(b.resize((640, 360), Image.LANCZOS), (24, 346))

    # 3) 実際の切り取られ方: デスクトップ (2560x423) とスマホ (1546x423 前後)
    d.text((700, 346), "Desktop crop", font=fs, fill=(170, 170, 170))
    desk = ban.crop((0, (bh - 423) // 2, 2560, (bh + 423) // 2)).resize((676, 112), Image.LANCZOS)
    canvas.paste(desk, (700, 366))
    d.text((700, 494), "Mobile crop", font=fs, fill=(170, 170, 170))
    mob = ban.crop(((bw - 1546) // 2, (bh - 423) // 2, (bw + 1546) // 2, (bh + 423) // 2)).resize((408, 112), Image.LANCZOS)
    canvas.paste(mob, (700, 514))

    # 4) チャンネルページ風のモック
    d.text((24, 728), "Channel page mock", font=f, fill=(120, 200, 220))
    canvas.paste(desk.resize((1352, 224), Image.LANCZOS), (24, 758))
    canvas.paste(circle(avs["avatar_A1_dot_horizon"], 120), (24, 1000))
    d.text((164, 1012), name, font=ImageFont.truetype(SANS_MED, 30), fill=(241, 241, 241))
    d.text((164, 1056), "@" + name.replace(" ", "").lower() + " · 0 subscribers · 1 video",
           font=fs, fill=(170, 170, 170))
    d.text((164, 1080), "Ambient rooms for sleep, study & meditation. New room every week.",
           font=fs, fill=(170, 170, 170))
    return canvas


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--name", default="Halcyon Rooms")
    ap.add_argument("--mono", default="H.")
    ap.add_argument("--tagline", default="AMBIENT ROOMS FOR SLEEP, STUDY & MEDITATION")
    args = ap.parse_args()

    bdir = OUT / "branding"
    bdir.mkdir(exist_ok=True)
    avs = avatars(args.mono)
    for n, im in avs.items():
        im.save(bdir / f"{n}.png")
    ban = banner(args.name, args.tagline)
    ban.save(bdir / "banner.png")
    watermark().save(bdir / "watermark.png")
    preview(avs, ban, args.name).save(OUT / "preview_branding.png")
    print(bdir, OUT / "preview_branding.png")


if __name__ == "__main__":
    main()
