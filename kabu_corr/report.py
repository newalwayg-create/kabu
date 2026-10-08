"""グラフ(PNG)と Markdown レポートの出力。"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from . import analysis as A  # noqa: E402
from .config import BASE_KEY, INSTRUMENTS, by_key  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
TEXT, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
DIVERGING = LinearSegmentedColormap.from_list("blue_gray_red", ["#2a78d6", "#f0efec", "#e34948"])

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "axes.titlecolor": TEXT,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 2,
        "legend.frameon": False,
    }
)


def _label(key: str) -> str:
    i = by_key().get(key)
    if i is None:
        return key
    return f"{key} (prev US)" if i.market == "US" else key


def heatmap(corr: pd.DataFrame, title: str, path: Path) -> None:
    n = len(corr)
    fig, ax = plt.subplots(figsize=(0.55 * n + 3, 0.5 * n + 2))
    ax.grid(False)
    im = ax.imshow(corr.to_numpy(), cmap=DIVERGING, vmin=-1, vmax=1)
    ax.set_xticks(range(n), [_label(c) for c in corr.columns], rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(n), [_label(c) for c in corr.index], fontsize=8)
    for i in range(n):
        for j in range(n):
            v = corr.iat[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5,
                        color="white" if abs(v) > 0.6 else TEXT)
    fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02, label="correlation")
    ax.set_title(title, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def lines(df: pd.DataFrame, title: str, ylabel: str, path: Path, hline: float | None = None) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for color, col in zip(SERIES, df.columns):
        s = df[col].dropna()
        ax.plot(s.index, s.to_numpy(), color=color, label=_label(col))
    if hline is not None:
        ax.axhline(hline, color=MUTED, linewidth=1)
    ax.set_title(title, loc="left")
    ax.set_ylabel(ylabel)
    ax.legend(loc="lower left", ncol=len(df.columns), fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def lead_lag_bars(ll: pd.DataFrame, title: str, path: Path) -> None:
    cols = list(ll.columns)
    keys = list(ll.index)
    width = 0.8 / len(cols)
    fig, ax = plt.subplots(figsize=(max(8, len(keys) * 0.9), 4.2))
    palette = ["#c3c2b7", "#8d8c85", SERIES[0], SERIES[1], "#52514e"][: len(cols)]
    for i, (c, color) in enumerate(zip(cols, palette)):
        ax.bar(np.arange(len(keys)) + (i - (len(cols) - 1) / 2) * width, ll[c].to_numpy(),
               width=width * 0.9, color=color, label=c)
    ax.set_xticks(range(len(keys)), keys, rotation=30, ha="right", fontsize=8)
    ax.axhline(0, color=MUTED, linewidth=1)
    ax.set_ylabel(f"corr with {BASE_KEY}(t)")
    ax.set_title(title, loc="left")
    ax.legend(ncol=len(cols), fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def scatter(x: pd.Series, y: pd.Series, fit: dict, title: str, path: Path) -> None:
    df = pd.concat([x, y], axis=1).dropna() * 100
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(df.iloc[:, 0], df.iloc[:, 1], s=14, color=SERIES[0], alpha=0.45,
               edgecolors=SURFACE, linewidths=0.5)
    xs = np.linspace(df.iloc[:, 0].min(), df.iloc[:, 0].max(), 50)
    b0, b1 = fit["coef"].iloc[0] * 100, fit["coef"].iloc[1]
    ax.plot(xs, b0 + b1 * xs, color=SERIES[1])
    ax.text(0.02, 0.97, f"y = {b1:.2f}x {b0:+.3f}\nR² = {fit['r2']:.3f}  n = {fit['n']}",
            transform=ax.transAxes, va="top", fontsize=9, color=TEXT)
    ax.set_xlabel(f"{_label(x.name)} return (%)")
    ax.set_ylabel(f"{y.name} (%)")
    ax.set_title(title, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _fmt_table(df: pd.DataFrame, digits: int = 3) -> str:
    def fmt(v):
        if isinstance(v, (float, np.floating)):
            if not np.isfinite(v):
                return "-"
            return f"{v:.2e}" if 0 < abs(v) < 10 ** -digits else f"{v:.{digits}f}"
        return str(v)

    cols = [df.index.name or "", *map(str, df.columns)]
    lines_ = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for idx, row in df.iterrows():
        lines_.append("| " + " | ".join([str(idx), *(fmt(v) for v in row)]) + " |")
    return "\n".join(lines_)


def build_report(aligned: dict[str, pd.DataFrame], out_dir: Path, window: int = 60) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ret = aligned["returns"]
    parts = aligned["jp_parts"]
    names = {i.key: i.name_ja for i in INSTRUMENTS}
    present = [i.key for i in INSTRUMENTS if i.key in ret.columns]
    others = [k for k in present if k != BASE_KEY]
    us_keys = [k for k in others if by_key()[k].market == "US"]
    jp_semi = [k for k in present if by_key()[k].group == "semi_jp"]

    md: list[str] = []
    md.append("# 日経平均・先物・時間外・半導体株・SOX・ダウ 相関分析レポート\n")
    md.append(f"- 期間: {ret.index.min():%Y-%m-%d} 〜 {ret.index.max():%Y-%m-%d}（日本の営業日 {len(ret):,} 日）")
    md.append("- リターン: 日次の対数リターン")
    md.append("- **時差の扱い**: 米国銘柄・CME先物は「その日の東京寄付き前に終わった直近セッション」"
              "（＝前夜）の値を対応させています。表中の `(prev US)` はこの意味です。\n")

    md.append("## 対象銘柄\n")
    md.append("| キー | 名称 | 市場 |\n|---|---|---|")
    for k in present:
        md.append(f"| {k} | {names[k]} | {'東京' if by_key()[k].market == 'JP' else '米国/CME(前夜)'} |")
    md.append("")

    # 1. 相関行列
    corr = A.correlation_matrix(ret[present])
    corr.to_csv(out_dir / "correlation_matrix.csv")
    heatmap(corr, "Daily return correlation (US = previous night)", out_dir / "correlation_heatmap.png")
    md.append("## 1. 相関行列\n")
    md.append("![correlation](correlation_heatmap.png)\n")

    # 2. 日経平均との相関ランキング
    tbl = A.correlation_table(ret[present], BASE_KEY)
    tbl.insert(0, "name", [names[k] for k in tbl.index])
    tbl.to_csv(out_dir / "n225_correlation_ranking.csv")
    md.append(f"## 2. 日経平均({BASE_KEY})との相関ランキング\n")
    md.append(_fmt_table(tbl))
    md.append("")

    # 3. ラグ相関
    ll = A.lead_lag(ret, BASE_KEY, us_keys + [k for k in jp_semi])
    ll.to_csv(out_dir / "lead_lag.csv")
    lead_lag_bars(ll.loc[us_keys], f"Lead-lag: corr({BASE_KEY}(t), X(t-k))", out_dir / "lead_lag.png")
    md.append("## 3. ラグ相関（どちらが先に動くか）\n")
    md.append("`lag+k` = 日経平均(t) と X(t-k) の相関。米国銘柄では **lag+0 が前夜の米国市場**、"
              "**lag-1 が東京引け後の米国市場**（東京→NYの波及）、lag+1 は前々夜です。\n")
    md.append("![lead-lag](lead_lag.png)\n")
    md.append(_fmt_table(ll))
    md.append("")

    # 4. 時間外と寄付きギャップ
    md.append("## 4. 時間外の動きと日経平均の「寄付きギャップ」「日中値動き」\n")
    md.append("日経平均の日次リターンを **ギャップ(前日終値→寄付)** と **日中(寄付→終値)** に分解し、"
              "前夜の米国市場・CME先物（時間外）がどちらを説明しているかを見ます。\n")
    rows = []
    for k in us_keys:
        for target in ["N225_GAP", "N225_INTRADAY"]:
            r, n, p = A.corr_with_pvalue(parts[target], ret[k])
            hit, _ = A.direction_hit_rate(parts[target], ret[k])
            rows.append({"X(prev US)": k, "target": target, "corr": r, "方向一致率": hit, "n": n, "p_value": p})
    if "CME_OVERNIGHT" in parts:
        for target in ["N225_GAP", "N225_INTRADAY"]:
            r, n, p = A.corr_with_pvalue(parts[target], parts["CME_OVERNIGHT"])
            hit, _ = A.direction_hit_rate(parts[target], parts["CME_OVERNIGHT"])
            rows.append({"X(prev US)": "CME_OVERNIGHT", "target": target, "corr": r, "方向一致率": hit, "n": n, "p_value": p})
    gap_tbl = pd.DataFrame(rows).set_index("X(prev US)")
    gap_tbl.to_csv(out_dir / "overnight_gap.csv")
    md.append(_fmt_table(gap_tbl))
    md.append("\n`CME_OVERNIGHT` = CME日経先物の直近終値 ÷ 前日の日経平均終値（直近20日の中央値ベーシスを控除）"
              "＝東京市場が閉まっている間（時間外）に先物が織り込んだ変動の推定値です。\n")

    gap_x = "CME_OVERNIGHT" if "CME_OVERNIGHT" in parts else ("SOX" if "SOX" in ret else None)
    if gap_x:
        xs = parts[gap_x] if gap_x == "CME_OVERNIGHT" else ret[gap_x]
        fit = A.ols(parts["N225_GAP"], xs.to_frame(gap_x))
        scatter(xs.rename(gap_x), parts["N225_GAP"], fit, f"{gap_x} vs Nikkei opening gap",
                out_dir / "gap_scatter.png")
        md.append("![gap](gap_scatter.png)\n")

    # 5. 回帰
    md.append("## 5. 重回帰: 日経平均リターンを前夜の米国市場で説明する\n")
    reg_sets = [["SOX", "DJI"], ["SOX", "DJI", "USDJPY"]]
    for xs_keys in reg_sets:
        xs_keys = [k for k in xs_keys if k in ret]
        if not xs_keys:
            continue
        fit = A.ols(ret[BASE_KEY], ret[xs_keys])
        df = pd.DataFrame({"係数(β)": fit["coef"], "t値": fit["t"]}).rename_axis("説明変数")
        md.append(f"**{BASE_KEY} ~ {' + '.join(xs_keys)}**  (R² = {fit['r2']:.3f}, 自由度調整済R² = {fit['adj_r2']:.3f}, n = {fit['n']})\n")
        md.append(_fmt_table(df, 4))
        md.append("")
    if jp_semi and "SOX" in ret:
        md.append("**日本の半導体株 ~ 前夜のSOX（β = SOXが1%動いた時の平均的な反応）**\n")
        rows = []
        for k in jp_semi:
            fit = A.ols(ret[k], ret[["SOX"]])
            rows.append({"key": k, "name": names[k], "beta_SOX": fit["coef"]["SOX"], "R2": fit["r2"], "n": fit["n"]})
        md.append(_fmt_table(pd.DataFrame(rows).set_index("key")))
        md.append("")

    # 6. ローリング相関
    roll_keys = [k for k in ["NK_FUT_CME", "SOX", "DJI", "TEL"] if k in ret][:4]
    if roll_keys:
        rc = A.rolling_corr(ret, BASE_KEY, roll_keys, window)
        rc.to_csv(out_dir / "rolling_corr.csv")
        lines(rc, f"Rolling {window}-day correlation with {BASE_KEY}", "correlation",
              out_dir / "rolling_corr.png", hline=0)
        md.append(f"## 6. ローリング相関（{window}営業日）\n")
        md.append("相関の強さは時期によって変わります。直近の関係性を確認してください。\n")
        md.append("![rolling](rolling_corr.png)\n")
        latest = rc.dropna(how="all").iloc[-1]
        md.append("直近値: " + ", ".join(f"{k} = {v:.2f}" for k, v in latest.items()) + "\n")

    # 7. 年別
    yc = A.yearly_corr(ret, BASE_KEY, [k for k in ["NK_FUT_CME", "SOX", "DJI", "NVDA", "TEL"] if k in ret])
    yc.to_csv(out_dir / "yearly_corr.csv")
    md.append("## 7. 年別の相関\n")
    md.append(_fmt_table(yc))
    md.append("")

    md.append("## 読み方の注意\n")
    md.append("- 相関は因果関係を意味しません。共通要因（金利・為替・リスク選好など）で同時に動いている可能性があります。")
    md.append("- CME先物は東京の取引時間中にも取引されるため、`NK_FUT_CME`(前夜終値の前日比) には"
              "東京時間の動きも含まれます。純粋な時間外の動きは `CME_OVERNIGHT` を参照してください。")
    md.append("- 日経平均の「始値」は 9:00 時点でまだ寄り付いていない銘柄を前日終値で計算するため、"
              "前夜の動きを織り込みきれません。その残りが `N225_INTRADAY` と前夜の米国市場との正の相関として現れます"
              "（個別株は寄付きが実際の約定値なので、この現象はほとんど出ません）。")
    md.append("- `NK_FUT_CME` と `USDJPY` の日足は東京の取引時間も含むため、lag-1（同じ日付の値）でも相関が出ます。")
    md.append("- Yahoo Finance の `NIY=F` は多くの日が出来高0・四本値が同じ足（清算値のみ）で、通常の足より時間外指標としての精度が落ちます。"
              "終値の記録時刻も年によって一定でないようで（例: 2021年は前夜の値より同じ日付の値の方が日経平均と強く連動）、CME先物を使った結果は SOX・ダウを使った結果より割り引いて見てください。")
    md.append("- p値は正規近似です。日次リターンは裾が厚いため、目安として扱ってください。")

    path = out_dir / "report.md"
    path.write_text("\n".join(md), encoding="utf-8")
    return path
