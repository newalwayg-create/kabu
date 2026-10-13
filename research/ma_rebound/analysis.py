"""移動平均線の下にある銘柄の反発パターン検証（本体）.

定義（すべて当日の終値までの情報で判定 = 先読みなし）
- MA: 単純移動平均（終値）。基本 短期5 / 中期25 / 長期75
- パターン: 終値より上にある MA の組み合わせ（7通り）。グループ0 = 3本すべてが終値以下
- 長期線の傾き: MA_long[t] と MA_long[t-k] の比較（基本 k=20）。上向き / 下向き（同値は除外）
- エントリー: 翌営業日(t+1)の始値。H日リターン = close[t+H] / open[t+1] - 1
- 最大下落幅(MAE): min(low[t+1..t+H]) / open[t+1] - 1
- MA到達: high[t+1..t+H] の最大値が、シグナル日 t の各MAの値以上になったか（目標値は t 時点で固定）
- 指数: 日経平均(^N225) と TOPIX連動ETF(1306)。同じ t+1 始値→t+H 終値のリターンを差し引いて超過リターン
- 信頼区間: 月単位のクラスター・ブートストラップ（2,000回）。同日・近接日の事例は強く相関するため、
  日単位の独立を仮定した t 検定は使わない
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from universe import UNIVERSE

D = Path(__file__).resolve().parent / "data"
HORIZONS = (5, 10, 20)
PATTERNS = {  # (短期, 中期, 長期) が終値より上 → パターン番号
    (1, 0, 0): 1, (0, 1, 0): 2, (0, 0, 1): 3, (1, 1, 0): 4,
    (1, 0, 1): 5, (0, 1, 1): 6, (1, 1, 1): 7, (0, 0, 0): 0,
}
PNAME = {0: "G0 3本すべて下(株価が上)", 1: "P1 短期のみ上", 2: "P2 中期のみ上", 3: "P3 長期のみ上",
         4: "P4 短期+中期", 5: "P5 短期+長期", 6: "P6 中期+長期", 7: "P7 3本すべて上"}
RNG = np.random.default_rng(20261013)


def load_prices() -> dict[str, pd.DataFrame]:
    p = pd.read_csv(D / "prices.csv", parse_dates=["date"], dtype={"code": str})
    return {c: g.set_index("date").sort_index() for c, g in p.groupby("code")}


def index_features(px: pd.DataFrame, tag: str) -> pd.DataFrame:
    o, c = px["open"], px["close"]
    f = pd.DataFrame(index=px.index)
    f[f"{tag}_day"] = c.pct_change()
    for n in (5, 25, 75):
        f[f"{tag}_above{n}"] = (c > c.rolling(n).mean()).astype(float).where(c.rolling(n).mean().notna())
    for h in HORIZONS:
        f[f"{tag}_ret{h}"] = c.shift(-h) / o.shift(-1) - 1
    return f


def macd_hist(c: pd.Series) -> pd.Series:
    m = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    return m - m.ewm(span=9, adjust=False).mean()


def stock_features(df: pd.DataFrame, s=5, m=25, l=75, k=20) -> pd.DataFrame:
    o, h, lo, c, v = (df[x] for x in ("open", "high", "low", "close", "volume"))
    f = pd.DataFrame(index=df.index)
    f["close"] = c
    mas = {"s": c.rolling(s).mean(), "m": c.rolling(m).mean(), "l": c.rolling(l).mean()}
    for key, ser in mas.items():
        f[f"ma_{key}"] = ser
        f[f"up_{key}"] = (ser > c).astype(int)
    f["pattern"] = [PATTERNS[t] for t in zip(f.up_s, f.up_m, f.up_l)]
    diff = mas["l"] - mas["l"].shift(k)
    f["slope"] = np.where(diff > 0, "上向き", np.where(diff < 0, "下向き", None))
    valid = mas["l"].notna() & mas["l"].shift(k).notna()
    entry = o.shift(-1)
    for H in HORIZONS:
        f[f"ret{H}"] = c.shift(-H) / entry - 1
        fut_low = pd.concat([lo.shift(-i) for i in range(1, H + 1)], axis=1).min(axis=1)
        fut_high = pd.concat([h.shift(-i) for i in range(1, H + 1)], axis=1).max(axis=1)
        f[f"mae{H}"] = fut_low / entry - 1
        for key in ("s", "m", "l"):
            f[f"reach{H}_{key}"] = (fut_high >= mas[key]).astype(float)
    # 足・出来高の特徴量（t 時点まで）
    f["vol_ratio"] = v / v.shift(1).rolling(20).mean()
    rng = (h - lo).replace(0, np.nan)
    f["lower_shadow"] = (np.minimum(o, c) - lo) / rng
    f["bull"] = ((c > o) & (c > c.shift(1))).astype(int)
    body = (c - o).abs() / c
    f["body_max3"] = body.rolling(3).max()
    mh = macd_hist(c)
    f["macd_h"] = mh
    rising = (mh > mh.shift(1)) & (mh < 0)
    f["macd_rise_n"] = rising.astype(int).groupby((~rising).cumsum()).cumsum()
    f = f[valid & f["slope"].notna()]
    return f


def build(prices, idx_feat, s=5, m=25, l=75, k=20) -> pd.DataFrame:
    rows = []
    for code in UNIVERSE:
        if code not in prices:
            continue
        f = stock_features(prices[code], s, m, l, k)
        f["code"] = code
        rows.append(f)
    allf = pd.concat(rows).reset_index()
    allf = allf.merge(idx_feat, left_on="date", right_index=True, how="left")
    allf["month"] = allf["date"].dt.to_period("M").astype(str)
    allf["group"] = allf["pattern"].map(PNAME) + "｜" + allf["slope"]
    for H in HORIZONS:
        allf[f"ex_n225_{H}"] = allf[f"ret{H}"] - allf[f"n225_ret{H}"]
        allf[f"ex_topix_{H}"] = allf[f"ret{H}"] - allf[f"topix_ret{H}"]
    return allf


# ---------- 統計 ----------
def _month_sums(df, col):
    g = df.dropna(subset=[col]).groupby("month")[col]
    return g.sum(), g.count()


def boot_ci(df, col, base=None, reps=2000):
    """月クラスター・ブートストラップ。base を渡すと (グループ平均 - 基準平均) の CI も返す."""
    s, n = _month_sums(df, col)
    months = s.index if base is None else s.index.union(_month_sums(base, col)[0].index)
    s = s.reindex(months, fill_value=0).to_numpy()
    n = n.reindex(months, fill_value=0).to_numpy()
    w = RNG.multinomial(len(months), np.full(len(months), 1 / len(months)), size=reps)
    means = (w @ s) / np.maximum(w @ n, 1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    if base is None:
        return lo, hi, None, None
    bs, bn = _month_sums(base, col)
    bs = bs.reindex(months, fill_value=0).to_numpy()
    bn = bn.reindex(months, fill_value=0).to_numpy()
    d = means - (w @ bs) / np.maximum(w @ bn, 1)
    dlo, dhi = np.percentile(d, [2.5, 97.5])
    return lo, hi, dlo, dhi


def summarize(df, base, H, col_prefix="ret"):
    col = f"{col_prefix}{H}" if col_prefix == "ret" else f"{col_prefix}_{H}"
    x = df[col].dropna()
    if len(x) == 0:
        return {}
    lo, hi, dlo, dhi = boot_ci(df, col, base)
    bmean = base[col].mean()
    return {"件数": len(x), "銘柄数": df.loc[x.index, "code"].nunique(),
            "平均%": x.mean() * 100, "中央値%": x.median() * 100, "勝率%": (x > 0).mean() * 100,
            "95%CI下%": lo * 100, "95%CI上%": hi * 100,
            "全日比 差%": (x.mean() - bmean) * 100, "差CI下%": dlo * 100, "差CI上%": dhi * 100}


def reliability(n_events, n_months):
    if n_events < 300 or n_months < 24:
        return "低（件数少）"
    if n_events < 1500:
        return "中"
    return "高"
