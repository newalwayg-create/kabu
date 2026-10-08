"""33業種の検証結果からWebページを作る: python research/sector33/export.py OUT.html [PREVIEW.html]"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from universe import SECTORS  # noqa: E402

R = pd.read_pickle(ROOT / "data/research/sector33/results.pkl")
ORDER = list(SECTORS)


def r(x, n=4):
    try:
        x = float(x); return None if not np.isfinite(x) else round(x, n)
    except (TypeError, ValueError):
        return x


def frame(df, n=4):
    return {"index": [i.strftime("%Y-%m") if hasattr(i, "strftime") else str(i) for i in df.index], "columns": list(df.columns),
            "values": [[r(v, n) for v in row] for row in df.to_numpy()]}


F = ["米10年金利", "国内金利", "ブレント原油", "SOX"]
data = {
    "order": ORDER, "members": SECTORS, "macro": R["macro_3m"], "cond_n": R["cond_n"],
    "monthly": frame(R["monthly"].iloc[-18:] * 100, 2),
    "beta": {k: {"b": frame(R[k][F], 3), "t": frame(R[k][[f + "_t" for f in F]], 2), "r2": [r(v, 3) for v in R[k]["R2"]]} for k in ("beta_full", "beta_1y")},
    "cond": {fac: [[r(v[0], 2), r(v[1], 2), r(v[2], 3)] for s, v in d.items()] for fac, d in R["cond"].items()},
    "tv": frame(R["tv_share"], 5), "cap": frame(R["cap_share"], 5),
    "recent": frame(R["recent"], 2),
    "h5": {k: {kk: r(vv, 3) for kk, vv in v.items()} for k, v in R["h5"].items()}, "h5_now": r(R["h5_now"], 2),
    "h6": frame(R["h6"], 3), "rot": {k: [r(a, 3), r(b, 3)] for k, (a, b) in R["rot"].items()},
}
page = (HERE / "template.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
Path(sys.argv[1]).write_text(page, encoding="utf-8")
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0">' + page + "</body></html>", encoding="utf-8")
print("ok")
