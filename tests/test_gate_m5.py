"""Gate M5 (Production Readiness) validation tests — Task #054.

Validates the 3 criteria of gate M5:
(1) Reproducibility E2E: 2 identical runs → ≥ 95% of key numeric fields within
    relative tolerance ≤ 1% (same seed, same config, same platform).
(2) Artefacts conformity: 100% JSON Schema validation (manifest + metrics),
    §15.1 arborescence complete.
(3) Execution: DummyModel + no_trade pipeline completes without crash.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from tests.conftest import make_integration_config

# ---------------------------------------------------------------------------
# Helpers — metrics comparison
# ---------------------------------------------------------------------------


def _extract_numeric_fields(data: dict, prefix: str = "") -> dict[str, float]:
    """Recursively extract all numeric (int/float) leaf values from a dict.

    Returns a flat dict with dotted keys, e.g.
    {"aggregate.trading.mean.net_pnl": 0.123, ...}

    Skips None values and non-numeric leaves.
    """
    result: dict[str, float] = {}
    for key, val in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict):
            result.update(_extract_numeric_fields(val, full_key))
        elif (
            isinstance(val, (int, float))
            and not isinstance(val, bool)
            and not math.isnan(val)
            and math.isfinite(val)
        ):
            result[full_key] = float(val)
    return result


def _compare_metrics_dicts(
    m1: dict,
    m2: dict,
    *,
    rtol: float = 0.01,
    atol: float = 1e-7,
) -> tuple[int, int, list[str]]:
    """Compare two metrics.json dicts.

    Returns (n_matching, n_total, mismatches) where:
    - n_matching: number of numeric fields within tolerance
    - n_total: total number of numeric fields compared
    - mismatches: list of field names that differ beyond tolerance
    """
    fields1 = _extract_numeric_fields(m1)
    fields2 = _extract_numeric_fields(m2)

    common_keys = sorted(set(fields1.keys()) & set(fields2.keys()))
    n_total = len(common_keys)
    n_matching = 0
    mismatches: list[str] = []

    for key in common_keys:
        v1 = fields1[key]
        v2 = fields2[key]
        if (
            abs(v1 - v2) <= atol
            or (abs(v1) > 0 and abs(v1 - v2) / abs(v1) <= rtol)
        ):
            n_matching += 1
        else:
            mismatches.append(f"{key}: {v1} vs {v2}")

    return n_matching, n_total, mismatches


# ---------------------------------------------------------------------------
# 1. Reproducibility E2E
# ---------------------------------------------------------------------------


class TestGateM5Reproducibility:
    """#054 — Criterion 1: 2 identical runs → >= 95% numeric fields match."""

    def test_reproducibility_same_seed_same_config(
        self, tmp_path: Path, synthetic_ohlcv: pd.DataFrame,
    ) -> None:
        """#054 — Two DummyModel runs with same seed produce >= 95% matching
        numeric fields in metrics.json (relative tolerance <= 1%)."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        # Run 1
        run1_dir = tmp_path / "run1"
        run1_dir.mkdir()
        cfg_path1 = make_integration_config(
            run1_dir, synthetic_ohlcv, strategy_name="dummy", seed=42,
        )
        config1 = load_config(str(cfg_path1))
        rd1 = run_pipeline(config1)
        metrics1 = json.loads((rd1 / "metrics.json").read_text())

        # Run 2 — same config, same seed, fresh directory
        run2_dir = tmp_path / "run2"
        run2_dir.mkdir()
        cfg_path2 = make_integration_config(
            run2_dir, synthetic_ohlcv, strategy_name="dummy", seed=42,
        )
        config2 = load_config(str(cfg_path2))
        rd2 = run_pipeline(config2)
        metrics2 = json.loads((rd2 / "metrics.json").read_text())

        n_match, n_total, mismatches = _compare_metrics_dicts(metrics1, metrics2)
        assert n_total > 0, "No numeric fields found in metrics.json"
        ratio = n_match / n_total
        assert ratio >= 0.95, (
            f"Reproducibility: {n_match}/{n_total} = {ratio:.2%} < 95%. "
            f"Mismatches: {mismatches}"
        )

    def test_reproducibility_key_fields_exact(
        self, tmp_path: Path, synthetic_ohlcv: pd.DataFrame,
    ) -> None:
        """#054 — Same-platform: key per-fold fields are exactly equal (atol=1e-7)."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        run1_dir = tmp_path / "run1"
        run1_dir.mkdir()
        cfg_path1 = make_integration_config(
            run1_dir, synthetic_ohlcv, strategy_name="dummy", seed=42,
        )
        config1 = load_config(str(cfg_path1))
        rd1 = run_pipeline(config1)
        m1 = json.loads((rd1 / "metrics.json").read_text())

        run2_dir = tmp_path / "run2"
        run2_dir.mkdir()
        cfg_path2 = make_integration_config(
            run2_dir, synthetic_ohlcv, strategy_name="dummy", seed=42,
        )
        config2 = load_config(str(cfg_path2))
        rd2 = run_pipeline(config2)
        m2 = json.loads((rd2 / "metrics.json").read_text())

        # Compare per-fold key fields
        assert len(m1["folds"]) == len(m2["folds"])
        trading_fields = ["n_trades", "net_pnl", "max_drawdown", "sharpe"]
        for i, (f1, f2) in enumerate(zip(m1["folds"], m2["folds"], strict=True)):
            for field in trading_fields:
                v1 = f1["trading"][field]
                v2 = f2["trading"][field]
                assert (v1 is None) == (v2 is None), (
                    f"Fold {i} trading.{field}: one is None and the other is not "
                    f"({v1} vs {v2})"
                )
                if v1 is not None:
                    assert abs(v1 - v2) <= 1e-7, (
                        f"Fold {i} trading.{field}: {v1} vs {v2}"
                    )
            # theta is in threshold block
            t1 = f1["threshold"]["theta"]
            t2 = f2["threshold"]["theta"]
            assert (t1 is None) == (t2 is None), (
                f"Fold {i} theta: one is None and the other is not ({t1} vs {t2})"
            )
            if t1 is not None:
                assert abs(t1 - t2) <= 1e-7, (
                    f"Fold {i} theta: {t1} vs {t2}"
                )

    def test_reproducibility_aggregate_means(
        self, tmp_path: Path, synthetic_ohlcv: pd.DataFrame,
    ) -> None:
        """#054 — Aggregate trading.mean fields are reproducible."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        run1_dir = tmp_path / "run1"
        run1_dir.mkdir()
        cfg_path1 = make_integration_config(
            run1_dir, synthetic_ohlcv, strategy_name="dummy", seed=42,
        )
        config1 = load_config(str(cfg_path1))
        rd1 = run_pipeline(config1)
        m1 = json.loads((rd1 / "metrics.json").read_text())

        run2_dir = tmp_path / "run2"
        run2_dir.mkdir()
        cfg_path2 = make_integration_config(
            run2_dir, synthetic_ohlcv, strategy_name="dummy", seed=42,
        )
        config2 = load_config(str(cfg_path2))
        rd2 = run_pipeline(config2)
        m2 = json.loads((rd2 / "metrics.json").read_text())

        # Aggregate trading means must match exactly (same platform)
        agg1 = m1["aggregate"]["trading"]["mean"]
        agg2 = m2["aggregate"]["trading"]["mean"]
        for key in agg1:
            v1 = agg1[key]
            v2 = agg2[key]
            assert (v1 is None) == (v2 is None), (
                f"aggregate.trading.mean.{key}: one is None ({v1} vs {v2})"
            )
            if v1 is not None:
                assert abs(v1 - v2) <= 1e-7, (
                    f"aggregate.trading.mean.{key}: {v1} vs {v2}"
                )


# ---------------------------------------------------------------------------
# 2. Artefacts conformity
# ---------------------------------------------------------------------------


class TestGateM5ArtefactsConformity:
    """#054 — Criterion 2: JSON Schema validation + §15.1 arborescence."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, synthetic_ohlcv: pd.DataFrame) -> None:
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        self.cfg_path = make_integration_config(
            tmp_path, synthetic_ohlcv, strategy_name="dummy", seed=42,
        )
        config = load_config(str(self.cfg_path))
        self.run_dir = run_pipeline(config)

    def test_manifest_json_schema_valid(self) -> None:
        """#054 — manifest.json validates against the JSON schema."""
        from ai_trading.artifacts.validation import validate_manifest

        manifest = json.loads((self.run_dir / "manifest.json").read_text())
        validate_manifest(manifest)

    def test_metrics_json_schema_valid(self) -> None:
        """#054 — metrics.json validates against the JSON schema."""
        from ai_trading.artifacts.validation import validate_metrics

        metrics = json.loads((self.run_dir / "metrics.json").read_text())
        validate_metrics(metrics)

    def test_arborescence_section_15_1_root(self) -> None:
        """#054 — §15.1: run_dir has manifest.json, metrics.json,
        config_snapshot.yaml, pipeline.log."""
        assert (self.run_dir / "manifest.json").is_file()
        assert (self.run_dir / "metrics.json").is_file()
        assert (self.run_dir / "config_snapshot.yaml").is_file()
        assert (self.run_dir / "pipeline.log").is_file()

    def test_arborescence_section_15_1_folds(self) -> None:
        """#054 — §15.1: folds/ directory with at least one fold subdirectory."""
        folds_dir = self.run_dir / "folds"
        assert folds_dir.is_dir()
        fold_dirs = sorted(folds_dir.iterdir())
        assert len(fold_dirs) >= 1

    def test_arborescence_section_15_1_fold_contents(self) -> None:
        """#054 — §15.1: each fold has metrics_fold.json."""
        folds_dir = self.run_dir / "folds"
        for fd in sorted(folds_dir.iterdir()):
            if fd.is_dir():
                assert (fd / "metrics_fold.json").is_file(), (
                    f"Missing metrics_fold.json in {fd.name}"
                )

    def test_arborescence_equity_curve_per_fold(self) -> None:
        """#054 — Equity curve CSV present in each fold (save_equity_curve=True)."""
        folds_dir = self.run_dir / "folds"
        for fd in sorted(folds_dir.iterdir()):
            if fd.is_dir():
                assert (fd / "equity_curve.csv").is_file(), (
                    f"Missing equity_curve.csv in {fd.name}"
                )

    def test_arborescence_predictions_per_fold(self) -> None:
        """#054 — Predictions CSVs present in each fold (save_predictions=True)."""
        folds_dir = self.run_dir / "folds"
        for fd in sorted(folds_dir.iterdir()):
            if fd.is_dir():
                assert (fd / "preds_val.csv").is_file(), (
                    f"Missing preds_val.csv in {fd.name}"
                )
                assert (fd / "preds_test.csv").is_file(), (
                    f"Missing preds_test.csv in {fd.name}"
                )

    def test_manifest_strategy_name(self) -> None:
        """#054 — manifest.json has correct strategy name."""
        manifest = json.loads((self.run_dir / "manifest.json").read_text())
        assert manifest["strategy"]["name"] == "dummy"

    def test_metrics_folds_count_matches_manifest(self) -> None:
        """#054 — metrics.json folds count matches manifest splits.folds count."""
        manifest = json.loads((self.run_dir / "manifest.json").read_text())
        metrics = json.loads((self.run_dir / "metrics.json").read_text())
        manifest_folds = manifest["splits"]["folds"]
        assert len(metrics["folds"]) == len(manifest_folds)

    def test_metrics_has_aggregate(self) -> None:
        """#054 — metrics.json has aggregate with trading and prediction."""
        metrics = json.loads((self.run_dir / "metrics.json").read_text())
        assert "aggregate" in metrics
        agg = metrics["aggregate"]
        assert "trading" in agg
        assert "prediction" in agg
        assert "mean" in agg["trading"]
        assert "std" in agg["trading"]

    def test_per_fold_metrics_json_schema_valid(self) -> None:
        """#054 — Each fold's metrics_fold.json is a valid JSON dict."""
        folds_dir = self.run_dir / "folds"
        for fd in sorted(folds_dir.iterdir()):
            if fd.is_dir():
                mf = fd / "metrics_fold.json"
                assert mf.is_file()
                data = json.loads(mf.read_text())
                assert isinstance(data, dict)
                assert "trading" in data
                assert "prediction" in data


