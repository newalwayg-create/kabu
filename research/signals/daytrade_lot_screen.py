"""単元株（100株〜）でデイトレの対象にしやすい、株価1,500円以下の銘柄を探す。

見るもの
- 1日の値幅: (高値-安値)/始値 の平均（直近1年）
- 寄り付き後30分の値幅: 9:00〜9:30 の (高値-安値)/始値 の平均（5分足、直近60日）
- 売買のしやすさ: 1日平均売買代金（直近60日）
- 呼値のコスト: 1刻みが株価の何%か。5分足の値段に小数があれば0.1円刻み（大型株）とみなす
- 値幅の刻み数: 1日の値幅が何刻みぶんあるか（多いほど細かく売買できる）
条件: 株価1,500円以下、売買代金20億円以上
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


def tick(price, fine):
    if fine:
        return 0.1 if price <= 1000 else 0.5
    return 1.0


def main():
    codes = sorted({c for m in SECTORS.values() for c in m} | set(EXTRA) | set(MORE) | set(ADD) | set(CHEAP) | set(WIDE))
    T = [c + ".T" for c in codes]
    d = yf.download(T, period="1y", progress=False, auto_adjust=False, threads=True)
    O, H, L, C, V = d["Open"], d["High"], d["Low"], d["Close"], d["Volume"]
    px = C.ffill().iloc[-1]
    turn = (C * V).iloc[-60:].mean() / 1e8
    keep = [t for t in T if t in px and px[t] <= 1500 and turn.get(t, 0) >= 20 and C[t].notna().sum() > 200]

    i = yf.download(keep, period="60d", interval="5m", progress=False, auto_adjust=False, threads=True)
    iH, iL, iO, iC = i["High"], i["Low"], i["Open"], i["Close"]
    idx = iH.index.tz_localize("UTC") if iH.index.tz is None else iH.index
    for x in (iH, iL, iO, iC):
        x.index = idx.tz_convert("Asia/Tokyo")
    first = (iH.index.hour == 9) & (iH.index.minute < 30)
    day = iH.index.normalize()

    rows = []
    for t in keep:
        p = px[t]
        rng = ((H[t] - L[t]) / O[t]).dropna() * 100
        oc = ((C[t] / O[t] - 1).abs()).dropna() * 100
        f = pd.DataFrame({"h": iH[t][first], "l": iL[t][first], "o": iO[t][first]}).dropna()
        g = f.groupby(f.index.normalize())
        r30 = ((g["h"].max() - g["l"].min()) / g["o"].first() * 100).mean()
        vals = iC[t].dropna().values
        fine = bool(np.any(np.abs(vals - np.round(vals)) > 1e-6))
        tk = tick(p, fine)
        rows.append({"code": t[:-2], "株価": p, "100株(万)": p / 100, "代金億": turn[t], "1日の値幅%": rng.mean(),
                     "寄り後30分の値幅%": r30, "寄→引けの動き%": oc.mean(), "呼値": tk, "呼値コスト%": tk / p * 100,
                     "値幅の刻み数": rng.mean() / 100 * p / tk})
    df = pd.DataFrame(rows)
    names = {}
    for t in df["code"]:
        try:
            names[t] = yf.Ticker(t + ".T").info.get("shortName")
        except Exception:
            names[t] = None
    df.insert(1, "銘柄", df["code"].map(names))
    df["向いてる度"] = (df["1日の値幅%"].rank(pct=True) + df["寄り後30分の値幅%"].rank(pct=True)
                    + np.log(df["代金億"]).rank(pct=True) + (-df["呼値コスト%"]).rank(pct=True)) / 4
    df = df.sort_values("向いてる度", ascending=False)
    out = HERE.parents[1] / "data" / "research" / "daytrade_lot_screen.csv"
    df.to_csv(out, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    print(f"対象 {len(df)} 銘柄（株価1,500円以下・売買代金20億円以上）")
    print(df.head(30).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
