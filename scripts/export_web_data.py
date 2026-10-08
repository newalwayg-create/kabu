import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from kabu_corr.collect import load_prices
from kabu_corr.align import build_aligned
from kabu_corr import analysis as A
from kabu_corr.config import INSTRUMENTS, by_key

a = build_aligned(load_prices("data/prices.csv"))
ret, parts = a["returns"], a["jp_parts"]
keys = [i.key for i in INSTRUMENTS if i.key in ret]
meta = {i.key: {"name": i.name_ja, "market": i.market, "group": i.group} for i in INSTRUMENTS}
r = lambda x: None if x is None or not np.isfinite(x) else round(float(x), 4)

corr = A.correlation_matrix(ret[keys])
rank = A.correlation_table(ret[keys], "N225")
us = [k for k in keys if by_key()[k].market == "US"]
semi = [k for k in keys if by_key()[k].group == "semi_jp"]
ll = A.lead_lag(ret, "N225", us + semi)
gap = []
for k in us + ["CME_OVERNIGHT"]:
    x = parts[k] if k == "CME_OVERNIGHT" else ret[k]
    g = A.corr_with_pvalue(parts["N225_GAP"], x); i = A.corr_with_pvalue(parts["N225_INTRADAY"], x)
    gap.append({"key": k, "gap": r(g[0]), "intra": r(i[0]), "hit": r(A.direction_hit_rate(parts["N225_GAP"], x)[0]), "n": g[1]})
regs = []
for xs in [["SOX", "DJI"], ["SOX", "DJI", "USDJPY"]]:
    f = A.ols(ret["N225"], ret[xs])
    regs.append({"x": xs, "coef": {k: r(v) for k, v in f["coef"].items()}, "t": {k: r(v) for k, v in f["t"].items()}, "r2": r(f["r2"]), "n": f["n"]})
beta = []
for k in semi:
    f = A.ols(ret[k], ret[["SOX"]]); beta.append({"key": k, "beta": r(f["coef"]["SOX"]), "r2": r(f["r2"])})
roll = A.rolling_corr(ret, "N225", ["NK_FUT_CME", "SOX", "DJI", "TEL"], 60).dropna(how="all")
yearly = A.yearly_corr(ret, "N225", ["NK_FUT_CME", "SOX", "DJI", "NVDA", "TEL"])
sc = {}
for k, x in [("SOX", ret["SOX"]), ("CME_OVERNIGHT", parts["CME_OVERNIGHT"])]:
    d = pd.concat([x.rename("x"), parts["N225_GAP"].rename("y")], axis=1).dropna()
    f = A.ols(d["y"], d[["x"]])
    sc[k] = {"pts": [[round(v * 100, 3), round(w * 100, 3), t.strftime("%Y-%m-%d")] for t, v, w in zip(d.index, d.x, d.y)],
             "b0": r(f["coef"]["const"] * 100), "b1": r(f["coef"]["x"]), "r2": r(f["r2"]), "n": f["n"]}
out = {
    "period": [ret.index.min().strftime("%Y-%m-%d"), ret.index.max().strftime("%Y-%m-%d")], "days": len(ret),
    "meta": meta, "keys": keys,
    "corr": [[r(v) for v in row] for row in corr.to_numpy()],
    "rank": [{"key": k, "corr": r(v)} for k, v in rank["corr"].items()],
    "leadlag": [{"key": k, **{c: r(v) for c, v in row.items()}} for k, row in ll.iterrows()],
    "gap": gap, "regs": regs, "beta": beta,
    "roll": {"dates": [d.strftime("%Y-%m-%d") for d in roll.index], **{c: [r(v) for v in roll[c]] for c in roll}},
    "yearly": {"years": [int(y) for y in yearly.index], **{c: [r(v) for v in yearly[c]] for c in yearly}},
    "scatter": sc,
}
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, separators=(",", ":"))
