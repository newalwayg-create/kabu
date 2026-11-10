"""単元株（100株）で2〜3日回すのに向いた候補を探す。

swing_candidates.py の移動平均線の条件に、100株で買える株価と、短期売買のしやすさを足したもの。

条件（すべて満たすもの）
1. 上昇トレンド: 株価が75日線より上、75日線が1か月前より上向き
2. 25日線から離れすぎていない: 乖離 -6%〜+4%
3. 先週急騰していない: 直近5日の上昇 +5%以下
4. 値動きがほどほどにある: 3日間の値動き（標準偏差）2%以上
5. 売買しやすい: 1日平均売買代金（直近60日）10億円以上
6. 100株で買える: 株価1,500円以下

あわせて出すもの: 1日の平均値幅（ATR）、米SOXとの連動、決算発表日
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
from universe import SECTORS  # noqa: E402

# 株価が1,500円以下になりやすい、売買の多い東証プライムの銘柄（業種をまたいで広めに）
WIDE = ("8306 8316 8411 8308 8309 7182 8304 8331 8354 8359 8366 8369 8377 8385 8386 8387 8388 8418 7186 7167 5831 8593 8570 8572 "
        "8473 8601 8604 8616 8628 8698 8697 5401 5411 5406 5471 5703 5706 5711 5713 5714 5801 5802 5803 3402 3401 3101 3861 3863 "
        "3880 3941 4004 4005 4021 4042 4043 4061 4183 4188 4208 4204 4205 4631 5019 5020 5021 1605 5101 5110 5105 5201 5214 5233 "
        "6113 6301 6305 6326 6361 6366 6471 6472 6473 6504 6724 6752 6753 6770 6952 7003 7012 7013 7201 7202 7205 7211 7259 7261 "
        "7267 7269 7270 7272 7276 7282 7731 7752 7911 7912 7951 3088 3099 3382 8233 8252 8267 8282 9831 7532 3197 2702 4385 4689 "
        "4755 3092 2432 4751 2127 2181 4324 9001 9005 9007 9008 9009 9041 9042 9044 9045 9048 9064 9101 9104 9107 9201 9202 9501 "
        "9502 9503 9504 9505 9506 9507 9508 9509 9513 9531 9532 9533 2002 2264 2282 2503 2531 2579 2801 2871 4151 4503 4528 4536 "
        "4565 4592 4902 4912 1801 1802 1803 3003 3231 3289 8801 8802 8804 1893 1820 1821 1860 1963 9432 9434 3778 9719 8020 2768 "
        "8012 7459 8088 6178 8697 4956 3861 9506 9533 8593 6544 3635 7906 4502 2502 6758").split()


def main():
    codes = sorted({c for m in SECTORS.values() for c in m} | set(EXTRA) | set(MORE) | set(ADD) | set(CHEAP) | set(WIDE))
    T = [c + ".T" for c in codes]
    d = yf.download(T + ["^SOX"], period="2y", progress=False, auto_adjust=True, threads=True)
    O, H, L, C, V = d["Open"], d["High"], d["Low"], d["Close"], d["Volume"]
    sox = C["^SOX"].pct_change()

    # 場中なら今日の値を5分足の最新値で置き換える
    i = yf.download(T, period="1d", interval="5m", progress=False, auto_adjust=False, threads=True)["Close"].ffill()
    if len(i):
        last = i.iloc[-1]
        day = pd.Timestamp(i.index[-1].date())
        C.index = pd.DatetimeIndex([pd.Timestamp(x.date()) for x in C.index])
        H.index = L.index = V.index = C.index
        C = C[~C.index.duplicated(keep="last")]
        if day in C.index:
            C.loc[day, last.dropna().index] = last.dropna()

    rows = []
    for t in T:
        p = C[t].dropna()
        if len(p) < 250:
            continue
        ma25, ma75 = p.rolling(25).mean(), p.rolling(75).mean()
        turn = (C[t] * V[t]).iloc[-61:-1].mean() / 1e8
        r3 = (p.shift(-3) / p - 1).dropna().iloc[-250:]
        h, l = H[t].reindex(p.index), L[t].reindex(p.index)
        tr = pd.concat([h - l, (h - p.shift()).abs(), (l - p.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        r = p.pct_change()
        sx = sox.reindex(p.index).shift(1)  # 前の晩のSOX
        both = pd.concat([r, sx], axis=1).dropna().iloc[-500:]
        beta = both.cov().iloc[0, 1] / both.iloc[:, 1].var()
        dl = p.diff(); up = dl.clip(lower=0).ewm(alpha=1 / 14).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=1 / 14).mean()
        rows.append({"t": t, "株価": p.iloc[-1], "100株(万)": p.iloc[-1] / 100, "代金億": turn,
                     "75日線%": (p.iloc[-1] / ma75.iloc[-1] - 1) * 100, "75日線の傾き%": (ma75.iloc[-1] / ma75.iloc[-21] - 1) * 100,
                     "25日線%": (p.iloc[-1] / ma25.iloc[-1] - 1) * 100, "直近5日%": (p.iloc[-1] / p.iloc[-6] - 1) * 100,
                     "3日の振れ%": r3.std() * 100, "ATR%": atr / p.iloc[-1] * 100, "SOX連動": beta,
                     "RSI": (100 - 100 / (1 + up / dn)).iloc[-1]})
    S = pd.DataFrame(rows).set_index("t")
    ok = S[(S["株価"] <= 1500) & (S["代金億"] >= 10) & (S["75日線%"] > 0) & (S["75日線の傾き%"] > 0)
           & S["25日線%"].between(-6, 4) & (S["直近5日%"] <= 5) & (S["3日の振れ%"] >= 2)]
    info = {}
    for t in ok.index:
        try:
            tk = yf.Ticker(t)
            nm = tk.info.get("shortName"); ind = tk.info.get("industry")
            cal = tk.calendar.get("Earnings Date") if isinstance(tk.calendar, dict) else None
            info[t] = (nm, ind, cal[0] if cal else None)
        except Exception:
            info[t] = (None, None, None)
    ok = ok.assign(名前=[info[t][0] for t in ok.index], 業種=[info[t][1] for t in ok.index], 決算=[info[t][2] for t in ok.index])
    ok = ok.sort_values("3日の振れ%", ascending=False)
    out = HERE.parents[1] / "data" / "research" / "swing_lot_candidates.csv"
    ok.to_csv(out)
    pd.set_option("display.width", 300); pd.set_option("display.max_rows", 200)
    print(f"対象 {len(S)} 銘柄 → 候補 {len(ok)}")
    print(ok[["名前", "業種", "株価", "100株(万)", "代金億", "3日の振れ%", "ATR%", "SOX連動", "25日線%", "75日線%", "75日線の傾き%",
              "直近5日%", "RSI", "決算"]].round(2).to_string())


if __name__ == "__main__":
    main()
