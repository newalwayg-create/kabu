"""S株で「その日のうちに売り買いする」のに向いた、株価1,400円以下の銘柄を探す。

S株は寄付き・後場の始値・後場の引けの3回しか約定しないので、できる日中の売買は
  A: 寄付きで買う → 後場の始値（12:30）で売る
  B: 寄付きで買う → 引けで売る
の2通り。向いているかどうかは
- 値幅: 寄付き→後場の始値、寄付き→引け の動きの大きさ（標準偏差、平均の絶対値）
- 売買のしやすさ: 1日平均売買代金（直近60日）
- 寄付きで買うと不利な癖がないか: 寄付き→引けの平均と、プラスで終わる割合（直近1年）
で見る。値幅が大きい＝もうけも損も大きい、という意味で、上がる銘柄の予想ではない。
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
from swing_candidates import ADD  # noqa: E402
from universe import SECTORS  # noqa: E402

CHEAP = ("7201 9434 9432 4689 5401 7211 8604 8601 7186 8331 8304 8358 9501 5020 7261 4188 6740 3350 4565 2158 4755 "
         "4475 3040 3857 5028 3042 4447 4592 7003 7012 9104 9107 7013 8410 8418 7167 8524 9142 3197 2702 8233 9831 7532 "
         "5706 5711 5714 5541 5631 5332 6740 2491 3778 3655 6232 4777 5253 9449 3690 4385 6619 6814 6327 4813 2928 "
         "8306 8316 8411 8308 5411 1605 6178 7182 3099 9201 9202 9020 1803 1801 7272 6301 4502 8473 6141 2462 7240 "
         "4004 4005 4183 3405 3402 3401 4021 4043 6448 6479 6952 7735 7752 7731 6305 6366 6201 6326 6471 6472 6473 "
         "2337 3994 4382 4396 4434 4485 4488 5032 5129 5574 7046 7095 9166 9348 9552 2160 4011 4053 4176 4384 4441").split()


def main():
    codes = sorted({c for m in SECTORS.values() for c in m} | set(EXTRA) | set(MORE) | set(ADD) | set(CHEAP))
    T = [c + ".T" for c in codes]
    d = yf.download(T, period="1y", progress=False, auto_adjust=False, threads=True)
    O, H, L, C, V = d["Open"], d["High"], d["Low"], d["Close"], d["Volume"]
    px = C.ffill().iloc[-1]
    turn = (C * V).iloc[-60:].mean() / 1e8
    keep = [t for t in T if t in px and px[t] <= 1400 and turn.get(t, 0) >= 3 and C[t].notna().sum() > 200]
    oc = (C / O - 1)[keep] * 100
    rng = ((H - L) / O)[keep] * 100
    gap = (O / C.shift(1) - 1)[keep] * 100

    # 後場の始値は5分足から（直近60日）
    i = yf.download(keep, period="60d", interval="5m", progress=False, auto_adjust=False, threads=True)
    io = i["Open"]
    idx = io.index.tz_localize("UTC") if io.index.tz is None else io.index
    io.index = idx.tz_convert("Asia/Tokyo")
    day = io.index.normalize()
    first = io.groupby(day).apply(lambda x: x.bfill().iloc[0])
    pm = io[(io.index.hour == 12) & (io.index.minute == 30)]
    pm.index = pm.index.normalize()
    a = (pm / first.reindex(pm.index) - 1) * 100

    rows = []
    for t in keep:
        x = oc[t].dropna(); aa = a[t].dropna() if t in a else pd.Series(dtype=float)
        rows.append({"code": t[:-2], "株価": round(px[t]), "代金億": turn[t],
                     "A 寄→後場始 sd%": aa.std(), "A 平均%": aa.mean(), "A プラス%": (aa > 0).mean() * 100,
                     "B 寄→引け sd%": x.std(), "B |平均|%": x.abs().mean(), "B 平均%": x.mean(), "B プラス%": (x > 0).mean() * 100,
                     "日中値幅%": rng[t].mean(), "ギャップsd%": gap[t].std(), "日数": len(x)})
    df = pd.DataFrame(rows)
    # 名前
    try:
        import json
        names = json.loads((HERE.parents[1] / "data" / "research" / "names.json").read_text())
    except Exception:
        names = {}
    for m in SECTORS.values():
        names.update({k: v for k, v in m.items()})
    df.insert(1, "銘柄", df["code"].map(lambda c: names.get(c, names.get(c + ".T", ""))))
    df["向いてる度"] = (df["B 寄→引け sd%"].rank(pct=True) + df["A 寄→後場始 sd%"].rank(pct=True) + np.log(df["代金億"]).rank(pct=True)) / 3
    df = df.sort_values("向いてる度", ascending=False)
    out = HERE.parents[1] / "data" / "research" / "daytrade_screen.csv"
    df.to_csv(out, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    print(f"対象 {len(df)} 銘柄（株価1,400円以下・売買代金3億円以上）")
    print(df.head(40).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
