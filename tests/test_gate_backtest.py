"""Gate G-Backtest validation tests — Task #036.

Validates the 6 criteria of gate G-Backtest:
1. Determinism: 2 identical runs → trades.csv SHA-256 match, equity atol=1e-10
2. Equity-trades coherence: E_final == E_0 * Π(1 + w * r_net_i) at atol=1e-8
3. One-at-a-time: no overlapping trades on dense signals
4. Costs: hand-calculated verification on >= 3 cases
5. trades.csv parseable with conforming columns (§12.6)
6. Anti-leak: perturbation of future prices does not change past trade decisions
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import pytest

from ai_trading.backtest.costs import apply_cost_model
from ai_trading.backtest.engine import build_equity_curve, execute_trades
from ai_trading.backtest.journal import export_trade_journal
from tests.conftest import make_ohlcv_random

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HORIZON = 4
FEE = 0.0005
SLIPPAGE = 0.00025
INITIAL_EQUITY = 1.0
POSITION_FRACTION = 1.0

EXPECTED_JOURNAL_COLUMNS = [
    "entry_time_utc",
    "exit_time_utc",
    "entry_price",
    "exit_price",
    "entry_price_eff",
    "exit_price_eff",
    "f",
    "s",
    "fees_paid",
    "slippage_paid",
    "y_true",
    "y_hat",
    "gross_return",
    "net_return",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sparse_signals(n: int, go_indices: list[int]) -> np.ndarray:
    """Build a binary signal array with 1s at specified indices."""
    signals = np.zeros(n, dtype=int)
    for i in go_indices:
        signals[i] = 1
    return signals


def _run_full_pipeline(
    ohlcv: pd.DataFrame,
    signals: np.ndarray,
    tmp_dir,
    run_id: str = "run",
) -> tuple[list[dict], pd.DataFrame, pd.DataFrame]:
    """Run complete backtest pipeline: execute → cost → equity → journal.

    Returns (enriched_trades, equity_df, journal_df).
    """
    trades = execute_trades(signals, ohlcv, HORIZON, "standard")

    enriched = apply_cost_model(trades, FEE, SLIPPAGE)

    # Add y_true / y_hat (required by journal)
    for t in enriched:
        entry_p = t["entry_price"]
        exit_p = t["exit_price"]
        t["y_true"] = np.log(exit_p / entry_p)
        t["y_hat"] = t["y_true"] + 0.001  # dummy prediction

    equity_df = build_equity_curve(enriched, ohlcv, INITIAL_EQUITY, POSITION_FRACTION)

    csv_path = tmp_dir / f"trades_{run_id}.csv"
    journal_df = export_trade_journal(enriched, csv_path, FEE, SLIPPAGE)

    return enriched, equity_df, journal_df


# ===================================================================
# Criterion 1 — Determinism
# ===================================================================


class TestDeterminism:
    """#036 — Two identical runs produce byte-identical trades.csv and equity."""

    def test_trades_csv_sha256_identical(self, tmp_path):
        """Two runs with same inputs → trades.csv files have identical SHA-256."""
        ohlcv = make_ohlcv_random(50, seed=99)
        signals = _make_sparse_signals(50, [2, 10, 20, 30])

        _run_full_pipeline(ohlcv, signals, tmp_path, run_id="a")
        _run_full_pipeline(ohlcv, signals, tmp_path, run_id="b")

        csv_a = (tmp_path / "trades_a.csv").read_bytes()
        csv_b = (tmp_path / "trades_b.csv").read_bytes()
        sha_a = hashlib.sha256(csv_a).hexdigest()
        sha_b = hashlib.sha256(csv_b).hexdigest()
        assert sha_a == sha_b, f"SHA-256 mismatch: {sha_a} != {sha_b}"

    def test_equity_curve_identical(self, tmp_path):
        """Two runs → equity values match at atol=1e-10."""
        ohlcv = make_ohlcv_random(50, seed=99)
        signals = _make_sparse_signals(50, [2, 10, 20, 30])

        _, eq1, _ = _run_full_pipeline(ohlcv, signals, tmp_path, run_id="c")
        _, eq2, _ = _run_full_pipeline(ohlcv, signals, tmp_path, run_id="d")

        np.testing.assert_allclose(
            np.asarray(eq1["equity"].values),
            np.asarray(eq2["equity"].values),
            atol=1e-10,
        )

    def test_determinism_with_different_seed_differs(self, tmp_path):
        """Sanity: different OHLCV data produces different results."""
        ohlcv_a = make_ohlcv_random(50, seed=1)
        ohlcv_b = make_ohlcv_random(50, seed=2)
        signals = _make_sparse_signals(50, [2, 10, 20])

        _, eq_a, _ = _run_full_pipeline(ohlcv_a, signals, tmp_path, run_id="e")
        _, eq_b, _ = _run_full_pipeline(ohlcv_b, signals, tmp_path, run_id="f")

        assert not np.allclose(
            np.asarray(eq_a["equity"].values),
            np.asarray(eq_b["equity"].values),
            atol=1e-10,
        )


