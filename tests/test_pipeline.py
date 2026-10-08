import numpy as np
import pandas as pd
import pytest

from kabu_corr import analysis as A
from kabu_corr.align import build_aligned, us_close_before
from kabu_corr.report import build_report
from kabu_corr.synthetic import make_prices


def _prices(rows):
    return pd.DataFrame(rows, columns=["date", "ticker", "open", "close"]).assign(
        date=lambda d: pd.to_datetime(d["date"]), high=np.nan, low=np.nan, volume=0
    )


def test_us_close_before_uses_strictly_previous_session():
    us = pd.Series([100.0, 110.0, 121.0], index=pd.to_datetime(["2024-01-04", "2024-01-05", "2024-01-08"]))
    cal = pd.to_datetime(["2024-01-05", "2024-01-09"])
    out = us_close_before(us, cal)
    # 1/5 の東京には 1/4 の NY 終値、1/9 の東京には 1/8 の NY 終値
    assert out.tolist() == [100.0, 121.0]


def test_build_aligned_accumulates_us_moves_over_jp_holiday():
    rows = [
        # 東京: 1/5(金) の次は 1/9(火)（1/8 は祝日）
        ("2024-01-05", "^N225", 100, 100),
        ("2024-01-09", "^N225", 104, 105),
        # NY: 1/4, 1/5, 1/8 の3セッション
        ("2024-01-04", "^SOX", 50, 50),
        ("2024-01-05", "^SOX", 55, 55),
        ("2024-01-08", "^SOX", 60, 60),
    ]
    aligned = build_aligned(_prices(rows))
    ret = aligned["returns"]
    # 1/9 の東京に対応する SOX の変化は 1/4→1/8（2セッション分を累積）
    assert ret.loc["2024-01-09", "SOX"] == pytest.approx(np.log(60 / 50))
    parts = aligned["jp_parts"]
    assert parts.loc["2024-01-09", "N225_GAP"] == pytest.approx(np.log(104 / 100))
    assert parts.loc["2024-01-09", "N225_INTRADAY"] == pytest.approx(np.log(105 / 104))


def test_ols_recovers_coefficients():
    rng = np.random.default_rng(1)
    X = pd.DataFrame({"a": rng.normal(size=500), "b": rng.normal(size=500)})
    y = 0.5 + 2.0 * X["a"] - 1.0 * X["b"] + rng.normal(scale=0.01, size=500)
    fit = A.ols(y, X)
    assert fit["coef"]["a"] == pytest.approx(2.0, abs=0.01)
    assert fit["coef"]["b"] == pytest.approx(-1.0, abs=0.01)
    assert fit["r2"] > 0.99


def test_synthetic_pipeline_detects_overnight_link(tmp_path):
    aligned = build_aligned(make_prices())
    ret, parts = aligned["returns"], aligned["jp_parts"]
    ll = A.lead_lag(ret, "N225", ["SOX", "DJI"])
    # 前夜(lag+0) の米国市場が最も強く効いている
    assert (ll.abs().idxmax(axis=1) == "lag+0").all()
    # 前夜の動きは寄付きギャップに出て、日中にはほぼ出ない
    assert parts["N225_GAP"].corr(ret["SOX"]) > 0.7
    assert abs(parts["N225_INTRADAY"].corr(ret["SOX"])) < 0.1
    assert parts["N225_GAP"].corr(parts["CME_OVERNIGHT"]) > 0.8

    path = build_report(aligned, tmp_path)
    assert path.exists()
    for f in ["correlation_heatmap.png", "lead_lag.png", "rolling_corr.png", "gap_scatter.png"]:
        assert (tmp_path / f).exists()


def test_download_parses_yfinance_frame(monkeypatch):
    import yfinance as yf

    from kabu_corr.collect import download

    idx = pd.DatetimeIndex(pd.to_datetime(["2024-01-04", "2024-01-05"]), name="Date")
    cols = pd.MultiIndex.from_product([["^N225", "^SOX"], ["Open", "High", "Low", "Close", "Volume"]],
                                      names=["Ticker", "Price"])
    raw = pd.DataFrame(np.arange(20, dtype=float).reshape(2, 10), index=idx, columns=cols)
    raw.loc[:, ("^SOX", "Close")] = np.nan  # 取得失敗銘柄
    monkeypatch.setattr(yf, "download", lambda *a, **k: raw)
    out = download(["^N225", "^SOX"], "2024-01-01")
    assert out["ticker"].unique().tolist() == ["^N225"]
    assert list(out.columns) == ["date", "ticker", "open", "high", "low", "close", "volume"]
    assert out["close"].tolist() == [3.0, 13.0]
