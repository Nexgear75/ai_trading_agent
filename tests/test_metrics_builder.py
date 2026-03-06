"""Tests for metrics builder — ai_trading.artifacts.metrics_builder.

Task #046 — WS-11.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from ai_trading.artifacts.metrics_builder import (
    build_metrics,
    write_fold_metrics,
    write_metrics,
)

# ---------------------------------------------------------------------------
# Path to the metrics JSON schema
# ---------------------------------------------------------------------------

SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "specifications"
    / "metrics.schema.json"
)


@pytest.fixture
def metrics_schema() -> dict:
    """Load the metrics JSON schema."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helpers — minimal valid inputs
# ---------------------------------------------------------------------------


def _minimal_strategy_info() -> dict:
    """Return a minimal valid strategy_info dict."""
    return {
        "strategy_type": "model",
        "name": "xgboost_reg",
        "output_type": "regression",
    }


def _minimal_prediction() -> dict:
    """Return a minimal valid prediction dict."""
    return {
        "mae": 0.0041,
        "rmse": 0.0062,
        "directional_accuracy": 0.53,
        "spearman_ic": 0.06,
    }


def _minimal_trading() -> dict:
    """Return a minimal valid trading dict."""
    return {
        "net_pnl": 0.021,
        "net_return": 0.021,
        "max_drawdown": 0.08,
        "sharpe": 0.9,
        "profit_factor": 1.12,
        "hit_rate": 0.54,
        "n_trades": 38,
        "avg_trade_return": 0.0006,
        "median_trade_return": 0.0003,
        "exposure_time_frac": 0.52,
        "sharpe_per_trade": 0.12,
    }


def _minimal_threshold() -> dict:
    """Return a minimal valid threshold dict."""
    return {
        "method": "quantile_grid",
        "theta": 0.0012,
        "selected_quantile": 0.9,
    }


def _minimal_period_test() -> dict:
    """Return a minimal valid period_test dict."""
    return {
        "start_utc": "2024-06-29T04:00:00Z",
        "end_utc": "2024-07-29T03:00:00Z",
    }


def _minimal_fold_data(fold_id: int = 0) -> dict:
    """Return a minimal valid fold data dict."""
    return {
        "fold_id": fold_id,
        "period_test": _minimal_period_test(),
        "threshold": _minimal_threshold(),
        "prediction": _minimal_prediction(),
        "n_samples_train": 3648,
        "n_samples_val": 912,
        "n_samples_test": 720,
        "trading": _minimal_trading(),
    }


def _minimal_aggregate_data() -> dict:
    """Return a minimal valid aggregate_data dict."""
    return {
        "prediction": {
            "mean": {
                "mae": 0.0041,
                "rmse": 0.0062,
                "directional_accuracy": 0.53,
                "spearman_ic": 0.06,
            },
            "std": {
                "mae": 0.0,
                "rmse": 0.0,
                "directional_accuracy": 0.0,
                "spearman_ic": 0.0,
            },
        },
        "trading": {
            "mean": {
                "net_pnl": 0.021,
                "net_return": 0.021,
                "max_drawdown": 0.08,
                "sharpe": 0.9,
                "profit_factor": 1.12,
                "hit_rate": 0.54,
                "n_trades": 38,
                "avg_trade_return": 0.0006,
                "median_trade_return": 0.0003,
                "exposure_time_frac": 0.52,
            },
            "std": {
                "net_pnl": 0.0,
                "net_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe": 0.0,
                "profit_factor": 0.0,
                "hit_rate": 0.0,
                "n_trades": 0.0,
                "avg_trade_return": 0.0,
                "median_trade_return": 0.0,
                "exposure_time_frac": 0.0,
            },
        },
    }


# ===================================================================
# AC-1: Module exists and is importable
# ===================================================================


