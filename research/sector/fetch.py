"""業種バスケットの株価・売買代金と、金利・原油・SOX のデータを取得する。"""
import json
from pathlib import Path
import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parents[2] / "data" / "research" / "sector"
BASKETS = {
    "半導体":      {"8035": "東京エレクトロン", "6857": "アドバンテスト", "6920": "レーザーテック", "7735": "SCREEN", "6146": "ディスコ",
                   "6723": "ルネサス", "6526": "ソシオネクスト", "3436": "SUMCO", "4062": "イビデン", "285A": "キオクシア"},
    "AI活用・ITサービス": {"4307": "野村総研", "6702": "富士通", "6701": "NEC", "6532": "ベイカレント", "3626": "TIS", "4684": "オービック",
                   "6098": "リクルート", "4689": "LINEヤフー"},
    "サイバーセキュリティ": {"4704": "トレンドマイクロ", "3692": "FFRI", "2326": "デジタルアーツ", "4475": "HENNGE", "4493": "サイバーセキュリティクラウド",
                   "4417": "GSX"},
    "医薬品":      {"4502": "武田薬品", "4503": "アステラス", "4519": "中外製薬", "4568": "第一三共", "4523": "エーザイ"},
    "食品":        {"2802": "味の素", "2502": "アサヒGHD", "2503": "キリンHD", "2914": "JT", "2801": "キッコーマン", "2269": "明治HD"},
    "陸運":        {"9020": "JR東日本", "9022": "JR東海", "9021": "JR西日本", "9005": "東急", "9064": "ヤマトHD"},
    "銀行":        {"8306": "三菱UFJ", "8316": "三井住友FG", "8411": "みずほFG", "8308": "りそなHD", "7182": "ゆうちょ銀行"},
    "保険":        {"8766": "東京海上", "8725": "MS&AD", "8630": "SOMPO", "8750": "第一生命", "7181": "かんぽ生命"},
    "海運":        {"9101": "日本郵船", "9104": "商船三井", "9107": "川崎汽船"},
}
FACTORS = {"^TNX": "米10年金利", "2510.T": "国内債券ETF", "BZ=F": "ブレント原油", "^SOX": "SOX", "1306.T": "TOPIX ETF", "JPY=X": "ドル円"}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    tick = [c + ".T" for b in BASKETS.values() for c in b]
    raw = yf.download(tick + list(FACTORS), start="2018-01-01", auto_adjust=False, progress=False, group_by="ticker", threads=True)
    raw.to_pickle(OUT / "raw.pkl")
    shares = {}
    for t in tick:
        try:
            i = yf.Ticker(t).info
            shares[t] = (i.get("sharesOutstanding") or (i.get("marketCap") or 0) / (i.get("currentPrice") or 1)), i.get("marketCap")
        except Exception as e:
            shares[t] = (None, None)
    json.dump({"baskets": BASKETS, "factors": FACTORS, "shares": shares}, open(OUT / "meta.json", "w"), ensure_ascii=False)
    print("tickers", len(tick), "rows", len(raw), "missing", [t for t in tick if t not in raw.columns.get_level_values(0) or raw[t]["Close"].dropna().empty])
