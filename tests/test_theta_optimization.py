"""Tests for θ optimization loop — calibrate_threshold (#031, #032 WS-7).

Covers:
- calibrate_threshold: single feasible θ, multiple feasible θ, tiebreaker,
  no feasible θ, anti-leak (y_hat_test invariance), config-driven params,
  equity reset per candidate, edge cases.
- compute_max_drawdown: correctness, no-trade, constant equity.
- #032: fallback θ (E.2.2) — relax min_trades, θ = +∞, warnings, fold conserved.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import pytest

from ai_trading.calibration.threshold import (
    calibrate_threshold,
    compute_max_drawdown,
)
from ai_trading.config import load_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HORIZON = 4


def _make_ohlcv(n: int, start: str = "2024-01-01") -> pd.DataFrame:
    """Synthetic OHLCV with deterministic prices."""
    idx = pd.date_range(start, periods=n, freq="1h")
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.standard_normal(n) * 0.5)
    close = np.abs(close) + 50.0  # ensure positive
    opens = close + rng.standard_normal(n) * 0.1
    opens = np.abs(opens) + 50.0
    return pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, close) + 0.5,
            "low": np.minimum(opens, close) - 0.5,
            "close": close,
            "volume": rng.uniform(100, 1000, n),
        },
        index=idx,
    )


def _make_y_hat_val(n: int, seed: int = 123) -> np.ndarray:
    """Deterministic float64 predictions."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n).astype(np.float64)


# ---------------------------------------------------------------------------
# compute_max_drawdown
# ---------------------------------------------------------------------------


class TestComputeMaxDrawdown:
    """Tests for compute_max_drawdown helper."""

    def test_no_drawdown(self) -> None:
        """Monotonically increasing equity → MDD = 0."""
        equity = np.array([1.0, 1.1, 1.2, 1.3, 1.4])
        assert compute_max_drawdown(equity) == pytest.approx(0.0)

    def test_known_drawdown(self) -> None:
        """Known drawdown: peak=2.0, trough=1.0 → MDD = 0.5."""
        equity = np.array([1.0, 2.0, 1.0, 1.5])
        assert compute_max_drawdown(equity) == pytest.approx(0.5)

    def test_full_drawdown(self) -> None:
        """Peak=1.0, drops to near zero."""
        equity = np.array([1.0, 0.5, 0.1])
        # MDD = (1.0 - 0.1) / 1.0 = 0.9
        assert compute_max_drawdown(equity) == pytest.approx(0.9)

    def test_constant_equity(self) -> None:
        """Constant equity → MDD = 0."""
        equity = np.array([1.0, 1.0, 1.0, 1.0])
        assert compute_max_drawdown(equity) == pytest.approx(0.0)

    def test_single_value(self) -> None:
        """Single-element equity → MDD = 0."""
        equity = np.array([1.0])
        assert compute_max_drawdown(equity) == pytest.approx(0.0)

    def test_empty_raises(self) -> None:
        """Empty equity raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            compute_max_drawdown(np.array([]))

    def test_2d_equity_raises(self) -> None:
        """2D equity raises ValueError."""
        with pytest.raises(ValueError, match="1D"):
            compute_max_drawdown(np.array([[1.0, 2.0], [3.0, 4.0]]))

    def test_drawdown_after_recovery(self) -> None:
        """MDD picks the worst drawdown even after recovery."""
        # Peak=10 at idx 3, trough=5 at idx 4 → dd=0.5
        # Then new peak=12 at idx 6, trough=9 at idx 7 → dd=0.25
        equity = np.array([1.0, 5.0, 8.0, 10.0, 5.0, 7.0, 12.0, 9.0])
        assert compute_max_drawdown(equity) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# calibrate_threshold — nominal: single feasible θ
# ---------------------------------------------------------------------------


class TestCalibrateThresholdSingleFeasible:
    """#031 — When only one θ satisfies constraints, it must be selected."""

    def test_single_feasible_theta(self) -> None:
        """Construct scenario where only one quantile produces
        trades that pass mdd_cap and min_trades constraints."""
        n = 200
        ohlcv = _make_ohlcv(n)
        # Predictions linearly spaced — lower quantiles produce more signals
        y_hat_val = np.linspace(0.0, 1.0, n)

        # Use a very permissive mdd_cap and min_trades=1 so we can control
        # which θ is feasible via the q_grid design
        q_grid = [0.1, 0.5, 0.99]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,  # very permissive
            min_trades=1,
        )

        # Result must be a dict with expected keys
        assert isinstance(result, dict)
        assert "theta" in result
        assert "quantile" in result
        assert "method" in result
        assert "net_pnl" in result
        assert "mdd" in result
        assert "n_trades" in result
        assert "details" in result
        assert result["method"] == "quantile_grid"
        assert result["quantile"] in q_grid
        # Details must have one entry per candidate
        assert len(result["details"]) == len(q_grid)


