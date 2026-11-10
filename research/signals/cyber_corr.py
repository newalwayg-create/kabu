"""日本のサイバーセキュリティ関連株と、日経平均・半導体株・米国（SOX・米サイバー株）との相関。

終値ベース（前日終値→終値）と、前場寄付（前日終値→始値）、寄付→引けに分けて測る。
日経平均の始値はYahooのデータに古い値が混ざることがあるため、寄付はTOPIX連動ETF（1306）で代用する。
"""
import numpy as np
import pandas as pd
import yfinance as yf

CY = {"4417": "グローバルセキュリティエキスパート", "3042": "セキュアヴェイル", "4498": "サイバートラスト", "4447": "PBシステムズ",
      "3692": "FFRI", "4475": "HENNGE", "2326": "デジタルアーツ", "4704": "トレンドマイクロ", "3040": "ソリトンシステムズ",
      "4493": "サイバーセキュリティクラウド", "3356": "テリロジーHD", "4288": "アズジェント"}
SEMI = ["8035.T", "6857.T", "6146.T", "3436.T"]
US = ["^SOX", "CIBR", "CRWD", "PANW"]


def main():
    T = [c + ".T" for c in CY]
    d = yf.download(T + SEMI + ["^N225", "1306.T"] + US, start="2019-01-01", progress=False, auto_adjust=False)
    C, O = d["Close"], d["Open"]
    jp = C["1306.T"].dropna().index
    day = C.reindex(jp).pct_change(fill_method=None)
    gap = (O / C.shift()).reindex(jp) - 1
    oc = (C / O).reindex(jp) - 1
    for X in (day, gap, oc):
        X[X.abs() > 0.3] = np.nan
    gap.loc[gap["1306.T"].abs() > 0.1, "1306.T"] = np.nan
    ur = C[US].dropna(how="all").pct_change(fill_method=None)
    prev = pd.Series([ur.index[ur.index < t][-1] for t in jp], index=jp)
    UA = ur.reindex(prev.values); UA.index = jp
    T = [t for t in T if C[t].notna().sum() > 200]
    cy = lambda X: X[T].mean(axis=1)  # noqa: E731  均等平均（その日に値がある銘柄だけ）
    sm = lambda X: X[SEMI].mean(axis=1)  # noqa: E731

    def c(a, b, since="2019"):
        z = pd.concat([a, b], axis=1).loc[since:].dropna()
        return round(z.iloc[:, 0].corr(z.iloc[:, 1]), 2)

    print("=== サイバー均等バスケット ===")
    for lab, s in (("全期間", "2019"), ("2024-", "2024")):
        print(lab, "終値: 日経", c(cy(day), day["^N225"], s), "半導体", c(cy(day), sm(day), s),
              "| 寄付: TOPIX寄付", c(cy(gap), gap["1306.T"], s), "半導体寄付", c(cy(gap), sm(gap), s), "前夜SOX", c(cy(gap), UA["^SOX"], s), "前夜米サイバーETF", c(cy(gap), UA["CIBR"], s),
              "| 寄付→引け: 日経終値との", c(cy(oc), oc["1306.T"], s), "半導体", c(cy(oc), sm(oc), s))
    print("参考 半導体: 終値 日経", c(sm(day), day["^N225"]), "寄付 前夜SOX", c(sm(gap), UA["^SOX"]))
    rows = []
    for t in T:
        rows.append({"銘柄": CY[t[:-2]], "開始": str(C[t].dropna().index[0].date()),
                     "終値×日経": c(day[t], day["^N225"]), "終値×半導体": c(day[t], sm(day)),
                     "寄付×TOPIX寄付": c(gap[t], gap["1306.T"]), "寄付×半導体寄付": c(gap[t], sm(gap)), "寄付×前夜SOX": c(gap[t], UA["^SOX"]), "寄付×前夜米サイバー": c(gap[t], UA["CIBR"]),
                     "終値×他のサイバー": c(day[t], day[[x for x in T if x != t]].mean(axis=1)),
                     "β(日経)": round(pd.concat([day[t], day["^N225"]], axis=1).dropna().cov().iloc[0, 1] / day["^N225"].var(), 2)})
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).to_string(index=False))
    # 日経・半導体が大きく動いた日のサイバー
    for lab, m in (("日経-2%以下の日", day["^N225"] <= -0.02), ("半導体-3%以下の日", sm(day) <= -0.03), ("前夜SOX-3%以下の翌朝(寄付)", UA["^SOX"] <= -0.03)):
        X = gap if "寄付" in lab else day
        ref = gap["1306.T"] if "寄付" in lab else day["^N225"]
        x = X[T].mean(axis=1)[m].loc["2019":]
        print(f"{lab} n={int(m.loc['2019':].sum())}: サイバー平均 {x.mean()*100:+.2f}% (同日の日経/TOPIX {ref[m].loc['2019':].mean()*100:+.2f}%), サイバーが下げた割合 {(x < 0).mean():.0%}, 2024- {x.loc['2024':].mean()*100:+.2f}%")


if __name__ == "__main__":
    main()
