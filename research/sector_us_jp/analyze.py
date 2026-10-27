"""米国の11業種（S&P500のセクターETF）が動いた翌日に、東証33業種がどう動くかを測る。

- 米国: XLK など11のセクターETF。日本: research/sector33 の時価総額加重の33業種（半導体銘柄も含む）
- 米国の t 日の動きを、東京の t+1 日に合わせる
- 3つの相関: 翌日の終値（前日終値から）、翌朝の寄り付き、寄り付きから引けまで
- 業種固有の連動: 米国はS&P500を、日本はTOPIX（1306）を差し引いた超過リターン同士の相関
- 2019〜23年と2024年以降に分けて、同じ向きが出るかを確かめる
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "research" / "sector33"))
from analyze import ORDER, load  # noqa: E402
from earnings_study import fix_splits  # noqa: E402
from universe import SECTORS  # noqa: E402

US = {"XLK": "情報技術", "XLC": "通信サービス", "XLY": "一般消費財", "XLP": "生活必需品", "XLV": "ヘルスケア", "XLF": "金融",
      "XLI": "資本財", "XLB": "素材", "XLE": "エネルギー", "XLU": "公益", "XLRE": "不動産", "SMH": "半導体（参考）"}
OUT = ROOT / "data" / "research" / "sector_us_jp"


def jp_sectors():
    P, _, shares = load()
    raw = pd.read_pickle(ROOT / "data" / "research" / "sector33" / "raw.pkl")
    O = pd.DataFrame({c: raw[c]["Open"] for c in P if c.endswith(".T") and c in raw.columns.get_level_values(0)}).reindex(P.index)
    Cl = pd.DataFrame({c: raw[c]["Close"] for c in O}).reindex(P.index)
    R = P.pct_change(fill_method=None)
    gap_s = O / Cl.shift() - 1
    oc_s = Cl / O - 1
    out = {k: {} for k in ("day", "gap", "oc")}
    for s, m in SECTORS.items():
        cols = [c + ".T" for c in m]
        w = pd.DataFrame({c: P[c] * shares[c] for c in cols}).shift(1)
        for k, X in (("day", R), ("gap", gap_s), ("oc", oc_s)):
            ww = w.where(X[cols].notna() & (X[cols].abs() < 0.3))
            out[k][s] = (X[cols] * ww).sum(axis=1) / ww.sum(axis=1)
    J = {k: pd.DataFrame(v)[ORDER] for k, v in out.items()}
    tp = {"day": R["1306.T"], "gap": (O["1306.T"] / Cl["1306.T"].shift() - 1) if "1306.T" in O else None}
    return J, R["1306.T"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    U = yf.download(list(US) + ["^GSPC"], start="2018-06-01", progress=False, auto_adjust=True)["Close"]
    ur = U.pct_change(fill_method=None)
    J, topix = jp_sectors()
    jd = J["day"].loc["2019-01-01":].index
    ud = ur.dropna(how="all").index
    prev = pd.Series([ud[ud < t][-1] for t in jd], index=jd)
    UA = ur.reindex(prev.values); UA.index = jd
    UX = UA[list(US)].sub(UA["^GSPC"], axis=0)
    JX = J["day"].loc[jd].sub(topix.loc[jd], axis=0)

    def corr(A, B):
        d = pd.concat([A, B], axis=1, keys=["a", "b"]).dropna()
        return round(float(d.a.corr(d.b)), 3) if len(d) > 100 else None

    res = {"us": list(US.values()), "us_keys": list(US), "jp": ORDER, "period": [str(jd[0].date()), str(jd[-1].date())]}
    for key, A, B in (("day", UA, J["day"]), ("gap", UA, J["gap"]), ("oc", UA, J["oc"]), ("excess", UX, JX)):
        res[key] = [[corr(A[u].loc[jd], B[s].loc[jd]) for s in ORDER] for u in US]
    for lab, sl in (("excess_is", slice(None, "2023-12-31")), ("excess_oos", slice("2024-01-01", None))):
        idx = jd[(jd >= pd.Timestamp(sl.start)) if sl.start else (jd <= pd.Timestamp(sl.stop))]
        res[lab] = [[corr(UX[u].loc[idx], JX[s].loc[idx]) for s in ORDER] for u in US]
    json.dump(res, open(OUT / "results.json", "w"), ensure_ascii=False)

    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
    for k in ("day", "gap", "oc", "excess"):
        M = pd.DataFrame(res[k], index=list(US.values()), columns=ORDER)
        print(f"\n=== {k} ===\n", M.T.round(2).to_string())
    I = pd.DataFrame(res["excess_is"], index=list(US.values()), columns=ORDER); O_ = pd.DataFrame(res["excess_oos"], index=list(US.values()), columns=ORDER)
    E = pd.DataFrame(res["excess"], index=list(US.values()), columns=ORDER)
    st = E.stack().sort_values()
    keep = [(u, s, E.loc[u, s], I.loc[u, s], O_.loc[u, s]) for (u, s) in list(st.index[:8]) + list(st.index[-15:])]
    print("\n=== 業種固有の連動（強い順）: 全期間 / 2019-23 / 2024- ===")
    for u, s, a, b, c in sorted(keep, key=lambda x: -x[2]):
        print(f"{u:>8} → {s:<10} {a:+.2f} {b:+.2f} {c:+.2f}")
    print("寄り後(日中)の相関の範囲", np.nanmin(res["oc"]), np.nanmax(res["oc"]))


if __name__ == "__main__":
    main()