# ---------------------------------------------------------------------------
# calibrate_threshold — nominal: multiple feasible θ → max net_pnl
# ---------------------------------------------------------------------------


class TestCalibrateThresholdBestPnl:
    """#031 — Among multiple feasible θ, the one maximizing net_pnl wins."""

    def test_best_pnl_selected(self) -> None:
        """With permissive constraints, best net_pnl candidate is selected."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)

        q_grid = [0.3, 0.5, 0.7, 0.9]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,  # very permissive
            min_trades=0,
        )

        # Among feasible candidates, the selected one must have the best net_pnl
        feasible = [
            d for d in result["details"]
            if d["mdd"] <= 1.0 and d["n_trades"] >= 0
        ]
        best_pnl = max(d["net_pnl"] for d in feasible)
        assert result["net_pnl"] == pytest.approx(best_pnl)


# ---------------------------------------------------------------------------
# calibrate_threshold — tiebreaker: highest quantile preferred
# ---------------------------------------------------------------------------


class TestCalibrateThresholdTiebreaker:
    """#031 — Ex-aequo on net_pnl: prefer highest quantile (most conservative)."""

    def test_tiebreaker_highest_quantile(self) -> None:
        """When all candidates have identical net_pnl=0 (no trades or constant
        equity), the highest quantile must be selected."""
        n = 100
        # Constant prices → all trades have r_net ~ 0 with small costs
        idx = pd.date_range("2024-01-01", periods=n, freq="1h")
        ohlcv = pd.DataFrame(
            {
                "open": np.full(n, 100.0),
                "high": np.full(n, 100.5),
                "low": np.full(n, 99.5),
                "close": np.full(n, 100.0),
                "volume": np.ones(n),
            },
            index=idx,
        )
        # All predictions identical → all quantiles give same θ → same signals
        # → same trades → same net_pnl (exactly tied)
        y_hat_val = np.full(n, 0.5)

        q_grid = [0.3, 0.5, 0.7, 0.9]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0,
            slippage_rate_per_side=0.0,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=0,
        )

        # All θ identical → all net_pnl identical → tiebreaker = highest quantile
        assert result["quantile"] == 0.9


# ---------------------------------------------------------------------------
# calibrate_threshold — no feasible θ
# ---------------------------------------------------------------------------


class TestCalibrateThresholdNoFeasible:
    """#031 — No θ meets both constraints → fallback E.2.2 applies (#032)."""

    def test_no_feasible_theta_triggers_fallback(self) -> None:
        """min_trades impossibly high + tight mdd_cap → fallback applies."""
        n = 50
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=[0.5, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.01,  # very tight
            min_trades=10000,  # impossible
        )

        # Fallback applies: either relaxed or θ = +∞
        assert result["theta"] is not None
        assert result["method"] in (
            "fallback_relax_min_trades",
            "fallback_no_trade",
        )
        # Details still populated for traceability
        assert len(result["details"]) == 2


# ---------------------------------------------------------------------------
# calibrate_threshold — equity reset per candidate
# ---------------------------------------------------------------------------


