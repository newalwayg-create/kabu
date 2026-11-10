"""週単位の売買に「向いている」銘柄の候補を出す（上がる銘柄の予測ではない）。

条件:
- 週の値幅がそこそこある（週次の値動きの標準偏差 3.5〜8%）
- 売買しやすい（直近60日の1日平均売買代金 10億円以上）
- 上昇トレンドの中にある（終値が75日線の上、75日線が1か月前より上）
- 先週急騰していない（先週の値動き +5%以下。検証で「先週大きく上げた株の翌週は負けやすい」と出たため）
- 25日線から大きく離れていない（-6%〜+4%）
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "research" / "sector33"))
from quality_screen import MORE  # noqa: E402
from similar_screen import EXTRA  # noqa: E402
from universe import SECTORS  # noqa: E402

ADD = "4417 3042 4498 4447 5028 3692 4475 2326 4704 6701 3040 4493 6526 6723 6963 285A 6920 7735 6525 6323 7729 6728 6856 4004 4186 4369 5384 4062 4980 3778 9984 6758 6857 8035 6146 3436 5803 5802 5801 7011 7012 7013".split()


def main():
    codes = sorted({c for m in SECTORS.values() for c in m} | set(EXTRA) | set(MORE) | set(ADD))
    T = [c + ".T" for c in codes]
    d = yf.download(T, start="2025-06-01", progress=False, auto_adjust=False, threads=True)
    C, V = d["Close"], d["Volume"]
    rows = []
    for t in T:
        p = C[t].dropna()
        if len(p) < 120:
            continue
        w = p.resample("W-FRI").last().pct_change().dropna().iloc[-52:]
        ma25 = p.rolling(25).mean(); ma75 = p.rolling(75).mean()
        dl = p.diff(); up = dl.clip(lower=0).ewm(alpha=1 / 14).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1 / 14).mean()
        rows.append({"t": t, "株価": p.iloc[-1], "週の振れ%": w.std() * 100, "代金億": (V[t].iloc[-60:] * p.iloc[-60:]).mean() / 1e8,
                     "75日線%": (p.iloc[-1] / ma75.iloc[-1] - 1) * 100, "75日線の傾き%": (ma75.iloc[-1] / ma75.iloc[-21] - 1) * 100,
                     "25日線%": (p.iloc[-1] / ma25.iloc[-1] - 1) * 100, "先週%": (p.iloc[-1] / p.iloc[-6] - 1) * 100,
                     "RSI": (100 - 100 / (1 + up / dn)).iloc[-1], "週で+5%以上あった割合": (w >= 0.05).mean(), "週で-5%以下あった割合": (w <= -0.05).mean()})
    S = pd.DataFrame(rows).set_index("t")
    ok = S[S["週の振れ%"].between(3.5, 8) & (S["代金億"] >= 10) & (S["75日線%"] > 0) & (S["75日線の傾き%"] > 0)
           & (S["先週%"] <= 5) & S["25日線%"].between(-6, 4)]
    names = {}
    for t in ok.index:
        try:
            names[t] = yf.Ticker(t).info.get("shortName")
        except Exception:
            names[t] = None
    ok = ok.assign(名前=pd.Series(names)).sort_values("週の振れ%", ascending=False)
    pd.set_option("display.width", 300)
    print("全体", len(S), "候補", len(ok))
    print(ok[["名前", "株価", "週の振れ%", "週で+5%以上あった割合", "週で-5%以下あった割合", "代金億", "25日線%", "75日線%", "75日線の傾き%", "先週%", "RSI"]].round(1).to_string())


if __name__ == "__main__":
    main()
