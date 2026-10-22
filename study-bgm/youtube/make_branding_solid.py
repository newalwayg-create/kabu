#!/usr/bin/env python3
"""単色でシンプルなチャンネル素材と、その見え方のプレビューを作る.

チャンネル自体は特定のテーマを持たない「中立な額縁」にし、毎回のコンセプトは
サムネイルに任せる、という方針の素材. 海 (青) を連想させない中間色を候補にしている.

    branding_solid/avatar_<色>.png        単色のみ
    branding_solid/avatar_<色>_dot.png    単色 + 中央に小さな点 (句点 = ひと休み)
    branding_solid/banner_<色>.png        単色のみ (2560x1440)
    branding_solid/banner_<色>_name.png   単色 + 安全領域内に小さくチャンネル名
    branding_solid/watermark_dot.png      150x150 透過 PNG (点だけ)
    preview_solid.png                     ライト/ダークモードでの見え方、アイコンなし (既定の頭文字) との比較

使い方:
    python3 make_branding_solid.py --name "Halcyon Rooms"
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from make_branding import SANS_MED, SERIF

OUT = Path(__file__).resolve().parent
SANS_REG = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"

# 白背景でも黒背景でも沈まない、中間の明るさの色を中心に選ぶ
COLORS = {
    "stone": (143, 138, 130),   # 温かいグレー
    "fog":   (158, 163, 166),   # 冷たいグレー
    "clay":  (168, 140, 124),   # くすんだ土色
    "sage":  (138, 150, 132),   # くすんだ緑
    "bone":  (233, 228, 218),   # 生成り (ダークモード向き、ライトモードで沈む例)
    "ink":   (40, 44, 48),      # 墨 (ライトモード向き、ダークモードで沈む例)
}
DOT = (250, 250, 248)
LIGHT_BG, DARK_BG = (255, 255, 255), (15, 15, 15)


def dot_color(rgb):
    # 明るい色の上では点を暗くする
    return (40, 40, 40) if sum(rgb) / 3 > 200 else DOT


def avatar(rgb, dot=False, s=800):
    im = Image.new("RGB", (s, s), rgb)
    if dot:
        r = s * 0.045
        ImageDraw.Draw(im).ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=dot_color(rgb))
    return im


def banner(rgb, name=None):
    w, h = 2560, 1440
    im = Image.new("RGB", (w, h), rgb)
    if name:
        f = ImageFont.truetype(SERIF, 64)
        ImageDraw.Draw(im).text((w / 2, h / 2), name, font=f, fill=dot_color(rgb), anchor="mm")
    return im


def watermark():
    s = 150
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((s / 2 - 22, s / 2 - 22, s / 2 + 22, s / 2 + 22), fill=(255, 255, 255, 230))
    return im


def default_avatar(name, s=800):
    """アイコンを設定しなかったときに YouTube が出す「色付きの丸に頭文字」のイメージ."""
    im = Image.new("RGB", (s, s), (92, 107, 192))
    f = ImageFont.truetype(SANS_REG, int(s * 0.55))
    ImageDraw.Draw(im).text((s / 2, s / 2), name[0].lower(), font=f, fill=(255, 255, 255), anchor="mm")
    return im


# ---------------------------------------------------------------------------
# プレビュー
# ---------------------------------------------------------------------------
def _circle_on(av, size, bg):
    """丸く切り抜いて、指定した背景色の上に置く."""
    im = av.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4, size * 4), fill=255)
    out = Image.new("RGB", (size, size), bg)
    out.paste(im, (0, 0), mask.resize((size, size), Image.LANCZOS))
    return out


def preview(name):
    variants = [("no icon (default)", default_avatar(name))]
    for c, rgb in COLORS.items():
        variants.append((c, avatar(rgb)))
        variants.append((c + " + dot", avatar(rgb, dot=True)))

    colw, rowh = 360, 112
    cols = 2
    rows = (len(variants) + cols - 1) // cols
    W = 30 + cols * 2 * colw
    H = 60 + rows * rowh + 520
    canvas = Image.new("RGB", (W, H), (40, 40, 40))
    d = ImageDraw.Draw(canvas)
    f = ImageFont.truetype(SANS_MED, 16)
    fs = ImageFont.truetype(SANS_MED, 13)
    d.text((16, 14), "Feed row in LIGHT mode  |  DARK mode   (avatar 36 px in row, 24 px and 88 px beside)",
           font=f, fill=(140, 210, 230))

    for k, (label, av) in enumerate(variants):
        r, c = divmod(k, cols)
        x0, y0 = 15 + c * 2 * colw, 50 + r * rowh
        for j, (bg, fg, sub) in enumerate(((LIGHT_BG, (15, 15, 15), (96, 96, 96)),
                                           (DARK_BG, (241, 241, 241), (170, 170, 170)))):
            panel = Image.new("RGB", (colw - 6, rowh - 8), bg)
            pd = ImageDraw.Draw(panel)
            panel.paste(_circle_on(av, 36, bg), (8, 30))
            pd.text((52, 30), "Ocean. | Deep Sea Ambient…", font=ImageFont.truetype(SANS_MED, 14), fill=fg)
            pd.text((52, 50), f"{name} · 1.2K views", font=ImageFont.truetype(SANS_REG, 12), fill=sub)
            panel.paste(_circle_on(av, 24, bg), (8, 72))
            pd.text((40, 76), "@user · great for studying", font=ImageFont.truetype(SANS_REG, 11), fill=sub)
            panel.paste(_circle_on(av, 88, bg), (colw - 6 - 96, 10))
            pd.text((8, 8), label, font=fs, fill=(200, 80, 80) if label.startswith("no icon") else sub)
            canvas.paste(panel, (x0 + j * colw, y0))

    # チャンネルページ: バナーなし / 単色バナー / 単色 + 名前
    y = 60 + rows * rowh
    d.text((16, y), "Channel page header (desktop, dark mode)", font=f, fill=(140, 210, 230))
    rgb = COLORS["stone"]
    mocks = [("no banner", None), ("solid banner", banner(rgb)), ("solid + name", banner(rgb, name))]
    mw = (W - 60) // 3
    for i, (label, ban) in enumerate(mocks):
        x0 = 15 + i * (mw + 15)
        page = Image.new("RGB", (mw, 440), DARK_BG)
        pd = ImageDraw.Draw(page)
        top = 10
        if ban is not None:
            strip = ban.crop((0, (1440 - 423) // 2, 2560, (1440 + 423) // 2)).resize((mw - 20, int((mw - 20) * 423 / 2560)), Image.LANCZOS)
            page.paste(strip, (10, 10))
            top = 20 + strip.height
        page.paste(_circle_on(avatar(rgb, dot=True), 96, DARK_BG), (10, top + 10))
        pd.text((120, top + 22), name, font=ImageFont.truetype(SANS_MED, 24), fill=(241, 241, 241))
        pd.text((120, top + 56), "@" + name.replace(" ", "").lower() + " · 1 video", font=fs, fill=(170, 170, 170))
        pd.text((120, top + 76), "Ambient rooms for sleep, study & meditation.", font=fs, fill=(170, 170, 170))
        # 動画一覧 (サムネイルが主役になる)
        for t in range(3):
            tx = 10 + t * ((mw - 20) // 3)
            tw = (mw - 20) // 3 - 8
            th = int(tw * 9 / 16)
            thumb = Image.open(OUT / "thumbnails" / ["T1_scene_serif.png", "T5_flat_serif.png", "T4_scene_notext.png"][t])
            page.paste(thumb.resize((tw, th), Image.LANCZOS), (tx, top + 120))
        canvas.paste(page, (x0, y + 30))
        d.text((x0, y + 476), label, font=fs, fill=(220, 220, 220))
    return canvas


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--name", default="Halcyon Rooms")
    args = ap.parse_args()

    bdir = OUT / "branding_solid"
    bdir.mkdir(exist_ok=True)
    for c, rgb in COLORS.items():
        avatar(rgb).save(bdir / f"avatar_{c}.png")
        avatar(rgb, dot=True).save(bdir / f"avatar_{c}_dot.png")
        banner(rgb).save(bdir / f"banner_{c}.png")
        banner(rgb, args.name).save(bdir / f"banner_{c}_name.png")
    watermark().save(bdir / "watermark_dot.png")
    preview(args.name).save(OUT / "preview_solid.png")
    print(bdir, OUT / "preview_solid.png")


if __name__ == "__main__":
    main()