# ---------------------------------------------------------------------------
# 3. Pipeline execution
# ---------------------------------------------------------------------------


class TestGateM5Execution:
    """#054 — Criterion 3: pipeline completes without crash."""

    def test_dummy_model_pipeline_completes(
        self, tmp_path: Path, synthetic_ohlcv: pd.DataFrame,
    ) -> None:
        """#054 — DummyModel pipeline runs to completion on synthetic data."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        cfg_path = make_integration_config(
            tmp_path, synthetic_ohlcv, strategy_name="dummy", strategy_type="model",
        )
        config = load_config(str(cfg_path))
        run_dir = run_pipeline(config)
        assert run_dir.is_dir()
        assert (run_dir / "metrics.json").is_file()
        assert (run_dir / "manifest.json").is_file()

    def test_no_trade_baseline_completes(
        self, tmp_path: Path, synthetic_ohlcv: pd.DataFrame,
    ) -> None:
        """#054 — no_trade baseline pipeline runs to completion."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        cfg_path = make_integration_config(
            tmp_path, synthetic_ohlcv,
            strategy_name="no_trade", strategy_type="baseline",
        )
        config = load_config(str(cfg_path))
        run_dir = run_pipeline(config)
        assert run_dir.is_dir()
        assert (run_dir / "metrics.json").is_file()

    def test_no_trade_theta_bypass(
        self, tmp_path: Path, synthetic_ohlcv: pd.DataFrame,
    ) -> None:
        """#054 — no_trade output_type='signal' → θ bypass verified."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        cfg_path = make_integration_config(
            tmp_path, synthetic_ohlcv,
            strategy_name="no_trade", strategy_type="baseline",
        )
        config = load_config(str(cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            assert fold["threshold"]["method"] == "none"
            assert fold["threshold"]["theta"] is None

    def test_no_trade_zero_pnl_zero_trades(
        self, tmp_path: Path, synthetic_ohlcv: pd.DataFrame,
    ) -> None:
        """#054 — no_trade produces n_trades=0, net_pnl=0 in all folds."""
        from ai_trading.config import load_config
        from ai_trading.pipeline.runner import run_pipeline

        cfg_path = make_integration_config(
            tmp_path, synthetic_ohlcv,
            strategy_name="no_trade", strategy_type="baseline",
        )
        config = load_config(str(cfg_path))
        run_dir = run_pipeline(config)
        metrics = json.loads((run_dir / "metrics.json").read_text())
        for fold in metrics["folds"]:
            assert fold["trading"]["n_trades"] == 0
            assert fold["trading"]["net_pnl"] == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Helpers — numeric extraction tests (unit tests for the comparison function)
