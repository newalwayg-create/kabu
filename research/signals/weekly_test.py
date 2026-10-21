"""週単位の売買ルールを検証する（約380銘柄、2019年以降）。

毎週金曜の終値で銘柄を選び、翌週の月曜の寄付で買い、金曜の終値で売ったとする（同じ週の全銘柄の平均に対する超過）。
- 逆張り: 先週の下落率が大きい銘柄
- 順張り: 先週の上昇率が大きい銘柄
- 安定株の押し目: 3年の値動きが穏やかな銘柄のうち、先週大きく下げたもの
2019〜2023年と2024年以降に分けて、同じ向きが出るかを見る。
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


def main():
    codes = sorted({c for m in SECTORS.values() for c in m} | set(EXTRA) | set(MORE))
    T = [c + ".T" for c in codes]
    d = yf.download(T + ["1306.T"], start="2018-06-01", progress=False, auto_adjust=True, threads=True)
    C, O = d["Close"], d["Open"]
    r = C.pct_change(fill_method=None)
    C = C.where(r.abs() < 0.4)  # 分割などの異常値を除く
    wk_close = C.resample("W-FRI").last()
    first_open = O.resample("W-FRI").first()
    past = wk_close.pct_change(fill_method=None)                     # 先週の値動き
    nxt = wk_close.shift(-1) / first_open.shift(-1) - 1                 # 翌週: 月曜寄付→金曜終値
    nxt = nxt.drop(columns="1306.T")
    nxt = nxt.where(nxt.abs() < 0.5)
    ex = nxt.sub(nxt.mean(axis=1), axis=0)  # 同じ週の全銘柄の平均に対する超過（TOPIX連動ETFは分割の異常値があるため使わない）
    past = past.drop(columns="1306.T")
    vol = r.rolling(250).std().resample("W-FRI").last().drop(columns="1306.T")
    low_vol = vol.le(vol.quantile(0.3, axis=1), axis=0)
    rules = {
        "先週の下落 下位10%（逆張り）": past.le(past.quantile(0.1, axis=1), axis=0),
        "先週-8%以下（逆張り）": past <= -0.08,
        "先週の上昇 上位10%（順張り）": past.ge(past.quantile(0.9, axis=1), axis=0),
        "先週+8%以上（順張り）": past >= 0.08,
        "値動きが穏やかな株（下位30%）で先週-5%以下": low_vol & (past <= -0.05),
        "全銘柄（比較）": past.notna(),
    }
    for lab, m in rules.items():
        x = ex.where(m).loc["2019":]
        per_week = x.mean(axis=1).dropna()
        allv = x.stack().dropna()
        a = per_week.loc[:"2023"]; b = per_week.loc["2024":]
        print(f"{lab}: 件数{len(allv)} 週数{len(per_week)} | 1回あたり平均{allv.mean()*100:+.2f}% 勝率{(allv>0).mean():.0%} | "
              f"週ごと平均{per_week.mean()*100:+.2f}% t{per_week.mean()/per_week.std()*np.sqrt(len(per_week)):.1f} | 2019-23 {a.mean()*100:+.2f}% / 2024- {b.mean()*100:+.2f}%")


if __name__ == "__main__":
    main()
