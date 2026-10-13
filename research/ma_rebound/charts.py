"""過去事例のチャート画像とグループ別HTMLギャラリーを作成.

- 日足ローソク足 + 移動平均（設定の短期/中期/長期）+ 出来高 + MACD(12,26,9)
- 期間: シグナル日の前60営業日〜後20営業日。シグナル日に▲印、その後20日を薄く着色
- 各グループ: 上昇事例（20日後リターン>0）6件 + 下落事例（≤0）6件。
  乱数（固定シード）で抽出し、同一銘柄は60営業日以上離れた日だけを採用
- 塩野義(4507)・KDDI(9433) の直近チャートも同じ形式で作成
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mplfinance as mpf  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from analysis import PNAME, macd_hist  # noqa: E402
from universe import UNIVERSE  # noqa: E402

HERE = Path(__file__).resolve().parent
D = HERE / "data"
plt.rcParams["font.family"] = "IPAGothic"
STYLE = mpf.make_mpf_style(base_mpf_style="yahoo", rc={"font.family": "IPAGothic", "font.size": 8},
                           marketcolors=mpf.make_marketcolors(up="#d64545", down="#2f6db5", inherit=True))
N_EACH = 6
GROUP_ORDER = [f"{PNAME[p]}｜{s}" for p in range(1, 8) for s in ("上向き", "下向き")] + \
              [f"{PNAME[0]}｜上向き", f"{PNAME[0]}｜下向き"]


def load_prices():
    p = pd.read_csv(D / "prices.csv", parse_dates=["date"], dtype={"code": str})
    return {c: g.set_index("date").sort_index() for c, g in p.groupby("code")}


def draw(df: pd.DataFrame, sig: pd.Timestamp, mas: tuple, title: str, path: Path, after=20):
    c = df["close"]
    full = pd.DataFrame({f"ma{n}": c.rolling(n).mean() for n in mas})
    full["ma50"] = c.rolling(50).mean()
    mh = macd_hist(c)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    sigl = macd.ewm(span=9, adjust=False).mean()
    i = df.index.get_loc(sig)
    lo, hi = max(0, i - 60), min(len(df), i + after + 1)
    w = df.iloc[lo:hi].rename(columns=str.capitalize)
    fw = full.iloc[lo:hi]
    colors = ["#e08a00", "#2a9d3f", "#7b3fb5"]
    aps = [mpf.make_addplot(fw[f"ma{n}"], color=colors[j], width=1.1) for j, n in enumerate(mas)]
    if 50 not in mas:
        aps.append(mpf.make_addplot(fw["ma50"], color="#888888", width=0.8, linestyle=":"))
    mark = pd.Series(np.nan, index=w.index)
    mark.loc[sig] = w.loc[sig, "Low"] * 0.985
    aps.append(mpf.make_addplot(mark, type="scatter", marker="^", markersize=70, color="black"))
    h = mh.iloc[lo:hi]
    aps.append(mpf.make_addplot(h, type="bar", panel=2, color=["#d64545" if x >= 0 else "#2f6db5" for x in h],
                                ylabel="MACD"))
    aps.append(mpf.make_addplot(macd.iloc[lo:hi], panel=2, color="#333333", width=0.8))
    aps.append(mpf.make_addplot(sigl.iloc[lo:hi], panel=2, color="#e08a00", width=0.8))
    fig, axes = mpf.plot(w, type="candle", style=STYLE, addplot=aps, volume=True, panel_ratios=(5, 1.4, 1.6),
                         figsize=(7.2, 5.0), returnfig=True, tight_layout=True, xrotation=0, datetime_format="%y/%m/%d")
    ax = axes[0]
    si = w.index.get_loc(sig)
    if hi - lo - 1 > si:
        ax.axvspan(si + 0.5, len(w) - 0.5, color="#f2c94c", alpha=0.12)
    labels = [f"{n}日" for n in mas] + ([] if 50 in mas else ["50日(参考)"])
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=col, lw=1.2) for col in colors] + \
              ([] if 50 in mas else [Line2D([0], [0], color="#888888", lw=0.9, ls=":")])
    ax.legend(handles, labels, loc="upper left", fontsize=7, frameon=False, ncol=4)
    ax.set_title(title, fontsize=9, loc="left")
    fig.savefig(path, dpi=80, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def pick(ev: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    ev = ev.sample(frac=1, random_state=seed)
    chosen, last = [], {}
    for r in ev.itertuples():
        prev = last.get(r.code, [])
        if any(abs((r.date - d).days) < 90 for d in prev):
            continue
        chosen.append(r.Index)
        last.setdefault(r.code, []).append(r.date)
        if len(chosen) >= n:
            break
    return ev.loc[chosen]


def gallery(tag: str, mas: tuple, title: str) -> None:
    prices = load_prices()
    ev = pd.read_csv(D / tag / "events.csv", parse_dates=["date"], dtype={"code": str})
    cdir = HERE / "charts" / tag
    cdir.mkdir(parents=True, exist_ok=True)
    sections, cases = [], []
    # 直近: 塩野義・KDDI
    cur = []
    for code in ("4507", "9433"):
        df = prices[code]
        sig = df.index[-1]
        f = cdir / f"current_{code}.png"
        draw(df, sig, mas, f"{code} {UNIVERSE[code]}  {sig.date()}（データ最終日）", f, after=0)
        cur.append((f.name, f"{code} {UNIVERSE[code]} {sig.date()}"))
    sections.append(("直近チャート（比較用）", "", [(n, cap, "") for n, cap in cur]))
    for gi, g in enumerate(GROUP_ORDER):
        sub = ev[ev.group == g]
        n_each = N_EACH if not g.startswith("G0") else 3
        good = pick(sub[sub.ret20 > 0], n_each, seed=gi)
        bad = pick(sub[sub.ret20 <= 0], n_each, seed=100 + gi)
        items = []
        for kind, part in (("上昇", good), ("下落", bad)):
            for r in part.itertuples():
                fn = f"{tag}_{gi:02d}_{kind}_{r.code}_{r.date.date()}.png"
                t = f"{r.code} {r.name} {r.date.date()}  {g}  20日後 {r.ret20*100:+.1f}%"
                draw(prices[r.code], r.date, mas, t, cdir / fn)
                cap = (f"<b>{kind}</b> {html.escape(str(r.code))} {html.escape(r.name)} {r.date.date()}<br>"
                       f"5日 {r.ret5*100:+.1f}% / 10日 {r.ret10*100:+.1f}% / 20日 {r.ret20*100:+.1f}%"
                       f"（対TOPIX {r.ex_topix_20*100:+.1f}pt, 最大下落 {r.mae20*100:.1f}%）")
                items.append((fn, cap, kind))
                cases.append({"group": g, "kind": kind, "code": r.code, "name": r.name, "date": r.date.date(),
                              "ret5%": round(r.ret5 * 100, 2), "ret10%": round(r.ret10 * 100, 2),
                              "ret20%": round(r.ret20 * 100, 2), "対TOPIX20日%": round(r.ex_topix_20 * 100, 2),
                              "最大下落20日%": round(r.mae20 * 100, 2), "chart": f"charts/{tag}/{fn}"})
        stat = (f"事例数 {len(sub):,}件 / 20日後上昇の割合 {(sub.ret20 > 0).mean()*100:.1f}% / "
                f"平均 {sub.ret20.mean()*100:+.2f}%")
        sections.append((g, stat, items))
        print(tag, g, len(items))
    pd.DataFrame(cases).to_csv(D / tag / "chart_cases.csv", index=False)
    write_html(tag, title, mas, sections)


def write_html(tag, title, mas, sections):
    nav = "".join(f'<a href="#s{i}">{html.escape(s[0])}</a>' for i, s in enumerate(sections))
    body = []
    for i, (name, stat, items) in enumerate(sections):
        figs = "".join(
            f'<figure class="{ "good" if k == "上昇" else "bad" if k == "下落" else "" }">'
            f'<img loading="lazy" src="charts/{tag}/{fn}" alt="{html.escape(fn)}"><figcaption>{cap}</figcaption></figure>'
            for fn, cap, k in items)
        body.append(f'<section id="s{i}"><h2>{html.escape(name)}</h2><p class="stat">{html.escape(stat)}</p>'
                    f'<div class="grid">{figs}</div></section>')
    page = f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>移動平均 反発事例 {html.escape(tag)}</title>
<style>
:root{{--bg:#fff;--fg:#1d1d1f;--muted:#666;--line:#ddd;--good:#d64545;--bad:#2f6db5}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151517;--fg:#eee;--muted:#aaa;--line:#333}}}}
body{{background:var(--bg);color:var(--fg);font-family:system-ui,"Hiragino Sans","Noto Sans JP",sans-serif;margin:0 16px 40px}}
h1{{font-size:20px}} h2{{font-size:16px;border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:32px}}
nav{{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:12px;position:sticky;top:0;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line)}}
nav a{{color:inherit}} .stat{{color:var(--muted);font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,460px),1fr));gap:14px}}
figure{{margin:0;border:1px solid var(--line);border-radius:6px;padding:6px;background:#fff}}
figure.good{{border-left:4px solid var(--good)}} figure.bad{{border-left:4px solid var(--bad)}}
img{{width:100%;height:auto;display:block}} figcaption{{font-size:12px;color:#333;margin-top:4px;line-height:1.5}}
.note{{font-size:13px;color:var(--muted);max-width:900px;line-height:1.6}}
</style></head><body>
<h1>{html.escape(title)}：移動平均線と株価の位置関係パターン別 過去事例</h1>
<p class="note">移動平均: {'/'.join(str(m) for m in mas)}日（単純移動平均, 終値）{'' if 50 in mas else '＋参考に50日線（灰色点線）'}。
▲=条件を満たした日（エントリーは翌営業日の始値）。黄色の網掛け=その後20営業日。下段=出来高、MACD(12,26,9)。
赤枠=20日後に上昇した事例、青枠=下落した事例（乱数で抽出。代表性は保証しない）。
対象はTOPIX100（現構成を遡って使用＝生存者バイアスあり）。株価は分割調整済み・配当未調整。売買の推奨ではありません。</p>
<nav>{nav}</nav>{''.join(body)}</body></html>"""
    (HERE / f"gallery_{tag}.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "base"):
        gallery("base_5_25_75", (5, 25, 75), "基本設定 5/25/75日線")
    if which in ("all", "app"):
        gallery("app_25_50_75", (25, 50, 75), "証券アプリ設定 25/50/75日線")