class TestImportable:
    """#046 — AC-1: Module is importable."""

    def test_import_build_metrics(self):
        """build_metrics is importable from ai_trading.artifacts.metrics_builder."""
        from ai_trading.artifacts.metrics_builder import build_metrics

        assert callable(build_metrics)

    def test_import_write_metrics(self):
        """write_metrics is importable from ai_trading.artifacts.metrics_builder."""
        from ai_trading.artifacts.metrics_builder import write_metrics

        assert callable(write_metrics)

    def test_import_write_fold_metrics(self):
        """write_fold_metrics is importable from ai_trading.artifacts.metrics_builder."""
        from ai_trading.artifacts.metrics_builder import write_fold_metrics

        assert callable(write_fold_metrics)


# ===================================================================
# AC-2: JSON global metrics.json valid against schema
# ===================================================================


class TestSchemaValidation:
    """#046 — AC-2: JSON global validates against metrics.schema.json."""

    def test_single_fold_validates(self, metrics_schema):
        """Single-fold metrics dict validates against the JSON schema."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        jsonschema.validate(instance=result, schema=metrics_schema)

    def test_multi_fold_validates(self, metrics_schema):
        """Multi-fold metrics dict validates against the JSON schema."""
        folds = [_minimal_fold_data(i) for i in range(3)]
        agg = _minimal_aggregate_data()
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=folds,
            aggregate_data=agg,
        )
        jsonschema.validate(instance=result, schema=metrics_schema)

    def test_baseline_strategy_validates(self, metrics_schema):
        """Baseline strategy validates against schema."""
        strategy = {"strategy_type": "baseline", "name": "buy_hold", "output_type": "signal"}
        result = build_metrics(
            run_id="20260227_120000_buy_hold",
            strategy_info=strategy,
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        jsonschema.validate(instance=result, schema=metrics_schema)

    def test_threshold_none_validates(self, metrics_schema):
        """Fold with threshold method 'none' and null theta validates."""
        fold = _minimal_fold_data(0)
        fold["threshold"] = {"method": "none", "theta": None, "selected_quantile": None}
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[fold],
            aggregate_data=_minimal_aggregate_data(),
        )
        jsonschema.validate(instance=result, schema=metrics_schema)

    def test_zero_trades_validates(self, metrics_schema):
        """Fold with 0 trades and all nullable trading metrics as None."""
        fold = _minimal_fold_data(0)
        fold["trading"] = {
            "net_pnl": 0.0,
            "net_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe": None,
            "profit_factor": None,
            "hit_rate": None,
            "n_trades": 0,
            "avg_trade_return": None,
            "median_trade_return": None,
            "exposure_time_frac": 0.0,
            "sharpe_per_trade": None,
        }
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[fold],
            aggregate_data=_minimal_aggregate_data(),
        )
        jsonschema.validate(instance=result, schema=metrics_schema)

    def test_aggregate_with_notes_validates(self, metrics_schema):
        """Aggregate with optional 'notes' field validates."""
        agg = _minimal_aggregate_data()
        agg["notes"] = "Single fold in this example."
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=agg,
        )
        jsonschema.validate(instance=result, schema=metrics_schema)

    def test_aggregate_with_comparison_type_validates(self, metrics_schema):
        """Aggregate with optional 'comparison_type' validates."""
        agg = _minimal_aggregate_data()
        agg["comparison_type"] = "go_nogo"
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=agg,
        )
        jsonschema.validate(instance=result, schema=metrics_schema)


# ===================================================================
# AC-3: Fold metrics files in folds/fold_XX/ are coherent
# ===================================================================


class TestFoldMetricsCoherence:
    """#046 — AC-3: metrics_fold.json is coherent with global metrics.json."""

    def test_write_fold_metrics_creates_file(self, tmp_path):
        """write_fold_metrics creates metrics_fold.json in the fold directory."""
        fold_dir = tmp_path / "folds" / "fold_00"
        fold_dir.mkdir(parents=True)
        fold_data = _minimal_fold_data(0)
        write_fold_metrics(fold_data, fold_dir)
        output_path = fold_dir / "metrics_fold.json"
        assert output_path.exists()

    def test_fold_metrics_content_matches_input(self, tmp_path):
        """Content of metrics_fold.json matches the input fold_data."""
        fold_dir = tmp_path / "folds" / "fold_00"
        fold_dir.mkdir(parents=True)
        fold_data = _minimal_fold_data(0)
        write_fold_metrics(fold_data, fold_dir)
        output_path = fold_dir / "metrics_fold.json"
        loaded = json.loads(output_path.read_text(encoding="utf-8"))
        assert loaded == fold_data

    def test_fold_metrics_coherent_with_global(self, tmp_path):
        """Each fold in global metrics.json matches the individual fold file."""
        folds = [_minimal_fold_data(i) for i in range(2)]
        global_metrics = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=folds,
            aggregate_data=_minimal_aggregate_data(),
        )
        # Write global
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        write_metrics(global_metrics, run_dir)
        # Write per-fold
        for fold_data in folds:
            fold_id = fold_data["fold_id"]
            fold_dir = run_dir / "folds" / f"fold_{fold_id:02d}"
            fold_dir.mkdir(parents=True)
            write_fold_metrics(fold_data, fold_dir)

        # Verify coherence
        global_loaded = json.loads(
            (run_dir / "metrics.json").read_text(encoding="utf-8")
        )
        for fold_entry in global_loaded["folds"]:
            fid = fold_entry["fold_id"]
            fold_file = run_dir / "folds" / f"fold_{fid:02d}" / "metrics_fold.json"
            fold_loaded = json.loads(fold_file.read_text(encoding="utf-8"))
            assert fold_loaded == fold_entry