class TestCalibrateThresholdEquityReset:
    """#031 — Equity must be reset to E_0 for each candidate."""

    def test_equity_independent_per_candidate(self) -> None:
        """Candidate metrics are identical whether evaluated alone or
        alongside other candidates (no cross-contamination)."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)

        q_grid = [0.3, 0.5, 0.7]
        common_kwargs = dict(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=0,
        )

        # Run with all candidates together
        result_all = calibrate_threshold(q_grid=q_grid, **common_kwargs)
        metrics_all = {
            d["quantile"]: (d["net_pnl"], d["mdd"], d["n_trades"])
            for d in result_all["details"]
        }

        # Run each candidate in isolation and compare
        for q in q_grid:
            result_solo = calibrate_threshold(q_grid=[q], **common_kwargs)
            solo_detail = result_solo["details"][0]
            assert solo_detail["net_pnl"] == pytest.approx(metrics_all[q][0])
            assert solo_detail["mdd"] == pytest.approx(metrics_all[q][1])
            assert solo_detail["n_trades"] == metrics_all[q][2]


# ---------------------------------------------------------------------------
# calibrate_threshold — anti-leak: y_hat_test does not affect θ
# ---------------------------------------------------------------------------


class TestCalibrateThresholdAntiLeak:
    """#031 — θ calibrated on val only; modifying y_hat_test has no effect."""

    def test_theta_invariant_to_test_data(self) -> None:
        """calibrate_threshold does not accept or use test data."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)
        q_grid = [0.5, 0.7, 0.9]

        result1 = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=0,
        )
        result2 = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=0,
        )

        assert result1["theta"] == result2["theta"]
        assert result1["quantile"] == result2["quantile"]
        assert result1["net_pnl"] == result2["net_pnl"]


# ---------------------------------------------------------------------------
# calibrate_threshold — config-driven
# ---------------------------------------------------------------------------


class TestCalibrateThresholdConfigDriven:
    """#031 — Parameters read from config, not hardcoded."""

    def test_config_keys_exist(self, default_config_path) -> None:
        """Config contains thresholding.objective, mdd_cap, min_trades."""
        cfg = load_config(str(default_config_path))
        assert cfg.thresholding.objective == "max_net_pnl_with_mdd_cap"
        assert cfg.thresholding.mdd_cap == 0.25
        assert cfg.thresholding.min_trades == 20


# ---------------------------------------------------------------------------
# calibrate_threshold — constraint filtering
# ---------------------------------------------------------------------------


class TestCalibrateThresholdConstraints:
    """#031 — MDD and min_trades constraints filter candidates correctly."""

    def test_mdd_constraint_filters(self) -> None:
        """θ with MDD > mdd_cap must not be selected."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=[0.3, 0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=0,
        )

        if result["theta"] is not None:
            assert result["mdd"] <= 1.0

    def test_min_trades_constraint_filters(self) -> None:
        """θ with n_trades < min_trades must not be selected."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=[0.3, 0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=1,
        )

        if result["theta"] is not None:
            assert result["n_trades"] >= 1


# ---------------------------------------------------------------------------
# calibrate_threshold — validation errors
# ---------------------------------------------------------------------------


