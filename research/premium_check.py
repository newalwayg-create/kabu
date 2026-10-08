"""決算をまたいで持つ効果（決算プレミアム）の頑健性チェック。

比較対象: 同じ銘柄の「決算期間以外」の同じ長さ（6営業日）の超過リターンの平均。
"""
import math
from pathlib import Path
import numpy as np
import pandas as pd
from earnings_study import load, tstat

C, O, E, I, names = load()
ev = pd.read_pickle(str(Path(__file__).resolve().parents[1] / "data/research/events.pkl"))
n = C["^N225"]
ex6 = (C.shift(-6).div(C) - 1).sub(n.shift(-6) / n - 1, axis=0)  # t から 6営業日後までの超過リターン
mask = pd.DataFrame(False, index=C.index, columns=C.columns)
for r in ev.itertuples():
    i = C.index.searchsorted(r.date)
    mask.iloc[max(0, i - 12): i + 12, C.columns.get_loc(r.ticker)] = True
base = ex6.where(~mask).mean()  # 銘柄ごとの「普段の6日間」の平均超過リターン
ev["premium"] = ev.pre5_to_t1 - ev.ticker.map(base)
def show(name, x):
    x = x.dropna()
    by_date = x.groupby(ev.loc[x.index, "date"]).mean()  # 同じ日の発表をまとめて相関を除く
    print(f"{name:22s} n={len(x):4d} 平均 {x.mean()*100:+.2f}% t={tstat(x):5.2f} | 日付クラスタ t={tstat(by_date):5.2f} | 上昇率 {(x>0).mean()*100:.0f}% | 5%点 {x.quantile(.05)*100:+.1f}% 95%点 {x.quantile(.95)*100:+.1f}%")
print("普段の6日間の平均超過（全銘柄平均）: %+.2f%%" % (base.mean()*100))
show("全期間（生）", ev.pre5_to_t1)
show("全期間（普段との差）", ev.premium)
show("2018-2021", ev.premium[ev.date < "2022"])
show("2022-2026", ev.premium[ev.date >= "2022"])
show("10-11月の決算", ev.premium[ev.date.dt.month.isin([10, 11])])
# モメンタム上位の銘柄に限る
mom = (C.shift(21) / C.shift(126) - 1)
ev["mom"] = [mom[r.ticker].asof(r.date) if r.ticker in mom else np.nan for r in ev.itertuples()]
q = ev.mom.quantile([.33, .67]).to_numpy()
show("モメンタム上位1/3", ev.premium[ev.mom >= q[1]])
show("モメンタム下位1/3", ev.premium[ev.mom <= q[0]])
ev.to_pickle(str(Path(__file__).resolve().parents[1] / "data/research/events.pkl"))