# ===================================================================
# AC-4: n_samples_train, n_samples_val, n_samples_test present
# ===================================================================


class TestNSamplesFields:
    """#046 — AC-4: n_samples fields present per fold."""

    def test_n_samples_fields_present(self):
        """Each fold in the output contains n_samples_train/val/test."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        fold = result["folds"][0]
        assert "n_samples_train" in fold
        assert "n_samples_val" in fold
        assert "n_samples_test" in fold

    def test_n_samples_values_correct(self):
        """n_samples values match input."""
        fold_data = _minimal_fold_data(0)
        fold_data["n_samples_train"] = 5000
        fold_data["n_samples_val"] = 1200
        fold_data["n_samples_test"] = 800
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[fold_data],
            aggregate_data=_minimal_aggregate_data(),
        )
        fold = result["folds"][0]
        assert fold["n_samples_train"] == 5000
        assert fold["n_samples_val"] == 1200
        assert fold["n_samples_test"] == 800

    def test_n_samples_are_integers(self):
        """n_samples fields are integers."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        fold = result["folds"][0]
        assert isinstance(fold["n_samples_train"], int)
        assert isinstance(fold["n_samples_val"], int)
        assert isinstance(fold["n_samples_test"], int)


# ===================================================================
# AC-5: Metrics are float64
# ===================================================================


