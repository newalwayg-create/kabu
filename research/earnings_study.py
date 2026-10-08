"""決算イベントと株価の関係を検証する（日本の大型株 約110銘柄、2018年7月〜）。

すべて日経平均を差し引いた超過リターンで測る。
  t0 = 発表日(JST)より前の最後の営業日、t1 = 発表日より後の最初の営業日
  反応     = close[t0] → close[t1]
  決算後の持続（PEAD） = t1 の翌営業日の始値で買う（S株で t1 の14時以降に出した注文が約定するタイミング）→ k 営業日後の終値
  決算前の上昇 = close[t0-10] → close[t0]
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data" / "research"


def tstat(x):
    x = pd.Series(x).dropna()
    return x.mean() / (x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 2 else float("nan")


def fix_splits(s: pd.Series) -> pd.Series:
    s = s.dropna().copy(); r = s / s.shift(1)
    for d in r[(r < 0.4) | (r > 2.2)].index:
        k = round(1 / r[d]) if r[d] < 1 else 1 / round(r[d])
        s[s.index < d] /= k
    return s


def load():
    px = pd.read_pickle(D / "prices.pkl")
    names = json.load(open(D / "names.json", encoding="utf-8"))
    tick = [c + ".T" for c in names]
    C = pd.DataFrame({t: fix_splits(px[t]["Close"]) for t in tick + ["^N225"] if t in px.columns.get_level_values(0)})
    O = pd.DataFrame({t: px[t]["Open"] for t in C.columns})
    O = O.where(O > 0)
    # 分割補正を始値にも反映
    O = O * (C / pd.DataFrame({t: px[t]["Close"] for t in C.columns}))
    idx = C["^N225"].dropna().index
    C, O = C.reindex(idx), O.reindex(idx)
    E = pd.read_pickle(D / "earnings_clean.pkl")
    I = pd.read_csv(D / "info.csv", index_col=0)
    return C, O, E, I, names


def events(C, O, E):
    idx = C.index
    rows = []
    for r in E.itertuples():
        t = r.ticker
        if t not in C:
            continue
        d = pd.Timestamp(r.jst.date())
        if d < idx[30] or d > idx[-1]:
            continue
        i0 = idx.searchsorted(d) - 1          # 発表日より前の最後の営業日
        i1 = idx.searchsorted(d, side="right")  # 発表日より後の最初の営業日
        if i0 < 11 or i1 >= len(idx):
            continue
        c, n = C[t], C["^N225"]
        if pd.isna(c.iloc[i0]) or pd.isna(c.iloc[i1]):
            continue
        ex = lambda a, b: (c.iloc[b] / c.iloc[a] - 1) - (n.iloc[b] / n.iloc[a] - 1)
        row = {"ticker": t, "date": d, "t1": idx[i1], "eps_est": r._2, "eps": r._3, "surprise": r._4,
               "reaction": ex(i0, i1), "pre10": ex(i0 - 10, i0), "pre5_to_t1": ex(i0 - 5, i1)}
        e = i1 + 1
        if e < len(idx) and not pd.isna(O[t].iloc[e]):
            for k in (5, 10, 20):
                j = e + k - 1
                if j < len(idx):
                    row[f"drift{k}"] = (c.iloc[j] / O[t].iloc[e] - 1) - (n.iloc[j] / O["^N225"].iloc[e] - 1)
        rows.append(row)
    ev = pd.DataFrame(rows)
    ev["beat"] = ev["surprise"] > 0
    return ev


def bucket_table(ev, by, cols, q=5, labels=None):
    x = ev.dropna(subset=[by])
    x = x.assign(b=pd.qcut(x[by], q, labels=labels or [f"Q{i+1}" for i in range(q)]))
    out = x.groupby("b", observed=True).agg(n=(by, "size"), **{f"{c}_mean": (c, "mean") for c in cols},
                                            **{f"{c}_hit": (c, lambda s: (s > 0).mean()) for c in cols})
    rng = x.groupby("b", observed=True)[by].agg(["min", "max"])
    return out.join(rng)


def momentum(C, names):
    """月次の横断面: 過去6か月（直近1か月を除く）・過去1か月のリターンで5分位 → 翌21営業日の超過リターン。"""
    tick = [c + ".T" for c in names if c + ".T" in C]
    P = C[tick]; n = C["^N225"]
    ends = list(range(130, len(C) - 21, 21))
    res = []
    for i in ends:
        mom = P.iloc[i - 21] / P.iloc[i - 126] - 1
        rev = P.iloc[i] / P.iloc[i - 21] - 1
        fwd = (P.iloc[i + 21] / P.iloc[i] - 1) - (n.iloc[i + 21] / n.iloc[i] - 1)
        df = pd.DataFrame({"mom": mom, "rev": rev, "fwd": fwd}).dropna()
        if len(df) < 50:
            continue
        for f in ("mom", "rev"):
            qq = pd.qcut(df[f], 5, labels=False)
            res.append({"date": C.index[i], "factor": f, "top": df.fwd[qq == 4].mean(), "bottom": df.fwd[qq == 0].mean()})
    m = pd.DataFrame(res)
    m["spread"] = m.top - m.bottom
    return m


def main():
    C, O, E, I, names = load()
    ev = events(C, O, E)
    past = ev.dropna(subset=["surprise"]).copy()
    past.to_pickle(D / "events.pkl")
    R = {}
    R["n_events"] = len(past); R["n_tickers"] = past.ticker.nunique()
    R["period"] = [str(past.date.min().date()), str(past.date.max().date())]
    R["beat_rate"] = past.beat.mean()
    R["abs_reaction_median"] = past.reaction.abs().median()
    R["abs_reaction_p90"] = past.reaction.abs().quantile(.9)
    R["corr_surprise_reaction"] = past[["surprise", "reaction"]].assign(surprise=past.surprise.clip(-100, 100)).corr(method="spearman").iloc[0, 1]
    R["reaction_by_beat"] = past.groupby("beat").reaction.agg(["mean", "median", "count", lambda s: (s > 0).mean()]).rename(columns={"<lambda_0>": "up_rate"})

    # 1) 上振れ率の5分位と反応
    R["surprise_q"] = bucket_table(past, "surprise", ["reaction"])
    # 2) 上振れは予想できるか: 過去4回の上振れ回数 → 次回の上振れ確率と反応
    past = past.sort_values(["ticker", "date"])
    past["prior_beats"] = past.groupby("ticker").beat.transform(lambda s: s.shift(1).rolling(4).sum())
    R["beat_persistence"] = past.dropna(subset=["prior_beats"]).groupby("prior_beats").agg(
        n=("beat", "size"), next_beat=("beat", "mean"), reaction=("reaction", "mean"), up_rate=("reaction", lambda s: (s > 0).mean()))
    # 3) 決算前の上昇（持ったまま決算を迎える戦略）
    R["hold_through"] = {"pre5_to_t1_mean": past.pre5_to_t1.mean(), "t": tstat(past.pre5_to_t1), "up_rate": (past.pre5_to_t1 > 0).mean(),
                         "p05": past.pre5_to_t1.quantile(.05), "p95": past.pre5_to_t1.quantile(.95)}
    # 4) PEAD: 反応の5分位 → その後の持続
    R["pead_q"] = bucket_table(past, "reaction", ["drift5", "drift10", "drift20"])
    top = past[past.reaction >= past.reaction.quantile(.8)]
    big = past[(past.reaction >= 0.05) & (past.surprise > 0)]
    R["pead_top"] = {k: {"mean": top[k].mean(), "t": tstat(top[k]), "hit": (top[k] > 0).mean(), "n": int(top[k].notna().sum())} for k in ("drift5", "drift10", "drift20")}
    R["pead_big_beat"] = {k: {"mean": big[k].mean(), "t": tstat(big[k]), "hit": (big[k] > 0).mean(), "n": int(big[k].notna().sum())} for k in ("drift5", "drift10", "drift20")}
    # 期間で分けた頑健性
    for name, sub in [("2018-2021", past[past.date < "2022-01-01"]), ("2022-2026", past[past.date >= "2022-01-01"]),
                      ("10-11月の決算のみ", past[past.date.dt.month.isin([10, 11])])]:
        s = sub[sub.reaction >= sub.reaction.quantile(.8)]
        b = sub[sub.reaction <= sub.reaction.quantile(.2)]
        R[f"pead_split_{name}"] = {"top_drift10": s.drift10.mean(), "top_t": tstat(s.drift10), "bottom_drift10": b.drift10.mean(), "bottom_t": tstat(b.drift10), "n": len(s)}
    # 5) モメンタム・リバーサル
    m = momentum(C, names)
    R["momentum"] = m.groupby("factor").agg(top=("top", "mean"), bottom=("bottom", "mean"), spread=("spread", "mean"),
                                           t=("spread", tstat), win=("spread", lambda s: (s > 0).mean()), months=("spread", "size"))
    pd.to_pickle(R, D / "study.pkl")
    pd.set_option("display.width", 200)
    for k, v in R.items():
        print(f"\n=== {k} ===")
        print(v.round(4) if isinstance(v, pd.DataFrame) else v)


if __name__ == "__main__":
    main()
