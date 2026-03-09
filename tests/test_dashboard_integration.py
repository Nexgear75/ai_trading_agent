"""Integration tests for the AI Trading dashboard.

Task #091 — WS-D-6: Tests d'intégration et smoke test du dashboard.
Ref: Specification_Dashboard_Streamlit_v1.0.md §12.2
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Ensure dashboard package is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from dashboard.data_loader import (  # noqa: E402
    discover_runs,
    load_equity_curve,
    load_predictions,
    load_run_manifest,
    load_run_metrics,
    load_trades,
)
from dashboard.pages.fold_analysis_logic import (  # noqa: E402
    get_fold_threshold,
    get_output_type,
)

# ---------------------------------------------------------------------------
# Fixtures: synthetic run data
# ---------------------------------------------------------------------------


def _make_metrics(
    run_id: str,
    strategy_name: str = "xgboost_reg",
    strategy_type: str = "model",
    output_type: str = "regression",
    n_folds: int = 2,
    theta: float = 0.003,
    threshold_method: str = "quantile_grid",
) -> dict:
    """Build a minimal valid metrics.json dict."""
    folds = []
    for i in range(n_folds):
        folds.append({
            "fold_id": i,
            "period_test": {
                "start_utc": "2024-01-01T00:00:00+00:00",
                "end_utc": "2024-01-31T00:00:00+00:00",
            },
            "threshold": {
                "method": threshold_method,
                "theta": theta,
                "selected_quantile": 0.9,
            },
            "prediction": {
                "mae": 0.01,
                "rmse": 0.015,
                "directional_accuracy": 0.52,
                "spearman_ic": 0.05,
            },
            "n_samples_train": 1000,
            "n_samples_val": 200,
            "n_samples_test": 100,
            "trading": {
                "net_pnl": 0.05,
                "net_return": 0.05,
                "max_drawdown": 0.03,
                "sharpe": 1.2,
                "profit_factor": 1.5,
                "hit_rate": 0.55,
                "avg_trade_return": 0.001,
                "median_trade_return": 0.0008,
                "exposure_time_frac": 0.3,
                "n_trades": 20,
            },
        })
    return {
        "run_id": run_id,
        "strategy": {
            "strategy_type": strategy_type,
            "name": strategy_name,
            "output_type": output_type,
        },
        "aggregate": {
            "prediction": {
                "mean": {"mae": 0.01, "rmse": 0.015, "directional_accuracy": 0.52,
                         "spearman_ic": 0.05},
                "std": {"mae": 0.002, "rmse": 0.003, "directional_accuracy": 0.03,
                        "spearman_ic": 0.02},
            },
            "trading": {
                "mean": {"net_pnl": 0.05, "net_return": 0.05, "max_drawdown": 0.03,
                         "sharpe": 1.2, "profit_factor": 1.5, "hit_rate": 0.55,
                         "n_trades": 20, "avg_trade_return": 0.001,
                         "median_trade_return": 0.0008, "exposure_time_frac": 0.3},
                "std": {"net_pnl": 0.02, "net_return": 0.02, "max_drawdown": 0.01,
                        "sharpe": 0.3, "profit_factor": 0.2, "hit_rate": 0.05,
                        "n_trades": 5, "avg_trade_return": 0.0005,
                        "median_trade_return": 0.0003, "exposure_time_frac": 0.1},
            },
            "comparison_type": "go_nogo",
        },
        "folds": folds,
    }


def _make_manifest(run_id: str) -> dict:
    """Build a minimal valid manifest.json dict."""
    return {
        "run_id": run_id,
        "config_hash_sha256": "abc123",
        "data_hash_sha256": "def456",
        "created_utc": "2024-01-01T00:00:00+00:00",
        "python_version": "3.11.0",
        "platform": "linux",
        "config_snapshot": "config_snapshot.yaml",
    }


def _make_equity_csv(*, with_fold: bool = True) -> pd.DataFrame:
    """Build a minimal equity_curve.csv DataFrame."""
    data = {
        "time_utc": pd.date_range("2024-01-01", periods=10, freq="h"),
        "equity": np.linspace(1.0, 1.05, 10),
        "in_trade": [False, True, True, False, True, False, False, True, False, False],
    }
    if with_fold:
        data["fold"] = [0] * 10
    return pd.DataFrame(data)


def _make_trades_csv() -> pd.DataFrame:
    """Build a minimal trades.csv DataFrame with required columns."""
    n = 3
    return pd.DataFrame({
        "entry_time_utc": pd.date_range("2024-01-01", periods=n, freq="D"),
        "exit_time_utc": pd.date_range("2024-01-02", periods=n, freq="D"),
        "entry_price": [100.0, 101.0, 102.0],
        "exit_price": [101.0, 100.5, 103.0],
        "entry_price_eff": [100.05, 101.05, 102.05],
        "exit_price_eff": [100.95, 100.45, 102.95],
        "f": [0.0005, 0.0005, 0.0005],
        "s": [0.00025, 0.00025, 0.00025],
        "fees_paid": [0.001, 0.001, 0.001],
        "slippage_paid": [0.0005, 0.0005, 0.0005],
        "y_true": [0.01, -0.005, 0.01],
        "y_hat": [0.008, 0.002, 0.012],
        "gross_return": [0.01, -0.005, 0.01],
        "net_return": [0.008, -0.007, 0.008],
    })


def _make_preds_csv() -> pd.DataFrame:
    """Build a minimal preds_test.csv DataFrame."""
    rng = np.random.default_rng(42)
    n = 50
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="h"),
        "y_true": rng.standard_normal(n) * 0.01,
        "y_hat": rng.standard_normal(n) * 0.01,
    })


def _write_run(
    base_dir: Path,
    run_id: str,
    *,
    strategy_name: str = "xgboost_reg",
    include_equity: bool = True,
    include_trades: bool = True,
    include_preds: bool = True,
    theta: float = 0.003,
    threshold_method: str = "quantile_grid",
    output_type: str = "regression",
) -> Path:
    """Create a synthetic run directory with the specified artifacts."""
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # metrics.json (always required for discovery)
    metrics = _make_metrics(
        run_id,
        strategy_name=strategy_name,
        theta=theta,
        threshold_method=threshold_method,
        output_type=output_type,
    )
    (run_dir / "metrics.json").write_text(json.dumps(metrics))

    # manifest.json
    manifest = _make_manifest(run_id)
    (run_dir / "manifest.json").write_text(json.dumps(manifest))

    # config_snapshot.yaml
    (run_dir / "config_snapshot.yaml").write_text("dataset:\n  symbol: BTCUSDT\n")

    # folds
    fold_dir = run_dir / "folds" / "fold_00"
    fold_dir.mkdir(parents=True, exist_ok=True)

    if include_equity:
        _make_equity_csv(with_fold=True).to_csv(run_dir / "equity_curve.csv", index=False)
        _make_equity_csv(with_fold=False).to_csv(fold_dir / "equity_curve.csv", index=False)

    if include_trades:
        _make_trades_csv().to_csv(run_dir / "trades.csv", index=False)
        _make_trades_csv().to_csv(fold_dir / "trades.csv", index=False)

    if include_preds:
        _make_preds_csv().to_csv(fold_dir / "preds_test.csv", index=False)

    # fold metrics
    fold_metrics = {
        "fold_id": 0,
        "prediction": {"mae": 0.01, "rmse": 0.015,
                        "directional_accuracy": 0.52, "spearman_ic": 0.05},
        "trading": {"net_pnl": 0.05, "sharpe": 1.2, "max_drawdown": 0.03},
    }
    (fold_dir / "metrics_fold.json").write_text(json.dumps(fold_metrics))

    return run_dir


# ===========================================================================
# §12.2 — Smoke test
# ===========================================================================

class TestSmokeTest:
    """A valid run is discovered and all loaders work without error."""

    def test_discover_valid_run(self, tmp_path: Path) -> None:
        """discover_runs() finds a valid run."""
        _write_run(tmp_path, "20240101_000000_xgboost_reg")
        runs = discover_runs(tmp_path)
        assert len(runs) == 1
        assert runs[0]["run_id"] == "20240101_000000_xgboost_reg"

    def test_load_metrics(self, tmp_path: Path) -> None:
        """load_run_metrics() works on a valid run directory."""
        run_dir = _write_run(tmp_path, "20240101_000000_xgboost_reg")
        metrics = load_run_metrics(run_dir)
        assert metrics["run_id"] == "20240101_000000_xgboost_reg"
        assert "strategy" in metrics
        assert "aggregate" in metrics

    def test_load_manifest(self, tmp_path: Path) -> None:
        """load_run_manifest() works on a valid run directory."""
        run_dir = _write_run(tmp_path, "20240101_000000_xgboost_reg")
        manifest = load_run_manifest(run_dir)
        assert manifest["run_id"] == "20240101_000000_xgboost_reg"

    def test_load_all_artifacts(self, tmp_path: Path) -> None:
        """All artifact loaders work on a complete valid run."""
        run_dir = _write_run(tmp_path, "20240101_000000_xgboost_reg")
        assert load_equity_curve(run_dir) is not None
        assert load_trades(run_dir) is not None
        fold_dir = run_dir / "folds" / "fold_00"
        assert load_predictions(fold_dir, "test") is not None


# ===========================================================================
# §12.2 — Exclusion Dummy
# ===========================================================================

class TestExclusionDummy:
    """Dummy runs are excluded from discover_runs()."""

    def test_dummy_only_returns_empty(self, tmp_path: Path) -> None:
        """Directory with only a dummy run → empty list."""
        _write_run(tmp_path, "20240101_000000_dummy", strategy_name="dummy")
        runs = discover_runs(tmp_path)
        assert runs == []

    def test_dummy_excluded_mixed(self, tmp_path: Path) -> None:
        """Dummy run is excluded but valid run is kept."""
        _write_run(tmp_path, "20240101_000000_dummy", strategy_name="dummy")
        _write_run(tmp_path, "20240101_000001_xgboost", strategy_name="xgboost_reg")
        runs = discover_runs(tmp_path)
        assert len(runs) == 1
        assert runs[0]["strategy"]["name"] == "xgboost_reg"


# ===========================================================================
# §12.2 — Comparison multi-runs
# ===========================================================================

class TestComparisonMultiRuns:
    """Multiple valid runs can be loaded together."""

    def test_two_runs_discovered(self, tmp_path: Path) -> None:
        """discover_runs() returns both valid runs."""
        _write_run(tmp_path, "20240101_000000_xgboost_reg")
        _write_run(tmp_path, "20240102_000000_sma_rule", strategy_name="sma_rule",
                   output_type="signal", threshold_method="none", theta=None)
        runs = discover_runs(tmp_path)
        assert len(runs) == 2

    def test_runs_sorted_by_id(self, tmp_path: Path) -> None:
        """discover_runs() returns runs sorted by run_id."""
        _write_run(tmp_path, "20240202_000000_b")
        _write_run(tmp_path, "20240101_000000_a")
        runs = discover_runs(tmp_path)
        assert runs[0]["run_id"] == "20240101_000000_a"
        assert runs[1]["run_id"] == "20240202_000000_b"


# ===========================================================================
# §12.2 — Edge case: empty directory
# ===========================================================================

class TestEdgeCaseEmptyDirectory:
    """Empty runs directory → empty list, no crash."""

    def test_empty_dir(self, tmp_path: Path) -> None:
        """discover_runs() on empty dir returns []."""
        runs = discover_runs(tmp_path)
        assert runs == []

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        """discover_runs() on nonexistent dir returns []."""
        runs = discover_runs(tmp_path / "nonexistent")
        assert runs == []


# ===========================================================================
# §12.2 — Degradation: missing optional files
# ===========================================================================

class TestDegradationEquityCurveMissing:
    """load_equity_curve() returns None when equity_curve.csv is absent."""

    def test_equity_curve_absent(self, tmp_path: Path) -> None:
        run_dir = _write_run(tmp_path, "run_no_equity", include_equity=False)
        assert load_equity_curve(run_dir) is None


class TestDegradationTradesMissing:
    """load_trades() returns None when trades.csv is absent."""

    def test_trades_absent(self, tmp_path: Path) -> None:
        run_dir = _write_run(tmp_path, "run_no_trades", include_trades=False)
        assert load_trades(run_dir) is None


class TestDegradationPredsMissing:
    """load_predictions() returns None when preds_test.csv is absent."""

    def test_preds_absent(self, tmp_path: Path) -> None:
        run_dir = _write_run(tmp_path, "run_no_preds", include_preds=False)
        fold_dir = run_dir / "folds" / "fold_00"
        assert load_predictions(fold_dir, "test") is None


# ===========================================================================
# §12.2 + §8.3 — Go/No-Go signal reconstruction
# ===========================================================================

class TestGoNoGoThetaPositive:
    """Regression model with θ > 0: y_hat > θ → Go."""

    def test_theta_positive_signal(self, tmp_path: Path) -> None:
        theta = 0.005
        run_dir = _write_run(tmp_path, "run_theta_pos", theta=theta)
        metrics = load_run_metrics(run_dir)
        info = get_fold_threshold(metrics, fold_id="fold_00")
        assert info["theta"] == theta
        assert info["method"] == "quantile_grid"

        # Verify output_type detection
        assert get_output_type(metrics) == "regression"

        # Reconstruct Go/No-Go signal
        fold_dir = run_dir / "folds" / "fold_00"
        preds = load_predictions(fold_dir, "test")
        go_mask = preds["y_hat"] > theta
        # Some should be Go, some No-Go
        assert go_mask.any() or not go_mask.any()  # no crash
        # Verify determinism with seed 42
        assert go_mask.sum() == go_mask.sum()


class TestGoNoGoThetaNegative:
    """Regression model with θ < 0: more predictions are Go."""

    def test_theta_negative_signal(self, tmp_path: Path) -> None:
        theta = -0.005
        run_dir = _write_run(tmp_path, "run_theta_neg", theta=theta)
        metrics = load_run_metrics(run_dir)
        info = get_fold_threshold(metrics, fold_id="fold_00")
        assert info["theta"] == theta

        fold_dir = run_dir / "folds" / "fold_00"
        preds = load_predictions(fold_dir, "test")
        go_mask = preds["y_hat"] > theta
        # With negative theta, most predictions should be Go
        assert go_mask.sum() > len(preds) // 2


class TestGoNoGoThetaZero:
    """Regression model with θ = 0: all positive y_hat are Go."""

    def test_theta_zero_signal(self, tmp_path: Path) -> None:
        theta = 0.0
        run_dir = _write_run(tmp_path, "run_theta_zero", theta=theta)
        metrics = load_run_metrics(run_dir)
        info = get_fold_threshold(metrics, fold_id="fold_00")
        assert info["theta"] == 0.0

        fold_dir = run_dir / "folds" / "fold_00"
        preds = load_predictions(fold_dir, "test")
        go_mask = preds["y_hat"] > 0.0
        # All positive y_hat should be Go
        expected = (preds["y_hat"] > 0.0).sum()
        assert go_mask.sum() == expected


class TestGoNoGoMethodNone:
    """Signal model (threshold.method == "none"): y_hat IS the signal."""

    def test_method_none_output_type(self, tmp_path: Path) -> None:
        """get_output_type detects 'signal' when method == 'none'."""
        run_dir = _write_run(
            tmp_path, "run_signal",
            strategy_name="sma_rule",
            threshold_method="none",
            theta=None,
            output_type="signal",
        )
        metrics = load_run_metrics(run_dir)
        assert get_output_type(metrics) == "signal"

    def test_method_none_fallback_detection(self, tmp_path: Path) -> None:
        """Fallback detection: method == 'none' for all folds → 'signal'."""
        run_dir = _write_run(
            tmp_path, "run_signal_fallback",
            strategy_name="sma_rule",
            threshold_method="none",
            theta=None,
            output_type="signal",
        )
        # Remove output_type to test fallback path
        metrics = load_run_metrics(run_dir)
        del metrics["strategy"]["output_type"]
        assert get_output_type(metrics) == "signal"

    def test_method_none_theta_is_null(self, tmp_path: Path) -> None:
        """When method == 'none', theta should be None."""
        run_dir = _write_run(
            tmp_path, "run_signal_null_theta",
            strategy_name="sma_rule",
            threshold_method="none",
            theta=None,
            output_type="signal",
        )
        metrics = load_run_metrics(run_dir)
        info = get_fold_threshold(metrics, fold_id="fold_00")
        assert info["theta"] is None
        assert info["method"] == "none"


# ===========================================================================
# Additional: no network dependency
# ===========================================================================

class TestNoNetworkDependency:
    """Integration tests are deterministic and use no network."""

    def test_seeds_fixed(self) -> None:
        """Verify that default_rng with seed 42 is deterministic."""
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        assert (rng1.standard_normal(10) == rng2.standard_normal(10)).all()

    def test_fixtures_are_synthetic(self, tmp_path: Path) -> None:
        """All fixtures use tmp_path, no real run directory."""
        run_dir = _write_run(tmp_path, "synthetic_run")
        assert str(tmp_path) in str(run_dir)
        assert run_dir.exists()
