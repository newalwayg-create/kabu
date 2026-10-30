"""日本株のセクター間資金移動（ローテーション）分析.

業種・テーマごとの大型株バスケット（等ウェイト）について
  - TOPIX(1306) 対比の相対リターン（1週・1か月・3か月）
  - 売買代金シェアの変化（直近20営業日 ÷ その前60営業日）= 資金流入の代理指標
  - TOPIX に対するベータ（120営業日）= ディフェンシブ度
  - 半導体バスケットとの相関（60営業日）= 半導体の受け皿かどうか
を計算し output/flow_analysis.{csv,md} に出力する.

    python scripts/flow_analysis.py
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parents[1] / "output"
BENCH = "1306.T"  # TOPIX連動ETF

# (区分, バスケット名, 銘柄コード)  区分はグラデーション確認用の大まかな性格
BASKETS = [
    ("グロース/景気敏感", "半導体", "8035 6857 6920 7735 6146 6723 4062 6526"),
    ("グロース/景気敏感", "AI電線・データセンター", "5803 5802 5801 6501"),
    ("グロース/景気敏感", "サイバーセキュリティ", "4704 3692 4493 2326 4417 4475 3040"),
    ("グロース/景気敏感", "防衛・重工", "7011 7012 7013"),
    ("グロース/景気敏感", "電子部品", "6981 6762 6971 6762 6963"),
    ("景気敏感(外需)", "自動車", "7203 7267 6902 7269 7270"),
    ("景気敏感(外需)", "海運", "9101 9104 9107"),
    ("景気敏感(外需)", "商社", "8058 8031 8001 8053 8002"),
    ("景気敏感(外需)", "化学・素材", "4063 4005 4188 3407 5401"),
    ("金利敏感", "銀行", "8306 8316 8411 8331 8354"),
    ("金利敏感", "保険", "8766 8725 8630 8750"),
    ("金利敏感", "不動産", "8801 8802 8830 3289"),
    ("内需景気", "建設", "1801 1802 1803 1812 1925 1928"),
    ("内需景気", "小売(百貨店・インバウンド)", "3099 8233 7532 9983"),
    ("内需景気", "外食", "7550 3197 7581 3563 9936 2702 3397 2695 7611 9887 3543 7616 9861"),
    ("内需景気", "レジャー・エンタメ", "4661 7974 9697 9766"),
    ("ディフェンシブ", "小売(生活必需)", "8267 3382 3088 9843 7516"),
    ("ディフェンシブ", "鉄道・陸運", "9020 9022 9021 9005 9064"),
    ("ディフェンシブ", "通信", "9432 9433 9434"),
    ("ディフェンシブ", "食品・飲料", "2914 2802 2502 2503 2269 2801"),
    ("ディフェンシブ", "医薬品", "4502 4568 4519 4503 4523"),
    ("ディフェンシブ", "電力・ガス", "9501 9503 9502 9531 9532"),
]


def load(tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = yf.download(tickers, period="1y", auto_adjust=True, progress=False, threads=True)
    close = raw["Close"].dropna(how="all")
    vol = raw["Volume"].reindex(close.index)
    return close, vol


def basket_stats(close, vol, codes, bench_ret, semi_ret):
    tk = [f"{c}.T" for c in dict.fromkeys(codes.split())]
    tk = [t for t in tk if t in close and close[t].notna().sum() > 150]
    px = close[tk].ffill()
    ret = px.pct_change(fill_method=None).mean(axis=1)  # 等ウェイト日次リターン
    idx = (1 + ret.fillna(0)).cumprod()
    tv = (px * vol[tk]).sum(axis=1)  # 売買代金
    b = (1 + bench_ret.fillna(0)).cumprod()

    def rel(n):
        return round(((idx.iloc[-1] / idx.iloc[-1 - n]) / (b.iloc[-1] / b.iloc[-1 - n]) - 1) * 100, 1)

    def absr(n):
        return round((idx.iloc[-1] / idx.iloc[-1 - n] - 1) * 100, 1)

    r120, b120 = ret.iloc[-120:], bench_ret.iloc[-120:]
    beta = np.cov(r120, b120)[0, 1] / np.var(b120, ddof=1)
    return {
        "銘柄数": len(tk),
        "1W%": absr(5), "1M%": absr(21), "3M%": absr(63),
        "対TOPIX 1W": rel(5), "対TOPIX 1M": rel(21), "対TOPIX 3M": rel(63),
        "_tv": tv,
        "ベータ": round(beta, 2),
        "半導体相関60d": round(ret.iloc[-60:].corr(semi_ret.iloc[-60:]), 2),
    }, idx


def main():
    codes = sorted({c for *_, s in BASKETS for c in s.split()})
    close, vol = load([f"{c}.T" for c in codes] + [BENCH])
    bench_ret = close[BENCH].pct_change(fill_method=None)
    semi_tk = [f"{c}.T" for c in BASKETS[0][2].split()]
    semi_ret = close[semi_tk].pct_change(fill_method=None).mean(axis=1)

    rows, idxs = [], {}
    for grp, name, cs in BASKETS:
        st, idx = basket_stats(close, vol, cs, bench_ret, semi_ret)
        rows.append({"区分": grp, "バスケット": name, **st})
        idxs[name] = idx
    df = pd.DataFrame(rows)

    # 売買代金シェア: 全バスケット合計に占める割合の変化
    tv = pd.concat({r["バスケット"]: r["_tv"] for r in rows}, axis=1)
    share = tv.div(tv.sum(axis=1), axis=0)
    recent, prior = share.iloc[-20:].mean(), share.iloc[-80:-20].mean()
    df["売買代金シェア%(直近20日)"] = df["バスケット"].map((recent * 100).round(2))
    df["シェア変化(倍)"] = df["バスケット"].map((recent / prior).round(2))
    tv_ratio = tv.iloc[-20:].mean() / tv.iloc[-80:-20].mean()
    df["売買代金増減(倍)"] = df["バスケット"].map(tv_ratio.round(2))
    df = df.drop(columns="_tv")

    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / "flow_analysis.csv", index=False, encoding="utf-8-sig")
    # 1か月の相対リターンを週次で追う（ローテーションの時系列）
    weekly = pd.DataFrame({k: v for k, v in idxs.items()})
    b = (1 + bench_ret.fillna(0)).cumprod()
    relw = weekly.div(b, axis=0).iloc[-65:].resample("W-FRI").last()
    relw = (relw / relw.iloc[0] - 1).mul(100).round(1).T
    relw.columns = [c.strftime("%m/%d") for c in relw.columns]
    relw.to_csv(OUT / "flow_weekly_relative.csv", encoding="utf-8-sig")

    end = close.index[-1].date()
    md = [f"# セクター資金移動分析（{end} 時点, Yahoo Finance）\n",
          "等ウェイトの大型株バスケット。売買代金シェア変化 = 直近20営業日のシェア ÷ その前60営業日のシェア。\n",
          df.sort_values("対TOPIX 1M", ascending=False).to_markdown(index=False, floatfmt="g"),
          "\n\n## 対TOPIX 累積相対リターン（直近13週, %）\n",
          relw.to_markdown(floatfmt="g")]
    (OUT / "flow_analysis.md").write_text("\n".join(md), encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(df.sort_values("対TOPIX 1M", ascending=False).to_string(index=False))
    print(relw.to_string())


if __name__ == "__main__":
    main()