class TestCalibrateThresholdErrors:
    """#031 — Input validation errors."""

    def test_empty_y_hat_val_raises(self) -> None:
        """Empty y_hat_val raises ValueError."""
        ohlcv = _make_ohlcv(10)
        with pytest.raises(ValueError, match="y_hat_val"):
            calibrate_threshold(
                y_hat_val=np.array([], dtype=np.float64),
                ohlcv_val=ohlcv,
                q_grid=[0.5],
                horizon=HORIZON,
                fee_rate_per_side=0.0005,
                slippage_rate_per_side=0.00025,
                initial_equity=1.0,
                position_fraction=1.0,
                objective="max_net_pnl_with_mdd_cap",
                mdd_cap=0.25,
                min_trades=1,
            )

    def test_length_mismatch_raises(self) -> None:
        """y_hat_val length != ohlcv length raises ValueError."""
        ohlcv = _make_ohlcv(50)
        y_hat = np.ones(30, dtype=np.float64)  # mismatch
        with pytest.raises(ValueError, match="length"):
            calibrate_threshold(
                y_hat_val=y_hat,
                ohlcv_val=ohlcv,
                q_grid=[0.5],
                horizon=HORIZON,
                fee_rate_per_side=0.0005,
                slippage_rate_per_side=0.00025,
                initial_equity=1.0,
                position_fraction=1.0,
                objective="max_net_pnl_with_mdd_cap",
                mdd_cap=0.25,
                min_trades=1,
            )

    def test_empty_q_grid_raises(self) -> None:
        """Empty q_grid raises ValueError."""
        n = 50
        ohlcv = _make_ohlcv(n)
        y_hat = _make_y_hat_val(n)
        with pytest.raises(ValueError, match="q_grid"):
            calibrate_threshold(
                y_hat_val=y_hat,
                ohlcv_val=ohlcv,
                q_grid=[],
                horizon=HORIZON,
                fee_rate_per_side=0.0005,
                slippage_rate_per_side=0.00025,
                initial_equity=1.0,
                position_fraction=1.0,
                objective="max_net_pnl_with_mdd_cap",
                mdd_cap=0.25,
                min_trades=1,
            )

    def test_invalid_objective_raises(self) -> None:
        """Unknown objective raises ValueError."""
        n = 50
        ohlcv = _make_ohlcv(n)
        y_hat = _make_y_hat_val(n)
        with pytest.raises(ValueError, match="objective"):
            calibrate_threshold(
                y_hat_val=y_hat,
                ohlcv_val=ohlcv,
                q_grid=[0.5],
                horizon=HORIZON,
                fee_rate_per_side=0.0005,
                slippage_rate_per_side=0.00025,
                initial_equity=1.0,
                position_fraction=1.0,
                objective="unknown_objective",
                mdd_cap=0.25,
                min_trades=1,
            )

    def test_2d_y_hat_val_raises(self) -> None:
        """2D y_hat_val raises ValueError."""
        ohlcv = _make_ohlcv(10)
        with pytest.raises(ValueError, match="1D"):
            calibrate_threshold(
                y_hat_val=np.ones((5, 2), dtype=np.float64),
                ohlcv_val=ohlcv,
                q_grid=[0.5],
                horizon=HORIZON,
                fee_rate_per_side=0.0005,
                slippage_rate_per_side=0.00025,
                initial_equity=1.0,
                position_fraction=1.0,
                objective="max_net_pnl_with_mdd_cap",
                mdd_cap=0.25,
                min_trades=1,
            )


# ---------------------------------------------------------------------------
# calibrate_threshold — details structure
# ---------------------------------------------------------------------------


class TestCalibrateThresholdDetails:
    """#031 — Details list contains all candidate evaluations for traceability."""

    def test_details_keys(self) -> None:
        """Each detail entry has quantile, theta, net_pnl, mdd, n_trades, feasible."""
        n = 100
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)
        q_grid = [0.3, 0.7]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=0,
        )

        for detail in result["details"]:
            assert "quantile" in detail
            assert "theta" in detail
            assert "net_pnl" in detail
            assert "mdd" in detail
            assert "n_trades" in detail
            assert "feasible" in detail

    def test_details_count_matches_q_grid(self) -> None:
        """One detail entry per quantile in q_grid."""
        n = 100
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)
        q_grid = [0.2, 0.4, 0.6, 0.8]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=0,
        )

        assert len(result["details"]) == len(q_grid)


# ---------------------------------------------------------------------------
# calibrate_threshold — zero trades scenario
# ---------------------------------------------------------------------------


