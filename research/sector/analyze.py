"""日本株の業種間の資金移動に関する6つの仮説を検証する。

業種 = 代表銘柄の均等加重バスケット。リターンは TOPIX ETF(1306) を差し引いた超過リターン。
要因（週次・金曜終値）:
  米10年金利   ^TNX の変化（%ポイント）
  国内金利     国内債券ETF(2510, NOMURA-BPI連動)の価格変化 ÷ 修正デュレーション約9年 × (−1)
               日本国債の利回りは取得できないため、その代わりの推定値
  ブレント原油 BZ=F の変化率（中東リスクの代わり）
  SOX          ^SOX の変化率
資金の流れ = 売買代金（終値×出来高）のシェア、資金の置き場所 = 時価総額（株価×現在の発行株数）のシェア
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data" / "research" / "sector"
sys.path.insert(0, str(ROOT / "research"))
from earnings_study import fix_splits, tstat  # noqa: E402

DURATION = 9.0
ORDER = ["半導体", "AI活用・ITサービス", "サイバーセキュリティ", "医薬品", "食品", "陸運", "銀行", "保険", "海運"]


def load():
    raw = pd.read_pickle(D / "raw.pkl")
    meta = json.load(open(D / "meta.json", encoding="utf-8"))
    B = meta["baskets"]
    px = {}
    for t in raw.columns.get_level_values(0).unique():
        s = raw[t]["Adj Close"].dropna()
        if len(s):
            px[t] = fix_splits(s)
    P = pd.DataFrame(px)
    jp_days = P["1306.T"].dropna().index
    P = P.reindex(P.index.union(jp_days)).ffill().reindex(jp_days)
    V = pd.DataFrame({t: raw[t]["Close"] * raw[t]["Volume"] for t in raw.columns.get_level_values(0).unique() if t.endswith(".T")}).reindex(jp_days)
    shares = {t: v[0] for t, v in meta["shares"].items()}
    return P, V, B, shares, meta


def basket_returns(P, B):
    R = P.pct_change(fill_method=None)
    out = {}
    for b, m in B.items():
        cols = [c + ".T" for c in m if c + ".T" in R]
        out[b] = R[cols].mean(axis=1, skipna=True)
    return pd.DataFrame(out)[ORDER]


def main():
    P, V, B, shares, meta = load()
    R = basket_returns(P, B)
    topix = P["1306.T"].pct_change(fill_method=None)
    X = R.sub(topix, axis=0)  # 日次超過リターン
    res = {}

    # ---- 週次データ ----
    idx = (1 + X.fillna(0)).cumprod()
    W = idx.resample("W-FRI").last().pct_change().dropna(how="all")
    f = pd.DataFrame({
        "米10年金利": P["^TNX"].resample("W-FRI").last().diff(),
        "国内金利": -np.log(P["2510.T"]).resample("W-FRI").last().diff() / DURATION * 100,
        "ブレント原油": P["BZ=F"].resample("W-FRI").last().pct_change(),
        "SOX": P["^SOX"].resample("W-FRI").last().pct_change(),
    }).reindex(W.index)
    WF = pd.concat([W, f], axis=1).loc["2019-01-01":].dropna()

    def betas(df):
        Z = df[f.columns]
        Zs = (Z - Z.mean()) / Z.std()
        A = np.column_stack([np.ones(len(Zs)), Zs.to_numpy()])
        rows = {}
        for b in ORDER:
            y = df[b].to_numpy()
            coef, *_ = np.linalg.lstsq(A, y, rcond=None)
            resid = y - A @ coef
            s2 = resid @ resid / (len(y) - A.shape[1])
            se = np.sqrt(np.diag(s2 * np.linalg.inv(A.T @ A)))
            r2 = 1 - resid @ resid / ((y - y.mean()) @ (y - y.mean()))
            rows[b] = {**{c: coef[i + 1] * 100 for i, c in enumerate(Z.columns)}, **{c + "_t": coef[i + 1] / se[i + 1] for i, c in enumerate(Z.columns)}, "R2": r2}
        return pd.DataFrame(rows).T

    res["beta_full"] = betas(WF)
    res["beta_1y"] = betas(WF.iloc[-52:])
    res["corr_full"] = WF[ORDER + list(f.columns)].corr().loc[ORDER, list(f.columns)]
    res["corr_1y"] = WF.iloc[-52:][ORDER + list(f.columns)].corr().loc[ORDER, list(f.columns)]

    # 金利が大きく上がった週（上位20%）の超過リターン
    cond = {}
    for fac in ["米10年金利", "国内金利", "ブレント原油"]:
        hi = WF[WF[fac] >= WF[fac].quantile(.8)]
        cond[fac] = {b: (hi[b].mean() * 100, tstat(hi[b]), (hi[b] > 0).mean()) for b in ORDER}
    res["cond"] = cond

    # ---- 月次の超過リターン（ヒートマップ） ----
    M = idx.resample("ME").last().pct_change().loc["2019-02":]
    res["monthly"] = M

    # ---- 資金シェア ----
    tv = {b: V[[c + ".T" for c in m if c + ".T" in V]].sum(axis=1, min_count=1) for b, m in B.items()}
    TV = pd.DataFrame(tv)[ORDER].resample("ME").sum()
    TVs = TV.div(TV.sum(axis=1), axis=0).loc["2019-01":]
    cap = {}
    for b, m in B.items():
        cols = [c + ".T" for c in m if c + ".T" in P and shares.get(c + ".T")]
        cap[b] = sum(P[c].ffill() * shares[c] for c in cols)
    CP = pd.DataFrame(cap)[ORDER].resample("ME").last()
    CPs = CP.div(CP.sum(axis=1), axis=0).loc["2019-01":]
    res["tv_share"], res["cap_share"] = TVs, CPs

    # ---- 直近の状況 ----
    last = X.index[-1]
    def ex(days):
        return ((1 + X.iloc[-days:]).prod() - 1) * 100
    recent = pd.DataFrame({"1か月": ex(21), "3か月": ex(63), "6か月": ex(126)})
    tvd = TV.iloc[-3:].sum() / TV.iloc[-3:].sum().sum() - TV.iloc[-15:-3].sum() / TV.iloc[-15:-3].sum().sum()
    recent["売買代金シェアの変化(pt)"] = tvd * 100
    res["recent"] = recent
    lvl = lambda s, n: (s.iloc[-1], s.iloc[-1 - n])
    us_now, us_3m = lvl(P["^TNX"].dropna(), 63)
    jgb_chg = (-np.log(P["2510.T"].iloc[-1] / P["2510.T"].iloc[-64]) / DURATION * 100)
    br_now, br_3m = lvl(P["BZ=F"].dropna(), 63)
    sox_3m = P["^SOX"].dropna().iloc[-1] / P["^SOX"].dropna().iloc[-64] - 1
    res["macro_3m"] = {"米10年金利": f"{us_3m:.2f}% → {us_now:.2f}%（{us_now - us_3m:+.2f}pt）",
                       "国内金利（推定）": f"{jgb_chg:+.2f}pt",
                       "ブレント原油": f"{br_3m:.1f} → {br_now:.1f}ドル（{(br_now / br_3m - 1) * 100:+.1f}%）",
                       "SOX": f"{sox_3m * 100:+.1f}%", "as_of": str(last.date())}

    # ---- H5 半導体の調整と決算 ----
    semi = idx["半導体"]
    semi_abs = (1 + R["半導体"].fillna(0)).cumprod()
    dd = semi_abs / semi_abs.rolling(252, min_periods=60).max() - 1
    fwd21 = semi.shift(-21) / semi - 1
    fwd63 = semi.shift(-63) / semi - 1
    h5 = {}
    for lab, m in [("下落率20%以上", dd <= -0.20), ("下落率10〜20%", (dd > -0.20) & (dd <= -0.10)), ("それ以外", dd > -0.10)]:
        h5[lab] = {"日数": int(m.sum()), "1か月後の超過(%)": fwd21[m].mean() * 100, "3か月後の超過(%)": fwd63[m].mean() * 100,
                   "3か月後にTOPIXを上回った割合": (fwd63[m] > 0).mean()}
    res["h5_drawdown"] = h5
    res["h5_now"] = {"半導体バスケットの高値からの下落率": dd.iloc[-1] * 100, "日付": str(dd.index[-1].date())}
    ev = pd.read_pickle(ROOT / "data/research/events.pkl")
    semis = [c + ".T" for c in B["半導体"]]
    se = ev[ev.ticker.isin(semis)].copy()
    C = P[semis]
    pre = []
    for r in se.itertuples():
        s = C[r.ticker].dropna()
        i = s.index.searchsorted(r.date) - 1
        pre.append(s.iloc[i] / s.iloc[i - 21] - 1 - (P["1306.T"].iloc[P.index.get_loc(s.index[i])] / P["1306.T"].iloc[P.index.get_loc(s.index[i]) - 21] - 1) if i > 21 else np.nan)
    se["pre21"] = pre
    h5e = {}
    for lab, m in [("決算前1か月にTOPIXより10%以上下げていた", se.pre21 <= -0.10), ("それ以外", se.pre21 > -0.10)]:
        x = se[m]
        h5e[lab] = {"件数": int(len(x)), "決算時の反応(%)": x.reaction.mean() * 100, "上昇した割合": (x.reaction > 0).mean(),
                    "上振れ率": x.beat.mean(), "決算後20日の超過(%)": x.drift20.mean() * 100}
    res["h5_earnings"] = h5e
    E = pd.read_pickle(ROOT / "data/research/earnings_clean.pkl")
    up = E[(E.ticker.isin(semis)) & (E.jst >= pd.Timestamp("2026-10-09", tz="Asia/Tokyo")) & (E.jst <= pd.Timestamp("2026-11-30", tz="Asia/Tokyo"))]
    res["h5_upcoming"] = {B["半導体"][t[:-2]]: d.strftime("%m/%d") for t, d in up.sort_values("jst").drop_duplicates("ticker")[["ticker", "jst"]].itertuples(index=False)}

    # ---- H6 サイバーの独立性 ----
    raw_w = (1 + R.fillna(0)).cumprod().resample("W-FRI").last().pct_change().loc["2019-01-01":]
    tw = P["1306.T"].resample("W-FRI").last().pct_change().reindex(raw_w.index)
    h6 = {}
    for b in ORDER:
        d = pd.concat([raw_w[b], tw.rename("TOPIX"), f.reindex(raw_w.index)], axis=1).dropna()
        A = np.column_stack([np.ones(len(d)), d[["TOPIX"] + list(f.columns)].to_numpy()])
        y = d[b].to_numpy(); coef, *_ = np.linalg.lstsq(A, y, rcond=None); resid = y - A @ coef
        h6[b] = {"市場と要因で説明できる割合(R2)": 1 - resid @ resid / ((y - y.mean()) @ (y - y.mean())),
                 "TOPIXとの相関": d[b].corr(d["TOPIX"]), "SOXとの相関": d[b].corr(d["SOX"]), "国内金利との相関": d[b].corr(d["国内金利"])}
    res["h6"] = pd.DataFrame(h6).T
    mx = M["サイバーセキュリティ"].dropna()
    res["h6_persist"] = {"月次超過リターンの自己相関(1か月)": mx.autocorr(1), "過去12か月の超過がプラスの月の翌月平均(%)":
                         M["サイバーセキュリティ"].where(M["サイバーセキュリティ"].rolling(12).sum().shift(1) > 0).mean() * 100,
                         "過去12か月の超過がマイナスの月の翌月平均(%)": M["サイバーセキュリティ"].where(M["サイバーセキュリティ"].rolling(12).sum().shift(1) <= 0).mean() * 100}
    sc = X["サイバーセキュリティ"].rolling(252).corr(X["半導体"])
    res["h6_corr_semis_1y"] = sc.dropna().iloc[-1]
    res["rot_corr"] = {"半導体×AI活用（週次超過）": WF["半導体"].corr(WF["AI活用・ITサービス"]), "半導体×サイバー（週次超過）": WF["半導体"].corr(WF["サイバーセキュリティ"]),
                       "直近1年 半導体×AI活用": WF.iloc[-52:]["半導体"].corr(WF.iloc[-52:]["AI活用・ITサービス"]),
                       "直近1年 半導体×サイバー": WF.iloc[-52:]["半導体"].corr(WF.iloc[-52:]["サイバーセキュリティ"])}
    pd.to_pickle(res, D / "results.pkl")
    pd.set_option("display.width", 220); pd.set_option("display.max_columns", 20)
    for k, v in res.items():
        if k in ("monthly", "tv_share", "cap_share"):
            print(f"\n=== {k} (直近6か月) ===\n", (v.tail(6) * (100 if k == "monthly" else 1)).round(3).to_string())
            continue
        print(f"\n=== {k} ===")
        print(v.round(3).to_string() if isinstance(v, pd.DataFrame) else v)


if __name__ == "__main__":
    main()
