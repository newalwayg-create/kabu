"""v2 共通処理: 特徴量・事例（初日のみ）・統計.

先読み防止: すべての条件はシグナル日 t の終値（とそれ以前）だけで計算する。
リターン・到達・最大下落は t より後のデータで計算する（結果側のみ）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ma_rebound"))
from universe import UNIVERSE  # noqa: E402

D = HERE / "data"
START, EXPLORE_END, TEST_START, END = "2020-06-01", "2024-12-30", "2025-01-01", "2026-10-13"
MAS = (25, 50, 75)
SLOPE_K = 20
PATTERNS = {(1, 0, 0): 1, (0, 1, 0): 2, (0, 0, 1): 3, (1, 1, 0): 4, (1, 0, 1): 5, (0, 1, 1): 6, (1, 1, 1): 7,
            (0, 0, 0): 0}
PNAME = {0: "G0 株価が3本の上", 1: "P1 25日のみ上", 2: "P2 50日のみ上", 3: "P3 75日のみ上", 4: "P4 25+50日",
         5: "P5 25+75日", 6: "P6 50+75日", 7: "P7 3本すべて上"}
RNG = np.random.default_rng(20261013)


def load_prices() -> dict[str, pd.DataFrame]:
    p = pd.read_csv(D / "prices.csv", parse_dates=["date"], dtype={"code": str})
    return {c: g.set_index("date").sort_index() for c, g in p.groupby("code")}


def topix_frame(prices) -> pd.DataFrame:
    t = prices["1306.T"]
    c = t["close"]
    f = pd.DataFrame(index=t.index)
    f["tpx_open"], f["tpx_close"] = t["open"], c
    f["tpx_ret20_past"] = c / c.shift(20) - 1          # 直近20営業日の騰落（t時点で既知）
    for n in (25, 75):
        ma = c.rolling(n).mean()
        f[f"tpx_above{n}"] = (c > ma).astype(float).where(ma.notna())
    return f


def macd_hist(c: pd.Series) -> pd.Series:
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    return m - m.ewm(span=9, adjust=False).mean()


def stock_frame(df: pd.DataFrame, tpx: pd.DataFrame) -> pd.DataFrame:
    o, h, lo, c, v = (df[x] for x in ("open", "high", "low", "close", "volume"))
    f = pd.DataFrame(index=df.index)
    f["open"], f["high"], f["low"], f["close"] = o, h, lo, c
    for n in MAS:
        f[f"ma{n}"] = c.rolling(n).mean()
        f[f"up{n}"] = (f[f"ma{n}"] > c).astype(int)
    f["pattern"] = [PATTERNS[t] for t in zip(f.up25, f.up50, f.up75)]
    d = f.ma75 - f.ma75.shift(SLOPE_K)
    f["slope"] = np.where(d > 0, "上向き", np.where(d < 0, "下向き", None))
    for k in (10, 40):
        d2 = f.ma75 - f.ma75.shift(k)
        f[f"slope{k}"] = np.where(d2 > 0, "上向き", np.where(d2 < 0, "下向き", None))
    # 乖離率: 株価の上にある線のうち最も近い線までの距離（G0 は 25日線からの乖離）
    above = f[[f"ma{n}" for n in MAS]].where(f[[f"up{n}" for n in MAS]].to_numpy() == 1)
    nearest = above.min(axis=1)
    f["dev_near"] = np.where(f.pattern == 0, c / f.ma25 - 1, c / nearest - 1)
    f["vol_ratio"] = v / v.shift(1).rolling(20).mean()
    rng = (h - lo).replace(0, np.nan)
    f["lower_shadow"] = (np.minimum(o, c) - lo) / rng
    f["bull"] = ((c > o) & (c > c.shift(1))).astype(int)
    f["body_max3"] = ((c - o).abs() / c).rolling(3).max()
    mh = macd_hist(c)
    rising = (mh > mh.shift(1)) & (mh < 0)
    f["macd_rise_n"] = rising.astype(int).groupby((~rising).cumsum()).cumsum()
    f = f.join(tpx, how="left")
    # 結果側（t+1 以降）
    nxt_open = o.shift(-1)
    for H in (5, 10, 20):
        f[f"ret{H}"] = c.shift(-H) / nxt_open - 1
        f[f"ret{H}_close"] = c.shift(-H) / c - 1
        f[f"tpx_ret{H}"] = f.tpx_close.shift(-H) / f.tpx_open.shift(-1) - 1
        f[f"ex{H}"] = f[f"ret{H}"] - f[f"tpx_ret{H}"]
    return f


def build_all(prices, gap: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """全日データ(all_days) と 事例(events: 状態に入った初日のみ) を返す.

    gap: 条件から外れた日数が gap 日以下で同じ状態に戻った場合は同一事例として扱う（新事例にしない）
    """
    tpx = topix_frame(prices)
    alld, evs = [], []
    for code in UNIVERSE:
        if code not in prices:
            continue
        f = stock_frame(prices[code], tpx)
        f["code"] = code
        f = f[f.ma75.notna() & f.ma75.shift(SLOPE_K).notna() & f.slope.notna()]
        f["state"] = f.pattern.astype(str) + "_" + f.slope.astype(str)
        ev = first_days(f, gap)          # 期間で切る前に判定（期間開始日に「初日」が人工的に生じないように）
        alld.append(f.loc[START:END])
        evs.append(ev.loc[START:END])
    return pd.concat(alld).reset_index(names="date"), pd.concat(evs).reset_index(names="date")


def first_days(f: pd.DataFrame, gap: int) -> pd.DataFrame:
    """各状態について、状態に入った初日のみを抽出。gap 日以内の中断は継続とみなす."""
    idx = np.arange(len(f))
    keep = np.zeros(len(f), dtype=bool)
    last_seen: dict[str, int] = {}
    states = f["state"].to_numpy()
    for i in idx:
        s = states[i]
        prev = last_seen.get(s)
        if prev is None or i - prev - 1 > gap:
            keep[i] = True
        last_seen[s] = i
    return f[keep]


PURGE_FROM = "2024-12-03"  # 探索期間の最後の約20営業日は、結果(20日後)が検証期間に入るため除く


def period(df: pd.DataFrame, which: str) -> pd.DataFrame:
    if which == "探索":
        return df[(df.date >= START) & (df.date < PURGE_FROM)]
    return df[(df.date >= TEST_START) & (df.date <= END)]


def stats(x: pd.DataFrame, H: int = 20) -> dict:
    r = x[f"ret{H}"].dropna()
    e = x[f"ex{H}"].dropna()
    return {"件数": len(r), "銘柄数": x.loc[r.index, "code"].nunique() if len(r) else 0,
            "上昇割合%": (r > 0).mean() * 100 if len(r) else np.nan,
            "平均%": r.mean() * 100 if len(r) else np.nan, "中央値%": r.median() * 100 if len(r) else np.nan,
            "対TOPIX超過%": e.mean() * 100 if len(e) else np.nan}


def boot_diff(x: pd.DataFrame, base: pd.DataFrame, col: str, reps: int = 2000):
    """月クラスター・ブートストラップで (x平均 - base平均) の95%CI."""
    x = x.dropna(subset=[col]); base = base.dropna(subset=[col])
    if len(x) < 10:
        return np.nan, np.nan
    m = lambda d: d.date.dt.to_period("M").astype(str)
    xs = x.groupby(m(x))[col].agg(["sum", "count"]); bs = base.groupby(m(base))[col].agg(["sum", "count"])
    months = xs.index.union(bs.index)
    xs = xs.reindex(months, fill_value=0); bs = bs.reindex(months, fill_value=0)
    w = RNG.multinomial(len(months), np.full(len(months), 1 / len(months)), size=reps)
    d = (w @ xs["sum"].to_numpy()) / np.maximum(w @ xs["count"].to_numpy(), 1) - \
        (w @ bs["sum"].to_numpy()) / np.maximum(w @ bs["count"].to_numpy(), 1)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return lo * 100, hi * 100
