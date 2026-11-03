"""長期保有向け 配当株スクリーニング（収益性・成長版）.

基準:
  ① 減配していない : 2016-2025年の年間配当が前年割れなし + 直近12か月が前年同期以上
  ② 利回り2.5%以上 : 直近12か月の実績配当 ÷ 株価
  ③ ROE 8%以上     : 直近期の 当期純利益 ÷ 期首期末平均の株主資本
  ④ EPS or FCF     : (a) EPSが3期前より増加  または
                     (b) 直近4期累計のFCFが同期間の配当支払総額以上（FCFで配当を賄えている）

    python scripts/dividend_screen2.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dividend_screen import OUT, UNIVERSE, dividend_check  # noqa: E402


def _get(fn, tries=3):
    for _ in range(tries):
        try:
            df = fn()
            if df is not None and not df.empty:
                return df
            return None
        except Exception:
            time.sleep(3)
    return None


def _row(df, name):
    if df is None or name not in df.index:
        return pd.Series(dtype=float)
    return df.loc[name].dropna().sort_index()  # 古い→新しい


def fundamentals(t: yf.Ticker) -> dict:
    inc = _get(lambda: t.income_stmt)
    bs = _get(lambda: t.balance_sheet)
    cf = _get(lambda: t.cashflow)

    ni = _row(inc, "Net Income Common Stockholders")
    if ni.empty:
        ni = _row(inc, "Net Income")
    eps = _row(inc, "Diluted EPS")
    if eps.empty:
        eps = _row(inc, "Basic EPS")
    eq = _row(bs, "Stockholders Equity")

    out = {}
    # ROE（直近期・平均資本ベース）と期間平均
    roes = []
    for d in ni.index:
        if d in eq.index:
            prev = eq[eq.index < d]
            base = (eq[d] + prev.iloc[-1]) / 2 if len(prev) else eq[d]
            if base > 0:
                roes.append(ni[d] / base * 100)
    out["ROE%"] = round(roes[-1], 1) if roes else np.nan
    out["ROE%(平均)"] = round(float(np.mean(roes)), 1) if roes else np.nan

    # EPS成長（株式分割で不連続な場合は純利益の伸びで代用）
    if len(eps) >= 2 and eps.iloc[0] > 0:
        g_eps = eps.iloc[-1] / eps.iloc[0]
        if len(ni) >= 2 and ni[ni.index.isin(eps.index)].iloc[0] > 0:
            n = ni[ni.index.isin(eps.index)]
            g_ni = n.iloc[-1] / n.iloc[0]
            if g_ni > 0 and not (0.6 < g_eps / g_ni < 1.6):
                g_eps = g_ni  # 分割調整漏れとみなす
        years = (eps.index[-1] - eps.index[0]).days / 365
        out["EPS成長率%/年"] = round((g_eps ** (1 / years) - 1) * 100, 1) if g_eps > 0 and years > 0 else np.nan
        out["EPS(直近)"] = round(float(eps.iloc[-1]), 1)
    else:
        out["EPS成長率%/年"] = np.nan
        out["EPS(直近)"] = round(float(eps.iloc[-1]), 1) if len(eps) else np.nan

    fcf = _row(cf, "Free Cash Flow")
    div = _row(cf, "Cash Dividends Paid")
    if div.empty:
        div = _row(cf, "Common Stock Dividend Paid")
    common = fcf.index.intersection(div.index)
    if len(common) and (-div[common].sum()) > 0:
        out["FCF配当カバー倍"] = round(float(fcf[common].sum() / -div[common].sum()), 2)
    else:
        out["FCF配当カバー倍"] = np.nan
    out["FCFマイナス期数"] = int((fcf < 0).sum()) if len(fcf) else np.nan
    return out


def main():
    tickers = [f"{c}.T" for c in UNIVERSE]
    px = yf.download(tickers, period="1y", auto_adjust=False, group_by="ticker", progress=False, threads=True)
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
        lo, hi = d["Low"].min(), d["High"].max()
        t = yf.Ticker(tk)
        try:
            dv = t.dividends
        except Exception:
            dv = pd.Series(dtype=float)
        dc = dividend_check(dv.copy(), pd.Timestamp(asof))
        f = fundamentals(t)
        time.sleep(0.3)
        eps = f.get("EPS(直近)")
        rows.append({
            "コード": code, "銘柄": name, "株価": round(close, 1), "日付": str(asof.date()),
            "利回り%": round(dc["TTM配当"] / close * 100, 2),
            "配当性向%": round(dc["TTM配当"] / eps * 100, 0) if eps and eps > 0 else np.nan,
            **f,
            "52週位置%": round((close - lo) / (hi - lo) * 100, 1) if hi > lo else np.nan,
            "無減配": dc["無減配"], "減配年": dc["減配年"], "TTM配当": dc["TTM配当"],
        })
        print(code, name, "ok", flush=True)

    df = pd.DataFrame(rows)
    df["①無減配"] = df["無減配"]
    df["②利回り"] = df["利回り%"] >= 2.5
    df["③ROE"] = df["ROE%"] >= 8
    df["④a_EPS成長"] = df["EPS成長率%/年"] > 0
    df["④b_FCFカバー"] = df["FCF配当カバー倍"] >= 1.0
    df["④EPSorFCF"] = df["④a_EPS成長"] | df["④b_FCFカバー"]
    df["該当数"] = df[["①無減配", "②利回り", "③ROE", "④EPSorFCF"]].sum(axis=1)
    df = df.sort_values(["該当数", "利回り%"], ascending=False)
    df.to_csv(OUT / "dividend_screen2.csv", index=False, encoding="utf-8-sig")
    cols = ["コード", "銘柄", "利回り%", "配当性向%", "ROE%", "ROE%(平均)", "EPS成長率%/年",
            "FCF配当カバー倍", "52週位置%", "減配年", "④a_EPS成長", "④b_FCFカバー", "該当数"]
    print(df[df["該当数"] >= 3][cols].to_string())


if __name__ == "__main__":
    main()