# ===================================================================
# Criterion 2 — Equity-trades coherence
# ===================================================================


class TestEquityTradeCoherence:
    """#036 — E_final == E_0 * Π(1 + w * r_net_i) at atol=1e-8."""

    def test_equity_final_matches_product_formula(self, tmp_path):
        """E_final computed from equity curve == manual product of trade returns."""
        ohlcv = make_ohlcv_random(60, seed=77)
        signals = _make_sparse_signals(60, [0, 8, 18, 30, 42])

        enriched, equity_df, _ = _run_full_pipeline(
            ohlcv, signals, tmp_path, run_id="eq1"
        )

        # Manual computation: E_final = E_0 * Π(1 + w * r_net_i)
        e_manual = INITIAL_EQUITY
        for t in enriched:
            e_manual *= 1.0 + POSITION_FRACTION * t["r_net"]

        e_final = equity_df["equity"].iloc[-1]
        np.testing.assert_allclose(e_final, e_manual, atol=1e-8)

    def test_coherence_single_trade(self, tmp_path):
        """Single trade: E_final = E_0 * (1 + w * r_net)."""
        ohlcv = make_ohlcv_random(30, seed=55)
        signals = _make_sparse_signals(30, [5])

        enriched, equity_df, _ = _run_full_pipeline(
            ohlcv, signals, tmp_path, run_id="eq2"
        )

        assert len(enriched) == 1
        r_net = enriched[0]["r_net"]
        expected = INITIAL_EQUITY * (1.0 + POSITION_FRACTION * r_net)
        np.testing.assert_allclose(equity_df["equity"].iloc[-1], expected, atol=1e-8)

    def test_coherence_no_trades(self, tmp_path):
        """No trades: equity stays at initial value."""
        ohlcv = make_ohlcv_random(30, seed=55)
        signals = np.zeros(30, dtype=int)

        enriched, equity_df, _ = _run_full_pipeline(
            ohlcv, signals, tmp_path, run_id="eq3"
        )

        assert len(enriched) == 0
        np.testing.assert_allclose(
            equity_df["equity"].iloc[-1], INITIAL_EQUITY, atol=1e-10
        )

    def test_coherence_multiple_trades(self, tmp_path):
        """Multiple trades: cumulative product matches equity curve final value."""
        ohlcv = make_ohlcv_random(80, seed=33)
        # Space signals far enough apart to avoid overlap (HORIZON=4)
        signals = _make_sparse_signals(80, [2, 12, 22, 32, 42, 55, 65])

        enriched, equity_df, _ = _run_full_pipeline(
            ohlcv, signals, tmp_path, run_id="eq4"
        )

        assert len(enriched) >= 4  # at least some trades should fire

        e_manual = INITIAL_EQUITY
        for t in enriched:
            e_manual *= 1.0 + POSITION_FRACTION * t["r_net"]

        np.testing.assert_allclose(equity_df["equity"].iloc[-1], e_manual, atol=1e-8)


# ===================================================================
# Criterion 3 — One-at-a-time (no overlap)
# ===================================================================


