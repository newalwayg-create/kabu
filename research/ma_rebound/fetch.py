"""株価データ取得（yfinance, auto_adjust=False = 分割調整済み・配当未調整）.

Yahoo の配当調整は 8766 東京海上 2026-09-29 の配当(122.5円)を分割前ベースで計上する誤りがあり、
過去株価が約23%歪むため、配当調整は使わない（リターンは配当を含まない値上がり益のみ）。

出力: data/prices.csv (date, code, open, high, low, close, volume)
      data/fetch_log.csv (取得結果・失敗銘柄)
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from universe import INDEXES, UNIVERSE

D = Path(__file__).resolve().parent / "data"
START = "2015-10-01"
END = "2026-10-14"  # 2026-10-13 を含む


def get(sym: str) -> pd.DataFrame:
    for attempt in range(4):
        try:
            df = yf.Ticker(sym).history(start=START, end=END, auto_adjust=False, actions=False)
            if len(df):
                return df
        except Exception:
            pass
        time.sleep(2 ** attempt)
    return pd.DataFrame()


def main() -> None:
    D.mkdir(exist_ok=True)
    frames, log = [], []
    targets = [(f"{c}.T", c, n) for c, n in UNIVERSE.items()] + [(s, s, n) for s, n in INDEXES.items()]
    for sym, code, name in targets:
        df = get(sym)
        if df.empty:
            log.append({"code": code, "name": name, "status": "FAILED", "rows": 0})
            continue
        df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
        # Yahoo 側の分割未調整の異常値（例: 1306.T 2026-03-30/31 だけ 1/10 の水準）を補正:
        # 前後11日の中央値から3倍以上離れた日を、比率を丸めた倍率で修正する
        med = df["close"].rolling(11, center=True, min_periods=3).median()
        ratio = med / df["close"]
        bad = (ratio > 3) | (ratio < 1 / 3)
        for dt in df.index[bad]:
            f = round(ratio[dt]) if ratio[dt] > 1 else 1 / round(1 / ratio[dt])
            df.loc[dt, ["open", "high", "low", "close"]] *= f
            df.loc[dt, "volume"] /= f
            log.append({"code": code, "name": name, "status": f"ADJUSTED x{f:g} on {dt.date()}", "rows": 0})
        df.index = pd.to_datetime(df.index.date)
        df.index.name = "date"
        df["code"] = code
        frames.append(df.reset_index())
        log.append({"code": code, "name": name, "status": "OK", "rows": len(df),
                    "first": df.index.min().date(), "last": df.index.max().date()})
        time.sleep(0.3)
    pd.concat(frames).to_csv(D / "prices.csv", index=False)
    lg = pd.DataFrame(log)
    lg["fetched_at_jst"] = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    lg.to_csv(D / "fetch_log.csv", index=False)
    print(lg[lg.status != "OK"])
    print(lg.status.value_counts())
    print(lg[["rows"]].describe().T)


if __name__ == "__main__":
    main()
