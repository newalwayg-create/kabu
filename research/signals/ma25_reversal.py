"""25日移動平均線から大きく下に離れた株を買うと、その後リバウンドするか（BNF氏の手法の検証）。

- 対象: 東証33業種の代表銘柄＋これまでのスクリーニング対象（約400銘柄）、過去5年
- シグナル: 終値が25日線より X% 以上下（X = 10, 15, 20, 25）
- 翌日の寄付きで買ったとして、1日後・5日後・10日後の引けまでのリターンを、同じ日の全銘柄平均と比べる
- 市場全体が大きく下げた局面（全銘柄平均の25日線乖離が -5% 以下）とそれ以外に分けて比べる
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


def main():
    codes = sorted({c for m in SECTORS.values() for c in m} | set(EXTRA) | set(MORE) | set(ADD))
    T = [c + ".T" for c in codes]
    d = yf.download(T, period="5y", progress=False, auto_adjust=True, threads=True)
    C, O = d["Close"], d["Open"]
    C = C.loc[:, C.notna().sum() > 500]; O = O[C.columns]
    r = C.pct_change().where(lambda x: x.abs() < 0.3)
    dev = C / C.rolling(25).mean() - 1
    mdev = dev.mean(axis=1)
    mkt = r.mean(axis=1)
    out = []
    for h in [1, 5, 10]:
        fwd = C.shift(-h) / O.shift(-1) - 1  # 翌日寄付きで買い、h日後の引けで売る
        mfwd = fwd.mean(axis=1)
        ex = fwd.sub(mfwd, axis=0)
        for x in [0.10, 0.15, 0.20, 0.25]:
            sig = dev <= -x
            for lab, mask in [("全期間", pd.Series(True, index=C.index)), ("市場パニック時", mdev <= -0.05), ("平常時", mdev > -0.05)]:
                s = sig.where(mask, False, axis=0)
                v = fwd[s].stack().dropna(); e = ex[s].stack().dropna()
                if len(v) < 20:
                    continue
                out.append({"保有日数": h, "乖離": f"-{int(x*100)}%以下", "局面": lab, "件数": len(v),
                            "平均%": v.mean() * 100, "中央値%": v.median() * 100, "勝率%": (v > 0).mean() * 100,
                            "市場との差%": e.mean() * 100, "市場に勝った%": (e > 0).mean() * 100})
    df = pd.DataFrame(out)
    pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200)
    print(f"銘柄数 {C.shape[1]}  期間 {C.index[0].date()}〜{C.index[-1].date()}")
    print(df.round(2).to_string(index=False))
    last = dev.iloc[-1].dropna().sort_values()
    print("\n今の25日線乖離 下位20:", {k[:-2]: round(v * 100, 1) for k, v in last.head(20).items()})
    print("市場全体の平均乖離:", round(mdev.iloc[-1] * 100, 2), "%")


if __name__ == "__main__":
    main()