class TestOneAtATime:
    """#036 — Dense signals: no overlapping trades under standard execution mode."""

    def test_dense_signals_no_overlap(self):
        """All-ones signal vector: trades must not overlap in time."""
        n = 40
        ohlcv = make_ohlcv_random(n, seed=11)
        signals = np.ones(n, dtype=int)  # all Go

        trades = execute_trades(signals, ohlcv, HORIZON, "standard")
        assert len(trades) >= 2, "Expected multiple trades with dense signals"

        for i in range(1, len(trades)):
            prev_exit = trades[i - 1]["exit_time"]
            curr_signal = trades[i]["signal_time"]
            assert curr_signal >= prev_exit, (
                f"Trade {i} signal_time ({curr_signal}) < "
                f"trade {i-1} exit_time ({prev_exit}): overlap detected"
            )

    def test_consecutive_signals_skip_while_in_position(self):
        """Consecutive Go signals while in position are ignored."""
        n = 20
        ohlcv = make_ohlcv_random(n, seed=22)
        # Signal at every bar
        signals = np.ones(n, dtype=int)

        trades = execute_trades(signals, ohlcv, HORIZON, "standard")

        # With H=4, first trade: signal=0, entry=1, exit=4.
        # Next trade can start at signal>=4 (when position closes).
        # So in 20 bars: max ~3-4 trades (not 20).
        assert len(trades) < n // 2

    def test_no_overlap_with_alternating_signals(self):
        """Alternating 1/0 pattern also produces no overlap."""
        n = 30
        ohlcv = make_ohlcv_random(n, seed=33)
        signals = np.array([1 if i % 2 == 0 else 0 for i in range(n)], dtype=int)

        trades = execute_trades(signals, ohlcv, HORIZON, "standard")

        for i in range(1, len(trades)):
            prev_exit = trades[i - 1]["exit_time"]
            curr_entry = trades[i]["entry_time"]
            assert curr_entry > prev_exit


# ===================================================================
# Criterion 4 — Costs: hand-computed verification (>= 3 cases)
# ===================================================================


class TestCostsHandComputed:
    """#036 — Cost model produces results identical to hand calculation."""

    @pytest.mark.parametrize(
        "p_entry,p_exit,f,s",
        [
            (100.0, 105.0, 0.001, 0.0005),
            (200.0, 190.0, 0.0005, 0.00025),
            (50.0, 55.0, 0.002, 0.001),
            (1000.0, 1000.0, 0.001, 0.0005),  # break-even gross
        ],
        ids=["gain", "loss", "high-cost", "break-even"],
    )
    def test_cost_formulas_match_hand_calculation(self, p_entry, p_exit, f, s):
        """Verify §12.3 formulas by hand for each case."""
        trade = {
            "signal_time": pd.Timestamp("2024-01-01 00:00"),
            "entry_time": pd.Timestamp("2024-01-01 01:00"),
            "exit_time": pd.Timestamp("2024-01-01 05:00"),
            "entry_price": p_entry,
            "exit_price": p_exit,
        }

        result = apply_cost_model([trade], f, s)
        r = result[0]

        # Hand computation
        p_entry_eff = p_entry * (1 + s)
        p_exit_eff = p_exit * (1 - s)
        m_net = (1 - f) ** 2 * (p_exit_eff / p_entry_eff)
        r_net = m_net - 1.0

        assert r["entry_price_eff"] == pytest.approx(p_entry_eff, rel=1e-12)
        assert r["exit_price_eff"] == pytest.approx(p_exit_eff, rel=1e-12)
        assert r["m_net"] == pytest.approx(m_net, rel=1e-12)
        assert r["r_net"] == pytest.approx(r_net, rel=1e-12)

    def test_zero_cost_rates_no_drag(self):
        """With f=0 and s=0, r_net == gross return - 1."""
        trade = {
            "signal_time": pd.Timestamp("2024-01-01"),
            "entry_time": pd.Timestamp("2024-01-01 01:00"),
            "exit_time": pd.Timestamp("2024-01-01 05:00"),
            "entry_price": 100.0,
            "exit_price": 110.0,
        }
        result = apply_cost_model([trade], 0.0, 0.0)
        expected_r_net = (110.0 / 100.0) - 1.0
        assert result[0]["r_net"] == pytest.approx(expected_r_net, rel=1e-12)

    def test_costs_always_reduce_return(self):
        """With positive fees/slippage, r_net < gross return for any trade."""
        trade = {
            "signal_time": pd.Timestamp("2024-01-01"),
            "entry_time": pd.Timestamp("2024-01-01 01:00"),
            "exit_time": pd.Timestamp("2024-01-01 05:00"),
            "entry_price": 100.0,
            "exit_price": 110.0,
        }
        result = apply_cost_model([trade], FEE, SLIPPAGE)
        gross = (110.0 / 100.0) - 1.0
        assert result[0]["r_net"] < gross


