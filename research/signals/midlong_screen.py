"""中長期（数か月〜1年）で持つ候補を探す。S株で少しずつ買う前提なので、株価の上限は置かない。

1. 株価の質（過去3年）: 年率リターン、シャープ比、上昇の安定度（対数株価の直線近似の R²）、
   3か月ごとに市場平均に勝った割合、最大下落、市場が崩れた日の値動き、米SOXとの連動
2. 業績（Yahoo Finance）: ROE、売上・利益の伸び、PER（実績・予想）、PBR、配当利回り
3. 今の買いやすさ: 200日線・75日線からの位置、RSI、1年高値からの位置

条件: 3年の年率リターン > 0、シャープ比 >= 0.4、売買代金 3億円以上、
      ROE >= 8%、売上の伸び > 0、実績PER <= 30（赤字は除く）
点数: 業績（ROE・売上の伸び・利益の伸び）、株価の質（シャープ比・R²・勝率）、割安さ（予想PER）、
      買いやすさ（75日線に近く、RSIが高すぎない）の順位の平均
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1] / "research" / "sector33"))
from daytrade_screen import CHEAP  # noqa: E402
from quality_screen import MORE  # noqa: E402
from similar_screen import EXTRA  # noqa: E402
from swing_candidates import ADD  # noqa: E402
from swing_lot_candidates import WIDE  # noqa: E402
from universe import SECTORS  # noqa: E402


def main():
    codes = sorted({c for m in SECTORS.values() for c in m} | set(EXTRA) | set(MORE) | set(ADD) | set(CHEAP) | set(WIDE))
    T = [c + ".T" for c in codes]
    d = yf.download(T + ["^SOX"], period="3y", progress=False, auto_adjust=True, threads=True)
    C, V = d["Close"], d["Volume"]
    sox = C["^SOX"].pct_change()
    J = C[T].dropna(how="all")
    R = J.pct_change().where(lambda x: x.abs() < 0.3)
    M = R.mean(axis=1)
    crash = M[M <= -0.02].index

    rows = []
    for t in T:
        p = J[t].dropna()
        if len(p) < 600:
            continue
        r = R[t].dropna()
        yrs = len(p) / 245
        ann = (p.iloc[-1] / p.iloc[0]) ** (1 / yrs) - 1
        lp = np.log(p.values); x = np.arange(len(lp))
        r2 = np.corrcoef(x, lp)[0, 1] ** 2 * np.sign(np.polyfit(x, lp, 1)[0])
        q = (1 + r).resample("QE").prod() - 1; qm = (1 + M.reindex(r.index)).resample("QE").prod() - 1
        both = pd.concat([r, sox.reindex(r.index).shift(1)], axis=1).dropna()
        ma200, ma75 = p.rolling(200).mean().iloc[-1], p.rolling(75).mean().iloc[-1]
        dl = p.diff(); up = dl.clip(lower=0).ewm(alpha=1 / 14).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1 / 14).mean()
        rows.append({"t": t, "株価": p.iloc[-1], "代金億": (C[t] * V[t]).iloc[-60:].mean() / 1e8,
                     "年率%": ann * 100, "シャープ": r.mean() / r.std() * np.sqrt(245), "R2": r2,
                     "四半期勝率%": (q > qm).mean() * 100, "最大下落%": ((p / p.cummax()) - 1).min() * 100,
                     "急落日%": r.reindex(crash).mean() * 100, "SOX連動": both.cov().iloc[0, 1] / both.iloc[:, 1].var(),
                     "200日線%": (p.iloc[-1] / ma200 - 1) * 100, "75日線%": (p.iloc[-1] / ma75 - 1) * 100,
                     "RSI": (100 - 100 / (1 + up / dn)).iloc[-1], "1年高値から%": (p.iloc[-1] / p.iloc[-245:].max() - 1) * 100})
    S = pd.DataFrame(rows).set_index("t")
    pre = S[(S["年率%"] > 0) & (S["シャープ"] >= 0.4) & (S["代金億"] >= 3)]

    fund = {}
    for t in pre.index:
        try:
            i = yf.Ticker(t).info
        except Exception:
            continue
        fund[t] = {"名前": i.get("shortName"), "業種": i.get("industry"), "ROE%": (i.get("returnOnEquity") or np.nan) * 100,
                   "売上の伸び%": (i.get("revenueGrowth") or np.nan) * 100, "利益の伸び%": (i.get("earningsGrowth") or np.nan) * 100,
                   "PER": i.get("trailingPE"), "予想PER": i.get("forwardPE"), "PBR": i.get("priceToBook"),
                   "配当%": i.get("dividendYield")}
    F = pre.join(pd.DataFrame(fund).T, how="inner")
    for c in ["ROE%", "売上の伸び%", "利益の伸び%", "PER", "予想PER", "PBR", "配当%"]:
        F[c] = pd.to_numeric(F[c], errors="coerce")
    F = F[(F["ROE%"] >= 8) & (F["売上の伸び%"] > 0) & (F["PER"] > 0) & (F["PER"] <= 30)]
    entry = -(F["75日線%"].abs()) - (F["RSI"] - 55).clip(lower=0)
    fpe = F["予想PER"].where(F["予想PER"] > 3)  # 明らかにおかしい予想PERは除く
    F["点数"] = (F["ROE%"].rank(pct=True) + F["売上の伸び%"].rank(pct=True) + F["利益の伸び%"].rank(pct=True, na_option="bottom")
               + F["シャープ"].rank(pct=True) + F["R2"].rank(pct=True) + F["四半期勝率%"].rank(pct=True)
               + (-fpe).rank(pct=True, na_option="bottom") + entry.rank(pct=True)) / 8
    F = F.sort_values("点数", ascending=False)
    out = HERE.parents[1] / "data" / "research" / "midlong_screen.csv"
    F.to_csv(out)
    pd.set_option("display.width", 320); pd.set_option("display.max_rows", 200)
    print(f"対象 {len(S)} → 株価の条件 {len(pre)} → 業績の条件 {len(F)}")
    cols = ["名前", "業種", "株価", "点数", "ROE%", "売上の伸び%", "利益の伸び%", "PER", "予想PER", "PBR", "配当%",
            "年率%", "シャープ", "R2", "四半期勝率%", "最大下落%", "急落日%", "SOX連動", "200日線%", "75日線%", "RSI", "1年高値から%"]
    print(F[cols].head(40).round(2).to_string())


if __name__ == "__main__":
    main()
