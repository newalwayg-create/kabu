"""シナリオモデルの事後検証（各時点で、それ以前のデータだけを使って予測する）。

予測 = P(上振れ) × 上振れ時の反応 + (1−P) × 下振れ時の反応
  P(上振れ): その時点までの全銘柄データで「直近4回の上振れ回数 → 次の上振れ率」を推定
  反応: その銘柄の過去の反応を全銘柄平均に縮小推定（重み n/(n+20)）
"""
from pathlib import Path
import numpy as np
import pandas as pd
from earnings_study import tstat

ROOT = Path(__file__).resolve().parents[1]
ev = pd.read_pickle(ROOT / "data/research/events.pkl").sort_values("date").reset_index(drop=True)
ev["prior_beats"] = ev.groupby("ticker").beat.transform(lambda s: s.shift(1).rolling(4).sum())
pred = []
for i, r in ev.iterrows():
    hist = ev[ev.date < r.date - pd.Timedelta(days=1)]
    if len(hist) < 500 or np.isnan(r.prior_beats):
        pred.append((np.nan, np.nan)); continue
    h = hist.dropna(subset=["prior_beats"])
    p = h[h.prior_beats == r.prior_beats].beat.mean()
    ub, um = hist[hist.beat].reaction.mean(), hist[~hist.beat].reaction.mean()
    own = hist[hist.ticker == r.ticker]
    ob, om = own[own.beat].reaction, own[~own.beat].reaction
    rb = (ob.sum() + 20 * ub) / (len(ob) + 20); rm = (om.sum() + 20 * um) / (len(om) + 20)
    pred.append((p, p * rb + (1 - p) * rm))
ev[["p_beat", "pred_reaction"]] = pd.DataFrame(pred, index=ev.index)
x = ev.dropna(subset=["pred_reaction"])
print("検証対象", len(x), "件", x.date.min().date(), "〜", x.date.max().date())
# 1) 上振れ確率の当たり具合（Brier スコア）
brier = ((x.p_beat - x.beat) ** 2).mean(); base = ((x.beat.expanding().mean().shift(1).fillna(.6) - x.beat) ** 2).mean()
print(f"上振れ確率のBrier: モデル {brier:.4f} / 単純な平均上振れ率 {base:.4f}（小さいほど良い）")
# 2) 予測反応と実際の反応
print("予測と実際の順位相関: %.3f" % x[["pred_reaction", "reaction"]].corr(method="spearman").iloc[0, 1])
x = x.assign(q=pd.qcut(x.pred_reaction, 5, labels=False))
g = x.groupby("q").agg(n=("reaction", "size"), pred=("pred_reaction", "mean"), actual=("reaction", "mean"), up=("reaction", lambda s: (s > 0).mean()))
print(g.round(4).to_string())
top, bot = x[x.q == 4].reaction, x[x.q == 0].reaction
print("上位5分位 − 下位5分位: %+.2f%%, t=%.2f" % ((top.mean() - bot.mean()) * 100, (top.mean() - bot.mean()) / np.sqrt(top.var() / len(top) + bot.var() / len(bot))))
ev.to_pickle(ROOT / "data/research/events_pred.pkl")
