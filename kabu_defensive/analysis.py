"""リスク指標・リスク回避度スコア・相場局面別の強さの計算。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from kabu_corr.analysis import ols

from .config import BANKS, BENCH, OIL, STRESS_PERIODS, USDJPY

# リスク回避度スコアの構成（指標名, 重み, 小さいほど良いか）
SCORE_WEIGHTS: list[tuple[str, float, bool]] = [
    ("beta", 0.25, True),
    ("down_capture", 0.25, True),
    ("vol", 0.15, True),
    ("max_dd", 0.15, False),  # max_dd は負の値なので「大きい(0に近い)ほど良い」
    ("stress_excess", 0.20, False),
]

REGIMES = ["下落相場", "急落局面", "円高", "金利上昇", "資源高・インフレ"]
MIN_WEEKS = 156  # 3年未満の銘柄は評価しない


def drop_bad_prints(wide: pd.DataFrame, window: int = 11, ratio: float = 2.0) -> pd.DataFrame:
    """前後の中央値から ratio 倍以上ずれた終値を欠損にする。

    Yahoo のデータには数日だけ価格が 1/10 になるような誤データが混じることがある
    （例: 1306.T の 2026-03-30〜31）。分割未調整のような恒久的な段差は残る点に注意。
    """
    med = wide.rolling(window, center=True, min_periods=window // 2).median()
    bad = (wide > med * ratio) | (wide < med / ratio)
    return wide.mask(bad)


def closes(prices: pd.DataFrame) -> pd.DataFrame:
    """縦持ちの価格表を、ベンチマークの営業日に揃えた終値の横持ち表にする。"""
    wide = drop_bad_prints(prices.pivot_table(index="date", columns="ticker", values="close").sort_index())
    bench_days = wide[BENCH].dropna().index
    # 米国市場の指標(ドル円・原油)は東京の営業日に合わせて直近値で埋める
    return wide.ffill(limit=5).reindex(bench_days)


def period_returns(close: pd.DataFrame, rule: str) -> pd.DataFrame:
    """週次("W-FRI")・月次("ME")の単純リターン。"""
    return close.resample(rule).last().pct_change(fill_method=None).iloc[1:]


def max_drawdown(s: pd.Series) -> float:
    s = s.dropna()
    return float((s / s.cummax() - 1).min())


def stress_excess(close: pd.DataFrame, ticker: str) -> dict[str, float]:
    """急落局面ごとの、TOPIX に対する超過リターン。"""
    out = {}
    for name, start, end in STRESS_PERIODS:
        seg = close.loc[start:end, [ticker, BENCH]].dropna()
        if len(seg) < 2 or seg.index[0] > pd.Timestamp(start) + pd.Timedelta(days=7):
            out[name] = np.nan
            continue
        r = seg.iloc[-1] / seg.iloc[0] - 1
        out[name] = float(r[ticker] - r[BENCH])
    return out


def factor_returns(r: pd.DataFrame) -> pd.DataFrame:
    """局面ファクター。符号は「その局面で値が大きくなる」向きに揃える。"""
    return pd.DataFrame(
        {
            "円高": -r[USDJPY],  # ドル円の下落 = 円高
            "金利上昇": r[BANKS] - r[BENCH],  # 銀行株の対TOPIX超過 = 国内金利上昇の代理
            "資源高・インフレ": r[OIL],
        }
    )


def regime_masks(monthly: pd.DataFrame) -> dict[str, pd.Series]:
    """月次の相場局面。円高・金利上昇・資源高は上位/下位 1/3 の月とする。"""
    b = monthly[BENCH]
    fx = monthly[USDJPY]
    rates = monthly[BANKS] - b  # 銀行株が TOPIX を上回る月 = 国内金利上昇が意識された月
    oil = monthly[OIL]
    return {
        "下落相場": b < 0,
        "上昇相場": b > 0,
        "円高": fx <= fx.quantile(1 / 3),
        "金利上昇": rates >= rates.quantile(2 / 3),
        "資源高・インフレ": oil >= oil.quantile(2 / 3),
    }


def stock_metrics(close: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    weekly = period_returns(close, "W-FRI")
    monthly = period_returns(close, "ME")
    bw, bm = weekly[BENCH], monthly[BENCH]
    masks = regime_masks(monthly)
    factors = factor_returns(weekly)
    rows = []
    for t in tickers:
        if t not in close or weekly[t].notna().sum() < MIN_WEEKS:
            continue
        w = pd.concat([weekly[t], bw], axis=1).dropna()
        m = pd.concat([monthly[t], bm], axis=1).dropna()
        sw, bw_ = w.iloc[:, 0], w.iloc[:, 1]
        sm, bm_ = m.iloc[:, 0], m.iloc[:, 1]
        down, up = bm_ < 0, bm_ > 0
        c = close[t].dropna()
        years = (c.index[-1] - c.index[0]).days / 365.25
        st = stress_excess(close, t)
        row = {
            "ticker": t,
            "beta": sw.cov(bw_) / bw_.var(),
            "corr": sw.corr(bw_),
            "vol": sw.std() * np.sqrt(52),
            "down_capture": sm[down].mean() / bm_[down].mean(),
            "up_capture": sm[up].mean() / bm_[up].mean(),
            "max_dd": max_drawdown(c),
            "cagr": (c.iloc[-1] / c.iloc[0]) ** (1 / years) - 1,
            "stress_excess": np.nanmean(list(st.values())),
            **{f"stress:{k}": v for k, v in st.items()},
        }
        # 市場(TOPIX)の動きを除いたうえでの各局面ファクターへの感応度（週次の重回帰）
        fit = ols(weekly[t], pd.concat([bw.rename("market"), factors], axis=1))
        for f in factors:
            row[f"sens:{f}"] = fit["coef"][f]
            row[f"sens_t:{f}"] = fit["t"][f]
        excess = sm - bm_
        for name, mask in masks.items():
            mk = mask.reindex(excess.index, fill_value=False)
            row[f"regime:{name}"] = excess[mk].mean()
            row[f"regime_n:{name}"] = int(mk.sum())
        rows.append(row)
    return pd.DataFrame(rows).set_index("ticker")


def risk_aversion_score(m: pd.DataFrame) -> pd.Series:
    """各指標の候補内パーセンタイル順位を重み付き平均して 0〜100 にする。"""
    total = 0
    for col, w, smaller_is_better in SCORE_WEIGHTS:
        pct = m[col].rank(pct=True, ascending=not smaller_is_better)
        total = total + w * pct.fillna(0.5)
    return (100 * total / sum(w for _, w, _ in SCORE_WEIGHTS)).round(1)


def regime_strength(m: pd.DataFrame) -> pd.DataFrame:
    """局面ごとの強さを候補内の z スコアにし、強い局面を判定する。

    下落相場 = 下落月の対TOPIX超過リターン、急落局面 = 急落期間の対TOPIX超過リターン、
    円高・金利上昇・資源高 = 市場の動きを除いた感応度（重回帰係数）で測る。
    単純に「円高の月の超過リターン」をとると、円高月が下落月と重なりやすいため
    ディフェンシブ株がどれも強く見えてしまう。それを避けるための使い分け。

    戻り値の列:
      z:<局面>  … 候補内での相対的な強さ
      mark:<局面> … 下落相場・急落局面: ◎(z≥1) ○(z≥0) △(プラスだが平均未満) ×(マイナス)
                    円高・金利上昇・資源高: ◎(感応度>0, t≥2) ○(t≥1) △(プラスだが有意でない) ×(マイナス)
      best     … 一番強い局面
      type     … 分類名
    """
    col = {"下落相場": "regime:下落相場", "急落局面": "stress_excess"}
    col |= {r: f"sens:{r}" for r in REGIMES if r not in col}
    out = pd.DataFrame(index=m.index)
    for r, c in col.items():
        x = m[c]
        z = (x - x.mean()) / x.std()
        out[f"z:{r}"] = z
        if r in ("下落相場", "急落局面"):
            # ディフェンシブ候補はほぼ全銘柄がプラスなので、候補内の相対順位で判定
            cond = [(z >= 1) & (x > 0), (z >= 0) & (x > 0), x > 0]
        else:
            # 感応度は t 値で統計的な確からしさを確認する
            t = m[f"sens_t:{r}"]
            cond = [(x > 0) & (t >= 2), (x > 0) & (t >= 1), x > 0]
        out[f"mark:{r}"] = np.select(cond, ["◎", "○", "△"], "×")
    # 一番強い局面: 印の良さ(◎>○>△>×)を優先し、同じ印なら z の高い方
    rank = {"◎": 3, "○": 2, "△": 1, "×": 0}
    key = pd.DataFrame({r: out[f"mark:{r}"].map(rank) * 100 + out[f"z:{r}"] for r in REGIMES})
    out["best"] = key.idxmax(axis=1)
    strong = (out[[f"mark:{r}" for r in REGIMES]].isin(["◎", "○"])).sum(axis=1)
    out["n_strong"] = strong
    out["type"] = np.where(strong >= 3, "全天候型", out["best"].map(TYPE_NAME))
    return out


TYPE_NAME = {
    "下落相場": "下落相場型",
    "急落局面": "暴落耐性型",
    "円高": "円高耐性型",
    "金利上昇": "金利上昇耐性型",
    "資源高・インフレ": "インフレ耐性型",
}
