"""33業種の代表銘柄の株価・売買代金・発行株数と、金利・原油・SOX を取得する。"""
import json
from pathlib import Path
import pandas as pd
import yfinance as yf
from universe import SECTORS

OUT = Path(__file__).resolve().parents[2] / "data" / "research" / "sector33"
FACTORS = ["^TNX", "2510.T", "BZ=F", "^SOX", "1306.T"]

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    tick = [c + ".T" for s in SECTORS.values() for c in s]
    raw = yf.download(tick + FACTORS, start="2018-01-01", auto_adjust=False, progress=False, group_by="ticker", threads=True)
    raw.to_pickle(OUT / "raw.pkl")
    info = {}
    for t in tick:
        try:
            i = yf.Ticker(t).info
            info[t] = {"shares": i.get("sharesOutstanding") or ((i.get("marketCap") or 0) / (i.get("currentPrice") or 1)) or None,
                       "industry": i.get("industry"), "name": i.get("shortName")}
        except Exception as e:
            info[t] = {"shares": None, "error": str(e)[:60]}
    json.dump(info, open(OUT / "info.json", "w"), ensure_ascii=False)
    miss = [t for t in tick if t not in raw.columns.get_level_values(0) or raw[t]["Close"].dropna().empty]
    print("tickers", len(tick), "missing price", miss, "missing shares", [t for t, v in info.items() if not v.get("shares")])
