"""動作確認用の合成データ（ネットワークなしでパイプラインを試すため）。

実際の市場データではありません。米国市場の動きが翌営業日の東京に波及する
構造を持たせた乱数データです。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import INSTRUMENTS


def make_prices(start: str = "2021-01-01", end: str = "2025-12-31", seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, end)
    n = len(days)
    us_cal = days[rng.random(n) > 0.04]
    jp_cal = days[rng.random(n) > 0.06]

    # 米国側の共通要因（米国の日付ごと）
    mkt = pd.Series(rng.normal(0, 0.009, n), index=days)
    semi = pd.Series(rng.normal(0, 0.012, n), index=days)
    fx = pd.Series(rng.normal(0, 0.005, n), index=days)
    us_ret = {
        "DJI": mkt,
        "SOX": 1.2 * mkt + semi,
        "USDJPY": fx + 0.1 * mkt,
    }
    for k, b in [("NVDA", 1.4), ("AMD", 1.3), ("AVGO", 1.1), ("TSM", 1.0), ("MU", 1.3)]:
        us_ret[k] = 0.8 * us_ret["SOX"] * b / 1.2 + pd.Series(rng.normal(0, 0.012, n), index=days)

    # 東京: 前日(米国日付 D-1)の米国の動き + 東京独自の動き
    prev_mkt, prev_semi, prev_fx = mkt.shift(1).fillna(0), semi.shift(1).fillna(0), fx.shift(1).fillna(0)
    jp_own = pd.Series(rng.normal(0, 0.007, n), index=days)
    gap = 0.6 * prev_mkt + 0.25 * prev_semi + 0.3 * prev_fx
    intraday = jp_own
    jp_ret = {"N225": gap + intraday}
    for k, b in [("TEL", 1.6), ("ADVANTEST", 1.8), ("LASERTEC", 2.0), ("SCREEN", 1.5),
                 ("DISCO", 1.5), ("RENESAS", 1.1)]:
        jp_ret[k] = 0.6 * jp_ret["N225"] + b * 0.5 * prev_semi + pd.Series(rng.normal(0, 0.012, n), index=days)

    # CME先物: 東京の動き + その夜の米国の動き（D の夜に東京 D+1 の寄付きを先取り）
    us_ret["NK_FUT_CME"] = intraday + 0.6 * mkt + 0.25 * semi + 0.3 * fx

    key2ticker = {i.key: i.ticker for i in INSTRUMENTS}
    rows = []
    for k, r in {**us_ret, **jp_ret}.items():
        cal = us_cal if k in us_ret else jp_cal
        r = r.cumsum()
        close = 100 * np.exp(r)
        if k == "N225":
            open_ = close.shift(1) * np.exp(gap)
        else:
            open_ = close * np.exp(rng.normal(0, 0.002, n))
        df = pd.DataFrame({"date": days, "open": open_, "close": close}).set_index("date").loc[cal]
        df["high"] = df[["open", "close"]].max(axis=1)
        df["low"] = df[["open", "close"]].min(axis=1)
        df["volume"] = 0
        df["ticker"] = key2ticker[k]
        rows.append(df.rename_axis("date").reset_index())
    out = pd.concat(rows, ignore_index=True)
    return out[["date", "ticker", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
