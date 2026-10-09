"""効率的フロンティア用の資産データ（日次・円建て・株式分割補正済み）を作る。

日本の半導体ETF（200A）は2024年上場のため、東京エレクトロン・アドバンテスト・レーザーテック・SCREEN・ディスコの
均等平均で代用する（2019年から使える）。
"""
import sys
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research"))
from earnings_study import fix_splits  # noqa: E402

OUT = ROOT / "data" / "research" / "frontier"
ASSETS = {
    "1475.T": "TOPIX ETF", "1655.T": "S&P500 ETF", "SEMI": "日本の半導体株", "2510.T": "国内債券ETF",
    "2511.T": "外国債券ETF", "1540.T": "金", "9433.T": "KDDI", "9020.T": "JR東日本", "4452.T": "花王",
}
BENCH = "^N225"  # 1321 は Yahoo の配当調整後価格が負になる不具合があるため、指数で代用（配当は含まない）
SEMIS = ["8035.T", "6857.T", "6920.T", "7735.T", "6146.T"]

def clean(s: pd.Series) -> pd.Series:
    """1日だけ価格が1/10などになって数日内に戻る誤りを除き、残った大きな段差は株式分割として補正する。"""
    s = s.copy()
    r = s / s.shift(1)
    bad = r[(r < 0.3) | (r > 3.3)].index
    drop = set()
    for d in bad:
        i = s.index.get_loc(d)
        for j in range(i + 1, min(i + 6, len(s))):
            back = s.iloc[j] / s.iloc[i - 1]
            if 0.7 < back < 1.4:  # 元の水準に戻った → その間はデータの誤り
                drop.update(s.index[i:j])
                break
    s = s.drop(index=sorted(drop))
    return fix_splits(s)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    tick = [t for t in ASSETS if t != "SEMI"] + SEMIS + [BENCH, "1306.T"]
    raw = yf.download(tick, start="2018-06-01", auto_adjust=True, progress=False, group_by="ticker")
    P = pd.DataFrame({t: clean(raw[t]["Close"].dropna()) for t in tick})
    days = P["1475.T"].dropna().index
    P = P.reindex(days).ffill(limit=3)
    R = P.pct_change(fill_method=None)
    R["SEMI"] = R[SEMIS].mean(axis=1)
    # 1475 のデータ誤りを除いた日の前後は、同じ TOPIX 連動の 1306 のリターンで置き換える
    off = (R["1475.T"] - R["1306.T"]).abs() > 0.03
    R.loc[off, "1475.T"] = R.loc[off, "1306.T"]
    print("1475 を 1306 で置き換えた日:", [str(d.date()) for d in R.index[off]])
    R = R[list(ASSETS) + [BENCH]].loc["2019-01-01":].dropna()
    R.to_pickle(OUT / "returns.pkl")
    print(R.index.min().date(), "〜", R.index.max().date(), len(R), "日")
    print((R.mean() * 250 * 100).round(1).to_string())
    print("年率ボラ", (R.std() * 250 ** .5 * 100).round(1).to_dict())
    print("最大日次変動", R.abs().max().round(3).to_dict())