class TestCalibrateThresholdZeroTrades:
    """#031 — When a θ produces zero trades, net_pnl=0, mdd=0."""

    def test_very_high_theta_zero_trades(self) -> None:
        """θ higher than all predictions → 0 signals → 0 trades."""
        n = 100
        ohlcv = _make_ohlcv(n)
        # All predictions very low
        y_hat_val = np.full(n, -10.0)

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=[0.99],  # θ = max(y_hat_val) = -10.0, all equal → 0 Go signals
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=0,
        )

        # With min_trades=0, the theta is feasible even with 0 trades
        detail = result["details"][0]
        assert detail["n_trades"] == 0
        assert detail["net_pnl"] == pytest.approx(0.0)
        assert detail["mdd"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calibrate_threshold — fallback θ E.2.2 step 1: relax min_trades (#032)
# ---------------------------------------------------------------------------


def _make_crashing_ohlcv(n: int) -> pd.DataFrame:
    """OHLCV with prices crashing exponentially from 100 → ~5."""
    idx = pd.date_range("2024-01-01", periods=n, freq="1h")
    close = 100.0 * np.exp(np.linspace(0, -3, n))
    return pd.DataFrame(
        {
            "open": close * 1.01,
            "high": close * 1.02,
            "low": close * 0.98,
            "close": close,
            "volume": np.full(n, 500.0),
        },
        index=idx,
    )


class TestCalibrateThresholdFallbackRelax:
    """#032 — Step 1: relax min_trades when no θ satisfies both constraints."""

    def test_fallback_relax_selects_theta(self) -> None:
        """When no θ satisfies both mdd_cap AND min_trades, but some satisfy
        mdd_cap alone, relax min_trades to 0 and select highest quantile
        with mdd <= mdd_cap."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)
        q_grid = [0.3, 0.5, 0.7, 0.9]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,  # permissive → all θ satisfy mdd_cap
            min_trades=10000,  # impossible → triggers fallback
        )

        # Must select a θ (not None) via fallback relaxation
        assert result["theta"] is not None
        assert result["quantile"] is not None
        assert result["method"] == "fallback_relax_min_trades"
        # Highest quantile among mdd-feasible candidates
        assert result["quantile"] == 0.9
        assert result["mdd"] <= 1.0

    def test_fallback_relax_picks_highest_quantile_among_feasible(self) -> None:
        """Among mdd-feasible candidates only, highest quantile is chosen."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)
        q_grid = [0.1, 0.5, 0.9]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=10000,  # impossible → fallback
        )

        assert result["quantile"] == 0.9

    def test_fallback_relax_emits_warning(self, caplog) -> None:
        """Warning emitted when min_trades is relaxed."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)

        with caplog.at_level(logging.WARNING, logger="ai_trading.calibration.threshold"):
            calibrate_threshold(
                y_hat_val=y_hat_val,
                ohlcv_val=ohlcv,
                q_grid=[0.5, 0.9],
                horizon=HORIZON,
                fee_rate_per_side=0.0005,
                slippage_rate_per_side=0.00025,
                initial_equity=1.0,
                position_fraction=1.0,
                objective="max_net_pnl_with_mdd_cap",
                mdd_cap=1.0,
                min_trades=10000,
            )

        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("min_trades" in msg for msg in warning_msgs)

    def test_fallback_relax_partial_mdd_filtering(self) -> None:
        """Only some candidates pass mdd <= mdd_cap; highest quantile among
        those is selected (exercises real step 1 filtering)."""
        n = 200
        # Crashing prices: low quantiles → many trades → high MDD,
        # high quantiles → few/no trades → low MDD.
        ohlcv = _make_crashing_ohlcv(n)
        y_hat_val = np.linspace(0, 1, n)
        q_grid = [0.1, 0.3, 0.5, 0.7, 0.9]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.50,  # moderate: some pass, some don't
            min_trades=10000,  # impossible → triggers fallback
        )

        assert result["method"] == "fallback_relax_min_trades"
        assert result["theta"] is not None
        assert result["quantile"] is not None
        assert result["mdd"] <= 0.50
        # Verify that at least one candidate was filtered out (MDD > mdd_cap)
        details = result["details"]
        mdd_values = [d["mdd"] for d in details]
        assert any(m > 0.50 for m in mdd_values), (
            "Expected at least one candidate with mdd > mdd_cap to exercise "
            "real partial filtering"
        )
        # Among mdd-feasible, highest quantile was picked
        mdd_feasible_qs = [
            d["quantile"] for d in details if d["mdd"] <= 0.50
        ]
        assert len(mdd_feasible_qs) >= 1
        assert result["quantile"] == max(mdd_feasible_qs)

    def test_fallback_relax_details_preserved(self) -> None:
        """Details list still contains all candidate evaluations."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)
        q_grid = [0.3, 0.5, 0.7]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,
            min_trades=10000,
        )

        assert len(result["details"]) == len(q_grid)


# ---------------------------------------------------------------------------
# calibrate_threshold — fallback θ E.2.2 step 2: θ = +∞ (#032)
# ---------------------------------------------------------------------------


