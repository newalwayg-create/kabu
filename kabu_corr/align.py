"""日米の取引時間のずれを考慮して、日本の営業日ベースのリターン表を作る。

東京市場の営業日 T に対して:
  * JP 銘柄 … 当日の値 (前日終値→当日終値 など)
  * US 銘柄 … 「T の寄付き前に終わった直近セッション」までの変化
              = 前夜の米国市場 / CME先物の夜間取引（時間外）の動き
米国が祝日の日や日本が連休明けの日も、終値ベースで正しく累積される。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BASE_KEY, by_ticker


def to_wide(prices: pd.DataFrame, field: str) -> pd.DataFrame:
    """long 形式の価格表から key を列にした wide 表を作る。"""
    tick = by_ticker()
    df = prices[prices["ticker"].isin(tick)].copy()
    df["key"] = df["ticker"].map(lambda t: tick[t].key)
    return df.pivot_table(index="date", columns="key", values=field, aggfunc="last").sort_index()


def jp_calendar(prices: pd.DataFrame) -> pd.DatetimeIndex:
    """日経平均の取引日を日本の営業日カレンダーとする。"""
    close = to_wide(prices, "close")
    if BASE_KEY not in close:
        raise ValueError(f"基準銘柄 {BASE_KEY} のデータがありません")
    return pd.DatetimeIndex(close[BASE_KEY].dropna().index)


def us_close_before(us_close: pd.Series, cal: pd.DatetimeIndex) -> pd.Series:
    """各営業日 T について、T より前(<T)の日付の直近終値を返す。"""
    s = us_close.dropna()
    left = pd.DataFrame({"date": cal})
    right = pd.DataFrame({"us_date": s.index, "value": s.to_numpy()})
    merged = pd.merge_asof(
        left, right, left_on="date", right_on="us_date",
        direction="backward", allow_exact_matches=False,
    )
    return pd.Series(merged["value"].to_numpy(), index=cal, name=us_close.name)


def build_aligned(prices: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """分析用の整列済みデータを返す。

    返り値:
      levels   … 営業日T時点で観測可能な価格水準 (JP: 当日終値, US: 前夜終値)
      returns  … levels の対数リターン (JP: 前日比, US: 前夜までの変化)
      jp_parts … 日経平均を「時間外(前日終値→寄付)」と「日中(寄付→終値)」に分解
    """
    keys = by_ticker()
    close = to_wide(prices, "close")
    opn = to_wide(prices, "open")
    cal = jp_calendar(prices)

    market = {i.key: i.market for i in keys.values()}
    levels = {}
    for k in close.columns:
        if market.get(k) == "JP":
            levels[k] = close[k].reindex(cal)
        else:
            levels[k] = us_close_before(close[k], cal)
    levels = pd.DataFrame(levels, index=cal)
    returns = np.log(levels).diff().iloc[1:]

    n225_close = close[BASE_KEY].reindex(cal)
    n225_open = opn[BASE_KEY].reindex(cal)
    prev_close = n225_close.shift(1)
    jp_parts = pd.DataFrame(
        {
            # 前日終値→当日寄付: 時間外に起きた変動が寄付きで反映された分
            "N225_GAP": np.log(n225_open / prev_close),
            # 当日寄付→当日終値: 東京の取引時間中の変動
            "N225_INTRADAY": np.log(n225_close / n225_open),
        },
        index=cal,
    ).iloc[1:]

    if "NK_FUT_CME" in levels:
        # 時間外の推定変動: CME日経先物の直近終値 vs 前日の日経平均終値
        # （先物と現物のベーシスは短期ではほぼ一定なので、変化の大きさを捉えるには十分）
        basis = np.log(levels["NK_FUT_CME"] / n225_close.shift(1))
        jp_parts["CME_OVERNIGHT"] = (basis - basis.rolling(20, min_periods=5).median().shift(1)).iloc[1:]

    return {"levels": levels, "returns": returns, "jp_parts": jp_parts}
