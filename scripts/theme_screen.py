"""自動運転・タクシー・関連部品/ソフト・周辺領域・Anthropic 関連銘柄のスクリーニング.

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
    # ④ 自動運転関連ソフトウェア
    ("関連ソフト", "4420", "イーソル", "車載RTOS・AUTOSAR、Autoware関連"),
    ("関連ソフト", "4440", "ヴィッツ", "機能安全・自動運転ソフト開発"),
    ("関連ソフト", "3687", "フィックスターズ", "自動運転向け演算高速化"),
    ("関連ソフト", "3741", "セック", "リアルタイム制御ソフト"),
    ("関連ソフト", "3858", "ユビキタスAI", "車載組込みソフト・セキュリティ"),
    ("関連ソフト", "3916", "デジタル・インフォメーション・テクノロジー", "車載ソフト開発・検証"),
    ("関連ソフト", "2317", "システナ", "車載ソフト受託開発"),
    ("関連ソフト", "4812", "電通総研", "自動車開発向けCAE・シミュレーション"),
    ("関連ソフト", "4704", "トレンドマイクロ", "車載セキュリティ(VicOne)"),
    ("関連ソフト", "4826", "CIJ", "車載組込みソフト受託"),
    # ⑤ その他自動運転周辺領域（保険・交通インフラ・通信・物流・地図測量）
    ("周辺領域", "8766", "東京海上HD", "自動運転向け保険・実証"),
    ("周辺領域", "8630", "SOMPO HD", "自動運転向け保険・ティアフォー出資"),
    ("周辺領域", "8725", "MS&AD", "自動運転向け保険"),
    ("周辺領域", "9432", "NTT", "遠隔監視・通信基盤、トヨタと協業"),
    ("周辺領域", "6741", "日本信号", "信号・路車間協調システム"),
    ("周辺領域", "6742", "京三製作所", "交通信号・路側インフラ"),
    ("周辺領域", "6754", "アンリツ", "V2X・車載通信の測定器"),
    ("周辺領域", "6632", "JVCケンウッド", "ドラレコ・車載機器"),
    ("周辺領域", "9233", "アジア航測", "3D地図・測量"),
    ("周辺領域", "9064", "ヤマトHD", "自動運転トラック実証"),
    ("周辺領域", "8031", "三井物産", "自動運転トラックT2の主要株主"),
    ("周辺領域", "9020", "JR東日本", "BRT自動運転（レベル4）"),
    # ⑥ アンソロピック関連（直接の出資・計算基盤・提携）
    ("Anthropic", "AMZN", "Amazon", "出資・主要クラウド(AWS/Trainium)"),
    ("Anthropic", "GOOGL", "Alphabet", "出資・TPU供給"),
    ("Anthropic", "MSFT", "Microsoft", "出資・Azure計算契約"),
    ("Anthropic", "NVDA", "NVIDIA", "出資・GPU供給"),
    ("Anthropic", "AVGO", "Broadcom", "TPU開発・計算契約"),
    ("Anthropic", "CRM", "Salesforce", "出資（Salesforce Ventures）・提携"),
    ("Anthropic", "6701", "NEC", "戦略的協業（日本企業向け展開）"),
    ("Anthropic", "6702", "富士通", "協業（Anthropic・OpenAI双方）"),
    ("Anthropic", "4307", "野村総合研究所", "Claude導入・提携パートナー"),
    ("Anthropic", "4755", "楽天グループ", "Claude導入企業"),
    ("Anthropic", "8316", "三井住友FG", "NEC経由の協業に参加"),
    ("Anthropic", "4062", "イビデン", "間接：TPU/AI半導体向けパッケージ基板"),
    ("Anthropic", "6857", "アドバンテスト", "間接：AI半導体テスター"),
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
    "東京海上HD(8766): Yahoo上で2026/9/29に1→15分割が記録され、PER50倍・予想PER1.2倍・配当利回り22.9%は分割前後の1株値の混在。"
    "時価総額÷純利益で実績PER約30倍、予想PER約17.6倍（予想EPS493円÷15）、配当利回り約1.5%（年130円÷15）。",
    "野村総研(4307): 直近12か月の純利益が185億円と例年より大幅に少なく、実績PER151倍・ROE4.6%はその影響（要一次情報確認）。予想PERは35.7倍。",
    "アドバンテスト(6857): 予想EPS(238円)が実績(742円)を大きく下回っており予想PER147倍は信頼性が低い。",
    "SCSK(9719): 住友商事の完全子会社化で上場廃止済みのため除外。",
    "イーソル(4420): 2026/8にMBO報道あり（会社発表は未確認）。10/30時点で売買は継続。",
    "楽天G・三井住友FG・損保各社は銀行/保険業を含むため自己資本比率・D/Eは事業会社と比較できない。",
    "米国株(AMZN等)の株価はUSD、時価総額はUSDJPYで円換算。",
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


_FX = {"JPY": 1.0}


def _fx(cur):
    """時価総額を円換算するための為替レート（直近終値）."""
    cur = cur or "JPY"
    if cur not in _FX:
        _FX[cur] = float(yf.Ticker(f"{cur}JPY=X").history(period="5d")["Close"].dropna().iloc[-1])
    return _FX[cur]


def fetch(code: str) -> dict:
    t = yf.Ticker(code if "." in code or code.isalpha() else f"{code}.T")
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
        "通貨": i.get("currency"),
        "時価総額(億円)": round(i["marketCap"] * _fx(i.get("currency")) / 1e8) if i.get("marketCap") else None,
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

    lines = [f"# テーマ別 銘柄一覧（{dt.date.today()} 取得, Yahoo Finance）\n"]
    for theme in df["テーマ"].unique():
        sub = df[df["テーマ"] == theme].drop(columns=["テーマ"])
        lines += [f"\n## {theme}\n", sub.to_markdown(index=False, floatfmt="g"), ""]
    lines += ["\n## データ上の注意（2026-10-30 時点で確認）\n", *[f"- {n}" for n in NOTES]]
    (OUT / "theme_screen.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
