"""指定銘柄と、日経平均・日経先物（CME）・SOX・S&P500との相関。

- 日経平均: 同じ日の値動き（前日終値→終値）
- 米国（SOX、S&P500）: 米国の t 日の値動きと、東京の t+1 日の寄付（前日終値→始値）・終値
- 日経先物: 東京の t 日の引け後〜米国の t 日の引けまでの動き（CMEの終値 ÷ 日経平均の終値）と、t+1 日の寄付・終値
"""
import numpy as np
import pandas as pd
import yfinance as yf

S = {"4417": "グローバルセキュリティエキスパート", "4980": "デクセリアルズ", "8766": "東京海上", "2201": "森永製菓",
     "1965": "テクノ菱和", "8151": "東陽テクニカ", "5711": "三菱マテリアル"}


def main():
    T = [c + ".T" for c in S]
    d = yf.download(T + ["^N225", "NIY=F", "^SOX", "^GSPC"], start="2019-01-01", progress=False, auto_adjust=False)
    C, O = d["Close"], d["Open"]
    jp = C["^N225"].dropna().index
    day = C.reindex(jp).pct_change(fill_method=None)
    gap = (O / C.shift()).reindex(jp) - 1
    for X in (day, gap):
        X[X.abs() > 0.3] = np.nan
    us = C[["^SOX", "^GSPC", "NIY=F"]].dropna(how="all")
    rows, nk = [], C["^N225"].dropna()
    for t in jp[1:]:
        prev_jp = jp[jp < t][-1]
        u = us.index[(us.index >= prev_jp) & (us.index < t)]
        if len(u) == 0:
            continue
        u = u[-1]; u0 = us.index[us.index < u]
        if len(u0) == 0:
            continue
        u0 = u0[-1]
        rows.append({"t": t, "SOX": us.at[u, "^SOX"] / us.at[u0, "^SOX"] - 1, "SP": us.at[u, "^GSPC"] / us.at[u0, "^GSPC"] - 1,
                     "NKF": us.at[u, "NIY=F"] / nk.at[prev_jp] - 1})
    U = pd.DataFrame(rows).set_index("t")
    U.loc[U["NKF"].abs() > 0.15, "NKF"] = np.nan

    def c(a, b, since="2019"):
        z = pd.concat([a, b], axis=1).loc[since:].dropna()
        return round(z.iloc[:, 0].corr(z.iloc[:, 1]), 2)

    out = []
    for t in T + ["^N225"]:
        name = S.get(t[:-2], "（参考）日経平均")
        z = pd.concat([day[t], day["^N225"]], axis=1).dropna()
        out.append({"銘柄": name,
                    "日経平均(同日)": c(day[t], day["^N225"]) if t != "^N225" else 1.0,
                    "β": round(z.cov().iloc[0, 1] / z.iloc[:, 1].var(), 2),
                    "寄付×日経先物": c(gap[t], U["NKF"]), "寄付×SOX": c(gap[t], U["SOX"]), "寄付×S&P500": c(gap[t], U["SP"]),
                    "終値×日経先物": c(day[t], U["NKF"]), "終値×SOX": c(day[t], U["SOX"]), "終値×S&P500": c(day[t], U["SP"]),
                    "2024- 日経平均": c(day[t], day["^N225"], "2024") if t != "^N225" else 1.0, "2024- 寄付×SOX": c(gap[t], U["SOX"], "2024"),
                    "開始": str(C[t].dropna().index[0].date())})
    pd.set_option("display.width", 250)
    print(pd.DataFrame(out).to_string(index=False))
    print("日数", len(U.dropna()))


if __name__ == "__main__":
    main()
