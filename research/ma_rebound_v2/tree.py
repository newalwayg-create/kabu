"""樹形図の構築（探索期間のみで分岐を決め、検証期間には同じ定義をそのまま当てはめる）."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

MIN_N = 100  # 1つの枝の独立事例がこれ未満なら分岐しない


def candidate_splits(pattern: int):
    """(要素ファミリー, 表示名, 条件関数) のリスト。条件は t 時点の情報のみ."""
    if pattern == 0:
        dev = [(f"乖離 ≥+{int(t*100)}%（25日線より上）", (lambda d, t=t: d.dev_near >= t)) for t in (0.02, 0.04, 0.06)]
    else:
        dev = [(f"乖離 ≤−{int(t*100)}%（最も近い上の線から）", (lambda d, t=t: d.dev_near <= -t)) for t in (0.02, 0.04, 0.06)]
    out = [("乖離率", n, f) for n, f in dev]
    out += [("出来高", f"出来高 ≥{t}倍", (lambda d, t=t: d.vol_ratio >= t)) for t in (1.0, 1.5, 2.0)]
    out += [("足の形", "反転陽線あり", lambda d: d.bull == 1),
            ("足の形", "下ヒゲ ≥30%", lambda d: d.lower_shadow >= 0.3),
            ("足の形", "下ヒゲ ≥50%", lambda d: d.lower_shadow >= 0.5),
            ("足の形", "直近3本の実体 ≤1.0%", lambda d: d.body_max3 <= 0.010),
            ("足の形", "直近3本の実体 ≤1.5%", lambda d: d.body_max3 <= 0.015)]
    out += [("MACD", "MACDヒスト縮小 ≥1日", lambda d: d.macd_rise_n >= 1),
            ("MACD", "MACDヒスト縮小 ≥2日連続", lambda d: d.macd_rise_n >= 2)]
    out += [("TOPIXの位置", "TOPIXが25日線の上", lambda d: d.tpx_above25 == 1),
            ("TOPIXの位置", "TOPIXが75日線の上", lambda d: d.tpx_above75 == 1)]
    return out


@dataclass
class Node:
    label: str
    path: list = field(default_factory=list)   # [(表示名, 条件関数, True/False)]
    children: list = field(default_factory=list)
    stats_ex: dict = field(default_factory=dict)
    stats_te: dict = field(default_factory=dict)
    note: str = ""
    split_rank: pd.DataFrame | None = None


def apply_path(df: pd.DataFrame, path) -> pd.DataFrame:
    m = pd.Series(True, index=df.index)
    for _, f, val in path:
        c = f(df).fillna(False).astype(bool)
        m &= c if val else ~c
    return df[m]


def rank_splits(ex: pd.DataFrame, pattern: int, used: set) -> pd.DataFrame:
    rows = []
    for fam, name, f in candidate_splits(pattern):
        if fam in used:
            continue
        c = f(ex).fillna(False).astype(bool)
        a, b = ex[c].ret20.dropna(), ex[~c].ret20.dropna()
        ok = len(a) >= MIN_N and len(b) >= MIN_N
        rows.append({"要素": fam, "条件": name, "該当 件数": len(a), "非該当 件数": len(b),
                     "該当 平均%": a.mean() * 100 if len(a) else np.nan,
                     "非該当 平均%": b.mean() * 100 if len(b) else np.nan,
                     "該当 上昇%": (a > 0).mean() * 100 if len(a) else np.nan,
                     "非該当 上昇%": (b > 0).mean() * 100 if len(b) else np.nan,
                     "平均の差pt": (a.mean() - b.mean()) * 100 if ok else np.nan,
                     "両側100件以上": ok, "_f": f})
    r = pd.DataFrame(rows)
    r["|差|"] = r["平均の差pt"].abs()
    return r.sort_values("|差|", ascending=False, na_position="last")


def grow(node: Node, ex_all, te_all, pattern: int, used: set, depth: int, max_depth: int, stats, order=None):
    """order が与えられた場合、深さ d では order[d] の要素で分岐（閾値はその要素内で探索期間の差が最大のもの）."""
    ex = apply_path(ex_all, node.path)
    te = apply_path(te_all, node.path)
    node.stats_ex, node.stats_te = stats(ex), stats(te)
    n = len(ex.ret20.dropna())
    if n < MIN_N:
        node.note = "事例不足（100件未満）"
        return
    if n < 2 * MIN_N:
        node.note = "分岐停止（分けると片側が100件未満）"
        return
    if depth >= max_depth:
        return
    rk = rank_splits(ex, pattern, used)
    node.split_rank = rk.drop(columns=["_f"])
    pool = rk if order is None else rk[rk["要素"] == order[depth]]
    best = pool[pool["両側100件以上"]].head(1)
    if best.empty:
        node.note = "分岐停止（分けると片側が100件未満）"
        return
    b = best.iloc[0]
    for val in (True, False):
        lab = b["条件"] if val else f"非（{b['条件']}）"
        ch = Node(label=lab, path=node.path + [(b["条件"], b["_f"], val)])
        node.children.append(ch)
        grow(ch, ex_all, te_all, pattern, used | {b["要素"]}, depth + 1, max_depth, stats, order)


def flatten(node: Node, depth=0, parent=""):
    rows = [{"深さ": depth, "枝": " → ".join([p[0] if p[2] else f"非（{p[0]}）" for p in node.path]) or "(第2階層)",
             **{f"探索 {k}": v for k, v in node.stats_ex.items()},
             **{f"検証 {k}": v for k, v in node.stats_te.items()}, "注記": node.note}]
    for c in node.children:
        rows += flatten(c, depth + 1)
    return rows
