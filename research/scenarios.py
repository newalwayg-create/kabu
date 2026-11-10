"""候補銘柄ごとの決算シナリオ（確率と株価反応）を、検証済みのモデルで数値化する。"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ev = pd.read_pickle(ROOT / "data/research/events_pred.pkl")
snap = pd.read_pickle(ROOT / "data/research/snapshot.pkl")
ev["prior_beats"] = ev.groupby("ticker").beat.transform(lambda s: s.shift(1).rolling(4).sum())
tab = ev.dropna(subset=["prior_beats"]).groupby("prior_beats").beat.mean()
ub, um = ev[ev.beat].reaction, ev[~ev.beat].reaction
out = {}
for t in ["9433.T", "9020.T", "4452.T"]:
    h = ev[ev.ticker == t]; s = snap.loc[t]
    p = tab.loc[float(s.beats_last4)]
    ob, om = h[h.beat].reaction, h[~h.beat].reaction
    rb = (ob.sum() + 20 * ub.mean()) / (len(ob) + 20); rm = (om.sum() + 20 * um.mean()) / (len(om) + 20)
    big_up = h.reaction.quantile(.9); big_dn = h.reaction.quantile(.1)
    out[t] = dict(name=s["name"], price=s.price, earn=s.earn_date, beats_last4=int(s.beats_last4), p_beat=p,
                  react_beat=rb, react_miss=rm, exp_react=p * rb + (1 - p) * rm,
                  p10=big_dn, p90=big_up, up_rate=(h.reaction > 0).mean(), n=len(h),
                  fwdPE=s.fwdPE, PBR=s.PBR, target_upside=s.target_upside, analysts=s.analysts, mom6_1=s.mom6_1)
df = pd.DataFrame(out).T
pd.set_option("display.width", 220)
print(df.to_string())
df.to_pickle(ROOT / "data/research/scenarios.pkl")