class TestFloat64Metrics:
    """#046 — AC-5: Numeric metrics are float (float64 precision)."""

    def test_prediction_metrics_are_float(self):
        """Prediction metrics in output are Python floats."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        pred = result["folds"][0]["prediction"]
        for key in ("mae", "rmse", "directional_accuracy"):
            assert isinstance(pred[key], float), f"{key} should be float"

    def test_trading_metrics_are_float(self):
        """Trading metrics in output are Python floats (except n_trades)."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        trading = result["folds"][0]["trading"]
        float_keys = [
            "net_pnl", "net_return", "max_drawdown", "sharpe",
            "profit_factor", "hit_rate", "avg_trade_return",
            "median_trade_return", "exposure_time_frac", "sharpe_per_trade",
        ]
        for key in float_keys:
            val = trading[key]
            if val is not None:
                assert isinstance(val, float), f"trading.{key} should be float"

    def test_n_trades_is_int(self):
        """n_trades is an integer, not float."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        assert isinstance(result["folds"][0]["trading"]["n_trades"], int)

    def test_aggregate_means_are_float(self):
        """Aggregate mean values are float."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        for key, val in result["aggregate"]["prediction"]["mean"].items():
            if val is not None:
                assert isinstance(val, float), f"aggregate.prediction.mean.{key}"
        for key, val in result["aggregate"]["trading"]["mean"].items():
            if val is not None:
                assert isinstance(val, float), f"aggregate.trading.mean.{key}"

    def test_aggregate_stds_are_float(self):
        """Aggregate std values are float."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        for key, val in result["aggregate"]["prediction"]["std"].items():
            if val is not None:
                assert isinstance(val, float), f"aggregate.prediction.std.{key}"
        for key, val in result["aggregate"]["trading"]["std"].items():
            if val is not None:
                assert isinstance(val, float), f"aggregate.trading.std.{key}"


# ===================================================================
# AC-6: Integration test — full build → write → validate
# ===================================================================


class TestIntegration:
    """#046 — AC-6: End-to-end integration with synthetic data."""

    def test_full_pipeline_single_fold(self, tmp_path, metrics_schema):
        """Build, write global, write fold, reload and validate."""
        fold = _minimal_fold_data(0)
        metrics = build_metrics(
            run_id="20260301_090000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[fold],
            aggregate_data=_minimal_aggregate_data(),
        )
        run_dir = tmp_path / "run"
        write_metrics(metrics, run_dir)
        fold_dir = run_dir / "folds" / "fold_00"
        fold_dir.mkdir(parents=True)
        write_fold_metrics(fold, fold_dir)

        # Reload and validate
        global_path = run_dir / "metrics.json"
        assert global_path.exists()
        loaded = json.loads(global_path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=loaded, schema=metrics_schema)

        fold_path = fold_dir / "metrics_fold.json"
        assert fold_path.exists()
        fold_loaded = json.loads(fold_path.read_text(encoding="utf-8"))
        assert fold_loaded == loaded["folds"][0]

    def test_full_pipeline_multi_fold(self, tmp_path, metrics_schema):
        """Multi-fold end-to-end: build, write, reload, validate."""
        folds = [_minimal_fold_data(i) for i in range(3)]
        agg = _minimal_aggregate_data()
        metrics = build_metrics(
            run_id="20260301_090000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=folds,
            aggregate_data=agg,
        )
        run_dir = tmp_path / "run"
        write_metrics(metrics, run_dir)

        for fold_data in folds:
            fid = fold_data["fold_id"]
            fold_dir = run_dir / "folds" / f"fold_{fid:02d}"
            fold_dir.mkdir(parents=True)
            write_fold_metrics(fold_data, fold_dir)

        # Reload global
        loaded = json.loads(
            (run_dir / "metrics.json").read_text(encoding="utf-8")
        )
        jsonschema.validate(instance=loaded, schema=metrics_schema)
        assert len(loaded["folds"]) == 3

        # Verify each fold file
        for i in range(3):
            fold_file = run_dir / "folds" / f"fold_{i:02d}" / "metrics_fold.json"
            fold_loaded = json.loads(fold_file.read_text(encoding="utf-8"))
            assert fold_loaded == loaded["folds"][i]


# ===================================================================
# AC-7: Error / edge case scenarios
# ===================================================================


