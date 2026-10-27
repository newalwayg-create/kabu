"""半導体が下げる局面で、どの業種が強いかを調べる。

半導体株（東京エレクトロン、アドバンテスト、ディスコ、SUMCO の均等）と、
前夜の米SOX指数を使い、3つの見方で業種の超過リターン（対TOPIX）を測る。
業種の計算からは半導体銘柄を除く（電気機器・機械・金属製品が機械的に連動するのを避けるため）。

A. 同じ週: 半導体が大きく下げた週（下位20%）に、各業種は TOPIX より強かったか
B. 事前に分かる合図1: 前夜にSOXが2%以上下げた翌日、各業種は TOPIX より強かったか
C. 事前に分かる合図2: 月末時点でSOXが直近高値から10%以上下げていたとき、翌月の各業種
どれも 2019〜2023年 と 2024年以降 に分けて、同じ結果が出るかを確かめる。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(HERE))
from analyze import load, ORDER  # noqa: E402
from earnings_study import tstat  # noqa: E402
from universe import SECTORS  # noqa: E402

SEMI = ["8035", "6857", "6146", "3436"]
SPLIT = "2024-01-01"


def sector_ex_semi(P, shares):
    R = P.pct_change(fill_method=None)
    out = {}
    for s, m in SECTORS.items():
        cols = [c + ".T" for c in m if c + ".T" in P and c not in SEMI]
        cap = pd.DataFrame({c: P[c] * shares[c] for c in cols})
        w = cap.shift(1).where(R[cols].notna())
        out[s] = (R[cols] * w).sum(axis=1) / w.sum(axis=1)
    return pd.DataFrame(out)[ORDER]


def summarize(X, mask, label):
    rows = {}
    for part, sl in [("全期間", slice(None)), ("2019-23", slice(None, "2023-12-31")), ("2024-", slice(SPLIT, None))]:
        m = mask.loc[sl]; x = X.loc[sl][m]
        rows[part] = x.mean() * 100
        rows[part + "_t"] = x.apply(tstat)
        rows[part + "_勝率"] = (x > 0).mean()
        rows[part + "_n"] = pd.Series(len(x), index=X.columns)
    df = pd.DataFrame(rows)
    df["両期間で同じ向き"] = np.sign(df["2019-23"]) == np.sign(df["2024-"])
    print(f"\n=== {label}（超過リターン%, n={int(mask.sum())}） ===")
    show = df[["全期間", "全期間_t", "全期間_勝率", "2019-23", "2024-", "両期間で同じ向き"]].sort_values("全期間", ascending=False)
    print(show.round(2).to_string())
    return df


def main():
    P, _, shares = load()
    R = sector_ex_semi(P, shares)
    topix = P["1306.T"].pct_change(fill_method=None)
    semi = P[[c + ".T" for c in SEMI]].pct_change(fill_method=None).mean(axis=1)
    X = R.sub(topix, axis=0).loc["2019-01-01":]
    sox = P["^SOX"].dropna()

    # A. 同じ週
    idx = (1 + X.fillna(0)).cumprod()
    W = idx.resample("W-FRI").last().pct_change().dropna(how="all")
    sw = (1 + semi.loc["2019-01-01":].fillna(0)).cumprod().resample("W-FRI").last().pct_change().reindex(W.index)
    A = summarize(W, sw <= sw.quantile(.2), "A. 日本の半導体株が大きく下げた週（下位20%）")
    beta = {}
    for part, sl in [("全期間", slice(None)), ("直近1年", slice(W.index[-52], None))]:
        s = sw.loc[sl]; beta[part] = W.loc[sl].apply(lambda c: c.cov(s) / s.var())
    print("\n半導体株への感応度（週次、超過リターンの回帰係数）\n", pd.DataFrame(beta).sort_values("全期間").round(2).to_string())

    # B. 前夜SOX -2%以下 → 翌営業日（東京）
    soxr = sox.pct_change()
    us = pd.DataFrame({"sox": soxr}).dropna()
    us.index = us.index + pd.Timedelta(hours=16)  # 米国の引け（東京の翌朝）
    jp = X.copy(); jp.index = jp.index + pd.Timedelta(hours=15)
    al = pd.merge_asof(jp.sort_index(), us.sort_index(), left_index=True, right_index=True, allow_exact_matches=False, tolerance=pd.Timedelta(days=4))
    al.index = X.index
    B = summarize(X, al["sox"] <= -0.02, "B. 前夜にSOXが2%以上下げた翌日（東京）")

    # C. SOXが直近1年高値から10%以上下 → 翌月
    me = X.groupby(X.index.to_period("M")).tail(1).index
    dd = (sox / sox.rolling(252, min_periods=60).max() - 1).reindex(me, method="ffill")
    M = idx.reindex(me).pct_change().shift(-1).dropna(how="all")
    C = summarize(M, (dd.reindex(M.index) <= -0.10), "C. 月末にSOXが高値から10%以上下 → 翌月")

    pd.to_pickle({"A": A, "B": B, "C": C, "beta": pd.DataFrame(beta)}, ROOT / "data" / "research" / "sector33" / "semi_down.pkl")
    print("\nSOXの現在の高値からの下落率:", round(float(sox.iloc[-1] / sox.iloc[-252:].max() - 1) * 100, 1), "%", sox.index[-1].date())


if __name__ == "__main__":
    main()
