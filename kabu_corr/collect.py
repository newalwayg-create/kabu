"""Yahoo Finance から日足データを取得して CSV に保存する。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import INSTRUMENTS, by_ticker

PRICE_COLUMNS = ["open", "high", "low", "close", "volume"]


def download(tickers: list[str], start: str, end: str | None = None) -> pd.DataFrame:
    """縦持ち(long)の価格表 [date, ticker, open, high, low, close, volume] を返す。"""
    import yfinance as yf  # ネットワーク不要な分析時に import を強制しない

    raw = yf.download(
        tickers,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        progress=False,
        threads=True,
    )
    frames = []
    for t in tickers:
        if t not in raw.columns.get_level_values(0):
            continue
        df = raw[t].rename(columns=str.lower)[PRICE_COLUMNS].dropna(subset=["close"])
        if df.empty:
            continue
        df = df.reset_index().rename(columns={"Date": "date", "index": "date"})
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
        df.insert(1, "ticker", t)
        frames.append(df)
    if not frames:
        raise RuntimeError(
            "データを1件も取得できませんでした。ネットワーク接続（Yahoo Finance への到達性）を確認してください。"
        )
    return pd.concat(frames, ignore_index=True)


def collect(out_path: Path, start: str, end: str | None = None) -> pd.DataFrame:
    tickers = [i.ticker for i in INSTRUMENTS]
    prices = download(tickers, start, end)
    missing = sorted(set(tickers) - set(prices["ticker"]))
    if missing:
        names = ", ".join(f"{t}({by_ticker()[t].name_ja})" for t in missing)
        print(f"[warn] 取得できなかった銘柄: {names}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(out_path, index=False)
    print(f"保存しました: {out_path} ({len(prices):,} 行, {prices['ticker'].nunique()} 銘柄)")
    return prices


def load_prices(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"])
