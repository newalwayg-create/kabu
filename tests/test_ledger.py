import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "trading"))
import ledger  # noqa: E402


def _trades(rows):
    df = pd.DataFrame(rows, columns=["date", "time", "ticker", "name", "side", "qty", "price", "fee", "tax", "note"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_replay_average_cost_and_realized_gain():
    t = _trades([
        ("2026-10-09", "09:10", "1475.T", "", "BUY", 50, 400, 0, 0, ""),
        ("2026-10-10", "09:10", "1475.T", "", "BUY", 50, 420, 0, 0, ""),
        ("2026-10-15", "10:00", "1475.T", "", "SELL", 40, 450, 0, 813, ""),
    ])
    b = ledger.replay(t, 50000)
    p = b.positions["1475.T"]
    assert p.qty == 60 and p.avg == pytest.approx(410)
    assert b.realized == pytest.approx(40 * (450 - 410))
    assert b.cash == pytest.approx(50000 - 20000 - 21000 + 18000 - 813)


def test_replay_rejects_overselling():
    t = _trades([("2026-10-09", "", "200A.T", "", "SELL", 1, 4700, 0, 0, "")])
    with pytest.raises(ValueError):
        ledger.replay(t, 50000)


def test_stop_levels_raise_after_trigger():
    cfg = ledger.load_config()
    p = ledger.Position("1475.T", qty=56, cost=56 * 400)
    assert ledger.stop_levels(cfg, p, 420)["stop"] == pytest.approx(372)
    lv = ledger.stop_levels(cfg, p, 433)
    assert lv["locked"] and lv["stop"] == pytest.approx(412)


def test_fix_splits_rescales_history():
    idx = pd.to_datetime(["2026-10-01", "2026-10-02", "2026-10-05"])
    df = pd.DataFrame({("X", "Open"): [70000.0, 71000.0, 7150.0], ("X", "Close"): [70500.0, 71200.0, 7200.0]}, index=idx)
    ledger._fix_splits(df, "X")
    assert df[("X", "Close")].tolist() == pytest.approx([7050.0, 7120.0, 7200.0])
