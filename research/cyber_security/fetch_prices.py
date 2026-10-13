"""② 株価取得と騰落率計算（サイバーセキュリティ関連銘柄）.

起点: 2026-10-01 の始値 / 終点: 基準日 2026-10-13 の終値。
データ: Yahoo Finance chart API (日足, 権利落ち等の調整なし生値)。

使い方: python research/cyber_security/fetch_prices.py
出力:   research/cyber_security/data/prices_daily.csv
        research/cyber_security/data/step2_returns.csv
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

JST = timezone(timedelta(hours=9))
START = "2026-10-01"
END = "2026-10-13"
THRESHOLD = 5.0  # %
HERE = Path(__file__).resolve().parent
OUT = HERE / "data"

# (code, name, rank) — ① のリスト
UNIVERSE = [
    ("4704", "トレンドマイクロ", "A"), ("3692", "FFRIセキュリティ", "A"),
    ("2326", "デジタルアーツ", "A"), ("4493", "サイバーセキュリティクラウド", "A"),
    ("4475", "HENNGE", "A"), ("4417", "グローバルセキュリティエキスパート", "A"),
    ("4398", "ブロードバンドセキュリティ", "A"), ("4258", "網屋", "A"),
    ("3042", "セキュアヴェイル", "A"), ("4288", "アズジェント", "A"),
    ("436A", "サイバーソリューションズ", "A"), ("153A", "カウリス", "A"),
    ("338A", "ZenmuTech", "A"), ("3682", "エンカレッジ・テクノロジ", "A"),
    ("3040", "ソリトンシステムズ", "A"),
    ("4498", "サイバートラスト", "B"), ("3788", "GMOグローバルサインHD", "B"),
    ("5133", "テリロジーHD", "B"), ("3968", "セグエグループ", "B"),
    ("4441", "トビラシステムズ", "B"), ("3927", "フーバーブレイン", "B"),
    ("4447", "ピー・ビーシステムズ", "B"), ("3132", "マクニカHD", "B"),
    ("3762", "テクマトリックス", "B"), ("3774", "IIJ", "B"),
    ("3858", "ユビキタスAI", "B"),
    ("6701", "NEC", "C"), ("6702", "富士通", "C"), ("6501", "日立製作所", "C"),
    ("6503", "三菱電機", "C"), ("9432", "NTT", "C"), ("9433", "KDDI", "C"),
    ("4307", "野村総合研究所", "C"), ("8056", "BIPROGY", "C"), ("9735", "セコム", "C"),
    ("3676", "デジタルハーツHD", "C"), ("6050", "イー・ガーディアン", "C"),
    ("4344", "ソースネクスト", "C"), ("3967", "エルテス", "C"), ("3697", "SHIFT", "C"),
    ("4812", "電通総研", "C"), ("5246", "ELEMENTS", "C"),
]
BENCH = [("^N225", "日経平均", "指数"), ("1306.T", "TOPIX連動ETF(1306)", "指数代替")]


def fetch(symbol: str) -> pd.DataFrame:
    p1 = int(datetime(2026, 4, 1, tzinfo=JST).timestamp())
    p2 = int(datetime(2026, 10, 14, tzinfo=JST).timestamp())
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                res = json.load(r)["chart"]["result"][0]
            break
        except Exception:
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError(symbol)
    q = res["indicators"]["quote"][0]
    idx = [datetime.fromtimestamp(t, JST).date() for t in res["timestamp"]]
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close", "volume")}, index=idx)
    df.index.name = "date"
    return df.dropna(subset=["close"])


def main() -> None:
    OUT.mkdir(exist_ok=True)
    rows, daily = [], []
    for code, name, rank in UNIVERSE + BENCH:
        sym = code if code.startswith("^") or code.endswith(".T") else f"{code}.T"
        df = fetch(sym)
        time.sleep(0.4)
        d = df.copy()
        d["code"], d["name"], d["rank"] = code, name, rank
        daily.append(d.reset_index())
        win = df.loc[pd.Timestamp(START).date():pd.Timestamp(END).date()]
        o = win["open"].iloc[0]
        c = win["close"].iloc[-1]
        start_close_prev = df.loc[:pd.Timestamp(START).date()]["close"].iloc[-2]
        rows.append({
            "code": code, "name": name, "rank": rank,
            "first_date": win.index[0], "last_date": win.index[-1],
            "open_1001": o, "close_1013": c,
            "ret_pct": (c / o - 1) * 100,
            "high_in_window": win["high"].max(),
            "max_runup_pct": (win["high"].max() / o - 1) * 100,
            "from_high_pct": (c / win["high"].max() - 1) * 100,
            "prev_close_0930": start_close_prev,
            "gap_1001_pct": (o / start_close_prev - 1) * 100,
            "ret_since_0901_pct": (c / df.loc[pd.Timestamp("2026-09-01").date():]["open"].iloc[0] - 1) * 100,
            "ret_0701_0930_pct": (start_close_prev / df.loc[pd.Timestamp("2026-07-01").date():]["open"].iloc[0] - 1) * 100,
            "turnover_window_oku": (win["close"] * win["volume"]).sum() / 1e8,
            "turnover_prev_window_oku": (
                df.loc[:pd.Timestamp("2026-09-30").date()].tail(len(win))
                .eval("close*volume").sum() / 1e8),
        })
    pd.concat(daily).to_csv(OUT / "prices_daily.csv", index=False)
    r = pd.DataFrame(rows)
    r["class"] = r.apply(
        lambda x: "-" if x["rank"].startswith("指数") else
        ("上げた(+5%以上)" if x["ret_pct"] >= THRESHOLD else "上げていない(+5%未満)"), axis=1)
    n225 = r.loc[r.code == "^N225", "ret_pct"].item()
    topix = r.loc[r.code == "1306.T", "ret_pct"].item()
    r["vs_n225_pt"] = r["ret_pct"] - n225
    r["vs_topix_pt"] = r["ret_pct"] - topix
    r.to_csv(OUT / "step2_returns.csv", index=False, float_format="%.2f")
    pd.set_option("display.width", 250)
    print(r[["code", "name", "rank", "first_date", "last_date", "open_1001", "close_1013",
             "ret_pct", "ret_since_0901_pct", "ret_0701_0930_pct", "gap_1001_pct", "max_runup_pct", "from_high_pct", "vs_n225_pt", "vs_topix_pt",
             "turnover_window_oku", "turnover_prev_window_oku", "class"]]
          .to_string(float_format=lambda v: f"{v:.2f}"))


if __name__ == "__main__":
    main()
