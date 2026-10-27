"""東証33業種（代表銘柄の時価総額加重）で、業種間の資金移動に関する6つの仮説を検証する。

方法は research/sector/analyze.py と同じ。違いは、業種を東証33業種にしたことと、業種の値動きを
前日の時価総額で加重したこと（東証の業種指数に近い計算方法）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
D = ROOT / "data" / "research" / "sector33"
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(HERE))
from earnings_study import fix_splits, tstat  # noqa: E402
from universe import SECTORS  # noqa: E402

DURATION = 9.0
ORDER = list(SECTORS)
F = ["米10年金利", "国内金利", "ブレント原油", "SOX"]


def load():
    raw = pd.read_pickle(D / "raw.pkl")
    info = json.load(open(D / "info.json", encoding="utf-8"))
    P = pd.DataFrame({t: fix_splits(raw[t]["Adj Close"].dropna()) for t in raw.columns.get_level_values(0).unique() if raw[t]["Adj Close"].notna().any()})
    days = P["1306.T"].dropna().index
    P = P.reindex(P.index.union(days)).ffill(limit=5).reindex(days)
    V = pd.DataFrame({t: raw[t]["Close"] * raw[t]["Volume"] for t in raw.columns.get_level_values(0).unique() if t.endswith(".T") and t != "1306.T"}).reindex(days)
    shares = {t: v["shares"] for t, v in info.items()}
    return P, V, shares


def sector_returns(P, shares):
    R = P.pct_change(fill_method=None)
    out, caps = {}, {}
    for s, m in SECTORS.items():
        cols = [c + ".T" for c in m if c + ".T" in P]
        cap = pd.DataFrame({c: P[c] * shares[c] for c in cols})
        w = cap.shift(1).where(R[cols].notna())
        out[s] = (R[cols] * w).sum(axis=1) / w.sum(axis=1)
        caps[s] = cap.sum(axis=1, min_count=1)
    return pd.DataFrame(out)[ORDER], pd.DataFrame(caps)[ORDER]


def main():
    P, V, shares = load()
    R, CAP = sector_returns(P, shares)
    topix = P["1306.T"].pct_change(fill_method=None)
    X = R.sub(topix, axis=0).loc["2018-07-01":]
    idx = (1 + X.fillna(0)).cumprod()
    res = {}

    W = idx.resample("W-FRI").last().pct_change()
    f = pd.DataFrame({
        "米10年金利": P["^TNX"].resample("W-FRI").last().diff(),
        "国内金利": -np.log(P["2510.T"]).resample("W-FRI").last().diff() / DURATION * 100,
        "ブレント原油": P["BZ=F"].resample("W-FRI").last().pct_change(),
        "SOX": P["^SOX"].resample("W-FRI").last().pct_change(),
    }).reindex(W.index)
    WF = pd.concat([W, f], axis=1).loc["2019-01-01":].dropna()

    def betas(df):
        Z = df[F]; Zs = (Z - Z.mean()) / Z.std()
        A = np.column_stack([np.ones(len(Zs)), Zs.to_numpy()])
        inv = np.linalg.inv(A.T @ A)
        rows = {}
        for s in ORDER:
            y = df[s].to_numpy(); coef, *_ = np.linalg.lstsq(A, y, rcond=None); e = y - A @ coef
            se = np.sqrt(np.diag(e @ e / (len(y) - A.shape[1]) * inv))
            rows[s] = {**{c: coef[i + 1] * 100 for i, c in enumerate(F)}, **{c + "_t": coef[i + 1] / se[i + 1] for i, c in enumerate(F)},
                       "R2": 1 - e @ e / ((y - y.mean()) @ (y - y.mean()))}
        return pd.DataFrame(rows).T

    res["beta_full"], res["beta_1y"] = betas(WF), betas(WF.iloc[-52:])
    res["cond"] = {fac: {s: (WF[WF[fac] >= WF[fac].quantile(.8)][s].mean() * 100, tstat(WF[WF[fac] >= WF[fac].quantile(.8)][s]),
                             (WF[WF[fac] >= WF[fac].quantile(.8)][s] > 0).mean()) for s in ORDER} for fac in ["米10年金利", "国内金利", "ブレント原油"]}
    res["cond_n"] = int((WF["国内金利"] >= WF["国内金利"].quantile(.8)).sum())
    res["monthly"] = idx.resample("ME").last().pct_change().loc["2019-02":]

    TV = pd.DataFrame({s: V[[c + ".T" for c in m]].sum(axis=1, min_count=1) for s, m in SECTORS.items()})[ORDER].resample("ME").sum()
    res["tv_share"] = TV.div(TV.sum(axis=1), axis=0).loc["2019-01":]
    CPm = CAP.resample("ME").last()
    res["cap_share"] = CPm.div(CPm.sum(axis=1), axis=0).loc["2019-01":]

    ex = lambda n: ((1 + X.iloc[-n:]).prod() - 1) * 100
    recent = pd.DataFrame({"1か月": ex(21), "3か月": ex(63), "6か月": ex(126)})
    for nm, S in [("売買代金シェアの変化(pt)", TV), ("時価総額シェアの変化(pt)", CPm)]:
        if nm.startswith("売買"):
            recent[nm] = (S.iloc[-3:].sum() / S.iloc[-3:].sum().sum() - S.iloc[-15:-3].sum() / S.iloc[-15:-3].sum().sum()) * 100
        else:
            sh = S.div(S.sum(axis=1), axis=0)
            recent[nm] = (sh.iloc[-1] - sh.iloc[-4]) * 100
    res["recent"] = recent
    us = P["^TNX"].dropna(); br = P["BZ=F"].dropna()
    res["macro_3m"] = {"米10年金利": f"{us.iloc[-64]:.2f}% → {us.iloc[-1]:.2f}%（{us.iloc[-1] - us.iloc[-64]:+.2f}pt）",
                       "国内金利（推定）": f"{-np.log(P['2510.T'].iloc[-1] / P['2510.T'].iloc[-64]) / DURATION * 100:+.2f}pt",
                       "ブレント原油": f"{br.iloc[-64]:.1f} → {br.iloc[-1]:.1f}ドル（{(br.iloc[-1] / br.iloc[-64] - 1) * 100:+.1f}%）",
                       "SOX": f"{(P['^SOX'].dropna().iloc[-1] / P['^SOX'].dropna().iloc[-64] - 1) * 100:+.1f}%", "as_of": str(X.index[-1].date())}

    # H5: 電気機器の下落局面
    s_abs = (1 + R["電気機器"].fillna(0)).cumprod()
    dd = s_abs / s_abs.rolling(252, min_periods=60).max() - 1
    e = idx["電気機器"]; f21 = e.shift(-21) / e - 1; f63 = e.shift(-63) / e - 1
    res["h5"] = {lab: {"日数": int(m.sum()), "1か月後": f21[m].mean() * 100, "3か月後": f63[m].mean() * 100, "上回った割合": (f63[m] > 0).mean()}
                 for lab, m in [("下落率20%以上", dd <= -.2), ("下落率10〜20%", (dd > -.2) & (dd <= -.1)), ("それ以外", dd > -.1)]}
    res["h5_now"] = dd.iloc[-1] * 100

    # H6: 市場と要因で説明できる割合（情報・通信業など）
    raw_w = (1 + R.loc["2018-07-01":].fillna(0)).cumprod().resample("W-FRI").last().pct_change().loc["2019-01-01":]
    tw = P["1306.T"].resample("W-FRI").last().pct_change().reindex(raw_w.index)
    h6 = {}
    for s in ORDER:
        d = pd.concat([raw_w[s], tw.rename("TOPIX"), f.reindex(raw_w.index)], axis=1).dropna()
        A = np.column_stack([np.ones(len(d)), d[["TOPIX"] + F].to_numpy()]); y = d[s].to_numpy()
        c, *_ = np.linalg.lstsq(A, y, rcond=None); e2 = y - A @ c
        h6[s] = {"R2": 1 - e2 @ e2 / ((y - y.mean()) @ (y - y.mean())), "TOPIX": d[s].corr(d["TOPIX"]), "SOX": d[s].corr(d["SOX"]), "国内金利": d[s].corr(d["国内金利"])}
    res["h6"] = pd.DataFrame(h6).T
    res["rot"] = {f"電気機器×{s}": (WF["電気機器"].corr(WF[s]), WF.iloc[-52:]["電気機器"].corr(WF.iloc[-52:][s])) for s in ["情報・通信業", "サービス業", "医薬品", "銀行業"]}
    pd.to_pickle(res, D / "results.pkl")

    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 50)
    print(res["macro_3m"])
    b = res["beta_full"]; b1 = res["beta_1y"]
    print("\n=== 感応度（全期間）と 直近1年の t値 ===")
    print(pd.concat([b[[c + "_t" for c in F]].round(1), b["R2"].round(2), b1[[c + "_t" for c in F]].round(1).add_suffix("_1y")], axis=1).to_string())
    print("\n=== 条件付き（上位20%の週, %, t） ===")
    print(pd.DataFrame({fac: {s: f"{v[0]:+.2f} ({v[1]:+.1f})" for s, v in d.items()} for fac, d in res["cond"].items()}).to_string())
    print("\n=== 直近 ===\n", recent.round(2).sort_values("3か月").to_string())
    print("\n=== H5 電気機器 ===", res["h5"], "now", res["h5_now"])
    print("\n=== H6 R2 ===\n", res["h6"].round(2).sort_values("R2").to_string())
    print("\n=== rot ===", res["rot"])


if __name__ == "__main__":
    main()
