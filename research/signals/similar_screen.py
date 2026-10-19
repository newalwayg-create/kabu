"""東陽テクニカ・テクノ菱和に「株価・ファンダ・テクニカル」が似た銘柄を探す。

業種は問わない。2銘柄の特徴から条件を決め、条件の中心にどれだけ近いかで並べる。
1) 株価とテクニカル（移動平均線との距離、RSI、高値からの下落率、1年の値動き、値動きの荒さ）を全銘柄で計算
2) ゆるい条件を通った銘柄だけ、Yahoo Financeから PER・PBR・ROE・配当・成長率を取る
3) 2銘柄の値を中心にした距離で並べる
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "sector33"))
from universe import SECTORS  # noqa: E402

EXTRA = """6278 6315 6331 6355 6339 6407 6413 6436 6457 6461 6463 6470 6480 6486 6498 6588 6617 6644 6653 6674 6703 6798 6800 6804 6807 6809 6817 6855
6877 6923 6927 6934 6941 6951 6955 6962 6995 6996 6997 7276 8020 8074 8075 8078 8088 8096 8130 8133 9810 3156 3107 3132 3626 4768 9719 4739 9759
4812 2327 4709 3916 4733 9682 2317 3762 4686 4743 4722 3844 1720 1721 1813 1820 1821 1833 1860 1885 1893 1934 1945 1946 1949 1414 4021 4118 4183
4202 4205 4212 4626 4631 4958 5232 5393 5463 5480 5698 5727 5741 3405 4045 4114 4401 4403 2154 2181 4544 9744 9755 2471 9622 4666 7752 8154 7537
8141 9880 7419 1969 1961 1979 1980 1952 1975 1982 1942 1944 1959 1951 1417 1950 1968 1983 1963 6366 6330 7433 8159 2331 6651 6727 6914 4826 3036
6875 2760 6849 6371 7272 6136 6474 6103 5703 5706 5016 5801 4475 4704 2326 6701 3692 1965 8151 6268 6324 6383 6481 6506 6645 6273 5714 5713 5711 6479""".split()
REF = {"8151.T": "東陽テクニカ", "1965.T": "テクノ菱和"}


def rsi(s, n=14):
    d = s.diff(); up = d.clip(lower=0).ewm(alpha=1 / n).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n).mean()
    return 100 - 100 / (1 + up / dn)


def main():
    codes = sorted({c for m in SECTORS.values() for c in m} | set(EXTRA))
    T = [c + ".T" for c in codes]
    d = yf.download(T + ["^N225", "8035.T", "6857.T", "6146.T", "3436.T"], start="2022-01-01", progress=False, auto_adjust=True, threads=True)
    C = d["Close"]; V = d["Volume"]
    r = C.pct_change(fill_method=None).clip(-.3, .3)
    semi = r[["8035.T", "6857.T", "6146.T", "3436.T"]].mean(axis=1)
    wk = lambda s: (1 + s.fillna(0)).cumprod().resample("W-FRI").last().pct_change()  # noqa: E731
    sw = wk(semi); tw = wk(r["^N225"]); weak = sw <= sw.quantile(.2)
    rows = []
    for t in T:
        p = C[t].dropna() if t in C else pd.Series(dtype=float)
        if len(p) < 300:
            continue
        W = (wk(r[t]) - tw).dropna(); m = weak.reindex(W.index).fillna(False)
        rows.append({"t": t, "株価": p.iloc[-1], "25日線%": (p.iloc[-1] / p.rolling(25).mean().iloc[-1] - 1) * 100,
                     "75日線%": (p.iloc[-1] / p.rolling(75).mean().iloc[-1] - 1) * 100, "RSI": rsi(p).iloc[-1],
                     "高値から%": (p.iloc[-1] / p.iloc[-250:].max() - 1) * 100, "1年%": (p.iloc[-1] / p.iloc[-250] - 1) * 100,
                     "ボラ%": r[t].iloc[-500:].std() * np.sqrt(250) * 100, "半導体安週%": W[m].mean() * 100,
                     "代金億": (V[t].iloc[-60:] * p.iloc[-60:]).mean() / 1e8,
                     "シャープ": r[t].loc["2024":].mean() / r[t].loc["2024":].std() * np.sqrt(250)})
    S = pd.DataFrame(rows).set_index("t")
    pre = S[(S["株価"] <= 4000) & (S["ボラ%"] <= 42) & (S["75日線%"].abs() <= 10) & (S["RSI"].between(30, 65)) & (S["高値から%"].between(-40, -3)) & (S["代金億"] >= 0.5)]
    pre = pd.concat([pre, S.loc[[k for k in REF if k in S.index and k not in pre.index]]])
    info = {}
    for t in pre.index:
        try:
            i = yf.Ticker(t).info
        except Exception:
            i = {}
        info[t] = {"名前": i.get("shortName"), "PER": i.get("trailingPE"), "PBR": i.get("priceToBook"), "ROE%": (i.get("returnOnEquity") or np.nan) * 100,
                   "配当%": i.get("dividendYield"), "売上伸び%": (i.get("revenueGrowth") or np.nan) * 100, "利益伸び%": (i.get("earningsGrowth") or np.nan) * 100}
    I = pd.DataFrame(info).T
    for c in I.columns.drop("名前"):
        I[c] = pd.to_numeric(I[c], errors="coerce")
    F = pre.join(I)
    # 2銘柄を中心にした距離（各項目を、中心からのずれ ÷ 許容幅 で測る）
    center = {"株価": (2000, 1000), "PER": (13.5, 4), "PBR": (1.65, 0.8), "ROE%": (15, 7), "配当%": (3.2, 1.0), "25日線%": (-1.5, 6),
              "75日線%": (1.2, 5), "RSI": (50, 10), "高値から%": (-17, 10), "ボラ%": (31, 7), "半導体安週%": (1.3, 1.0)}
    dist = pd.DataFrame({k: ((F[k] - c) / w) ** 2 for k, (c, w) in center.items()})
    F["似ている度"] = 1 / (1 + np.sqrt(dist.mean(axis=1, skipna=True)))
    ok = F[(F["PER"].between(5, 22)) & (F["ROE%"] >= 7) & ((F["売上伸び%"] > 0) | F["売上伸び%"].isna())]
    out = pd.concat([ok, F.loc[[k for k in REF if k in F.index and k not in ok.index]]]).sort_values("似ている度", ascending=False)
    cols = ["名前", "株価", "PER", "PBR", "ROE%", "配当%", "売上伸び%", "利益伸び%", "25日線%", "75日線%", "RSI", "高値から%", "1年%", "ボラ%", "シャープ", "半導体安週%", "代金億", "似ている度"]
    pd.set_option("display.width", 320); pd.set_option("display.max_rows", 80)
    print("全体", len(S), "1次通過", len(pre), "最終", len(ok))
    print(out[cols].round(2).head(40).to_string())
    out[cols].to_csv(ROOT / "data" / "research" / "similar_screen.csv")


if __name__ == "__main__":
    main()
