import numpy as np
import pandas as pd

from kabu_defensive import analysis as A
from kabu_defensive.config import BANKS, BENCH, OIL, USDJPY


def test_drop_bad_prints_removes_temporary_glitch_only():
    s = pd.Series([100.0] * 10 + [10.0, 10.0] + [101.0] * 10)
    out = A.drop_bad_prints(s.to_frame("x"))["x"]
    assert out.iloc[10:12].isna().all()
    assert out.drop(index=[10, 11]).notna().all()


def _synthetic_close(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2019-01-01", "2025-12-31")
    mkt = rng.normal(0, 0.01, len(days))
    noise = lambda: rng.normal(0, 0.005, len(days))
    rets = {
        BENCH: mkt,
        "LOW.T": 0.3 * mkt + noise(),  # 低β = 守りが固い
        "HIGH.T": 1.5 * mkt + noise(),
        USDJPY: noise(),
        BANKS: mkt + noise(),
        OIL: noise(),
    }
    return pd.DataFrame({k: 100 * np.exp(np.cumsum(v)) for k, v in rets.items()}, index=days)


def test_low_beta_stock_scores_higher():
    close = _synthetic_close()
    m = A.stock_metrics(close, ["LOW.T", "HIGH.T"])
    assert m.loc["LOW.T", "beta"] < 0.5 < 1.2 < m.loc["HIGH.T", "beta"]
    score = A.risk_aversion_score(m)
    assert score["LOW.T"] > score["HIGH.T"]
    r = A.regime_strength(m)
    assert set(r["type"]) <= {"全天候型", *A.TYPE_NAME.values()}
