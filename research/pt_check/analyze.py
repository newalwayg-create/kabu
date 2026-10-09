"""ポートフォリオの検証: 個別のリスク、相関、リスク寄与、急落局面、フロンティア上の位置、実際に持っていた場合の成績。

python research/pt_check/analyze.py   （銘柄と比率は下の PT を書き換える）
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research")); sys.path.insert(0, str(ROOT / "research/frontier"))
from data import clean  # noqa: E402
from frontier import ledoit_wolf, solve  # noqa: E402

OUT = ROOT / "data" / "research" / "pt_check"
PT = {"4507.T": "塩野義製薬", "6954.T": "ファナック", "5802.T": "住友電工", "3778.T": "さくらインターネット",
      "1568.T": "TOPIXブル2倍（1568）", "9433.T": "KDDI", "3042.T": "セキュアヴェイル"}
WEIGHTS = {t: 1 / len(PT) for t in PT}  # 実際の金額が分かったら書き換える
REF = {"1306.T": "TOPIX", "^N225": "日経平均"}
PLAN = {"1475.T": 22557, "1655.T": 15979, "9433.T": 2893, "9020.T": 3376, "4452.T": 3557}  # 運用計画 v1.2（現金を除く）
AN = 250
STRESS = {"コロナショック（2020/2/20〜3/16）": ("2020-02-20", "2020-03-16"), "2022年の金利上昇（2022/1/4〜3/8）": ("2022-01-04", "2022-03-08"),
          "2024年8月の急落（7/31〜8/5）": ("2024-07-31", "2024-08-05"), "2025年4月の関税ショック（3/27〜4/7）": ("2025-03-27", "2025-04-07")}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tick = list(PT) + list(REF) + ["1475.T", "1655.T", "9020.T", "4452.T"]
    raw = yf.download(sorted(set(tick)), start="2018-06-01", auto_adjust=True, progress=False, group_by="ticker")
    vol_raw = yf.download(list(PT), period="3mo", auto_adjust=False, progress=False, group_by="ticker")
    P = pd.DataFrame({t: clean(raw[t]["Close"].dropna()) for t in sorted(set(tick))})
    days = P["1306.T"].dropna().index
    P = P.reindex(days).ffill(limit=3)
    R = P.pct_change(fill_method=None).loc["2019-01-01":]
    off = (R["1475.T"] - R["1306.T"]).abs() > 0.03
    R.loc[off, "1475.T"] = R.loc[off, "1306.T"]
    X = R[list(PT)].dropna()
    w = np.array([WEIGHTS[t] for t in PT])
    tpx = R["1306.T"].reindex(X.index)

    # 1) 個別
    rows = []
    for t in PT:
        r = X[t]; nav = (1 + r).cumprod()
        b = np.cov(r, tpx)[0, 1] / tpx.var()
        m21 = (P[t].shift(-21) / P[t] - 1).loc["2019":].dropna()
        tv = float((vol_raw[t]["Close"] * vol_raw[t]["Volume"]).tail(20).mean() / 1e8)
        rows.append({"key": t, "name": PT[t], "ret": float((1 + r).prod() ** (AN / len(r)) - 1), "vol": float(r.std() * np.sqrt(AN)),
                     "mdd": float((nav / nav.cummax() - 1).min()), "beta": float(b), "corr_tpx": float(r.corr(tpx)),
                     "var1m": float(m21.quantile(.05)), "tv_oku": tv, "weight": WEIGHTS[t], "price": float(P[t].dropna().iloc[-1])})
    # 2) ポートフォリオ（毎月末に比率を戻す）
    def port(Xs, ws):
        out = []
        for _, g in Xs.groupby(Xs.index.to_period("M")):
            v = np.cumprod(1 + g.to_numpy(), axis=0) @ ws
            out.append(pd.Series(np.diff(np.concatenate([[1], v])) / np.concatenate([[1], v[:-1]]), index=g.index))
        return pd.concat(out)
    pr = port(X, w)
    pw = np.array(list(PLAN.values()), float); pw /= pw.sum()
    plan_r = port(R[list(PLAN)].dropna().reindex(X.index).dropna(), pw)
    series = {"このポートフォリオ（均等）": pr, "TOPIX": tpx, "日経平均": R["^N225"].reindex(X.index), "運用計画v1.2": plan_r}
    def stats(r):
        r = r.dropna(); nav = (1 + r).cumprod(); mo = (1 + r).groupby(r.index.to_period("M")).prod() - 1
        return {"年率リターン": float(nav.iloc[-1] ** (AN / len(r)) - 1), "年率ボラ": float(r.std() * np.sqrt(AN)), "シャープ比": float(r.mean() / r.std() * np.sqrt(AN)),
                "最大下落": float((nav / nav.cummax() - 1).min()), "最悪の月": float(mo.min()), "月次の勝率": float((mo > 0).mean()),
                "TOPIXに対するβ": float(np.cov(r, tpx.reindex(r.index))[0, 1] / tpx.reindex(r.index).var())}
    summ = {k: stats(v) for k, v in series.items()}
    # 3) リスク寄与（直近2年の共分散）
    C = ledoit_wolf(X.iloc[-500:].to_numpy()) * AN
    pv = w @ C @ w
    rc = (w * (C @ w)) / pv
    corr = X.corr().to_numpy()
    # 4) 急落局面
    stress = {}
    for lab, (a, b_) in STRESS.items():
        seg = lambda s: float((1 + s.loc[a:b_]).prod() - 1)  # noqa: E731
        stress[lab] = {k: seg(v) for k, v in series.items()} | {PT[t]: seg(X[t]) for t in PT}
    # 5) レバレッジETFの目減り（TOPIXの2倍と比べる）
    lev = {}
    for y in range(2019, 2027):
        s = X["1568.T"].loc[str(y)]; tp = tpx.loc[str(y)]
        lev[str(y)] = {"1568": float((1 + s).prod() - 1), "TOPIXの2倍（単純）": float(2 * ((1 + tp).prod() - 1)), "TOPIX": float((1 + tp).prod() - 1)}
    # 6) フロンティア（この7銘柄）
    mu = X.mean().to_numpy() * AN; Cf = ledoit_wolf(X.to_numpy()) * AN
    w_ms = solve(Cf, mu, kind="maxsharpe"); w_mv = solve(Cf)
    pts = []
    for tgt in np.linspace(float(w_mv @ mu), float(mu.max()), 30):
        ww = solve(Cf, mu, target=tgt); pts.append({"ret": float(ww @ mu), "vol": float(np.sqrt(ww @ Cf @ ww)), "w": ww.round(4).tolist()})
    fr = {"points": pts, "assets": [{"name": PT[t], "ret": float(mu[i]), "vol": float(np.sqrt(Cf[i, i]))} for i, t in enumerate(PT)],
          "port": {k: {"ret": float(v @ mu), "vol": float(np.sqrt(v @ Cf @ v)), "w": v.round(4).tolist()} for k, v in [("このポートフォリオ（均等）", w), ("最大シャープ", w_ms), ("最小分散", w_mv)]}}
    navw = pd.DataFrame({k: (1 + v.dropna()).cumprod() for k, v in series.items()}).resample("W-FRI").last()
    res = {"names": [PT[t] for t in PT], "keys": list(PT), "assets": rows, "summary": summ, "rc": rc.round(4).tolist(), "corr": corr.round(3).tolist(),
           "stress": stress, "lev": lev, "frontier": fr, "period": [str(X.index[0].date()), str(X.index[-1].date())],
           "nav": {"dates": [d.strftime("%Y-%m-%d") for d in navw.index], **{k: [None if pd.isna(x) else round(float(x), 4) for x in navw[k]] for k in navw}},
           "eff_beta_from_lev": float(WEIGHTS["1568.T"] * rows[list(PT).index("1568.T")]["beta"])}
    json.dump(res, open(OUT / "results.json", "w"), ensure_ascii=False)

    pd.set_option("display.width", 220)
    print("期間", res["period"])
    A = pd.DataFrame(rows).set_index("name")[["ret", "vol", "mdd", "beta", "corr_tpx", "var1m", "tv_oku", "price"]]
    print(A.round(3).to_string())
    print("\nリスク寄与:", {PT[t]: round(x * 100, 1) for t, x in zip(PT, rc)})
    print("\n", pd.DataFrame(summ).T.round(3).to_string())
    print("\n急落局面:"); print(pd.DataFrame(stress).T[list(series)].round(3).to_string())
    print("\nレバETF:", {y: {k: round(v, 3) for k, v in d.items()} for y, d in lev.items()})
    print("\n最大シャープ:", {PT[t]: x for t, x in zip(PT, w_ms.round(3)) if x > .005}, "最小分散:", {PT[t]: x for t, x in zip(PT, w_mv.round(3)) if x > .005})
    print("均等のフロンティア上:", {k: (round(v["ret"], 3), round(v["vol"], 3), round(v["ret"] / v["vol"], 2)) for k, v in fr["port"].items()})
    print("相関（平均, 除対角）:", round((corr.sum() - len(corr)) / (len(corr) ** 2 - len(corr)), 3))


if __name__ == "__main__":
    main()