# ===================================================================
# Criterion 5 — trades.csv parseable with conforming columns
# ===================================================================


class TestTradesCSVConformity:
    """#036 — trades.csv is parseable and has columns per §12.6."""

    def test_csv_parseable_and_columns_match(self, tmp_path):
        """CSV file is valid and column order matches §12.6."""
        ohlcv = make_ohlcv_random(30, seed=44)
        signals = _make_sparse_signals(30, [2, 12])

        _, _, journal_df = _run_full_pipeline(ohlcv, signals, tmp_path, run_id="csv1")

        # Re-read from disk
        csv_path = tmp_path / "trades_csv1.csv"
        parsed = pd.read_csv(csv_path)

        assert list(parsed.columns) == EXPECTED_JOURNAL_COLUMNS

    def test_csv_row_count_matches_trades(self, tmp_path):
        """Number of CSV rows == number of trades."""
        ohlcv = make_ohlcv_random(50, seed=44)
        signals = _make_sparse_signals(50, [2, 12, 25, 38])

        enriched, _, _ = _run_full_pipeline(ohlcv, signals, tmp_path, run_id="csv2")

        csv_path = tmp_path / "trades_csv2.csv"
        parsed = pd.read_csv(csv_path)
        assert len(parsed) == len(enriched)

    def test_csv_numeric_columns_finite(self, tmp_path):
        """All numeric columns contain finite values."""
        ohlcv = make_ohlcv_random(50, seed=44)
        signals = _make_sparse_signals(50, [2, 12, 25])

        _run_full_pipeline(ohlcv, signals, tmp_path, run_id="csv3")

        csv_path = tmp_path / "trades_csv3.csv"
        parsed = pd.read_csv(csv_path)

        numeric_cols = [
            "entry_price", "exit_price", "entry_price_eff", "exit_price_eff",
            "f", "s", "fees_paid", "slippage_paid", "y_true", "y_hat",
            "gross_return", "net_return",
        ]
        for col in numeric_cols:
            assert parsed[col].notna().all(), f"NaN found in column {col}"
            assert np.isfinite(parsed[col].values).all(), f"Non-finite in {col}"

    def test_csv_fee_slippage_columns_match_config(self, tmp_path):
        """f and s columns in CSV match the configured rates."""
        ohlcv = make_ohlcv_random(30, seed=44)
        signals = _make_sparse_signals(30, [2])

        _run_full_pipeline(ohlcv, signals, tmp_path, run_id="csv4")

        csv_path = tmp_path / "trades_csv4.csv"
        parsed = pd.read_csv(csv_path)

        assert np.allclose(np.asarray(parsed["f"].values, dtype=np.float64), FEE)
        assert np.allclose(np.asarray(parsed["s"].values, dtype=np.float64), SLIPPAGE)

    def test_empty_trades_produces_empty_csv(self, tmp_path):
        """No trades → CSV has header only, 0 rows."""
        ohlcv = make_ohlcv_random(30, seed=44)
        signals = np.zeros(30, dtype=int)

        _run_full_pipeline(ohlcv, signals, tmp_path, run_id="csv5")

        csv_path = tmp_path / "trades_csv5.csv"
        parsed = pd.read_csv(csv_path)
        assert len(parsed) == 0
        assert list(parsed.columns) == EXPECTED_JOURNAL_COLUMNS


# ===================================================================
# Criterion 6 — Anti-leak: future price perturbation
# ===================================================================


