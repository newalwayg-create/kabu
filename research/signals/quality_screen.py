"""テーマに頼らず、業績が安定していて株価も強い銘柄を探す。

株価の「強さの安定度」を中心に並べる。
- 3年（2023年10月以降）のシャープ比、年率リターン、値動きの荒さ、最大下落
- 上昇の安定度: 対数株価を直線で近似したときの決定係数（R²。1に近いほど一直線に上がっている）
- 3か月ごとに区切ったとき、TOPIX（1306）に勝った割合
- 市場が崩れた日（TOPIXが-2%以下）の平均の値動き
ファンダ（ROE、利益・売上の伸び、PER）はYahoo Financeから取り、条件を満たす銘柄だけ残す。
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "research" / "sector33"))
from similar_screen import EXTRA  # noqa: E402
from universe import SECTORS  # noqa: E402

MORE = """4684 9843 7532 4543 6098 4661 4502 2802 8697 4519 3038 2269 2914 4452 7974 6367 8591 4568 7741 4063 3391 3141 9989 2730 8279
3349 7564 9267 2229 2875 1878 9672 4732 2670 3092 4681 7867 9020 9433 9432 9434 2801 2502 2503 4911 4901 8058 8001 6501 6503 7011 4507
8766 8725 8630 9983 7453 3088 3099 8233 2501 2282 2264 2212 9831 3197 7550 3048 7202 6869 4528 4523 4578 4151 4887 9735 2433 4324 9602
9603 3659 9697 9766 6460 4751 2371 3994 6200 9086 9364 9065 9076 9064 9147 9022 9021 9005 9007 9008 9001 9042 9048 4755 3769 4385""".split()


def main():
    codes = sorted({c for m in SECTORS.values() for c in m} | set(EXTRA) | set(MORE))
    T = [c + ".T" for c in codes]
    d = yf.download(T + ["1306.T"], start="2023-07-01", progress=False, auto_adjust=True, threads=True)["Close"]
    r = d.pct_change(fill_method=None).clip(-.3, .3)
    tp = r["1306.T"].copy(); tp[tp.abs() > .1] = np.nan
    start = "2023-10-20"
    q = pd.date_range(start, d.index[-1], freq="QE")
    crash = tp <= -0.02
    rows = []
    for t in T:
        p = d[t].loc[start:].dropna() if t in d else pd.Series(dtype=float)
        if len(p) < 600:
            continue
        x = r[t].loc[start:].dropna(); nav = (1 + x).cumprod()
        y = np.log(p.to_numpy()); X = np.arange(len(y))
        b = np.polyfit(X, y, 1); r2 = 1 - ((y - np.polyval(b, X)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        qs = (1 + x).resample("QE").prod() - 1; qt = (1 + tp.loc[start:]).resample("QE").prod() - 1
        rows.append({"t": t, "株価": p.iloc[-1], "年率%": (nav.iloc[-1] ** (250 / len(x)) - 1) * 100, "ボラ%": x.std() * np.sqrt(250) * 100,
                     "シャープ": x.mean() / x.std() * np.sqrt(250), "最大下落%": (nav / nav.cummax() - 1).min() * 100,
                     "上昇の安定度R2": r2 * np.sign(b[0]), "四半期でTOPIXに勝った割合": (qs > qt.reindex(qs.index)).mean(),
                     "暴落日%": x[crash.reindex(x.index).fillna(False)].mean() * 100,
                     "75日線%": (p.iloc[-1] / p.rolling(75).mean().iloc[-1] - 1) * 100})
    S = pd.DataFrame(rows).set_index("t")
    pre = S[(S["シャープ"] >= 0.8) & (S["ボラ%"] <= 32) & (S["最大下落%"] >= -30) & (S["上昇の安定度R2"] >= 0.6) & (S["株価"] <= 8000)]
    info = {}
    for t in pre.index:
        try:
            i = yf.Ticker(t).info
        except Exception:
            i = {}
        info[t] = {"名前": i.get("shortName"), "PER": i.get("trailingPE"), "予PER": i.get("forwardPE"), "ROE%": (i.get("returnOnEquity") or np.nan) * 100,
                   "配当%": i.get("dividendYield"), "売上伸び%": (i.get("revenueGrowth") or np.nan) * 100, "利益伸び%": (i.get("earningsGrowth") or np.nan) * 100}
    I = pd.DataFrame(info).T
    for c in I.columns.drop("名前"):
        I[c] = pd.to_numeric(I[c], errors="coerce")
    F = pre.join(I)
    F = F[(F["ROE%"] >= 10) & ((F["売上伸び%"] > 0) | F["売上伸び%"].isna())]
    z = lambda s: (s - s.mean()) / s.std()  # noqa: E731
    F["総合点"] = z(F["シャープ"]) + z(F["上昇の安定度R2"]) + z(F["四半期でTOPIXに勝った割合"]) + z(F["暴落日%"]) - z(F["ボラ%"]) * 0.5
    pd.set_option("display.width", 320); pd.set_option("display.max_rows", 60)
    cols = ["名前", "株価", "PER", "予PER", "ROE%", "配当%", "売上伸び%", "利益伸び%", "年率%", "ボラ%", "シャープ", "最大下落%", "上昇の安定度R2", "四半期でTOPIXに勝った割合", "暴落日%", "75日線%", "総合点"]
    print("全体", len(S), "株価条件通過", len(pre), "最終", len(F))
    print(F.sort_values("総合点", ascending=False)[cols].round(2).to_string())


if __name__ == "__main__":
    main()