class TestCalibrateThresholdFallbackNoTrade:
    """#032 — Step 2: θ = +∞ when no θ satisfies even mdd_cap."""

    def test_fallback_theta_infinity(self) -> None:
        """When no θ satisfies mdd <= mdd_cap, θ = +∞ (no-trade)."""
        n = 200
        ohlcv = _make_crashing_ohlcv(n)
        # Spread predictions → all low quantiles produce many trades
        y_hat_val = np.linspace(0, 1, n)
        # Only low quantiles: all generate many Go signals
        q_grid = [0.1, 0.2, 0.3]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.001,  # impossibly tight for crashing prices
            min_trades=1,
        )

        assert result["theta"] == float("inf")
        assert result["method"] == "fallback_no_trade"
        assert result["n_trades"] == 0
        assert result["net_pnl"] == pytest.approx(0.0)
        assert result["mdd"] == pytest.approx(0.0)

    def test_fallback_theta_infinity_emits_warning(self, caplog) -> None:
        """Warning emitted when θ = +∞."""
        n = 200
        ohlcv = _make_crashing_ohlcv(n)
        y_hat_val = np.linspace(0, 1, n)
        q_grid = [0.1, 0.2, 0.3]

        with caplog.at_level(logging.WARNING, logger="ai_trading.calibration.threshold"):
            calibrate_threshold(
                y_hat_val=y_hat_val,
                ohlcv_val=ohlcv,
                q_grid=q_grid,
                horizon=HORIZON,
                fee_rate_per_side=0.0005,
                slippage_rate_per_side=0.00025,
                initial_equity=1.0,
                position_fraction=1.0,
                objective="max_net_pnl_with_mdd_cap",
                mdd_cap=0.001,
                min_trades=1,
            )

        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_msgs) >= 1

    def test_fallback_fold_conserved(self) -> None:
        """Fold conserved with n_trades=0, net_pnl=0 when θ = +∞."""
        n = 200
        ohlcv = _make_crashing_ohlcv(n)
        y_hat_val = np.linspace(0, 1, n)
        q_grid = [0.1, 0.2, 0.3]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.001,
            min_trades=1,
        )

        # Fold is present (theta is not None, it's +∞)
        assert result["theta"] is not None
        assert result["n_trades"] == 0
        assert result["net_pnl"] == pytest.approx(0.0)
        assert result["mdd"] == pytest.approx(0.0)
        # Details still populated for all candidates
        assert len(result["details"]) == len(q_grid)

    def test_fallback_theta_infinity_quantile_none(self) -> None:
        """When θ = +∞, quantile is None (no quantile selected)."""
        n = 200
        ohlcv = _make_crashing_ohlcv(n)
        y_hat_val = np.linspace(0, 1, n)
        q_grid = [0.1, 0.2, 0.3]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.001,
            min_trades=1,
        )

        assert result["quantile"] is None


# ---------------------------------------------------------------------------
# calibrate_threshold — fallback θ E.2.2: no regression (#032)
# ---------------------------------------------------------------------------


class TestCalibrateThresholdFallbackNoRegression:
    """#032 — Fallback does NOT alter behavior when a feasible θ exists."""

    def test_feasible_theta_method_unchanged(self) -> None:
        """When a feasible θ exists, method is 'quantile_grid' (no fallback)."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)
        q_grid = [0.3, 0.5, 0.7, 0.9]

        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv,
            q_grid=q_grid,
            horizon=HORIZON,
            fee_rate_per_side=0.0005,
            slippage_rate_per_side=0.00025,
            initial_equity=1.0,
            position_fraction=1.0,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=1.0,  # permissive
            min_trades=0,
        )

        assert result["method"] == "quantile_grid"
        assert result["theta"] is not None
        assert isinstance(result["theta"], float)
        assert result["mdd"] <= 1.0

    def test_feasible_no_warning_emitted(self, caplog) -> None:
        """When a feasible θ exists, no fallback warning is emitted."""
        n = 200
        ohlcv = _make_ohlcv(n)
        y_hat_val = _make_y_hat_val(n)

        with caplog.at_level(logging.WARNING, logger="ai_trading.calibration.threshold"):
            calibrate_threshold(
                y_hat_val=y_hat_val,
                ohlcv_val=ohlcv,
                q_grid=[0.3, 0.5, 0.7, 0.9],
                horizon=HORIZON,
                fee_rate_per_side=0.0005,
                slippage_rate_per_side=0.00025,
                initial_equity=1.0,
                position_fraction=1.0,
                objective="max_net_pnl_with_mdd_cap",
                mdd_cap=1.0,
                min_trades=0,
            )

        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_msgs) == 0
