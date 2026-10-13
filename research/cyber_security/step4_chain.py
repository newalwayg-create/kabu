"""④ 資金の波及順序の計測.

(1) AI・半導体テーマ (キオクシア起点 2025-09-05) のセクター別 波及順序
    - セクター = 代表銘柄の等ウェイト
    - 上昇開始日: 2025-08-29 終値比で初めて +20% に達した日 (TOPIX 比ではなく絶対値。TOPIX 比版も併記)
    - ピーク日, 期間別騰落率 (四半期程度に区切る)
(2) 過去のサイバー物色局面の後、候補セクターがどう動いたか (day0 から 20/60 営業日, 対日経平均)
出力: data/step4_*.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from step3_data import fetch  # noqa: E402

D = Path(__file__).resolve().parent / "data"

SEMI_CHAIN = {
    "1_メモリ": {"285A": "キオクシア"},
    "2_検査・テスター": {"6857": "アドバンテスト", "6920": "レーザーテック", "7729": "東京精密", "6855": "日本電子材料"},
    "3_前工程装置": {"8035": "東京エレクトロン", "6525": "KOKUSAI", "7735": "SCREEN", "6323": "ローツェ"},
    "4_後工程装置": {"6146": "ディスコ", "6315": "TOWA"},
    "5_材料・基板": {"4062": "イビデン", "3436": "SUMCO", "4063": "信越化学", "4004": "レゾナック", "4186": "東京応化", "3110": "日東紡", "5016": "JX金属"},
    "6_電子部品": {"6981": "村田製作所", "6762": "TDK", "6976": "太陽誘電"},
    "7_電線・光": {"5803": "フジクラ", "5801": "古河電工", "5805": "SWCC", "5802": "住友電工"},
    "8_重電・電力設備": {"6501": "日立", "6504": "富士電機", "6508": "明電舎", "7011": "三菱重工"},
    "9_電気工事・電力": {"1942": "関電工", "1944": "きんでん", "9503": "関西電力", "9501": "東京電力HD"},
    "10_DC・AI投資": {"9984": "ソフトバンクG", "3778": "さくらインターネット"},
}

CYBER_NEXT = {  # ④ サイバーの次の候補セクター
    "サイバーA(基準)": {"4704": "トレンドマイクロ", "3692": "FFRI", "2326": "デジタルアーツ", "4493": "CSC",
                     "4417": "GSX", "4398": "BBSec", "3042": "セキュアヴェイル", "4288": "アズジェント", "3040": "ソリトン"},
    "大手SI・ITサービス": {"6701": "NEC", "6702": "富士通", "4307": "NRI", "8056": "BIPROGY", "3774": "IIJ"},
    "防衛": {"7011": "三菱重工", "7012": "川崎重工", "7013": "IHI", "6203": "豊和工業", "6946": "日本アビオニクス"},
    "認証・本人確認・不正対策": {"5246": "ELEMENTS", "3788": "GMOグローバルサイン", "4498": "サイバートラスト", "4441": "トビラ", "3909": "ショーケース"},
    "OT・制御": {"6841": "横河電機", "6845": "アズビル", "5133": "テリロジー", "6501": "日立"},
    "損保(サイバー保険)": {"8766": "東京海上", "8725": "MS&AD", "8630": "SOMPO"},
    "クラウド・DC": {"3778": "さくらインターネット", "3774": "IIJ", "9432": "NTT"},
    "AIソフト・グロース": {"4011": "ヘッドウォータース", "5588": "ファーストアカウンティング", "4382": "HEROZ", "3993": "PKSHA", "4180": "Appier"},
}

CYBER_EPISODES = ["2015-06-01", "2017-05-15", "2022-03-01", "2024-06-10", "2025-09-29", "2025-10-20", "2026-10-01"]


def load(groups: dict, start: str) -> pd.DataFrame:
    rows = []
    for g, members in groups.items():
        for c in members:
            try:
                d = fetch(f"{c}.T", start)
            except Exception as e:  # 上場前など
                print("skip", c, e)
                continue
            d = d.reset_index(names="date")
            d["code"], d["group"], d["name"] = c, g, members[c]
            rows.append(d)
    return pd.concat(rows)


def semi_chain() -> None:
    p = load(SEMI_CHAIN, "2025-01-01")
    p = p[p.date <= "2026-10-09"]
    topix = fetch("^N225", "2025-01-01")["close"]  # 1306.T は分割調整に欠損があるため日経平均を基準に使用
    base_day = pd.Timestamp("2025-08-29")
    px = p.pivot_table(index="date", columns="code", values="close")
    rel = px / px.loc[base_day] - 1
    tpx_rel = topix.reindex(px.index).ffill() / topix.loc[base_day] - 1
    periods = [("2025-08-29", "2025-10-31"), ("2025-10-31", "2025-12-30"), ("2025-12-30", "2026-03-31"),
               ("2026-03-31", "2026-06-30"), ("2026-06-30", "2026-10-09")]
    out = []
    for g, members in SEMI_CHAIN.items():
        cs = [c for c in members if c in px]
        ew = rel[cs].mean(axis=1)
        ex = ew - tpx_rel
        after = ew.loc[base_day:]
        hit20 = after[after >= 0.20]
        exhit = ex.loc[base_day:][ex.loc[base_day:] >= 0.20]
        row = {"sector": g, "members": "/".join(members[c] for c in cs),
               "start_+20%": hit20.index[0].date() if len(hit20) else None,
               "start_N225比+20pt": exhit.index[0].date() if len(exhit) else None,
               "peak_date": after.idxmax().date(), "peak_ret%": round(after.max() * 100, 1),
               "ret_to_1009%": round(after.iloc[-1] * 100, 1),
               "from_peak%": round(((1 + after.iloc[-1]) / (1 + after.max()) - 1) * 100, 1)}
        for a, b in periods:
            pa = px[cs].loc[:a].iloc[-1]
            pb = px[cs].loc[:b].iloc[-1]
            row[f"{a[2:7]}→{b[2:7]}%"] = round(((pb / pa) - 1).mean() * 100, 1)
        out.append(row)
    t = topix
    out.append({"sector": "参考_日経平均", "peak_ret%": round((t.loc[base_day:"2026-10-09"].max() / t.loc[base_day] - 1) * 100, 1),
                "ret_to_1009%": round((t.loc[:"2026-10-09"].iloc[-1] / t.loc[base_day] - 1) * 100, 1),
                **{f"{a[2:7]}→{b[2:7]}%": round((t.loc[:b].iloc[-1] / t.loc[:a].iloc[-1] - 1) * 100, 1) for a, b in periods}})
    df = pd.DataFrame(out)
    df.to_csv(D / "step4_semi_chain.csv", index=False)
    # 銘柄別の上昇開始日
    per = []
    for g, members in SEMI_CHAIN.items():
        for c in members:
            if c not in px:
                continue
            s = rel[c].loc[base_day:]
            h = s[s >= 0.20]
            per.append({"sector": g, "code": c, "name": members[c],
                        "start_+20%": h.index[0].date() if len(h) else None,
                        "peak_date": s.idxmax().date(), "peak_ret%": round(s.max() * 100, 1),
                        "ret_to_1009%": round(s.iloc[-1] * 100, 1)})
    pd.DataFrame(per).to_csv(D / "step4_semi_chain_stocks.csv", index=False)
    pd.set_option("display.width", 300)
    print(df.to_string())
    print(pd.DataFrame(per).to_string())


def cyber_next() -> None:
    p = load(CYBER_NEXT, "2014-01-01")
    p = p[p.date <= "2026-10-09"]
    n225 = fetch("^N225", "2014-01-01")["close"]
    px = p.pivot_table(index="date", columns="code", values="close")
    out = []
    for d0 in CYBER_EPISODES:
        i0 = px.index.searchsorted(pd.Timestamp(d0))
        base = px.index[i0 - 1]
        for g, members in CYBER_NEXT.items():
            cs = [c for c in members if c in px and pd.notna(px.loc[base, c])]
            if not cs:
                continue
            row = {"day0": d0, "group": g, "n": len(cs)}
            for h in (5, 20, 60):
                if i0 - 1 + h < len(px.index):
                    dt = px.index[i0 - 1 + h]
                    r = (px.loc[dt, cs] / px.loc[base, cs] - 1).mean() * 100
                    nk = (n225.loc[:dt].iloc[-1] / n225.loc[:base].iloc[-1] - 1) * 100
                    row[f"{h}d_vsN225pt"] = round(r - nk, 1)
            out.append(row)
    df = pd.DataFrame(out)
    df.to_csv(D / "step4_cyber_next.csv", index=False)
    piv = df.pivot_table(index="group", columns="day0", values=["5d_vsN225pt", "20d_vsN225pt", "60d_vsN225pt"])
    pd.set_option("display.width", 300)
    print(piv.round(1).to_string())


if __name__ == "__main__":
    semi_chain()
    cyber_next()
