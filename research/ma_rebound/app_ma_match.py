"""証券アプリの移動平均の期間設定を推定する.

アプリの値は 2026-10-13 14:05 のザラ場価格を含む。
→ 10/9 までの確定終値 + 10/13 をアプリの現在値で置き換えた系列で、
  単純移動平均(SMA)・指数移動平均(EMA) の期間 2〜300 を総当たりし、アプリの値に最も近い期間を探す。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent / "data"
APP = {
    "4507": {"name": "塩野義", "price": 2817.5, "短期": 2858.8, "中期": 2872.7, "長期": 2861.4},
    "9433": {"name": "KDDI", "price": 2905.5, "短期": 2975.1, "中期": 2941.8, "長期": 2892.6},
}


def series(code: str, use_app_price: bool) -> pd.Series:
    p = pd.read_csv(D / "prices.csv", parse_dates=["date"], dtype={"code": str})
    s = p[p.code == code].set_index("date").close.sort_index()
    s = s[s.index <= "2026-10-13"]
    if use_app_price:
        s.loc[pd.Timestamp("2026-10-13")] = APP[code]["price"]
    return s


def main() -> None:
    rows, best = [], []
    for variant, use_app in (("10/13=アプリ現在値", True), ("10/13=取得データの終値", False)):
        for code, a in APP.items():
            s = series(code, use_app)
            for kind in ("SMA", "EMA"):
                for n in range(2, 301):
                    v = s.rolling(n).mean().iloc[-1] if kind == "SMA" else s.ewm(span=n, adjust=False).mean().iloc[-1]
                    for line in ("短期", "中期", "長期"):
                        rows.append({"variant": variant, "code": code, "name": a["name"], "kind": kind, "n": n,
                                     "line": line, "app": a[line], "calc": v, "err%": (v / a[line] - 1) * 100})
            # 5/25/75 SMA の参考値
    df = pd.DataFrame(rows)
    df.to_csv(D / "app_ma_match.csv", index=False)
    out = []
    for variant in df.variant.unique():
        d = df[df.variant == variant]
        # 2銘柄同時に合う (kind, n) を線ごとに探す: 2銘柄の |誤差| の最大値で評価
        g = d.assign(abs_err=d["err%"].abs()).groupby(["line", "kind", "n"]).abs_err.max().reset_index()
        for line in ("短期", "中期", "長期"):
            top = g[g.line == line].nsmallest(5, "abs_err")
            for _, r in top.iterrows():
                vals = d[(d.line == line) & (d.kind == r.kind) & (d.n == r.n)]
                out.append({"前提": variant, "線": line, "種類": r.kind, "期間": int(r.n), "2銘柄の最大誤差%": r.abs_err,
                            **{f"{x.name} 計算値": x.calc for x in vals.itertuples()},
                            **{f"{x.name} アプリ": x.app for x in vals.itertuples()}})
    res = pd.DataFrame(out)
    res.to_csv(D / "app_ma_best.csv", index=False)
    print(res.to_string())


if __name__ == "__main__":
    main()
