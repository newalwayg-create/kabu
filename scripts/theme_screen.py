"""自動運転・タクシー・自動運転関連部品の関連銘柄スクリーニング.

Yahoo Finance から株価と財務指標を取得し、テーマ別の一覧を
output/theme_screen.csv と output/theme_screen.md に書き出す。

    python scripts/theme_screen.py
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parents[1] / "output"

# (テーマ, コード, 銘柄名, 関連内容)
UNIVERSE = [
    # ① 自動運転（車両・サービス・ソフト・地図）
    ("自動運転", "7203", "トヨタ自動車", "Woven by Toyota、Waymoと協業"),
    ("自動運転", "7267", "ホンダ", "都内ロボタクシー計画（GM/Cruise提携解消後も継続）"),
    ("自動運転", "7201", "日産自動車", "ProPILOT、Wayveと次世代ADAS"),
    ("自動運転", "7270", "SUBARU", "アイサイト"),
    ("自動運転", "9984", "ソフトバンクG", "Wayve出資、DiDi・MONET"),
    ("自動運転", "9434", "ソフトバンク", "MONET Technologies、BOLDLY(自動運転バス)"),
    ("自動運転", "9433", "KDDI", "自動運転向け通信基盤・遠隔監視"),
    ("自動運転", "3132", "マクニカHD", "自動運転EVバス導入・運行支援"),
    ("自動運転", "4667", "アイサンテクノロジー", "高精度3D地図、ティアフォーと協業"),
    ("自動運転", "336A", "ダイナミックマッププラットフォーム", "自動運転用HDマップ"),
    ("自動運転", "9474", "ゼンリン", "地図データ・自動運転用地図"),
    ("自動運転", "4425", "Kudan", "SLAM（空間認識）ソフト"),
    ("自動運転", "3040", "ソリトンシステムズ", "遠隔監視映像伝送"),
    # ② タクシー
    ("タクシー", "581A", "GO", "配車アプリ最大手（2026/6上場）"),
    ("タクシー", "9082", "大和自動車交通", "都内大手4社で唯一の上場"),
    ("タクシー", "9035.F", "第一交通産業", "保有台数国内最大級（福証単独上場）"),
    ("タクシー", "9048", "名古屋鉄道", "名鉄タクシーHD"),
    ("タクシー", "9031", "西日本鉄道", "西鉄タクシー"),
    ("タクシー", "6758", "ソニーグループ", "S.RIDE、ホンダとAFEELA"),
    # ③ 自動運転関連部品（センサー・半導体・電装）
    ("関連部品", "6902", "デンソー", "ADAS ECU・ミリ波レーダー・カメラ"),
    ("関連部品", "7259", "アイシン", "駐車支援・電動ユニット"),
    ("関連部品", "6723", "ルネサス", "車載SoC（R-Car）・MCU"),
    ("関連部品", "6526", "ソシオネクスト", "車載カスタムSoC"),
    ("関連部品", "6963", "ローム", "車載パワー半導体・センサー"),
    ("関連部品", "6981", "村田製作所", "車載MLCC・慣性センサー"),
    ("関連部品", "6762", "TDK", "車載センサー・受動部品"),
    ("関連部品", "6971", "京セラ", "車載カメラ・LiDAR一体ランプ"),
    ("関連部品", "6503", "三菱電機", "ADAS・xAUTO(レベル4)"),
    ("関連部品", "7276", "小糸製作所", "LiDAR(Cepton)・ヘッドランプ"),
    ("関連部品", "6923", "スタンレー電気", "ランプ・センシング"),
    ("関連部品", "6965", "浜松ホトニクス", "LiDAR向け受光素子"),
    ("関連部品", "6995", "東海理化", "電子キー・HMI"),
    ("関連部品", "7282", "豊田合成", "センサー対応エンブレム等"),
    ("関連部品", "6875", "メガチップス", "車載向けLSI"),
]


# Yahoo Finance の既知の不整合（分割直後の1株指標ずれ等）。値は手で補正せず注記する
NOTES = [
    "豊田合成(7282): 2026/9/29 に1→5株分割。配当利回り10.8%・予想PER2.8は分割前の1株値によるずれ。"
    "実質は配当利回り約2.1%（年102.6円÷5）、予想PER約14倍。",
    "KDDI(9433): 予想EPSが2.33円と誤っており予想PER(1217倍)は無効。実績PER 14.6倍を参照。",
    "メガチップス(6875): 1株純資産が過大に登録されておりPBR・ROAは信頼できない。純利益率108%は保有株売却益などの一時要因とみられる。",
    "第一交通産業(9035): 福証単独上場（Yahoo: 9035.F）。配当利回り0%は欠損で、年25円配当なら約3.4%。",
    "トヨタ(7203)・GO(581A): ROE等の一部が Yahoo 側で未提供（nan）。GO は上場後間もないため6M/1Yの騰落率なし。",
    "ソフトバンクG(9984)は2025/12に1→4分割、KDDIは2025/3に1→2分割済み（株価は分割後）。",
    "ROE/ROA/利益率は直近12か月、自己資本比率は直近四半期末の株主資本÷総資産。",
]


def _pct(x):
    return None if x is None else round(x * 100, 1)


def _equity_ratio(t: yf.Ticker):
    """自己資本比率(%) = 株主資本 / 総資産（直近期末）."""
    try:
        bs = t.quarterly_balance_sheet
        if bs is None or bs.empty:
            bs = t.balance_sheet
        col = bs.columns[0]
        eq = bs.loc["Stockholders Equity", col]
        ta = bs.loc["Total Assets", col]
        return round(eq / ta * 100, 1)
    except Exception:
        return None


def fetch(code: str) -> dict:
    t = yf.Ticker(code if "." in code else f"{code}.T")
    i = t.info or {}
    hist = t.history(period="1y", auto_adjust=False)
    close = hist["Close"].dropna()
    price = i.get("currentPrice") or i.get("regularMarketPrice")
    if price is None and not close.empty:
        price = float(close.iloc[-1])

    def chg(days):
        if len(close) <= days:
            return None
        return round((close.iloc[-1] / close.iloc[-1 - days] - 1) * 100, 1)

    ytd = close[close.index >= f"{close.index[-1].year}-01-01"] if not close.empty else close
    de = i.get("debtToEquity")
    return {
        "株価": price,
        "日付": close.index[-1].date().isoformat() if not close.empty else None,
        "1M%": chg(21),
        "6M%": chg(126),
        "1Y%": round((close.iloc[-1] / close.iloc[0] - 1) * 100, 1) if len(close) > 200 else None,
        "YTD%": round((ytd.iloc[-1] / ytd.iloc[0] - 1) * 100, 1) if len(ytd) > 1 else None,
        "時価総額(億円)": round(i["marketCap"] / 1e8) if i.get("marketCap") else None,
        "PER": round(i["trailingPE"], 1) if i.get("trailingPE") else None,
        "予想PER": round(i["forwardPE"], 1) if i.get("forwardPE") else None,
        "PBR": round(i["priceToBook"], 2) if i.get("priceToBook") else None,
        "配当利回り%": i.get("dividendYield"),  # yfinance は既に % 表記
        "ROE%": _pct(i.get("returnOnEquity")),
        "ROA%": _pct(i.get("returnOnAssets")),
        "営業利益率%": _pct(i.get("operatingMargins")),
        "純利益率%": _pct(i.get("profitMargins")),
        "売上成長%": _pct(i.get("revenueGrowth")),
        "自己資本比率%": _equity_ratio(t),
        "D/Eレシオ": round(de / 100, 2) if de is not None else None,
        "流動比率": round(i["currentRatio"], 2) if i.get("currentRatio") else None,
    }


def main():
    rows = []
    for theme, code, name, note in UNIVERSE:
        try:
            d = fetch(code)
        except Exception as e:  # 上場廃止・取得失敗など
            print(f"skip {code} {name}: {e}")
            d = {}
        rows.append({"テーマ": theme, "コード": code.split(".")[0], "銘柄": name, **d, "関連": note})
        print(code, name, d.get("株価"))
    df = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    df.to_csv(OUT / "theme_screen.csv", index=False, encoding="utf-8-sig")

    lines = [f"# 自動運転・タクシー・関連部品 銘柄一覧（{dt.date.today()} 取得, Yahoo Finance）\n"]
    for theme in df["テーマ"].unique():
        sub = df[df["テーマ"] == theme].drop(columns=["テーマ"])
        lines += [f"\n## {theme}\n", sub.to_markdown(index=False, floatfmt="g"), ""]
    lines += ["\n## データ上の注意（2026-10-30 時点で確認）\n", *[f"- {n}" for n in NOTES]]
    (OUT / "theme_screen.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
