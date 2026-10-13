"""樹形図を図として出力（figures/tree_*.png）.

各箱: 枝の条件 / 探索期間の 件数・上昇割合・平均・対TOPIX超過 / 検証期間の同じ数字。
箱の色: 探索期間の平均リターンが全日平均より高いほど赤、低いほど青（差 ±3pt で飽和）。
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

HERE = Path(__file__).resolve().parent
D, F = HERE / "data", HERE / "figures"
F.mkdir(exist_ok=True)
plt.rcParams["font.family"] = "IPAGothic"
CMAP = plt.get_cmap("RdBu_r")


def fmt(s, tag):
    if not s or s.get("件数", 0) == 0:
        return f"{tag} 事例なし"
    return (f"{tag} n={int(s['件数'])}  上昇{s['上昇割合%']:.0f}%  平均{s['平均%']:+.2f}%  超過{s['対TOPIX超過%']:+.2f}%")


def leaves(n):
    return 1 if not n["children"] else sum(leaves(c) for c in n["children"])


def layout(n, depth, y0, out):
    if not n["children"]:
        out.append((n, depth, y0 + 0.5))
        return y0 + 1
    y = y0
    ys = []
    for c in n["children"]:
        start = y
        y = layout(c, depth + 1, y, out)
        ys.append(out[[i for i, o in enumerate(out) if o[0] is c][0]][2])
    out.append((n, depth, sum(ys) / len(ys)))
    return y


def draw(root, base_ex, path: Path, title: str, box_w=3.3, x_gap=0.55):
    pts = []
    total = layout(root, 0, 0, pts)
    max_d = max(d for _, d, _ in pts)
    fig_h = max(3.0, total * 1.05)
    fig_w = (max_d + 1) * (box_w + x_gap) + 0.4
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-0.2, fig_w - 0.2)
    ax.set_ylim(total + 0.2, -0.6)
    ax.axis("off")
    norm = TwoSlopeNorm(vmin=-3, vcenter=0, vmax=3)
    pos = {}
    for n, d, y in pts:
        x = d * (box_w + x_gap)
        pos[id(n)] = (x, y)
        s = n["ex"]
        diff = (s.get("平均%", base_ex) - base_ex) if s and s.get("件数", 0) else 0
        col = CMAP(norm(max(-3, min(3, diff))))
        insufficient = (s.get("件数", 0) < 100) if s else True
        lab = "\n".join(textwrap.wrap(n["label"].replace("≤", "≦").replace("≥", "≧"), 22)[:3])
        txt = lab + "\n" + fmt(n["ex"], "探索") + "\n" + fmt(n["te"], "検証")
        if n.get("note"):
            txt += "\n" + n["note"]
        ax.add_patch(plt.Rectangle((x, y - 0.46), box_w, 0.92, facecolor=col, alpha=0.35 if not insufficient else 0.12,
                                   edgecolor="#555" if not insufficient else "#aaa", lw=0.8,
                                   linestyle="-" if not insufficient else "--"))
        ax.text(x + 0.06, y, txt, va="center", ha="left", fontsize=6.3, color="#111" if not insufficient else "#666",
                linespacing=1.25)
    for n, d, y in pts:
        for c in n["children"]:
            x1, y1 = pos[id(n)]
            x2, y2 = pos[id(c)]
            ax.plot([x1 + box_w, x1 + box_w + x_gap / 2, x1 + box_w + x_gap / 2, x2], [y1, y1, y2, y2],
                    color="#777", lw=0.7)
    ax.set_title(title, fontsize=9, loc="left")
    fig.savefig(path, dpi=110, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def combine(nodes, key):
    """上向き・下向きの2ノードを件数で加重して合算（平均・上昇割合・超過は件数加重平均で正確に一致）."""
    tot = sum(n[key].get("件数", 0) for n in nodes)
    if not tot:
        return {}
    out = {"件数": tot}
    for k in ("上昇割合%", "平均%", "対TOPIX超過%"):
        out[k] = sum(n[key][k] * n[key]["件数"] for n in nodes if n[key].get("件数", 0)) / tot
    return out


def main():
    trees = json.load(open(D / "trees.json"))
    meta = json.load(open(D / "meta.json"))
    b = meta["base"]
    bex = {k: v["探索 全日"] for k, v in b.items()}
    bte = {k: v["検証 全日"] for k, v in b.items()}
    base_ex = bex["平均%"]
    root_label = "条件なし（全日）"
    pats = {}
    for st, t in trees.items():
        p = int(st.split("_")[0])
        pats.setdefault(p, []).append(t)
    names = {0: "G0 株価が3本の上", 1: "P1 25日のみ上", 2: "P2 50日のみ上", 3: "P3 75日のみ上", 4: "P4 25+50日",
             5: "P5 25+75日", 6: "P6 50+75日", 7: "P7 3本すべて上"}
    # 全体（第1・第2階層）
    over = {"label": root_label, "ex": bex, "te": bte, "note": "", "children": []}
    for p in [1, 2, 3, 4, 5, 6, 7, 0]:
        kids = [{**k, "label": k["label"].split("｜")[1], "children": []} for k in pats[p]]
        over["children"].append({"label": names[p], "ex": combine(pats[p], "ex"), "te": combine(pats[p], "te"), "note": "", "children": kids})
    draw(over, base_ex, F / "tree_overview.png", "樹形図（第1・第2階層）: 根=条件なし（全日）、色=探索期間の平均の全日比（赤=高い/青=低い）")
    for p in [1, 2, 3, 4, 5, 6, 7, 0]:
        r = {"label": root_label, "ex": bex, "te": bte, "note": "",
             "children": [{"label": names[p], "ex": combine(pats[p], "ex"), "te": combine(pats[p], "te"), "note": "",
                           "children": [{**k, "label": k["label"].split("｜")[1]} for k in pats[p]]}]}
        draw(r, base_ex, F / f"tree_P{p}.png",
             f"樹形図 {names[p]}（分岐順: TOPIXの位置 → 乖離率 → 足の形。点線の箱=探索の事例が100件未満）")
        print("tree", p)


if __name__ == "__main__":
    main()