class TestStrictValidation:
    """#046 — AC-7: Error and edge cases."""

    def test_empty_run_id_raises(self):
        """Empty run_id raises ValueError."""
        with pytest.raises(ValueError, match="run_id"):
            build_metrics(
                run_id="",
                strategy_info=_minimal_strategy_info(),
                folds_data=[_minimal_fold_data(0)],
                aggregate_data=_minimal_aggregate_data(),
            )

    def test_empty_folds_raises(self):
        """Empty folds_data list raises ValueError."""
        with pytest.raises(ValueError, match="folds_data"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=_minimal_strategy_info(),
                folds_data=[],
                aggregate_data=_minimal_aggregate_data(),
            )

    def test_missing_strategy_type_raises(self):
        """Missing strategy_type key raises KeyError."""
        strategy = {"name": "xgboost_reg"}
        with pytest.raises(KeyError, match="strategy_type"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=strategy,
                folds_data=[_minimal_fold_data(0)],
                aggregate_data=_minimal_aggregate_data(),
            )

    def test_missing_strategy_name_raises(self):
        """Missing strategy name key raises KeyError."""
        strategy = {"strategy_type": "model"}
        with pytest.raises(KeyError, match="name"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=strategy,
                folds_data=[_minimal_fold_data(0)],
                aggregate_data=_minimal_aggregate_data(),
            )

    def test_missing_fold_field_raises(self):
        """Fold missing a required field raises KeyError."""
        fold = _minimal_fold_data(0)
        del fold["prediction"]
        with pytest.raises(KeyError, match="prediction"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=_minimal_strategy_info(),
                folds_data=[fold],
                aggregate_data=_minimal_aggregate_data(),
            )

    def test_missing_aggregate_prediction_raises(self):
        """Missing aggregate.prediction raises KeyError."""
        agg = _minimal_aggregate_data()
        del agg["prediction"]
        with pytest.raises(KeyError, match="prediction"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=_minimal_strategy_info(),
                folds_data=[_minimal_fold_data(0)],
                aggregate_data=agg,
            )

    def test_missing_aggregate_trading_raises(self):
        """Missing aggregate.trading raises KeyError."""
        agg = _minimal_aggregate_data()
        del agg["trading"]
        with pytest.raises(KeyError, match="trading"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=_minimal_strategy_info(),
                folds_data=[_minimal_fold_data(0)],
                aggregate_data=agg,
            )

    def test_duplicate_fold_ids_raises(self):
        """Duplicate fold_id values raise ValueError."""
        folds = [_minimal_fold_data(0), _minimal_fold_data(0)]
        with pytest.raises(ValueError, match="fold_id"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=_minimal_strategy_info(),
                folds_data=folds,
                aggregate_data=_minimal_aggregate_data(),
            )

    def test_missing_prediction_required_key_raises(self):
        """Missing required prediction sub-key (mae) raises KeyError."""
        fold = _minimal_fold_data(0)
        del fold["prediction"]["mae"]
        with pytest.raises(KeyError, match="mae"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=_minimal_strategy_info(),
                folds_data=[fold],
                aggregate_data=_minimal_aggregate_data(),
            )

    def test_missing_trading_required_key_raises(self):
        """Missing required trading sub-key (n_trades) raises KeyError."""
        fold = _minimal_fold_data(0)
        del fold["trading"]["n_trades"]
        with pytest.raises(KeyError, match="n_trades"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=_minimal_strategy_info(),
                folds_data=[fold],
                aggregate_data=_minimal_aggregate_data(),
            )

    def test_missing_prediction_directional_accuracy_raises(self):
        """Missing required prediction key directional_accuracy raises KeyError."""
        fold = _minimal_fold_data(0)
        del fold["prediction"]["directional_accuracy"]
        with pytest.raises(KeyError, match="directional_accuracy"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=_minimal_strategy_info(),
                folds_data=[fold],
                aggregate_data=_minimal_aggregate_data(),
            )

    def test_missing_trading_net_pnl_raises(self):
        """Missing required trading key net_pnl raises KeyError."""
        fold = _minimal_fold_data(0)
        del fold["trading"]["net_pnl"]
        with pytest.raises(KeyError, match="net_pnl"):
            build_metrics(
                run_id="20260227_120000_xgboost_reg",
                strategy_info=_minimal_strategy_info(),
                folds_data=[fold],
                aggregate_data=_minimal_aggregate_data(),
            )


# ===================================================================
# AC-8: Write functions — file I/O
# ===================================================================


