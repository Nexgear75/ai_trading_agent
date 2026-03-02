"""Tests for inter-fold aggregation — metrics, stitched equity, warnings.

Task #042 — WS-10.
"""

from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd
import pytest

from ai_trading.metrics.aggregation import (
    aggregate_fold_metrics,
    check_acceptance_criteria,
    derive_comparison_type,
    stitch_equity_curves,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TRADING_KEYS = [
    "net_pnl",
    "net_return",
    "max_drawdown",
    "sharpe",
    "profit_factor",
    "hit_rate",
    "n_trades",
    "avg_trade_return",
    "median_trade_return",
    "exposure_time_frac",
]

PREDICTION_KEYS = ["mae", "rmse", "directional_accuracy", "spearman_ic"]

EXCLUDED_KEYS = [
    "sharpe_per_trade",
    "n_samples_train",
    "n_samples_val",
    "n_samples_test",
]


def _make_fold_metrics(
    *,
    net_pnl: float = 0.05,
    net_return: float = 0.05,
    max_drawdown: float = 0.10,
    sharpe: float | None = 1.2,
    profit_factor: float | None = 1.5,
    hit_rate: float | None = 0.6,
    n_trades: int = 10,
    avg_trade_return: float | None = 0.005,
    median_trade_return: float | None = 0.004,
    exposure_time_frac: float = 0.3,
    sharpe_per_trade: float | None = 0.8,
    mae: float | None = None,
    rmse: float | None = None,
    directional_accuracy: float | None = None,
    spearman_ic: float | None = None,
) -> dict:
    """Build a fold metrics dict mirroring compute_trading/prediction_metrics output."""
    d: dict = {
        "net_pnl": net_pnl,
        "net_return": net_return,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "profit_factor": profit_factor,
        "hit_rate": hit_rate,
        "n_trades": n_trades,
        "avg_trade_return": avg_trade_return,
        "median_trade_return": median_trade_return,
        "exposure_time_frac": exposure_time_frac,
        "sharpe_per_trade": sharpe_per_trade,
    }
    # Add prediction keys only if at least one is not None
    if any(v is not None for v in [mae, rmse, directional_accuracy, spearman_ic]):
        d["mae"] = mae
        d["rmse"] = rmse
        d["directional_accuracy"] = directional_accuracy
        d["spearman_ic"] = spearman_ic
    return d


def _make_equity_df(
    equities: list[float],
    start: str = "2024-01-01",
    freq: str = "1h",
    in_trade: list[bool] | None = None,
) -> pd.DataFrame:
    """Build an equity curve DataFrame."""
    n = len(equities)
    times = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    if in_trade is None:
        in_trade = [False] * n
    return pd.DataFrame({
        "time_utc": times,
        "equity": equities,
        "in_trade": in_trade,
    })


# ============================================================================
# aggregate_fold_metrics
# ============================================================================


class TestAggregateFoldMetrics:
    """#042 — aggregate_fold_metrics: mean/std over folds."""

    def test_three_folds_mean_std_correct(self):
        """AC: 3 folds synthétiques → mean et std (ddof=1) corrects."""
        folds = [
            _make_fold_metrics(net_pnl=0.10, max_drawdown=0.05, n_trades=10),
            _make_fold_metrics(net_pnl=0.20, max_drawdown=0.10, n_trades=20),
            _make_fold_metrics(net_pnl=0.30, max_drawdown=0.15, n_trades=30),
        ]
        result = aggregate_fold_metrics(folds)

        # net_pnl
        expected_mean = np.mean([0.10, 0.20, 0.30])
        expected_std = np.std([0.10, 0.20, 0.30], ddof=1)
        assert result["net_pnl_mean"] == pytest.approx(expected_mean)
        assert result["net_pnl_std"] == pytest.approx(expected_std)

        # max_drawdown
        expected_mdd_mean = np.mean([0.05, 0.10, 0.15])
        expected_mdd_std = np.std([0.05, 0.10, 0.15], ddof=1)
        assert result["max_drawdown_mean"] == pytest.approx(expected_mdd_mean)
        assert result["max_drawdown_std"] == pytest.approx(expected_mdd_std)

        # n_trades (int, but still aggregated as float64)
        expected_nt_mean = np.mean([10.0, 20.0, 30.0])
        expected_nt_std = np.std([10.0, 20.0, 30.0], ddof=1)
        assert result["n_trades_mean"] == pytest.approx(expected_nt_mean)
        assert result["n_trades_std"] == pytest.approx(expected_nt_std)

    def test_all_trading_metrics_present(self):
        """All expected trading metric keys appear in result."""
        folds = [_make_fold_metrics(), _make_fold_metrics()]
        result = aggregate_fold_metrics(folds)

        for key in TRADING_KEYS:
            assert f"{key}_mean" in result, f"Missing {key}_mean"
            assert f"{key}_std" in result, f"Missing {key}_std"

    def test_excluded_keys_absent(self):
        """AC: excluded keys (sharpe_per_trade, n_samples_*) absent from aggregate."""
        folds = [
            _make_fold_metrics(),
            _make_fold_metrics(),
        ]
        # Artificially add excluded keys to fold dicts
        for f in folds:
            f["n_samples_train"] = 100
            f["n_samples_val"] = 20
            f["n_samples_test"] = 30
        result = aggregate_fold_metrics(folds)

        for key in EXCLUDED_KEYS:
            assert f"{key}_mean" not in result, f"{key}_mean should be excluded"
            assert f"{key}_std" not in result, f"{key}_std should be excluded"

    def test_prediction_metrics_aggregated(self):
        """Prediction metrics (mae, rmse, etc.) are included when present."""
        folds = [
            _make_fold_metrics(mae=0.01, rmse=0.02, directional_accuracy=0.55,
                               spearman_ic=0.3),
            _make_fold_metrics(mae=0.03, rmse=0.04, directional_accuracy=0.65,
                               spearman_ic=0.5),
            _make_fold_metrics(mae=0.02, rmse=0.03, directional_accuracy=0.60,
                               spearman_ic=0.4),
        ]
        result = aggregate_fold_metrics(folds)

        assert result["mae_mean"] == pytest.approx(np.mean([0.01, 0.03, 0.02]))
        assert result["mae_std"] == pytest.approx(np.std([0.01, 0.03, 0.02], ddof=1))
        assert result["spearman_ic_mean"] == pytest.approx(np.mean([0.3, 0.5, 0.4]))

    def test_null_handling_omits_none(self):
        """AC: folds with metric=None are omitted from mean/std."""
        folds = [
            _make_fold_metrics(sharpe=1.0, profit_factor=2.0),
            _make_fold_metrics(sharpe=None, profit_factor=3.0),
            _make_fold_metrics(sharpe=3.0, profit_factor=None),
        ]
        result = aggregate_fold_metrics(folds)

        # sharpe: only fold 0 and 2 → [1.0, 3.0]
        assert result["sharpe_mean"] == pytest.approx(np.mean([1.0, 3.0]))
        assert result["sharpe_std"] == pytest.approx(np.std([1.0, 3.0], ddof=1))

        # profit_factor: only fold 0 and 1 → [2.0, 3.0]
        assert result["profit_factor_mean"] == pytest.approx(np.mean([2.0, 3.0]))
        assert result["profit_factor_std"] == pytest.approx(np.std([2.0, 3.0], ddof=1))

    def test_all_none_metric_yields_none(self):
        """If all folds have None for a metric, mean/std are None."""
        folds = [
            _make_fold_metrics(sharpe=None),
            _make_fold_metrics(sharpe=None),
        ]
        result = aggregate_fold_metrics(folds)
        assert result["sharpe_mean"] is None
        assert result["sharpe_std"] is None

    def test_single_fold(self):
        """Single fold: mean = value, std = NaN (ddof=1 on 1 sample)."""
        folds = [_make_fold_metrics(net_pnl=0.15)]
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result = aggregate_fold_metrics(folds)
        assert result["net_pnl_mean"] == pytest.approx(0.15)
        # std with ddof=1 on 1 element is NaN
        net_pnl_std = result["net_pnl_std"]
        assert net_pnl_std is not None
        assert math.isnan(net_pnl_std)

    def test_single_non_none_among_nones(self):
        """One non-None value among Nones: mean = value, std = NaN."""
        folds = [
            _make_fold_metrics(sharpe=None),
            _make_fold_metrics(sharpe=2.5),
            _make_fold_metrics(sharpe=None),
        ]
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result = aggregate_fold_metrics(folds)
        assert result["sharpe_mean"] == pytest.approx(2.5)
        sharpe_std = result["sharpe_std"]
        assert sharpe_std is not None
        assert math.isnan(sharpe_std)

    def test_float64_precision(self):
        """Results are float64."""
        folds = [_make_fold_metrics(), _make_fold_metrics()]
        result = aggregate_fold_metrics(folds)
        for key, val in result.items():
            if val is not None:
                assert isinstance(val, float), f"{key} should be float, got {type(val)}"

    def test_empty_fold_list_raises(self):
        """Empty fold list → ValueError."""
        with pytest.raises(ValueError, match="fold_metrics_list"):
            aggregate_fold_metrics([])

    def test_two_folds_exact_values(self):
        """Verify exact mean/std for 2 folds."""
        folds = [
            _make_fold_metrics(net_pnl=0.10, exposure_time_frac=0.4),
            _make_fold_metrics(net_pnl=0.20, exposure_time_frac=0.6),
        ]
        result = aggregate_fold_metrics(folds)
        assert result["net_pnl_mean"] == pytest.approx(0.15)
        assert result["net_pnl_std"] == pytest.approx(
            np.std([0.10, 0.20], ddof=1)
        )
        assert result["exposure_time_frac_mean"] == pytest.approx(0.5)


# ============================================================================
# stitch_equity_curves
# ============================================================================


class TestStitchEquityCurves:
    """#042 — stitch_equity_curves: continuation stitching."""

    def test_two_folds_continuation(self):
        """AC: E_start[k+1] == E_end[k]."""
        ec0 = _make_equity_df([1.0, 1.1, 1.2], start="2024-01-01")
        ec1 = _make_equity_df([1.0, 1.05, 1.1], start="2024-01-04")

        stitched = stitch_equity_curves([ec0, ec1])

        # Fold 0: unchanged (starts at 1.0, ends at 1.2)
        fold0 = stitched[stitched["fold"] == 0]
        assert fold0["equity"].iloc[0] == pytest.approx(1.0)
        assert fold0["equity"].iloc[-1] == pytest.approx(1.2)

        # Fold 1: rescaled so start = 1.2 (E_end of fold 0)
        fold1 = stitched[stitched["fold"] == 1]
        assert fold1["equity"].iloc[0] == pytest.approx(1.2)
        # Original fold 1 ends at 1.1 = 1.1x start → rescaled end = 1.2 * 1.1 = 1.32
        assert fold1["equity"].iloc[-1] == pytest.approx(1.2 * 1.1)

    def test_three_folds_chain(self):
        """Three folds chained: E_start[k+1] == E_end[k]."""
        ec0 = _make_equity_df([1.0, 1.5], start="2024-01-01")
        ec1 = _make_equity_df([2.0, 3.0], start="2024-02-01")
        ec2 = _make_equity_df([1.0, 0.8], start="2024-03-01")

        stitched = stitch_equity_curves([ec0, ec1, ec2])

        # Fold 0 ends at 1.5
        fold0 = stitched[stitched["fold"] == 0]
        assert fold0["equity"].iloc[-1] == pytest.approx(1.5)

        # Fold 1 starts at 1.5, ratio = 3.0/2.0 = 1.5 → end = 1.5 * 1.5 = 2.25
        fold1 = stitched[stitched["fold"] == 1]
        assert fold1["equity"].iloc[0] == pytest.approx(1.5)
        assert fold1["equity"].iloc[-1] == pytest.approx(2.25)

        # Fold 2 starts at 2.25, ratio = 0.8/1.0 = 0.8 → end = 2.25 * 0.8 = 1.8
        fold2 = stitched[stitched["fold"] == 2]
        assert fold2["equity"].iloc[0] == pytest.approx(2.25)
        assert fold2["equity"].iloc[-1] == pytest.approx(1.8)

    def test_fold_column_present(self):
        """Stitched result has 'fold' column with 0-based indices."""
        ec0 = _make_equity_df([1.0, 1.1], start="2024-01-01")
        ec1 = _make_equity_df([1.0, 1.2], start="2024-02-01")

        stitched = stitch_equity_curves([ec0, ec1])
        assert "fold" in stitched.columns
        assert set(stitched["fold"].unique()) == {0, 1}

    def test_columns_present(self):
        """Stitched result contains required columns."""
        ec0 = _make_equity_df([1.0, 1.1], start="2024-01-01")
        stitched = stitch_equity_curves([ec0])
        assert set(stitched.columns) >= {"time_utc", "equity", "in_trade", "fold"}

    def test_single_fold_no_rescaling(self):
        """Single fold: no rescaling needed."""
        ec0 = _make_equity_df([1.0, 1.5, 2.0], start="2024-01-01")
        stitched = stitch_equity_curves([ec0])
        assert stitched["equity"].iloc[0] == pytest.approx(1.0)
        assert stitched["equity"].iloc[-1] == pytest.approx(2.0)
        assert all(stitched["fold"] == 0)

    def test_export_csv(self, tmp_path):
        """AC: equity curve exportable to CSV with correct columns."""
        ec0 = _make_equity_df([1.0, 1.1], start="2024-01-01")
        ec1 = _make_equity_df([1.0, 1.2], start="2024-02-01")

        stitched = stitch_equity_curves([ec0, ec1])
        csv_path = tmp_path / "equity_curve.csv"
        stitched.to_csv(csv_path, index=False)

        loaded = pd.read_csv(csv_path)
        assert set(loaded.columns) >= {"time_utc", "equity", "in_trade", "fold"}
        assert len(loaded) == 4

    def test_gap_detection_warning(self, caplog):
        """AC: gaps inter-fold → warning emitted and equity constant during gap."""
        # Fold 0 ends 2024-01-03, fold 1 starts 2024-01-10 → gap
        ec0 = _make_equity_df([1.0, 1.2], start="2024-01-01", freq="1D")
        ec1 = _make_equity_df([1.0, 1.1], start="2024-01-10", freq="1D")

        with caplog.at_level(logging.WARNING):
            stitched = stitch_equity_curves([ec0, ec1])

        # Warning should be emitted
        assert any("gap" in msg.lower() for msg in caplog.messages)

        # Gap rows should have constant equity = E_end[fold0]
        fold0_end = stitched[stitched["fold"] == 0]["equity"].iloc[-1]
        fold1_start = stitched[stitched["fold"] == 1]["equity"].iloc[0]
        assert fold1_start == pytest.approx(fold0_end)

    def test_empty_folds_list_raises(self):
        """Empty fold equities list → ValueError."""
        with pytest.raises(ValueError, match="fold_equities"):
            stitch_equity_curves([])

    def test_in_trade_preserved(self):
        """in_trade column is preserved through stitching."""
        ec0 = _make_equity_df(
            [1.0, 1.1, 1.2],
            start="2024-01-01",
            in_trade=[True, False, True],
        )
        stitched = stitch_equity_curves([ec0])
        assert list(stitched["in_trade"]) == [True, False, True]

    def test_missing_columns_raises(self):
        """Missing required columns → ValueError."""
        df = pd.DataFrame({"equity": [1.0, 1.1]})
        with pytest.raises(ValueError, match="time_utc"):
            stitch_equity_curves([df])

    def test_missing_equity_raises(self):
        """Missing equity column → ValueError."""
        df = pd.DataFrame({
            "time_utc": pd.date_range("2024-01-01", periods=2, freq="1h"),
            "in_trade": [False, False],
        })
        with pytest.raises(ValueError, match="equity"):
            stitch_equity_curves([df])

    def test_equity_starting_at_zero_raises(self):
        """Fold equity starting at 0.0 → ValueError (cannot rescale)."""
        ec0 = _make_equity_df([1.0, 1.2], start="2024-01-01")
        ec1 = _make_equity_df([0.0, 0.5], start="2024-02-01")
        with pytest.raises(ValueError, match="equity starting at 0.0"):
            stitch_equity_curves([ec0, ec1])


# ============================================================================
# check_acceptance_criteria
# ============================================================================


class TestCheckAcceptanceCriteria:
    """#042 — check_acceptance_criteria: §14.4 warnings."""

    def test_warning_net_pnl_negative(self):
        """AC: warning if net_pnl_mean <= 0."""
        agg = {"net_pnl_mean": -0.05, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.10}
        notes = check_acceptance_criteria(agg, mdd_cap=0.25)
        assert any("net_pnl" in n.lower() for n in notes)

    def test_warning_net_pnl_zero(self):
        """AC: warning if net_pnl_mean == 0."""
        agg = {"net_pnl_mean": 0.0, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.10}
        notes = check_acceptance_criteria(agg, mdd_cap=0.25)
        assert any("net_pnl" in n.lower() for n in notes)

    def test_warning_profit_factor_below_one(self):
        """AC: warning if profit_factor_mean <= 1.0."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": 0.8,
               "max_drawdown_mean": 0.10}
        notes = check_acceptance_criteria(agg, mdd_cap=0.25)
        assert any("profit_factor" in n.lower() for n in notes)

    def test_warning_profit_factor_exactly_one(self):
        """AC: warning if profit_factor_mean == 1.0."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": 1.0,
               "max_drawdown_mean": 0.10}
        notes = check_acceptance_criteria(agg, mdd_cap=0.25)
        assert any("profit_factor" in n.lower() for n in notes)

    def test_warning_mdd_exceeds_cap(self):
        """AC: warning if max_drawdown_mean >= mdd_cap."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.30}
        notes = check_acceptance_criteria(agg, mdd_cap=0.25)
        assert any("max_drawdown" in n.lower() or "mdd" in n.lower()
                    for n in notes)

    def test_warning_mdd_equals_cap(self):
        """AC: warning if max_drawdown_mean == mdd_cap."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.25}
        notes = check_acceptance_criteria(agg, mdd_cap=0.25)
        assert any("max_drawdown" in n.lower() or "mdd" in n.lower()
                    for n in notes)

    def test_no_warnings_healthy_aggregate(self):
        """Healthy aggregate → empty list."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.10}
        notes = check_acceptance_criteria(agg, mdd_cap=0.25)
        assert notes == []

    def test_multiple_warnings(self):
        """Multiple conditions triggered → multiple notes."""
        agg = {"net_pnl_mean": -0.05, "profit_factor_mean": 0.5,
               "max_drawdown_mean": 0.30}
        notes = check_acceptance_criteria(agg, mdd_cap=0.25)
        assert len(notes) >= 3

    def test_none_metrics_skipped(self):
        """If a metric is None in aggregate, skip its check."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": None,
               "max_drawdown_mean": 0.10}
        notes = check_acceptance_criteria(agg, mdd_cap=0.25)
        # No warning for profit_factor since it's None
        assert not any("profit_factor" in n.lower() for n in notes)

    def test_warnings_logged(self, caplog):
        """AC: warnings are also logged via logging.warning."""
        agg = {"net_pnl_mean": -0.05, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.10}
        with caplog.at_level(logging.WARNING):
            check_acceptance_criteria(agg, mdd_cap=0.25)
        assert any("net_pnl" in msg.lower() for msg in caplog.messages)

    def test_mdd_cap_validation(self):
        """mdd_cap must be > 0."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.10}
        with pytest.raises(ValueError, match="mdd_cap"):
            check_acceptance_criteria(agg, mdd_cap=0.0)

    def test_mdd_cap_negative_raises(self):
        """mdd_cap < 0 → ValueError."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.10}
        with pytest.raises(ValueError, match="mdd_cap"):
            check_acceptance_criteria(agg, mdd_cap=-0.1)

    def test_mdd_cap_nan_raises(self):
        """mdd_cap=NaN → ValueError."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.10}
        with pytest.raises(ValueError, match="mdd_cap"):
            check_acceptance_criteria(agg, mdd_cap=float("nan"))

    def test_mdd_cap_inf_raises(self):
        """mdd_cap=inf → ValueError."""
        agg = {"net_pnl_mean": 0.10, "profit_factor_mean": 1.5,
               "max_drawdown_mean": 0.10}
        with pytest.raises(ValueError, match="mdd_cap"):
            check_acceptance_criteria(agg, mdd_cap=float("inf"))


# ============================================================================
# derive_comparison_type
# ============================================================================


class TestDeriveComparisonType:
    """#042 — derive_comparison_type: strategy name → comparison type."""

    def test_buy_hold_contextual(self):
        """AC: buy_hold → contextual."""
        assert derive_comparison_type("buy_hold") == "contextual"

    def test_no_trade_go_nogo(self):
        """AC: no_trade → go_nogo."""
        assert derive_comparison_type("no_trade") == "go_nogo"

    def test_sma_rule_go_nogo(self):
        """sma_rule → go_nogo."""
        assert derive_comparison_type("sma_rule") == "go_nogo"

    def test_xgboost_go_nogo(self):
        """xgboost_reg → go_nogo."""
        assert derive_comparison_type("xgboost_reg") == "go_nogo"

    def test_empty_string_raises(self):
        """Empty strategy_name → ValueError."""
        with pytest.raises(ValueError, match="strategy_name"):
            derive_comparison_type("")
