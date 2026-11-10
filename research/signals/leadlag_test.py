"""「前夜の米国 → 東京の株」の組み合わせを過去データで探し、その後の期間でも当たったかを確かめる。

材料（前夜の米国セッション、T の寄付き前に確定）: SOX, ダウ, NVDA, TSM, MU, AMD, AVGO の変化率、米10年金利の変化、原油、ドル円
対象: 東証33業種（代表銘柄の時価総額加重）と 161 銘柄。いずれも TOPIX との差
  今日 = T の始値 → T の終値（寄付きで買って引けで売る。S株の約定タイミング）
  今週 = T の始値 → T+4 の終値
  今月 = T の始値 → T+20 の終値
探索期間 2019-2023 で |t| > 3 の組み合わせを選び、検証期間 2024-2026 で同じ向きに当たったかを見る。
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research")); sys.path.insert(0, str(ROOT / "research/sector33")); sys.path.insert(0, str(ROOT))
from earnings_study import fix_splits  # noqa: E402
from universe import SECTORS  # noqa: E402
from kabu_corr.collect import load_prices  # noqa: E402
from kabu_corr.align import build_aligned  # noqa: E402

raw = pd.read_pickle(ROOT / "data/research/sector33/raw.pkl")
info = pd.read_json(ROOT / "data/research/sector33/info.json").T
tick = [c + ".T" for m in SECTORS.values() for c in m]
C = pd.DataFrame({t: fix_splits(raw[t]["Adj Close"].dropna()) for t in tick + ["1306.T"]})
ratio = C / pd.DataFrame({t: raw[t]["Close"] for t in C.columns}).reindex(C.index)
O = pd.DataFrame({t: raw[t]["Open"] for t in C.columns}).reindex(C.index) * ratio
days = C["1306.T"].dropna().index
C, O = C.reindex(days), O.reindex(days)

# 前夜の米国（東京の営業日 T に揃えたもの）
al = build_aligned(load_prices(ROOT / "data/prices.csv"))["returns"]
us = al[["SOX", "DJI", "NVDA", "TSM", "MU", "AMD", "AVGO", "USDJPY"]].copy()
def prev_night(s):
    s = s.dropna(); left = pd.DataFrame({"d": days}); right = pd.DataFrame({"u": s.index, "v": s.to_numpy()})
    m = pd.merge_asof(left, right, left_on="d", right_on="u", allow_exact_matches=False)
    return pd.Series(m["v"].to_numpy(), index=days)
tnx = prev_night(raw["^TNX"]["Close"]); brent = prev_night(raw["BZ=F"]["Close"])
us["米10年金利"] = tnx.diff(); us["原油"] = np.log(brent).diff()
us = us.reindex(days)

def horizon_ret(k):
    """T の始値 → T+k の終値の、TOPIX との差。"""
    stock = C.shift(-k) / O - 1
    tpx = C["1306.T"].shift(-k) / O["1306.T"] - 1
    return stock.sub(tpx, axis=0)

def sector_ret(Rk):
    sh = info["shares"].astype(float)
    cap = (C * sh.reindex(C.columns)).shift(1)
    out = {}
    for s, m in SECTORS.items():
        cols = [c + ".T" for c in m]
        w = cap[cols].where(Rk[cols].notna())
        out[s] = (Rk[cols] * w).sum(axis=1) / w.sum(axis=1)
    return pd.DataFrame(out)

def corr_t(x, y):
    d = pd.concat([x, y], axis=1).dropna()
    if len(d) < 100: return np.nan, np.nan, len(d)
    r = d.iloc[:, 0].corr(d.iloc[:, 1]); n = len(d)
    return r, r * np.sqrt((n - 2) / (1 - r * r)), n

rows = []
for lab, k in [("今日", 0), ("今週", 4), ("今月", 20)]:
    Rk = horizon_ret(k)
    targets = {**{("業種", s): v for s, v in sector_ret(Rk).items()}, **{("銘柄", t): Rk[t] for t in tick}}
    step = {0: 1, 4: 5, 20: 21}[k]  # 重なりのない期間だけ使う（t値の水増しを防ぐ）
    for (kind, name), y in targets.items():
        for f in us.columns:
            x = us[f]
            ins = slice("2019-01-01", "2023-12-31"); oos = slice("2024-01-01", None)
            xi, yi = x.loc[ins].iloc[::step], y.loc[ins].iloc[::step]
            xo, yo = x.loc[oos].iloc[::step], y.loc[oos].iloc[::step]
            ri, ti, ni = corr_t(xi, yi); ro, to, no = corr_t(xo, yo)
            # 検証期間で「材料の符号どおりに買う/買わない」としたときの平均（材料が上がった日だけ、相関の向きに賭ける）
            d = pd.concat([xo, yo], axis=1).dropna()
            bet = (np.sign(d.iloc[:, 0]) * np.sign(ri) * d.iloc[:, 1]).mean() if len(d) else np.nan
            rows.append(dict(期間=lab, 種類=kind, 対象=name, 材料=f, 探索r=ri, 探索t=ti, 検証r=ro, 検証t=to, 検証n=no, 検証の売買平均=bet))
res = pd.DataFrame(rows)
res.to_pickle(ROOT / "data/research/leadlag_scan.pkl")

pd.set_option("display.width", 220)
print("調べた組み合わせ:", len(res))
for lab in ["今日", "今週", "今月"]:
    r = res[res.期間 == lab]
    sel = r[r.探索t.abs() > 3]
    same = (np.sign(sel.探索r) == np.sign(sel.検証r))
    held = sel[same & (sel.検証t.abs() > 2)]
    print(f"\n=== {lab} ===  組み合わせ {len(r)}  探索期間で|t|>3: {len(sel)}（偶然でも期待される数 約{len(r)*0.0027:.1f}）"
          f"  検証期間で同じ向き: {same.sum()}（{same.mean()*100 if len(sel) else 0:.0f}%）  検証期間でも|t|>2: {len(held)}")
    if len(sel):
        print(f"  選ばれた組み合わせの検証期間の売買平均: {sel.検証の売買平均.mean()*100:+.3f}%/回（中央値 {sel.検証の売買平均.median()*100:+.3f}%）")
        print(sel.sort_values("探索t", key=abs, ascending=False).head(8)[["種類", "対象", "材料", "探索r", "探索t", "検証r", "検証t", "検証の売買平均"]].round(3).to_string(index=False))