class TestAntiLeak:
    """#036 — Perturbing future prices does not change past trade decisions."""

    def test_future_price_perturbation_preserves_past_trades(self):
        """Modifying prices from bar K onwards doesn't change trades with signal_time <= K."""
        n = 60
        ohlcv_orig = make_ohlcv_random(n, seed=88)
        # Signals well-spaced: bars 2, 15, 30, 45
        signals = _make_sparse_signals(n, [2, 15, 30, 45])

        trades_orig = execute_trades(signals, ohlcv_orig, HORIZON, "standard")
        assert len(trades_orig) >= 3

        # Perturbation point: from bar 25 onwards (between signal 15 and signal 30)
        k = 25
        ohlcv_perturbed = ohlcv_orig.copy()
        rng = np.random.default_rng(999)
        perturb = rng.uniform(0.9, 1.1, n - k)
        for col in ("open", "high", "low", "close"):
            vals = np.asarray(ohlcv_perturbed[col].values, dtype=np.float64).copy()
            vals[k:] *= perturb
            ohlcv_perturbed[col] = vals

        trades_perturbed = execute_trades(
            signals, ohlcv_perturbed, HORIZON, "standard"
        )

        # All trades with signal_time at or before bar K must be present
        # and have same signal_time, entry_time, exit_time
        orig_before_k = [
            t for t in trades_orig if t["signal_time"] <= ohlcv_orig.index[k]
        ]
        pert_before_k = [
            t for t in trades_perturbed
            if t["signal_time"] <= ohlcv_perturbed.index[k]
        ]

        assert len(orig_before_k) == len(pert_before_k)
        for t_orig, t_pert in zip(orig_before_k, pert_before_k, strict=True):
            assert t_orig["signal_time"] == t_pert["signal_time"]
            assert t_orig["entry_time"] == t_pert["entry_time"]
            assert t_orig["exit_time"] == t_pert["exit_time"]

    def test_past_entry_prices_unchanged_if_within_perturbation_boundary(self):
        """Trades fully before perturbation point have identical prices."""
        n = 60
        ohlcv_orig = make_ohlcv_random(n, seed=88)
        signals = _make_sparse_signals(n, [2, 15])

        trades_orig = execute_trades(signals, ohlcv_orig, HORIZON, "standard")

        # Perturbation from bar 30 onwards — both trades (signal 2, signal 15) are
        # fully contained before bar 30 (entry <= 16, exit <= 19).
        k = 30
        ohlcv_perturbed = ohlcv_orig.copy()
        rng = np.random.default_rng(777)
        perturb = rng.uniform(0.8, 1.2, n - k)
        for col in ("open", "high", "low", "close"):
            vals = np.asarray(ohlcv_perturbed[col].values, dtype=np.float64).copy()
            vals[k:] *= perturb
            ohlcv_perturbed[col] = vals

        trades_perturbed = execute_trades(
            signals, ohlcv_perturbed, HORIZON, "standard"
        )

        # Both trades should have identical prices (fully before perturbation)
        assert len(trades_orig) == len(trades_perturbed)
        for t_o, t_p in zip(trades_orig, trades_perturbed, strict=True):
            assert t_o["entry_price"] == pytest.approx(t_p["entry_price"], rel=1e-15)
            assert t_o["exit_price"] == pytest.approx(t_p["exit_price"], rel=1e-15)

    def test_signal_decisions_independent_of_future_data(self):
        """Demonstrate trade decisions only depend on signal[t] and position state."""
        n = 40
        ohlcv_a = make_ohlcv_random(n, seed=10)
        ohlcv_b = make_ohlcv_random(n, seed=20)  # completely different prices
        signals = _make_sparse_signals(n, [3, 15, 28])

        trades_a = execute_trades(signals, ohlcv_a, HORIZON, "standard")
        trades_b = execute_trades(signals, ohlcv_b, HORIZON, "standard")

        # Same signal vector ⇒ same trade structure (timing), different prices
        assert len(trades_a) == len(trades_b)
        for ta, tb in zip(trades_a, trades_b, strict=True):
            assert ta["signal_time"] == tb["signal_time"]
            assert ta["entry_time"] == tb["entry_time"]
            assert ta["exit_time"] == tb["exit_time"]