# ---------------------------------------------------------------------------


class TestMetricsComparison:
    """#054 — Unit tests for the _compare_metrics_dicts helper."""

    def test_identical_dicts_match_100_percent(self) -> None:
        d = {"a": 1.0, "b": {"c": 2.0, "d": 3.0}}
        n_match, n_total, mismatches = _compare_metrics_dicts(d, d)
        assert n_match == n_total
        assert n_total == 3
        assert mismatches == []

    def test_within_tolerance_matches(self) -> None:
        d1 = {"a": 100.0}
        d2 = {"a": 100.5}  # 0.5% relative diff < 1%
        n_match, n_total, _ = _compare_metrics_dicts(d1, d2, rtol=0.01)
        assert n_match == n_total

    def test_beyond_tolerance_mismatches(self) -> None:
        d1 = {"a": 100.0}
        d2 = {"a": 110.0}  # 10% relative diff > 1%
        n_match, n_total, mismatches = _compare_metrics_dicts(d1, d2, rtol=0.01)
        assert n_match == 0
        assert len(mismatches) == 1

    def test_nested_dict_extraction(self) -> None:
        d = {"x": {"y": {"z": 42.0}}, "a": "text", "b": None}
        fields = _extract_numeric_fields(d)
        assert "x.y.z" in fields
        assert len(fields) == 1

    def test_nan_and_inf_skipped(self) -> None:
        d = {"a": float("nan"), "b": float("inf"), "c": 1.0}
        fields = _extract_numeric_fields(d)
        assert "c" in fields
        assert len(fields) == 1

    def test_bool_skipped(self) -> None:
        d = {"flag": True, "val": 5.0}
        fields = _extract_numeric_fields(d)
        assert "flag" not in fields
        assert "val" in fields
