"""③ 米国株の先行性: 日本側の起点日以前の米国株騰落率と、日米の日次リターン連動."""
from pathlib import Path
import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent / "data"
p = pd.read_csv(D / "step3_prices.csv", parse_dates=["date"])
px = p.pivot_table(index="date", columns="code", values="close")

def ret(code, end, days):
    s = px[code].dropna()
    e = s.loc[:pd.Timestamp(end)]
    if len(e) <= days: return np.nan
    return (e.iloc[-1] / e.iloc[-1 - days] - 1) * 100

rows = []
for label, day0, codes in (
    ("半導体(日本側起点 2025-09-05)", "2025-09-04", ["^SOX", "NVDA", "MU", "SNDK", "WDC", "^IXIC"]),
    ("サイバー(日本側起点 2026-10-01)", "2026-09-30", ["CIBR", "HACK", "CRWD", "PANW", "ZS", "FTNT", "NET", "OKTA", "S", "^IXIC", "^SOX"]),
):
    for c in codes:
        rows.append({"case": label, "code": c, "ret_21d": ret(c, day0, 21), "ret_63d": ret(c, day0, 63),
                     "ret_126d": ret(c, day0, 126), "ret_252d": ret(c, day0, 252)})
lead = pd.DataFrame(rows).round(1)
lead.to_csv(D / "step3_us_lead.csv", index=False)
print(lead.to_string())

# 日本サイバーA(等ウェイト) と 前夜の米CIBR の日次連動 (2023-2026)
A = ["4704","3692","2326","4493","4475","4417","4398","4258","3042","4288","3682","3040"]
ja = px[A].pct_change().mean(axis=1)
us = px["CIBR"].dropna().pct_change()
us.index = us.index + pd.Timedelta(days=1)  # 米国T日の終値は日本T+1日の寄付前
al = pd.concat([ja.rename("ja"), us.reindex(ja.index, method="ffill").rename("us")], axis=1).dropna()
for y in (2023, 2024, 2025, 2026):
    s = al[al.index.year == y]
    print(y, "corr(日本サイバーA, 前夜CIBR)=", round(s.corr().iloc[0, 1], 3), "n=", len(s))
semi_ja = px["285A"].pct_change()
sox = px["^SOX"].dropna().pct_change(); sox.index = sox.index + pd.Timedelta(days=1)
al2 = pd.concat([semi_ja.rename("k"), sox.reindex(semi_ja.index, method="ffill").rename("sox")], axis=1).dropna()
for y in (2025, 2026):
    s = al2[al2.index.year == y]
    print(y, "corr(キオクシア, 前夜SOX)=", round(s.corr().iloc[0, 1], 3), "n=", len(s))
