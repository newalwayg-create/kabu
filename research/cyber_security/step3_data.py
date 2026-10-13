"""③ 用の価格・売買代金データ取得と集計.

- 日本: サイバー(①のA+B) / AI・半導体バスケット の日次売買代金（終値×出来高）
- 米国: サイバー株・ETF と 半導体 (SOX, MU など)
- 過去のサイバー物色局面（事件発生後）の値動き

出力: data/step3_*.csv
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

JST = timezone(timedelta(hours=9))
OUT = Path(__file__).resolve().parent / "data"

CYBER_A = ["4704", "3692", "2326", "4493", "4475", "4417", "4398", "4258", "3042", "4288",
           "436A", "153A", "338A", "3682", "3040"]
CYBER_B = ["4498", "3788", "5133", "3968", "4441", "3927", "4447", "3132", "3762", "3774", "3858"]
SEMI = {  # AI・半導体テーマの代表銘柄
    "285A": "キオクシアHD", "6857": "アドバンテスト", "8035": "東京エレクトロン",
    "6146": "ディスコ", "6920": "レーザーテック", "7735": "SCREEN", "6525": "KOKUSAI",
    "7729": "東京精密", "4062": "イビデン", "3436": "SUMCO", "6526": "ソシオネクスト",
    "6723": "ルネサス", "5803": "フジクラ",
}
US = ["CRWD", "PANW", "ZS", "FTNT", "NET", "OKTA", "S", "CIBR", "HACK",
      "^SOX", "NVDA", "MU", "SNDK", "WDC", "^GSPC", "^IXIC"]


def fetch(symbol: str, start: str, end: str = "2026-10-14") -> pd.DataFrame:
    p1 = int(datetime.fromisoformat(start).replace(tzinfo=JST).timestamp())
    p2 = int(datetime.fromisoformat(end).replace(tzinfo=JST).timestamp())
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.load(r)["chart"]["result"][0]
            break
        except Exception:
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError(symbol)
    tz = timezone(timedelta(seconds=res["meta"]["gmtoffset"]))
    q = res["indicators"]["quote"][0]
    idx = pd.to_datetime([datetime.fromtimestamp(t, tz).date() for t in res["timestamp"]])
    df = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close", "volume")}, index=idx)
    time.sleep(0.3)
    return df.dropna(subset=["close"])


def jp(code: str) -> str:
    return f"{code}.T"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    frames = []
    for grp, codes in (("cyberA", CYBER_A), ("cyberB", CYBER_B), ("semi", list(SEMI))):
        for c in codes:
            d = fetch(jp(c), "2014-01-01")
            d["code"], d["group"] = c, grp
            frames.append(d.reset_index(names="date"))
    for s in US:
        d = fetch(s, "2019-01-01")
        d["code"], d["group"] = s, "us"
        frames.append(d.reset_index(names="date"))
    for s in ("^N225", "1306.T"):
        d = fetch(s, "2014-01-01")
        d["code"], d["group"] = s, "index"
        frames.append(d.reset_index(names="date"))
    allp = pd.concat(frames)
    allp["turnover"] = allp["close"] * allp["volume"]
    allp.to_csv(OUT / "step3_prices.csv", index=False)
    print(allp.groupby("code")["date"].agg(["min", "max", "count"]).to_string())


if __name__ == "__main__":
    main()
