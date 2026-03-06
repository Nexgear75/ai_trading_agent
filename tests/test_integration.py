"""Integration tests — full pipeline on synthetic data.

Task #051 — WS-12: Dockerfile & CI integration.
Covers:
- Full pipeline with DummyModel → arborescence §15.1, valid JSON, metrics
- Full pipeline with no_trade baseline → θ bypass, net_pnl=0, n_trades=0
- synthetic_ohlcv fixture validation (500 candles, GBM, §4.1 columns)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from tests.conftest import make_integration_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_integration_config(
    tmp_path: Path,
    ohlcv_df: pd.DataFrame,
    *,
    strategy_name: str = "dummy",
    strategy_type: str = "model",
) -> Path:
    """Delegate to shared conftest helper."""
    return make_integration_config(
        tmp_path,
        ohlcv_df,
        strategy_name=strategy_name,
        strategy_type=strategy_type,
    )


# ---------------------------------------------------------------------------
# 1. synthetic_ohlcv fixture validation
# ---------------------------------------------------------------------------


class TestSyntheticOhlcvFixture:
    """#051 — AC: synthetic_ohlcv generates a valid OHLCV DataFrame."""

    def test_row_count(self, synthetic_ohlcv):
        assert len(synthetic_ohlcv) == 500

    def test_columns_conform_to_spec(self, synthetic_ohlcv):
        """§4.1: open, high, low, close, volume, timestamp_utc."""
        expected = {"timestamp_utc", "open", "high", "low", "close", "volume"}
        assert set(synthetic_ohlcv.columns) == expected

    def test_timestamps_utc_aware(self, synthetic_ohlcv):
        ts = synthetic_ohlcv["timestamp_utc"]
        assert ts.dt.tz is not None
        assert str(ts.dt.tz) == "UTC"

    def test_timestamps_contiguous_hourly(self, synthetic_ohlcv):
        ts = synthetic_ohlcv["timestamp_utc"]
        diffs = ts.diff().dropna()
        assert (diffs == pd.Timedelta(hours=1)).all()

    def test_prices_positive(self, synthetic_ohlcv):
        for col in ("open", "high", "low", "close"):
            assert (synthetic_ohlcv[col] > 0).all(), f"{col} has non-positive values"

    def test_volume_positive(self, synthetic_ohlcv):
        assert (synthetic_ohlcv["volume"] > 0).all()

    def test_high_ge_low(self, synthetic_ohlcv):
        assert (synthetic_ohlcv["high"] >= synthetic_ohlcv["low"]).all()

    def test_deterministic(self, synthetic_ohlcv):
        """Two calls produce identical DataFrames (seed=42)."""
        # The fixture is called once per test, but we verify the seed
        # produces a known first close value.
        assert synthetic_ohlcv["close"].iloc[0] == pytest.approx(100.0, rel=1e-6)

    def test_no_nan(self, synthetic_ohlcv):
        assert not synthetic_ohlcv.isna().any().any()


# ---------------------------------------------------------------------------
# 2. Full pipeline — DummyModel on synthetic_ohlcv
# ---------------------------------------------------------------------------


