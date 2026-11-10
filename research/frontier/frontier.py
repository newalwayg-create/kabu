"""効率的フロンティアと、その配分を事後検証（ウォークフォワード）する。

- 共分散は Ledoit-Wolf の縮小推定、空売りなし、比率の合計は1
- 現金はリターン0の安全資産。フロンティアはリスク資産だけで描き、最大シャープはリスクフリー金利0で計算する
- ウォークフォワード: 毎月末に直前2年（504営業日）のデータで配分を決め、翌月その配分を持つ。売買手数料は0（SBIの条件下）とする
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data" / "research" / "frontier"
NAMES = {"1475.T": "TOPIX ETF", "1655.T": "S&P500 ETF", "SEMI": "日本の半導体株", "2510.T": "国内債券ETF",
         "2511.T": "外国債券ETF", "1540.T": "金", "9433.T": "KDDI", "9020.T": "JR東日本", "4452.T": "花王"}
A = list(NAMES)
AN = 250
# 計画の比率（現金を含む。合計1）
PLANS = {
    "計画v1.2（現在）": {"1475.T": 22557, "1655.T": 15979, "9433.T": 2893, "9020.T": 3376, "4452.T": 3557, "CASH": 1638},
    "計画v1（当初）": {"1475.T": 23727, "1655.T": 15975, "SEMI": 4740, "CASH": 5558},
}


def ledoit_wolf(X: np.ndarray) -> np.ndarray:
    """単位行列×平均分散 に向けた Ledoit-Wolf 縮小推定。"""
    X = X - X.mean(0)
    n, p = X.shape
    S = X.T @ X / n
    mu = np.trace(S) / p
    F = mu * np.eye(p)
    d2 = ((S - F) ** 2).sum()
    b2 = sum(((np.outer(x, x) - S) ** 2).sum() for x in X) / n ** 2
    b2 = min(b2, d2)
    k = b2 / d2 if d2 > 0 else 1.0
    return k * F + (1 - k) * S


def estimate(R: pd.DataFrame):
    X = R[A].to_numpy()
    return X.mean(0) * AN, ledoit_wolf(X) * AN


def solve(cov, mu=None, target=None, kind="minvar"):
    n = len(cov)
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1}]
    if target is not None:
        cons.append({"type": "eq", "fun": lambda w: w @ mu - target})
    if kind == "maxsharpe":
        f = lambda w: -(w @ mu) / np.sqrt(w @ cov @ w)  # noqa: E731
    else:
        f = lambda w: w @ cov @ w  # noqa: E731
    best = None
    for start in [np.full(n, 1 / n), *np.eye(n)[:3]]:
        r = minimize(f, start, method="SLSQP", bounds=[(0, 1)] * n, constraints=cons, options={"maxiter": 500, "ftol": 1e-12})
        if r.success and (best is None or r.fun < best.fun):
            best = r
    w = np.clip(best.x, 0, None) if best is not None else np.full(n, 1 / n)
    return w / w.sum()


def plan_weights(plan):
    tot = sum(plan.values())
    w = np.array([plan.get(a, 0) / tot for a in A])
    return w, plan.get("CASH", 0) / tot


def stats(mu, cov, w):
    return float(w @ mu), float(np.sqrt(w @ cov @ w))


def frontier(R: pd.DataFrame, n_pts: int = 40):
    mu, cov = estimate(R)
    w_min = solve(cov)
    w_ms = solve(cov, mu, kind="maxsharpe")
    lo, hi = float(w_min @ mu), float(mu.max())
    pts = []
    for t in np.linspace(lo, hi, n_pts):
        w = solve(cov, mu, target=t)
        r, s = stats(mu, cov, w)
        pts.append({"ret": r, "vol": s, "w": [round(float(x), 4) for x in w]})
    port = {}
    for name, w in [("最小分散", w_min), ("最大シャープ", w_ms), ("均等（1/N）", np.full(len(A), 1 / len(A))),
                    ("逆ボラティリティ", (1 / np.sqrt(np.diag(cov))) / (1 / np.sqrt(np.diag(cov))).sum())]:
        r, s = stats(mu, cov, w)
        port[name] = {"ret": r, "vol": s, "w": [round(float(x), 4) for x in w], "cash": 0.0}
    for name, plan in PLANS.items():
        w, cash = plan_weights(plan)
        r, s = stats(mu, cov, w)
        port[name] = {"ret": r, "vol": s, "w": [round(float(x), 4) for x in w], "cash": round(cash, 4)}
    nk = R["^N225"]
    port["日経平均（参考）"] = {"ret": float(nk.mean() * AN), "vol": float(nk.std() * np.sqrt(AN)), "w": None, "cash": 0.0}
    assets = [{"key": a, "name": NAMES[a], "ret": float(mu[i]), "vol": float(np.sqrt(cov[i, i]))} for i, a in enumerate(A)]
    corr = np.corrcoef(R[A].to_numpy().T)
    return {"points": pts, "portfolios": port, "assets": assets, "corr": [[round(float(x), 3) for x in row] for row in corr],
            "period": [str(R.index[0].date()), str(R.index[-1].date())], "days": len(R)}


def bootstrap(R: pd.DataFrame, n: int = 200, block: int = 21, seed: int = 0):
    """21営業日ブロックで再標本化し、最大シャープの配分と、計画のシャープ比がどれだけぶれるかを見る。"""
    rng = np.random.default_rng(seed)
    X = R[A].to_numpy(); T = len(X)
    wp, _ = plan_weights(PLANS["計画v1.2（現在）"])
    ws, gap, ms_sharpe, plan_sharpe = [], [], [], []
    for _ in range(n):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, T - block, T // block)])
        Xb = X[idx]
        mu, cov = Xb.mean(0) * AN, ledoit_wolf(Xb) * AN
        w = solve(cov, mu, kind="maxsharpe")
        sr_ms = (w @ mu) / np.sqrt(w @ cov @ w)
        sr_p = (wp @ mu) / np.sqrt(wp @ cov @ wp)
        ws.append(w); ms_sharpe.append(sr_ms); plan_sharpe.append(sr_p)
    ws = np.array(ws)
    return {"w_mean": ws.mean(0).round(4).tolist(), "w_p10": np.quantile(ws, .1, axis=0).round(4).tolist(),
            "w_p90": np.quantile(ws, .9, axis=0).round(4).tolist(), "w_zero_share": (ws < 0.01).mean(0).round(3).tolist(),
            "ms_sharpe": np.quantile(ms_sharpe, [.1, .5, .9]).round(3).tolist(), "plan_sharpe": np.quantile(plan_sharpe, [.1, .5, .9]).round(3).tolist(),
            "plan_ratio_median": float(np.median(np.array(plan_sharpe) / np.array(ms_sharpe)))}


def walk_forward(R: pd.DataFrame, lookback: int = 504):
    """毎月末に直前 lookback 日で配分を決め、翌月持つ。"""
    X = R[A]
    month_ends = X.groupby(X.index.to_period("M")).tail(1).index
    starts = [d for d in month_ends if X.index.get_loc(d) >= lookback - 1]
    methods = ["最小分散", "最大シャープ", "均等（1/N）", "逆ボラティリティ", "計画v1.2（固定）"]
    out = {m: [] for m in methods + ["日経平均"]}
    weights = {m: [] for m in methods}
    wp, cash = plan_weights(PLANS["計画v1.2（現在）"])
    for i, d in enumerate(starts[:-1]):
        loc = X.index.get_loc(d)
        hist = X.iloc[loc - lookback + 1: loc + 1]
        mu, cov = hist.mean().to_numpy() * AN, ledoit_wolf(hist.to_numpy()) * AN
        ws = {"最小分散": solve(cov), "最大シャープ": solve(cov, mu, kind="maxsharpe"), "均等（1/N）": np.full(len(A), 1 / len(A)),
              "逆ボラティリティ": (1 / np.sqrt(np.diag(cov))) / (1 / np.sqrt(np.diag(cov))).sum(), "計画v1.2（固定）": wp}
        nxt = X.loc[(X.index > d) & (X.index <= starts[i + 1])]
        for m, w in ws.items():
            out[m].append(pd.Series(nxt.to_numpy() @ w, index=nxt.index))
            weights[m].append(w)
        out["日経平均"].append(R["^N225"].loc[nxt.index])
    rets = pd.DataFrame({m: pd.concat(v) for m, v in out.items()})
    summ = {}
    for m in rets:
        r = rets[m]
        nav = (1 + r).cumprod()
        mo = (1 + r).groupby(r.index.to_period("M")).prod() - 1
        summ[m] = {"年率リターン": float(nav.iloc[-1] ** (AN / len(r)) - 1), "年率ボラ": float(r.std() * np.sqrt(AN)),
                   "シャープ比": float(r.mean() / r.std() * np.sqrt(AN)), "最大下落": float((nav / nav.cummax() - 1).min()),
                   "最悪の月": float(mo.min()), "月次の勝率": float((mo > 0).mean())}
        if m in weights:
            W = np.array(weights[m])
            summ[m]["月平均の入れ替え率"] = float(np.abs(np.diff(W, axis=0)).sum(1).mean() / 2)
            summ[m]["平均配分"] = W.mean(0).round(4).tolist()
    nav = (1 + rets).cumprod()
    navw = nav.resample("W-FRI").last()
    return {"summary": summ, "nav": {"dates": [d.strftime("%Y-%m-%d") for d in navw.index], **{m: navw[m].round(4).tolist() for m in navw}},
            "period": [str(rets.index[0].date()), str(rets.index[-1].date())],
            "weights_last": {m: np.array(weights[m][-1]).round(4).tolist() for m in methods},
            "ms_weights_path": {"dates": [d.strftime("%Y-%m") for d in starts[:-1]], "w": np.array(weights["最大シャープ"]).round(4).tolist()},
            "mv_weights_path": np.array(weights["最小分散"]).round(4).tolist()}


def main():
    R = pd.read_pickle(D / "returns.pkl")
    res = {"names": [NAMES[a] for a in A], "keys": A,
           "full": frontier(R), "last3y": frontier(R.iloc[-750:]), "boot": bootstrap(R), "wf": walk_forward(R),
           "plans": {k: {kk: v for kk, v in p.items()} for k, p in PLANS.items()}}
    json.dump(res, open(D / "results.json", "w"), ensure_ascii=False)
    pd.set_option("display.width", 200)
    for k in ("full", "last3y"):
        print(f"\n=== {k} {res[k]['period']} ===")
        P = pd.DataFrame({n: {"リターン": v["ret"], "ボラ": v["vol"], "シャープ": v["ret"] / v["vol"]} for n, v in res[k]["portfolios"].items()}).T
        print((P * [100, 100, 1]).round(2).to_string())
        print("最大シャープの配分:", {NAMES[a]: w for a, w in zip(A, res[k]["portfolios"]["最大シャープ"]["w"]) if w > 0.005})
        print("最小分散の配分:", {NAMES[a]: w for a, w in zip(A, res[k]["portfolios"]["最小分散"]["w"]) if w > 0.005})
    b = res["boot"]
    print("\n=== bootstrap ===")
    print("最大シャープ配分 平均/10%/90%/ほぼ0の割合:", {NAMES[a]: (m, lo, hi, z) for a, m, lo, hi, z in zip(A, b["w_mean"], b["w_p10"], b["w_p90"], b["w_zero_share"])})
    print("シャープ: 最大", b["ms_sharpe"], "計画", b["plan_sharpe"], "比の中央値", round(b["plan_ratio_median"], 3))
    print("\n=== walk-forward", res["wf"]["period"], "===")
    S = pd.DataFrame(res["wf"]["summary"]).T.drop(columns=["平均配分"], errors="ignore")
    print(S.round(3).to_string())


if __name__ == "__main__":
    main()
