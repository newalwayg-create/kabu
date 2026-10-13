"""③ 過去のサイバー物色局面と半導体テーマ立ち上がり期の比較（イベントスタディ）."""
from pathlib import Path
import pandas as pd

D = Path(__file__).resolve().parent / "data"
p = pd.read_csv(D / "step3_prices.csv", parse_dates=["date"])
p = p[p.date <= "2026-10-09"]  # 10/13は場中のため除外

def basket(group_codes):
    sub = p[p.code.isin(group_codes)]
    close = sub.pivot_table(index="date", columns="code", values="close")
    to = sub.pivot_table(index="date", columns="code", values="turnover").sum(axis=1) / 1e8
    return close, to

A = ["4704","3692","2326","4493","4475","4417","4398","4258","3042","4288","436A","153A","338A","3682","3040"]
SEMI = ["285A","6857","8035","6146","6920","7735","6525","7729","4062","3436","6526","6723","5803"]
n225 = p[p.code=="^N225"].set_index("date").close

EPISODES = [  # (名称, 事象日, 出典メモ)
    ("日本年金機構 125万件流出", "2015-06-01"),
    ("WannaCry 世界的拡散", "2017-05-15"),
    ("小島プレス攻撃・トヨタ全工場停止/ウクライナ侵攻", "2022-03-01"),
    ("KADOKAWA ランサム攻撃", "2024-06-10"),
    ("アサヒGHD ランサム攻撃", "2025-09-29"),
    ("アスクル ランサム攻撃", "2025-10-20"),
    ("今回: 情報漏えい連鎖(大和証券ほか)", "2026-10-01"),
]

def study(close, to, day0, horizons=(5, 20, 60, 120, 250)):
    idx = close.index
    i0 = idx.searchsorted(pd.Timestamp(day0))
    base_i = i0 - 1
    avail = close.iloc[base_i].notna()
    c = close.loc[:, avail]
    rel = c.iloc[base_i:] / c.iloc[base_i] - 1
    ew = rel.mean(axis=1) * 100  # 等ウェイト累積リターン
    nk = (n225.reindex(idx).ffill().iloc[base_i:] / n225.reindex(idx).ffill().iloc[base_i] - 1) * 100
    base_to = to.iloc[max(0, base_i-60):base_i].mean()
    out = {"n": int(avail.sum()), "base_to_oku": round(base_to, 1)}
    window = ew.iloc[:21]
    out["peak_ret_20d"] = round(window.max(), 1)
    out["peak_day"] = int(window.values.argmax())
    out["peak_to_x"] = round((to.iloc[i0:i0+20].max() / base_to), 1)
    for h in horizons:
        if base_i + h < len(idx):
            out[f"ret_{h}d"] = round(ew.iloc[h], 1)
            out[f"vsN225_{h}d"] = round(ew.iloc[h] - nk.iloc[h], 1)
            out[f"to_x_{h}d"] = round(to.iloc[base_i+h-4:base_i+h+1].mean() / base_to, 1)  # 5日平均売買代金/基準
    return out

if __name__ == "__main__":
    cA, tA = basket(A)
    rows = []
    for name, d0 in EPISODES:
        rows.append({"episode": name, "day0": d0, **study(cA, tA, d0)})
    cS, tS = basket(SEMI)
    rows.append({"episode": "【比較】AI・半導体 (キオクシア急騰開始)", "day0": "2025-09-05", **study(cS, tS, "2025-09-05")})
    k = p[p.code=="285A"].set_index("date")
    rows.append({"episode": "【比較】キオクシア単独", "day0": "2025-09-05",
                 **study(k[["close"]], k.turnover/1e8, "2025-09-05")})
    df = pd.DataFrame(rows)
    df.to_csv(D / "step3_episodes.csv", index=False)
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
    print(df.to_string())