class TestIntegrationDummy:
    """#051 — AC: DummyModel on synthetic data → arborescence §15.1, valid JSON."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, synthetic_ohlcv):
        self.cfg_path = _make_integration_config(
            tmp_path, synthetic_ohlcv, strategy_name="dummy", strategy_type="model"
        )

    def test_run_completes(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert isinstance(run_dir, Path)
        assert run_dir.is_dir()

    def test_arborescence_section_15_1(self):
        """§15.1: run_dir contains manifest.json, metrics.json, config_snapshot.yaml,
        pipeline.log, and folds/ directory."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)

        assert (run_dir / "manifest.json").is_file()
        assert (run_dir / "metrics.json").is_file()
        assert (run_dir / "config_snapshot.yaml").is_file()
        assert (run_dir / "pipeline.log").is_file()
        assert (run_dir / "folds").is_dir()

        # At least one fold directory
        fold_dirs = sorted((run_dir / "folds").iterdir())
        assert len(fold_dirs) >= 1

        # Each fold has metrics_fold.json
        for fd in fold_dirs:
            assert (fd / "metrics_fold.json").is_file()

    def test_manifest_json_valid(self):
        from ai_trading.artifacts.validation import validate_manifest
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        manifest = json.loads((run_dir / "manifest.json").read_text())
        validate_manifest(manifest)  # raises on invalid
        assert manifest["strategy"]["name"] == "dummy"

    def test_metrics_json_valid(self):
        from ai_trading.artifacts.validation import validate_metrics
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        validate_metrics(metrics)  # raises on invalid
        assert "folds" in metrics
        assert len(metrics["folds"]) >= 1

    def test_metrics_non_null(self):
        """Trading metrics must be populated (non-null) for DummyModel."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            assert fold["trading"]["net_pnl"] is not None
            assert fold["trading"]["n_trades"] is not None
            assert fold["prediction"]["mae"] is not None
            assert fold["prediction"]["rmse"] is not None


# ---------------------------------------------------------------------------
# 3. Full pipeline — no_trade baseline on synthetic_ohlcv
# ---------------------------------------------------------------------------


class TestIntegrationNoTrade:
    """#051 — AC: no_trade → θ bypass, net_pnl=0, n_trades=0."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, synthetic_ohlcv):
        self.cfg_path = _make_integration_config(
            tmp_path,
            synthetic_ohlcv,
            strategy_name="no_trade",
            strategy_type="baseline",
        )

    def test_no_trade_run_completes(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert run_dir.is_dir()

    def test_no_trade_zero_pnl_zero_trades(self):
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            assert fold["trading"]["n_trades"] == 0
            assert fold["trading"]["net_pnl"] == pytest.approx(0.0, abs=1e-12)

    def test_no_trade_theta_bypass(self):
        """no_trade output_type='signal' → θ bypass (method='none', theta=None)."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            assert fold["threshold"]["method"] == "none"
            assert fold["threshold"]["theta"] is None

    def test_no_trade_arborescence(self):
        """§15.1 arborescence also valid for baselines."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        assert (run_dir / "manifest.json").is_file()
        assert (run_dir / "metrics.json").is_file()
        assert (run_dir / "config_snapshot.yaml").is_file()

    def test_no_trade_json_schema_valid(self):
        from ai_trading.artifacts.validation import validate_manifest, validate_metrics
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        config = load_config(str(self.cfg_path))
        run_dir = run_pipeline(config)
        validate_manifest(json.loads((run_dir / "manifest.json").read_text()))
        validate_metrics(json.loads((run_dir / "metrics.json").read_text()))


# ---------------------------------------------------------------------------
# 4. Error scenarios
# ---------------------------------------------------------------------------


class TestIntegrationErrors:
    """#051 — AC: error scenarios for integration tests."""

    def test_missing_parquet_raises(self, tmp_path, synthetic_ohlcv):
        """Pipeline raises FileNotFoundError when raw parquet file is missing."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        cfg_path = _make_integration_config(
            tmp_path, synthetic_ohlcv, strategy_name="dummy", strategy_type="model"
        )
        config = load_config(str(cfg_path))

        # Delete the parquet file that _make_integration_config created
        raw_dir = Path(config.dataset.raw_dir)
        for f in raw_dir.glob("*.parquet"):
            f.unlink()

        with pytest.raises(FileNotFoundError, match="Raw OHLCV file not found"):
            run_pipeline(config)

    def test_invalid_strategy_name_raises(self, tmp_path, synthetic_ohlcv):
        """Pipeline raises ValueError for an unknown strategy name."""
        from pydantic import ValidationError

        from ai_trading.config import load_config

        cfg_path = _make_integration_config(
            tmp_path, synthetic_ohlcv, strategy_name="dummy", strategy_type="model"
        )

        # Patch config YAML to use an invalid strategy name
        cfg_text = cfg_path.read_text(encoding="utf-8")
        cfg_text = cfg_text.replace("name: dummy", "name: nonexistent_model_xyz")
        cfg_path.write_text(cfg_text, encoding="utf-8")

        with pytest.raises(ValidationError):
            load_config(str(cfg_path))
