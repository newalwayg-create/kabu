"""相関・ラグ相関・ローリング相関・回帰の計算。"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def corr_with_pvalue(x: pd.Series, y: pd.Series) -> tuple[float, int, float]:
    """ピアソン相関係数・サンプル数・p値(t分布を正規近似, 両側)を返す。"""
    df = pd.concat([x, y], axis=1).dropna()
    n = len(df)
    if n < 3:
        return float("nan"), n, float("nan")
    r = float(df.iloc[:, 0].corr(df.iloc[:, 1]))
    if abs(r) >= 1:
        return r, n, 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r))
    p = math.erfc(abs(t) / math.sqrt(2))
    return r, n, p


def correlation_matrix(returns: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    return returns.corr(method=method, min_periods=30)


def correlation_table(returns: pd.DataFrame, base: str) -> pd.DataFrame:
    """base と他の全銘柄の相関を p値つきで一覧にする（|r| 降順）。"""
    rows = []
    for col in returns.columns:
        if col == base:
            continue
        r, n, p = corr_with_pvalue(returns[base], returns[col])
        rows.append({"key": col, "corr": r, "n": n, "p_value": p})
    out = pd.DataFrame(rows).set_index("key")
    return out.reindex(out["corr"].abs().sort_values(ascending=False).index)


def lead_lag(returns: pd.DataFrame, base: str, others: list[str], lags=range(-2, 3)) -> pd.DataFrame:
    """corr(base_t, other_{t-k}) を各ラグ k について計算する。

    returns は align.build_aligned() の出力を想定:
      US 銘柄の k=0 は「T の寄付き前に終わった前夜セッション」
      US 銘柄の k=-1 は「T の東京引け後に始まる米国セッション」（東京→米国の波及）
    """
    out = {}
    for o in others:
        out[o] = {k: returns[base].corr(returns[o].shift(k)) for k in lags}
    return pd.DataFrame(out).T.rename_axis("key").rename(columns=lambda k: f"lag{k:+d}")


def rolling_corr(returns: pd.DataFrame, base: str, others: list[str], window: int = 60) -> pd.DataFrame:
    return pd.DataFrame(
        {o: returns[base].rolling(window, min_periods=window // 2).corr(returns[o]) for o in others}
    )


def yearly_corr(returns: pd.DataFrame, base: str, others: list[str]) -> pd.DataFrame:
    """年ごとの相関（関係が安定しているかの確認用）。"""
    g = returns.groupby(returns.index.year)
    return pd.DataFrame({o: g.apply(lambda d, o=o: d[base].corr(d[o])) for o in others}).rename_axis("year")


def ols(y: pd.Series, X: pd.DataFrame) -> dict:
    """切片付き最小二乗法。係数・t値・決定係数を返す。"""
    df = pd.concat([y.rename("_y"), X], axis=1).dropna()
    n, k = len(df), X.shape[1] + 1
    if n <= k:
        raise ValueError("回帰に必要なサンプル数が足りません")
    yv = df["_y"].to_numpy()
    Xv = np.column_stack([np.ones(n), df[X.columns].to_numpy()])
    beta, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
    resid = yv - Xv @ beta
    sigma2 = resid @ resid / (n - k)
    se = np.sqrt(np.diag(sigma2 * np.linalg.pinv(Xv.T @ Xv)))
    ss_tot = ((yv - yv.mean()) ** 2).sum()
    r2 = 1 - (resid @ resid) / ss_tot if ss_tot > 0 else float("nan")
    names = ["const", *X.columns]
    return {
        "coef": pd.Series(beta, index=names),
        "t": pd.Series(beta / se, index=names),
        "r2": float(r2),
        "adj_r2": float(1 - (1 - r2) * (n - 1) / (n - k)),
        "n": n,
    }


def direction_hit_rate(y: pd.Series, x: pd.Series) -> tuple[float, int]:
    """x と y の符号（上げ/下げ）が一致した割合。"""
    df = pd.concat([x, y], axis=1).dropna()
    df = df[(df.iloc[:, 0] != 0) & (df.iloc[:, 1] != 0)]
    if df.empty:
        return float("nan"), 0
    return float((np.sign(df.iloc[:, 0]) == np.sign(df.iloc[:, 1])).mean()), len(df)
