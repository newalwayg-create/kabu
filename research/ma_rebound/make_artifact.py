"""ギャラリーHTMLを Artifact 公開用（スケルトンなし・テーマ対応）に変換 → artifact_<tag>.html"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLES = {"base_5_25_75": "移動平均 反発事例集 5/25/75", "app_25_50_75": "移動平均 反発事例集 25/50/75"}

CSS = """<style>
/* layout: 上部に固定の目次、その下にグループごとのチャート格子（1〜3列） */
:root{--bg:#f6f7f9;--fg:#1c2230;--muted:#5d6676;--line:#d9dde4;--card:#ffffff;--cardfg:#2a3140;
--up:#c8423f;--down:#2d64ad;--accent:#2d64ad;
--sans:"Noto Sans JP",system-ui,"Hiragino Sans",sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14171d;--fg:#e8ebf0;--muted:#a3abb8;--line:#2f3540;--card:#ffffff;--cardfg:#2a3140;--up:#e0605c;--down:#5b8fd6;--accent:#7aa6e6;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#14171d;--fg:#e8ebf0;--muted:#a3abb8;--line:#2f3540;--card:#ffffff;--cardfg:#2a3140;--up:#e0605c;--down:#5b8fd6;--accent:#7aa6e6;color-scheme:dark}
body{background:var(--bg);color:var(--fg);font-family:var(--sans);padding-inline:16px;padding-block:8px 40px}
h1{font-size:1.3rem;text-wrap:balance;margin-block:12px 6px}
h2{font-size:1.05rem;border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:32px;text-wrap:balance}
nav{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:12px;position:sticky;top:env(safe-area-inset-top,0px);background:var(--bg);padding-block:8px;border-bottom:1px solid var(--line);z-index:2}
nav a{color:var(--accent)} a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.stat{color:var(--muted);font-size:13px;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,440px),1fr));gap:14px}
figure{margin:0;border:1px solid var(--line);border-radius:6px;padding:6px;background:var(--card);min-width:0}
figure.good{border-left:4px solid var(--up)} figure.bad{border-left:4px solid var(--down)}
img{width:100%;height:auto;display:block}
figcaption{font-size:12px;color:var(--cardfg);margin-top:4px;line-height:1.5;font-variant-numeric:tabular-nums}
.note{font-size:13px;color:var(--muted);max-width:70ch;line-height:1.7}
</style>"""


def convert(tag: str) -> Path:
    src = (HERE / f"gallery_{tag}.html").read_text(encoding="utf-8")
    body = src.split("</style></head><body>", 1)[1].rsplit("</body></html>", 1)[0]
    body = body.replace("赤枠=20日後に上昇した事例、青枠=下落した事例", "赤い左線=20日後に上昇した事例、青い左線=下落した事例")
    out = f"<title>{TITLES[tag]}</title>\n" + \
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap">\n' + \
        CSS + "\n" + body
    dst = HERE / f"artifact_{tag}.html"
    dst.write_text(out, encoding="utf-8")
    n = len(re.findall(r'<img ', out))
    print(dst.name, n, "images", round(len(out) / 1024), "KB")
    return dst


if __name__ == "__main__":
    for t in (sys.argv[1:] or TITLES):
        convert(t)
