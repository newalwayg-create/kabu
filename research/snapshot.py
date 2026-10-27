"""今回の期間（10/13〜11/13）に決算がある銘柄の現在の数値を一覧にする。"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from earnings_study import load

ROOT = Path(__file__).resolve().parents[1]
C, O, E, I, names = load()
ev = pd.read_pickle(ROOT / "data/research/events.pkl").sort_values("date")
S = pd.read_pickle(Path(__file__).resolve().parents[1] / "data/research/etf.pkl")  # etf_series.py で作成
port = (0.53 * S["TOPIX ETF"].pct_change() + 0.36 * S["S&P500 ETF"].pct_change() + 0.11 * S["日経半導体ETF"].pct_change()).dropna()
R = C.pct_change()
last1y = R.index[-250:]
up = E[(E.jst >= "2026-10-13") & (E.jst <= "2026-11-13")].sort_values("jst").drop_duplicates("ticker")
rows = []
for r in up.itertuples():
    t = r.ticker
    if t not in C: continue
    inf = I.loc[t]; px = C[t].dropna().iloc[-1]
    h = ev[ev.ticker == t]
    last4 = h.tail(4)
    rr = R[t].loc[last1y]
    pc = pd.concat([rr, port], axis=1, sort=True).dropna()
    nk = pd.concat([rr, R["^N225"].loc[last1y]], axis=1, sort=True).dropna()
    rows.append({
        "ticker": t, "name": names[t[:-2]], "price": px, "earn_date": r.jst.strftime("%m/%d"), "earn_hour": r.jst.hour,
        "eps_est": r._2,
        "beats_last4": int(last4.beat.sum()) if len(last4) == 4 else np.nan,
        "beat_rate_all": h.beat.mean(), "n_hist": len(h),
        "abs_react_med": h.reaction.abs().median(), "react_sd": h.reaction.std(),
        "mom6_1": C[t].iloc[-22] / C[t].iloc[-127] - 1, "ret1m": C[t].iloc[-1] / C[t].iloc[-22] - 1,
        "vol_ann": rr.std() * np.sqrt(250), "beta_n225": np.polyfit(nk.iloc[:, 1], nk.iloc[:, 0], 1)[0],
        "corr_port": pc.corr().iloc[0, 1],
        "fwdPE": inf.forwardPE, "PBR": inf.priceToBook, "div": inf.dividendYield,
        "target_upside": inf.targetMeanPrice / px - 1 if inf.targetMeanPrice else np.nan,
        "rec": inf.recommendationMean, "analysts": inf.numberOfAnalystOpinions,
        "from_52w_high": px / inf.fiftyTwoWeekHigh - 1 if inf.fiftyTwoWeekHigh else np.nan,
        "sector": inf.sector,
    })
df = pd.DataFrame(rows).set_index("ticker")
df.to_pickle(ROOT / "data/research/snapshot.pkl")
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
fit = df[df.price <= 10000]
print(len(df), "銘柄に決算予定 /", len(fit), "銘柄が1株1万円以下")
cols = ["name", "price", "earn_date", "beats_last4", "abs_react_med", "mom6_1", "vol_ann", "beta_n225", "corr_port", "fwdPE", "PBR", "target_upside", "analysts"]
print(fit[cols].sort_values("corr_port").round(3).to_string())
