"""比較に使うETFの日足（株式分割を補正）を data/research/etf.pkl に保存する。"""
from pathlib import Path
import pandas as pd
import yfinance as yf
from earnings_study import fix_splits

OUT = Path(__file__).resolve().parents[1] / "data" / "research" / "etf.pkl"
T = {"1321.T": "日経225ETF", "1475.T": "TOPIX ETF", "1655.T": "S&P500 ETF", "200A.T": "日経半導体ETF", "2644.T": "日本半導体ETF"}

if __name__ == "__main__":
    px = yf.download(list(T), start="2019-01-01", auto_adjust=True, progress=False)["Close"]
    pd.to_pickle({v: fix_splits(px[k]) for k, v in T.items()}, OUT)
    print("saved", OUT)