class TestWriteFunctions:
    """#046 — AC-8: write_metrics and write_fold_metrics I/O."""

    def test_write_metrics_creates_file(self, tmp_path):
        """write_metrics creates metrics.json in run_dir."""
        metrics = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        run_dir = tmp_path / "run"
        write_metrics(metrics, run_dir)
        output_path = run_dir / "metrics.json"
        assert output_path.exists()

    def test_write_metrics_creates_parent_dirs(self, tmp_path):
        """write_metrics creates parent directories if needed."""
        metrics = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        run_dir = tmp_path / "deep" / "nested" / "run"
        write_metrics(metrics, run_dir)
        assert (run_dir / "metrics.json").exists()

    def test_write_metrics_valid_json(self, tmp_path):
        """metrics.json is valid JSON that round-trips."""
        metrics = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        run_dir = tmp_path / "run"
        write_metrics(metrics, run_dir)
        loaded = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
        assert loaded["run_id"] == "20260227_120000_xgboost_reg"

    def test_write_fold_metrics_creates_parent_dirs(self, tmp_path):
        """write_fold_metrics creates parent dirs if needed."""
        fold_dir = tmp_path / "folds" / "fold_00"
        write_fold_metrics(_minimal_fold_data(0), fold_dir)
        assert (fold_dir / "metrics_fold.json").exists()

    def test_write_fold_metrics_valid_json(self, tmp_path):
        """metrics_fold.json is valid JSON."""
        fold_dir = tmp_path / "folds" / "fold_00"
        fold_dir.mkdir(parents=True)
        write_fold_metrics(_minimal_fold_data(0), fold_dir)
        loaded = json.loads(
            (fold_dir / "metrics_fold.json").read_text(encoding="utf-8")
        )
        assert loaded["fold_id"] == 0

    def test_write_metrics_rejects_nan(self, tmp_path):
        """write_metrics rejects NaN values with allow_nan=False."""
        metrics = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        metrics["folds"][0]["prediction"]["mae"] = float("nan")
        with pytest.raises(ValueError):
            write_metrics(metrics, tmp_path / "run")

    def test_write_fold_metrics_rejects_nan(self, tmp_path):
        """write_fold_metrics rejects NaN values with allow_nan=False."""
        fold = _minimal_fold_data(0)
        fold["prediction"]["mae"] = float("nan")
        with pytest.raises(ValueError):
            write_fold_metrics(fold, tmp_path / "fold")

    def test_write_metrics_rejects_inf(self, tmp_path):
        """write_metrics rejects inf values with allow_nan=False."""
        metrics = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        metrics["folds"][0]["trading"]["net_pnl"] = float("inf")
        with pytest.raises(ValueError):
            write_metrics(metrics, tmp_path / "run")


# ===================================================================
# AC-9: build_metrics output structure
# ===================================================================


class TestBuildMetricsStructure:
    """#046 — AC-9: build_metrics output has correct top-level keys."""

    def test_top_level_keys(self):
        """Output has run_id, strategy, folds, aggregate."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        assert set(result.keys()) == {"run_id", "strategy", "folds", "aggregate"}

    def test_strategy_section(self):
        """Strategy section has strategy_type and name."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        assert result["strategy"]["strategy_type"] == "model"
        assert result["strategy"]["name"] == "xgboost_reg"

    def test_folds_is_list(self):
        """Folds is a list of dicts."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        assert isinstance(result["folds"], list)
        assert len(result["folds"]) == 1

    def test_aggregate_has_prediction_and_trading(self):
        """Aggregate block has prediction and trading sub-keys."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        agg = result["aggregate"]
        assert "prediction" in agg
        assert "trading" in agg
        assert "mean" in agg["prediction"]
        assert "std" in agg["prediction"]

    def test_run_id_passthrough(self):
        """run_id in output matches input."""
        result = build_metrics(
            run_id="my_custom_run_id_123",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        assert result["run_id"] == "my_custom_run_id_123"

    def test_json_serializable(self):
        """Output is JSON-serializable."""
        result = build_metrics(
            run_id="20260227_120000_xgboost_reg",
            strategy_info=_minimal_strategy_info(),
            folds_data=[_minimal_fold_data(0)],
            aggregate_data=_minimal_aggregate_data(),
        )
        # Should not raise
        json.dumps(result)
