"""検証結果をWebページ用のJSONに書き出し、HTMLを作る: python research/sector/export.py OUT.html"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
R = pd.read_pickle(ROOT / "data/research/sector/results.pkl")
meta = json.load(open(ROOT / "data/research/sector/meta.json", encoding="utf-8"))
ORDER = list(R["recent"].index)
GROUPS = {"半導体": ["半導体"], "AI活用・ITサービス": ["AI活用・ITサービス"], "サイバーセキュリティ": ["サイバーセキュリティ"],
          "ディフェンシブ（医薬・食品・陸運）": ["医薬品", "食品", "陸運"], "銀行": ["銀行"], "保険": ["保険"], "海運": ["海運"]}


def r(x, n=4):
    try:
        x = float(x)
        return None if not np.isfinite(x) else round(x, n)
    except (TypeError, ValueError):
        return x


def frame(df, n=4):
    return {"index": [str(i.date()) if hasattr(i, "date") else str(i) for i in df.index], "columns": list(df.columns),
            "values": [[r(v, n) for v in row] for row in df.to_numpy()]}


def shares(df):
    g = pd.DataFrame({k: df[v].sum(axis=1) for k, v in GROUPS.items()})
    return {"months": [d.strftime("%Y-%m") for d in df.index], "groups": list(GROUPS),
            "group": [[r(v, 5) for v in row] for row in g.to_numpy()],
            "detail": [[r(v, 5) for v in row] for row in df[ORDER].to_numpy()]}


tv, cap = R["tv_share"], R["cap_share"]
tv_ex = tv.drop(columns="半導体"); tv_ex = tv_ex.div(tv_ex.sum(axis=1), axis=0); tv_ex.insert(0, "半導体", 0.0)
F = ["米10年金利", "国内金利", "ブレント原油", "SOX"]
data = {
    "order": ORDER, "baskets": meta["baskets"], "macro": R["macro_3m"],
    "monthly": frame(R["monthly"].iloc[-18:] * 100, 2),
    "beta": {k: {"b": frame(R[k][F], 3), "t": frame(R[k][[f + "_t" for f in F]], 2), "r2": {b: r(v, 3) for b, v in R[k]["R2"].items()}} for k in ("beta_full", "beta_1y")},
    "cond": {fac: {b: [r(v[0], 2), r(v[1], 2), r(v[2], 3)] for b, v in d.items()} for fac, d in R["cond"].items()},
    "tv": shares(tv), "tv_ex": shares(tv_ex), "cap": shares(cap),
    "recent": frame(R["recent"], 2),
    "h5": {k: {kk: r(vv, 3) for kk, vv in v.items()} for k, v in R["h5_drawdown"].items()},
    "h5e": {k: {kk: r(vv, 3) for kk, vv in v.items()} for k, v in R["h5_earnings"].items()},
    "h5_now": {k: r(v, 2) for k, v in R["h5_now"].items()}, "h5_up": R["h5_upcoming"],
    "h6": frame(R["h6"], 3), "h6p": {k: r(v, 3) for k, v in R["h6_persist"].items()},
    "rot": {k: r(v, 3) for k, v in R["rot_corr"].items()},
}
page = (HERE / "template.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
Path(sys.argv[1]).write_text(page, encoding="utf-8")
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">' + page + "</body></html>", encoding="utf-8")
print("ok")
