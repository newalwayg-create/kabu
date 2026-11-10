"""シナリオ枠の候補を入れた場合の運用全体の23営業日リターンを、過去データで比べる（ヒストリカル・シミュレーション）。"""
from pathlib import Path
import numpy as np
import pandas as pd
from earnings_study import load

C, O, E, I, names = load()
S = pd.read_pickle(Path(__file__).resolve().parents[1] / "data/research/etf.pkl")  # etf_series.py で作成
P = pd.concat({"1475": S["TOPIX ETF"], "1655": S["S&P500 ETF"], "200A": S["日経半導体ETF"], "N225ETF": S["日経225ETF"],
               "KDDI": C["9433.T"], "JR東日本": C["9020.T"], "花王": C["4452.T"], "OLC": C["4661.T"], "カプコン": C["9697.T"]}, axis=1, sort=True).dropna()
cap = 50000
alts = {
    "A 今の計画（200A＋現金）": {"1475": 23727, "1655": 15975, "200A": 4740},
    "B 200Aを外し、低相関3銘柄": {"1475": 23727, "1655": 15975, "KDDI": 2905, "JR東日本": 3350, "花王": 3522},
    "C 200Aを残し、低相関2銘柄": {"1475": 20338, "1655": 14197, "200A": 4740, "KDDI": 2905, "花王": 3522},
    "参考 日経225 ETFのみ": {"N225ETF": 49646},
}
H = 23
r = P.shift(-H) / P - 1
bench = r["N225ETF"] * 49646 / cap
for since in ["2024-06-03", "2021-01-01"]:
    print(f"\n=== {since} 以降（23営業日の運用全体リターン。200Aは2024-06上場のため2021年以降は日本半導体ETFで代用なし→A/Cは2024-06以降のみ有効）===")
    for name, w in alts.items():
        cols = list(w)
        x = r.loc[since:, cols].dropna()
        tot = (x * pd.Series(w)).sum(axis=1) / cap
        b = bench.reindex(tot.index)
        print(f"{name:26s} 投資 {sum(w.values()):,}円 | 平均 {tot.mean()*100:+.2f}% 標準偏差 {tot.std()*100:.2f}% 下位5% {tot.quantile(.05)*100:+.1f}% 最悪 {tot.min()*100:+.1f}% | 日経225ETF超え {((tot-b)>0).mean()*100:.0f}% n={len(tot)}")
# 日次の相関（直近1年）
d = P.pct_change().iloc[-250:]
print("\n直近1年の日次相関（対 運用の中核）")
core = 0.6 * d["1475"] + 0.4 * d["1655"]
for k in ["200A", "KDDI", "JR東日本", "花王", "OLC", "カプコン"]:
    print(f"  {k}: 中核との相関 {d[k].corr(core):+.2f}  年率ボラ {d[k].std()*np.sqrt(250)*100:.0f}%")
