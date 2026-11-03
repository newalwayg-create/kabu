"""長期保有向け 配当株スクリーニング.

基準:
  ① 減配していない     : 過去10暦年(2016-2025)の年間配当合計が前年割れなし（1%未満の端数差は許容）
                          + 直近12か月配当が前年同期以上
  ② 利回り2.5%以上     : 直近12か月の実績配当 ÷ 現在株価
  ③ チャートが底付近   : 52週レンジの下から30%以内
  ④ 自己資本比率50%以上: 直近4期の年次決算すべてで 株主資本÷総資産 ≥ 50%

    python scripts/dividend_screen.py
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parents[1] / "output"

UNIVERSE = {
    "1414": "ショーボンドHD", "1605": "INPEX", "1801": "大成建設", "1802": "大林組", "1803": "清水建設",
    "1812": "鹿島建設", "1820": "西松建設", "1878": "大東建託", "1925": "大和ハウス", "1928": "積水ハウス",
    "1930": "北陸電気工事", "1942": "関電工", "1944": "きんでん", "1951": "エクシオG",
    "2002": "日清製粉G", "2181": "パーソルHD", "2206": "江崎グリコ", "2269": "明治HD", "2502": "アサヒGHD",
    "2503": "キリンHD", "2593": "伊藤園", "2659": "サンエー", "2768": "双日", "2802": "味の素",
    "2897": "日清食品HD", "2914": "JT", "3003": "ヒューリック", "3048": "ビックカメラ", "3088": "マツキヨココカラ",
    "3231": "野村不動産HD", "3289": "東急不動産HD", "3402": "東レ", "3405": "クラレ", "3407": "旭化成",
    "3861": "王子HD", "4004": "レゾナック", "4005": "住友化学", "4021": "日産化学", "4042": "東ソー",
    "4061": "デンカ", "4063": "信越化学", "4182": "三菱ガス化学", "4183": "三井化学", "4188": "三菱ケミカルG",
    "4204": "積水化学", "4208": "UBE", "4307": "野村総研", "4452": "花王", "4502": "武田薬品",
    "4503": "アステラス", "4507": "塩野義", "4519": "中外製薬", "4523": "エーザイ", "4527": "ロート製薬",
    "4528": "小野薬品", "4536": "参天製薬", "4568": "第一三共", "4578": "大塚HD", "4613": "関西ペイント",
    "4631": "DIC", "4641": "アルプス技研", "4684": "オービック", "4704": "トレンドマイクロ", "4732": "USS",
    "4733": "OBC", "4911": "資生堂", "4912": "ライオン", "4917": "マンダム", "4922": "コーセー",
    "5020": "ENEOS", "5101": "横浜ゴム", "5108": "ブリヂストン", "5110": "住友ゴム", "5201": "AGC",
    "5214": "日本電気硝子", "5233": "太平洋セメント", "5332": "TOTO", "5333": "日本ガイシ", "5334": "日本特殊陶業",
    "5401": "日本製鉄", "5406": "神戸製鋼", "5411": "JFEHD", "5711": "三菱マテリアル", "5713": "住友金属鉱山",
    "5801": "古河電工", "5802": "住友電工", "5938": "LIXIL", "5947": "リンナイ", "5970": "ジーテクト",
    "6098": "リクルートHD", "6141": "DMG森精機", "6178": "日本郵政", "6268": "ナブテスコ", "6273": "SMC",
    "6301": "コマツ", "6305": "日立建機", "6326": "クボタ", "6345": "アイチコーポ", "6361": "荏原",
    "6367": "ダイキン", "6383": "ダイフク", "6417": "SANKYO", "6463": "TPR", "6471": "日本精工",
    "6472": "NTN", "6473": "ジェイテクト", "6501": "日立", "6503": "三菱電機", "6504": "富士電機",
    "6506": "安川電機", "6586": "マキタ", "6594": "ニデック", "6645": "オムロン", "6701": "NEC",
    "6702": "富士通", "6724": "セイコーエプソン", "6752": "パナソニックHD", "6758": "ソニーG", "6762": "TDK",
    "6770": "アルプスアルパイン", "6841": "横河電機", "6857": "アドバンテスト", "6861": "キーエンス", "6902": "デンソー",
    "6914": "オプテックスG", "6920": "レーザーテック", "6923": "スタンレー電気", "6952": "カシオ", "6954": "ファナック",
    "6963": "ローム", "6971": "京セラ", "6981": "村田製作所", "6988": "日東電工", "7011": "三菱重工",
    "7012": "川崎重工", "7013": "IHI", "7202": "いすゞ", "7203": "トヨタ", "7240": "NOK",
    "7261": "マツダ", "7267": "ホンダ", "7269": "スズキ", "7270": "SUBARU", "7272": "ヤマハ発動機",
    "7466": "SPK", "7476": "アズワン", "7564": "ワークマン", "7731": "ニコン", "7733": "オリンパス",
    "7741": "HOYA", "7751": "キヤノン", "7752": "リコー", "7832": "バンダイナムコ", "7911": "TOPPAN",
    "7912": "大日本印刷", "7951": "ヤマハ", "7974": "任天堂", "7988": "ニフコ", "7990": "グローブライド",
    "8001": "伊藤忠", "8002": "丸紅", "8015": "豊田通商", "8031": "三井物産", "8053": "住友商事",
    "8058": "三菱商事", "8113": "ユニ・チャーム", "8130": "サンゲツ", "8267": "イオン", "8306": "三菱UFJ",
    "8316": "三井住友FG", "8411": "みずほFG", "8424": "芙蓉リース", "8566": "リコーリース", "8591": "オリックス",
    "8593": "三菱HCキャピタル", "8601": "大和証券G", "8604": "野村HD", "8630": "SOMPO", "8725": "MS&AD",
    "8750": "第一生命HD", "8766": "東京海上HD", "8801": "三井不動産", "8802": "三菱地所", "8830": "住友不動産",
    "9020": "JR東日本", "9022": "JR東海", "9101": "日本郵船", "9104": "商船三井", "9107": "川崎汽船",
    "9201": "JAL", "9202": "ANA", "9432": "NTT", "9433": "KDDI", "9434": "ソフトバンク",
    "9436": "沖縄セルラー", "9501": "東京電力HD", "9502": "中部電力", "9503": "関西電力", "9531": "東京ガス",
    "9532": "大阪ガス", "9613": "NTTデータG", "9697": "カプコン", "9735": "セコム", "9746": "TKC",
    "9766": "コナミG", "9769": "学究社", "9843": "ニトリHD", "9983": "ファーストリテイリング", "9984": "ソフトバンクG",
}

YEARS = list(range(2016, 2026))
TOL = 0.99


def dividend_check(div: pd.Series, asof: pd.Timestamp) -> dict:
    if div.empty:
        return {"無減配": False, "連続年数": 0, "減配年": "配当なし", "TTM配当": 0.0}
    div.index = div.index.tz_localize(None)
    annual = div.groupby(div.index.year).sum()
    cuts, streak, prev = [], 0, None
    for y in YEARS:
        v = annual.get(y, 0.0)
        if prev is not None and v < prev * TOL:
            cuts.append(str(y))
            streak = 0
        elif prev is not None:
            streak += 1
        prev = v
    ttm = div[div.index > asof - pd.Timedelta(days=365)].sum()
    ttm_prev = div[(div.index > asof - pd.Timedelta(days=730)) & (div.index <= asof - pd.Timedelta(days=365))].sum()
    if ttm < ttm_prev * TOL:
        cuts.append("直近12M")
    return {
        "無減配": not cuts and annual.get(YEARS[0], 0) > 0,
        "連続年数": streak,
        "減配年": ",".join(cuts),
        "TTM配当": round(float(ttm), 2),
        "2016配当": round(float(annual.get(2016, 0)), 2),
        "2025配当": round(float(annual.get(2025, 0)), 2),
    }


def equity_ratios(t: yf.Ticker) -> list[float]:
    for _ in range(3):
        try:
            bs = t.balance_sheet
            if bs is not None and not bs.empty:
                eq = bs.loc["Stockholders Equity"]
                ta = bs.loc["Total Assets"]
                r = (eq / ta * 100).dropna()
                return [round(float(x), 1) for x in r.values]
            return []
        except Exception:
            time.sleep(3)
    return []


def main():
    tickers = [f"{c}.T" for c in UNIVERSE]
    px = yf.download(tickers, period="3y", actions=True, auto_adjust=False, group_by="ticker",
                     progress=False, threads=True)
    rows = []
    for code, name in UNIVERSE.items():
        tk = f"{code}.T"
        try:
            d = px[tk].dropna(subset=["Close"])
        except KeyError:
            continue
        if d.empty:
            continue
        asof = d.index[-1].tz_localize(None) if d.index.tz else d.index[-1]
        close = float(d["Close"].iloc[-1])
        last1y = d[d.index >= d.index[-1] - pd.Timedelta(days=365)]
        hi, lo = last1y["High"].max(), last1y["Low"].min()
        pos52 = (close - lo) / (hi - lo) * 100 if hi > lo else np.nan
        hi3 = d["High"].max()
        ma200 = d["Close"].rolling(200).mean().iloc[-1]

        t = yf.Ticker(tk)
        try:
            div = t.dividends
        except Exception:
            div = pd.Series(dtype=float)
        dc = dividend_check(div.copy(), pd.Timestamp(asof))
        er = equity_ratios(t)
        time.sleep(0.4)

        yld = dc["TTM配当"] / close * 100 if close else np.nan
        rows.append({
            "コード": code, "銘柄": name, "株価": round(close, 1), "日付": str(asof.date()),
            "利回り%": round(yld, 2),
            "52週位置%": round(pos52, 1), "3年高値比%": round((close / hi3 - 1) * 100, 1),
            "200日線乖離%": round((close / ma200 - 1) * 100, 1) if pd.notna(ma200) else np.nan,
            "自己資本比率%(直近)": er[0] if er else np.nan,
            "自己資本比率%(4期最低)": min(er) if er else np.nan,
            **dc,
        })
        print(code, name, "ok", flush=True)

    df = pd.DataFrame(rows)
    df["①無減配"] = df["無減配"]
    df["②利回り"] = df["利回り%"] >= 2.5
    df["③底付近"] = df["52週位置%"] <= 30
    df["④自己資本"] = df["自己資本比率%(4期最低)"] >= 50
    df["該当数"] = df[["①無減配", "②利回り", "③底付近", "④自己資本"]].sum(axis=1)
    df = df.sort_values(["該当数", "利回り%"], ascending=False)
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / "dividend_screen.csv", index=False, encoding="utf-8-sig")
    print(df[df["該当数"] >= 3].to_string())


if __name__ == "__main__":
    main()
