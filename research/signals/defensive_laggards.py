"""半導体が急落した局面で「まだ反応していない／反応が薄い」ディフェンシブ株を探す。

1. ディフェンシブ度（過去5年）
   - 米SOXが-3.5%以下の夜の翌日（日本）に、市場平均より強かった平均と勝率
   - 市場平均が-1.5%以下の日の、市場平均との差
   - 市場平均に対するβ（直近2年）
2. 今回の反応
   - 10/22〜今日の、市場平均との差（実績）
   - 過去のSOX急落の翌日の平均（期待）と比べて、どれだけ出遅れているか
3. 出遅れは後から追いつくのか（検証）
   - 過去のSOX急落の翌日に、ディフェンシブ株の中で出遅れた銘柄が、その後4日で追いついたか
4. 今のテクニカル（RSI、25日線・75日線からの位置）と、株価・売買代金・PER/PBR/配当

市場平均は東証33業種の代表銘柄（research/sector33/universe.py）の単純平均。
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "research" / "sector33"))
from universe import SECTORS  # noqa: E402

DEF = {
    # 食品・飲料・たばこ
    "2502": "アサヒ", "2503": "キリン", "2587": "サントリーBF", "2269": "明治", "2201": "森永製菓", "2206": "江崎グリコ",
    "2212": "山崎製パン", "2229": "カルビー", "2264": "森永乳業", "2282": "日本ハム", "2296": "伊藤ハム米久", "2801": "キッコーマン",
    "2802": "味の素", "2809": "キユーピー", "2810": "ハウス食品", "2811": "カゴメ", "2871": "ニチレイ", "2875": "東洋水産",
    "2897": "日清食品", "2002": "日清製粉G", "2531": "宝HD", "2593": "伊藤園", "2914": "JT", "1332": "ニッスイ", "2267": "ヤクルト",
    # 医薬品・医療
    "4502": "武田", "4503": "アステラス", "4507": "塩野義", "4519": "中外", "4523": "エーザイ", "4528": "小野薬品",
    "4568": "第一三共", "4578": "大塚HD", "4151": "協和キリン", "4536": "参天", "4516": "日本新薬", "4521": "科研製薬",
    "4530": "久光", "4540": "ツムラ", "4543": "テルモ", "4547": "キッセイ", "4527": "ロート", "4544": "H.U.G",
    # 日用品
    "4452": "花王", "4911": "資生堂", "4967": "小林製薬", "8113": "ユニチャーム", "4912": "ライオン", "4927": "ポーラ", "4922": "コーセー",
    # 通信
    "9432": "NTT", "9433": "KDDI", "9434": "ソフトバンク", "9436": "沖縄セルラー",
    # 電力・ガス
    "9501": "東京電力", "9502": "中部電力", "9503": "関西電力", "9504": "中国電力", "9506": "東北電力", "9508": "九州電力",
    "9513": "Jパワー", "9531": "東京ガス", "9532": "大阪ガス", "9533": "東邦ガス",
    # 鉄道
    "9020": "JR東日本", "9021": "JR西日本", "9022": "JR東海", "9142": "JR九州", "9005": "東急", "9007": "小田急", "9008": "京王",
    "9009": "京成", "9041": "近鉄", "9042": "阪急阪神", "9001": "東武", "9048": "名鉄",
    # 小売（生活必需）
    "8267": "イオン", "3382": "セブン&i", "7532": "PPIH", "3088": "マツキヨココカラ", "3391": "ツルハ", "9989": "サンドラッグ",
    "7649": "スギHD", "3349": "コスモス薬品", "9843": "ニトリ", "8279": "ヤオコー", "3038": "神戸物産", "2782": "セリア",
    "8282": "ケーズHD", "9831": "ヤマダHD",
    # 保険
    "8766": "東京海上", "8725": "MS&AD", "8630": "SOMPO", "8750": "第一ライフ", "7181": "かんぽ生命", "8795": "T&D",
    # その他の内需・ディフェンシブ
    "6178": "日本郵政", "9735": "セコム", "2331": "ALSOK", "4661": "OLC", "9602": "東宝", "9766": "コナミ", "7974": "任天堂",
    "1925": "大和ハウス", "1928": "積水ハウス",
}
GROUP = {}
for g, codes in [
    ("食品", "2502 2503 2587 2269 2201 2206 2212 2229 2264 2282 2296 2801 2802 2809 2810 2811 2871 2875 2897 2002 2531 2593 2914 1332 2267"),
    ("医薬", "4502 4503 4507 4519 4523 4528 4568 4578 4151 4536 4516 4521 4530 4540 4543 4547 4527 4544"),
    ("日用品", "4452 4911 4967 8113 4912 4927 4922"), ("通信", "9432 9433 9434 9436"),
    ("電力ガス", "9501 9502 9503 9504 9506 9508 9513 9531 9532 9533"),
    ("鉄道", "9020 9021 9022 9142 9005 9007 9008 9009 9041 9042 9001 9048"),
    ("小売", "8267 3382 7532 3088 3391 9989 7649 3349 9843 8279 3038 2782 8282 9831"),
    ("保険", "8766 8725 8630 8750 7181 8795"), ("その他", "6178 9735 2331 4661 9602 9766 7974 1925 1928"),
]:
    for c in codes.split():
        GROUP[c] = g

START_EVENT = pd.Timestamp("2026-10-22")  # 今回の半導体安で日本が反応し始めた日


def rsi(p, n=14):
    d = p.diff(); up = d.clip(lower=0).ewm(alpha=1 / n).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n).mean()
    return 100 - 100 / (1 + up / dn)


def main():
    mkt = sorted({c + ".T" for m in SECTORS.values() for c in m})
    dft = [c + ".T" for c in DEF]
    allt = sorted(set(mkt) | set(dft))
    d = yf.download(allt + ["^SOX"], period="5y", progress=False, auto_adjust=True, threads=True)
    C, V = d["Close"], d["Volume"]
    sox = C["^SOX"].dropna().pct_change() * 100
    J = C[allt].dropna(how="all")
    J = J[J.index.dayofweek < 5]

    # 今日の場中の値で今日の終値を置き換える（日足の終値は場中は更新されないことがある）
    i = yf.download(allt, period="2d", interval="5m", progress=False, auto_adjust=False, threads=True)["Close"]
    idx = i.index.tz_localize("UTC") if i.index.tz is None else i.index
    i.index = idx.tz_convert("Asia/Tokyo")
    today = pd.Timestamp(i.index[-1].date())
    last = i[[x.date() == today.date() for x in i.index]].ffill().iloc[-1]
    J.index = pd.DatetimeIndex([pd.Timestamp(x.date()) for x in J.index])
    J = J[~J.index.duplicated(keep="last")]
    J.loc[today] = last.reindex(J.columns).fillna(J.loc[today] if today in J.index else np.nan)
    J = J.sort_index()

    R = J.pct_change() * 100
    R = R.where(R.abs() < 25)
    M = R[[t for t in mkt if t in R]].mean(axis=1)
    X = R.sub(M, axis=0)  # 市場平均との差

    sox.index = pd.DatetimeIndex([pd.Timestamp(x.date()) for x in sox.index])
    ev = []
    for dt in sox[sox <= -3.5].index:
        nx = J.index[J.index > dt]
        if len(nx) and nx[0] < START_EVENT:
            ev.append(nx[0])
    ev = sorted(set(ev))
    down = M[(M <= -1.5) & (M.index < START_EVENT)].index

    # 3. 出遅れの追いつき検証: SOX急落の翌日（day1）にディフェンシブ株の中で順位を付け、day2〜day5 の市場差を比べる
    lv = np.log(J).diff().mul(100)
    lvx = lv.sub(lv[[t for t in mkt if t in lv]].mean(axis=1), axis=0)
    ic, spread = [], []
    for e in ev:
        k = J.index.get_loc(e)
        if k + 4 >= len(J.index) or J.index[k + 4] >= START_EVENT:
            continue
        d1 = X.loc[e, dft].dropna()
        fwd = lvx.iloc[k + 1:k + 5][dft].sum().reindex(d1.index).dropna()
        d1 = d1.reindex(fwd.index)
        if len(d1) < 30:
            continue
        ic.append(d1.rank().corr(fwd.rank()))
        q = pd.qcut(d1, 5, labels=False)
        spread.append(fwd[q == 0].mean() - fwd[q == 4].mean())
    print(f"出遅れの追いつき検証: SOX急落の翌日 {len(ic)}回")
    print(f"  day1の市場差 と その後4日の市場差 の順位相関 平均 {np.mean(ic):+.3f}（マイナスなら出遅れが追いつく）")
    print(f"  day1の出遅れ上位20% − 先行上位20% のその後4日 平均 {np.mean(spread):+.2f}%  勝率 {np.mean(np.array(spread) > 0) * 100:.0f}%")

    two = X.loc[X.index >= START_EVENT]
    rows = []
    for c, n in DEF.items():
        t = c + ".T"
        if t not in J or J[t].dropna().shape[0] < 500:
            continue
        p = J[t].dropna()
        x_ev = X.loc[ev, t].dropna()
        x_dn = X.loc[down, t].dropna()
        r2 = R[t].iloc[-500:].dropna(); m2 = M.reindex(r2.index)
        beta = np.cov(r2, m2)[0, 1] / m2.var()
        now = two[t].sum()
        exp_ = x_ev.mean() * len(two)
        ma25, ma75 = p.rolling(25).mean().iloc[-1], p.rolling(75).mean().iloc[-1]
        rows.append({
            "code": c, "銘柄": n, "業種": GROUP.get(c, ""), "株価": round(p.iloc[-1]),
            "SOX急落翌日の市場差": x_ev.mean(), "勝率%": (x_ev > 0).mean() * 100,
            "市場急落日の市場差": x_dn.mean(), "β": beta,
            "今回の市場差": now, "期待": exp_, "出遅れ": now - exp_,
            "今日%": R[t].iloc[-1], "10/22%": R.loc[START_EVENT, t] if START_EVENT in R.index else np.nan,
            "RSI": rsi(p).iloc[-1], "25日線%": (p.iloc[-1] / ma25 - 1) * 100, "75日線%": (p.iloc[-1] / ma75 - 1) * 100,
            "1か月%": (p.iloc[-1] / p.iloc[-22] - 1) * 100,
            "代金億": (V[t].iloc[-61:-1] * C[t].iloc[-61:-1]).mean() / 1e8,
        })
    df = pd.DataFrame(rows)
    df["ディフェンシブ度"] = (df["SOX急落翌日の市場差"].rank(pct=True) + df["勝率%"].rank(pct=True)
                         + df["市場急落日の市場差"].rank(pct=True) + (-df["β"]).rank(pct=True)) / 4
    out = HERE.parents[1] / "data" / "research" / "defensive_laggards.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    cols = ["銘柄", "業種", "株価", "ディフェンシブ度", "SOX急落翌日の市場差", "勝率%", "β", "10/22%", "今日%", "今回の市場差", "出遅れ",
            "RSI", "25日線%", "75日線%", "1か月%", "代金億"]
    print("\n市場平均 今回:", {str(k.date()): round(v, 2) for k, v in M.loc[M.index >= START_EVENT].items()})
    print("\n業種ごとの今回の市場差（平均）")
    print(df.groupby("業種")[["今回の市場差", "期待", "出遅れ", "RSI", "25日線%"]].mean().round(2).sort_values("出遅れ").to_string())
    print("\nディフェンシブ度 上位50% で、出遅れ順")
    sel = df[df["ディフェンシブ度"] >= 0.5].sort_values("出遅れ")
    print(sel[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
