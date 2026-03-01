"""Tests for feature pipeline (assemblage et orchestration).

Task #013 — WS-3: Feature pipeline.
"""

from types import SimpleNamespace

import pandas as pd
import pytest

import ai_trading.features.ema as _ema_module
import ai_trading.features.log_returns as _lr_module
import ai_trading.features.rsi as _rsi_module
import ai_trading.features.volatility as _vol_module
import ai_trading.features.volume as _volume_module
from ai_trading.features.registry import FEATURE_REGISTRY, BaseFeature
from tests.conftest import clean_registry_with_reload, make_ohlcv_random

# ---------------------------------------------------------------------------
# All 9 MVP feature names in canonical order
# ---------------------------------------------------------------------------
ALL_9_FEATURES = [
    "logret_1",
    "logret_2",
    "logret_4",
    "vol_24",
    "vol_72",
    "logvol",
    "dlogvol",
    "rsi_14",
    "ema_ratio_12_26",
]

# Default params that satisfy every feature's required_params
DEFAULT_PARAMS = {
    "rsi_period": 14,
    "rsi_epsilon": 1e-12,
    "ema_fast": 12,
    "ema_slow": 26,
    "vol_windows": [24, 72],
    "logvol_epsilon": 1e-8,
    "volatility_ddof": 0,
}


def _make_config(
    feature_list: list[str] | None = None,
    params: dict | None = None,
    feature_version: str = "mvp_v1",
) -> SimpleNamespace:
    """Build a lightweight config namespace mimicking PipelineConfig.features."""
    fl = feature_list if feature_list is not None else list(ALL_9_FEATURES)
    p = params if params is not None else dict(DEFAULT_PARAMS)
    features_ns = SimpleNamespace(
        feature_version=feature_version,
        feature_list=fl,
        params=SimpleNamespace(**p),
    )
    return SimpleNamespace(features=features_ns)


_clean_registry = clean_registry_with_reload(
    _lr_module, _vol_module, _rsi_module, _ema_module, _volume_module,
)


# ===========================================================================
# Nominal: compute_features with all 9 features
# ===========================================================================


class TestComputeFeaturesNominal:
    """#013 — Nominal scenarios for compute_features."""

    def test_output_shape_all_9(self):
        """compute_features produces (N_total, 9) DataFrame with all 9 features."""
        from ai_trading.features.pipeline import compute_features

        ohlcv = make_ohlcv_random(200, seed=42)
        config = _make_config()
        result = compute_features(ohlcv, config)

        assert isinstance(result, pd.DataFrame)
        assert result.shape == (200, 9)

    def test_column_names_all_9(self):
        """Columns match the 9 feature names."""
        from ai_trading.features.pipeline import compute_features

        ohlcv = make_ohlcv_random(200, seed=42)
        config = _make_config()
        result = compute_features(ohlcv, config)

        assert list(result.columns) == ALL_9_FEATURES

    def test_column_order_matches_feature_list(self):
        """Column order matches the order in feature_list config."""
        from ai_trading.features.pipeline import compute_features

        # Reverse order
        reversed_list = list(reversed(ALL_9_FEATURES))
        config = _make_config(feature_list=reversed_list)
        ohlcv = make_ohlcv_random(200, seed=42)
        result = compute_features(ohlcv, config)

        assert list(result.columns) == reversed_list

    def test_subset_features(self):
        """compute_features works with a subset of features."""
        from ai_trading.features.pipeline import compute_features

        subset = ["logret_1", "rsi_14"]
        config = _make_config(feature_list=subset)
        ohlcv = make_ohlcv_random(200, seed=42)
        result = compute_features(ohlcv, config)

        assert result.shape == (200, 2)
        assert list(result.columns) == subset

    def test_index_preserved(self):
        """Output index matches input OHLCV index."""
        from ai_trading.features.pipeline import compute_features

        ohlcv = make_ohlcv_random(200, seed=42)
        config = _make_config()
        result = compute_features(ohlcv, config)

        pd.testing.assert_index_equal(result.index, ohlcv.index)

    def test_feature_version_traced(self):
        """feature_version is read from config (no crash, used internally)."""
        from ai_trading.features.pipeline import compute_features

        config = _make_config(feature_version="test_v2")
        ohlcv = make_ohlcv_random(200, seed=42)
        # Should not raise — feature_version is read and traced
        result = compute_features(ohlcv, config)
        assert result.shape[1] == 9


# ===========================================================================
# Registry population after import
# ===========================================================================


class TestRegistryPopulation:
    """#013 — Verify registry has all 9 features after importing the package."""

    def test_registry_has_9_features(self):
        """FEATURE_REGISTRY contains exactly the 9 MVP features."""
        assert len(FEATURE_REGISTRY) == 9

    def test_all_9_names_present(self):
        """All 9 expected feature names are in the registry."""
        for name in ALL_9_FEATURES:
            assert name in FEATURE_REGISTRY, f"'{name}' not in FEATURE_REGISTRY"

    def test_all_entries_are_base_feature(self):
        """Each registered value is a BaseFeature subclass."""
        for name, cls in FEATURE_REGISTRY.items():
            assert issubclass(cls, BaseFeature), f"'{name}' → {cls} is not BaseFeature"


# ===========================================================================
# Error: unknown feature in feature_list
# ===========================================================================


class TestUnknownFeature:
    """#013 — ValueError for unknown feature names."""

    def test_unknown_feature_raises(self):
        """Feature not in registry → ValueError with feature name."""
        from ai_trading.features.pipeline import compute_features

        config = _make_config(feature_list=["logret_1", "nonexistent_feature"])
        ohlcv = make_ohlcv_random(100, seed=42)

        with pytest.raises(ValueError, match="nonexistent_feature"):
            compute_features(ohlcv, config)

    def test_unknown_feature_among_valid(self):
        """Even if some features are valid, an unknown one raises."""
        from ai_trading.features.pipeline import compute_features

        config = _make_config(feature_list=["logret_1", "logret_2", "BAD_NAME"])
        ohlcv = make_ohlcv_random(100, seed=42)

        with pytest.raises(ValueError, match="BAD_NAME"):
            compute_features(ohlcv, config)


# ===========================================================================
# Error: missing required parameter
# ===========================================================================


class TestMissingRequiredParam:
    """#013 — ValueError for missing required_params."""

    def test_missing_rsi_period(self):
        """rsi_14 requires 'rsi_period'; missing → ValueError."""
        from ai_trading.features.pipeline import compute_features

        bad_params = dict(DEFAULT_PARAMS)
        del bad_params["rsi_period"]
        config = _make_config(feature_list=["rsi_14"], params=bad_params)
        ohlcv = make_ohlcv_random(100, seed=42)

        with pytest.raises(ValueError, match="rsi_period"):
            compute_features(ohlcv, config)

    def test_missing_ema_fast(self):
        """ema_ratio_12_26 requires 'ema_fast'; missing → ValueError."""
        from ai_trading.features.pipeline import compute_features

        bad_params = dict(DEFAULT_PARAMS)
        del bad_params["ema_fast"]
        config = _make_config(feature_list=["ema_ratio_12_26"], params=bad_params)
        ohlcv = make_ohlcv_random(100, seed=42)

        with pytest.raises(ValueError, match="ema_fast"):
            compute_features(ohlcv, config)

    def test_missing_logvol_epsilon(self):
        """logvol requires 'logvol_epsilon'; missing → ValueError."""
        from ai_trading.features.pipeline import compute_features

        bad_params = dict(DEFAULT_PARAMS)
        del bad_params["logvol_epsilon"]
        config = _make_config(feature_list=["logvol"], params=bad_params)
        ohlcv = make_ohlcv_random(100, seed=42)

        with pytest.raises(ValueError, match="logvol_epsilon"):
            compute_features(ohlcv, config)


# ===========================================================================
# Error: empty registry
# ===========================================================================


class TestEmptyRegistry:
    """#013 — Error when registry is empty."""

    def test_empty_registry_raises(self):
        """If registry is empty, compute_features raises ValueError."""
        from ai_trading.features.pipeline import compute_features

        # Temporarily clear registry
        saved = dict(FEATURE_REGISTRY)
        FEATURE_REGISTRY.clear()
        try:
            config = _make_config(feature_list=["logret_1"])
            ohlcv = make_ohlcv_random(100, seed=42)

            with pytest.raises(ValueError):
                compute_features(ohlcv, config)
        finally:
            FEATURE_REGISTRY.update(saved)


# ===========================================================================
# Resolved instances accessible
# ===========================================================================


class TestResolvedInstances:
    """#013 — compute_features exposes resolved BaseFeature instances."""

    def test_resolve_features_returns_instances(self):
        """resolve_features returns list of BaseFeature instances."""
        from ai_trading.features.pipeline import resolve_features

        config = _make_config(feature_list=["logret_1", "rsi_14"])
        instances = resolve_features(config)

        assert len(instances) == 2
        assert all(isinstance(inst, BaseFeature) for inst in instances)

    def test_resolve_features_order(self):
        """Instances match the order of feature_list."""
        from ai_trading.features.pipeline import resolve_features

        config = _make_config(feature_list=["rsi_14", "logret_1"])
        instances = resolve_features(config)

        assert len(instances) == 2
        # First instance should produce rsi_14 column
        ohlcv = make_ohlcv_random(100, seed=42)
        params = vars(config.features.params)
        s0 = instances[0].compute(ohlcv, params)
        assert s0.name == "rsi_14"

    def test_resolve_features_has_min_periods(self):
        """Each resolved instance exposes min_periods callable."""
        from ai_trading.features.pipeline import resolve_features

        config = _make_config(feature_list=["logret_1", "vol_72"])
        instances = resolve_features(config)
        params = vars(config.features.params)

        for inst in instances:
            mp = inst.min_periods(params)
            assert isinstance(mp, int)
            assert mp >= 0


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    """#013 — Edge cases for feature pipeline."""

    def test_single_feature(self):
        """Pipeline works with a single feature."""
        from ai_trading.features.pipeline import compute_features

        config = _make_config(feature_list=["logret_1"])
        ohlcv = make_ohlcv_random(50, seed=42)
        result = compute_features(ohlcv, config)

        assert result.shape == (50, 1)
        assert list(result.columns) == ["logret_1"]

    def test_empty_feature_list_raises(self):
        """Empty feature_list → ValueError."""
        from ai_trading.features.pipeline import compute_features

        config = _make_config(feature_list=[])
        ohlcv = make_ohlcv_random(50, seed=42)

        with pytest.raises(ValueError):
            compute_features(ohlcv, config)

    def test_duplicate_feature_list_raises(self):
        """Duplicate feature names → ValueError."""
        from ai_trading.features.pipeline import compute_features

        config = _make_config(feature_list=["logret_1", "logret_1"])
        ohlcv = make_ohlcv_random(50, seed=42)

        with pytest.raises(ValueError, match="logret_1"):
            compute_features(ohlcv, config)

    def test_values_not_all_nan(self):
        """With enough data, not all values are NaN (sanity check)."""
        from ai_trading.features.pipeline import compute_features

        ohlcv = make_ohlcv_random(200, seed=42)
        config = _make_config()
        result = compute_features(ohlcv, config)

        for col in result.columns:
            assert not result[col].isna().all(), f"Column '{col}' is all NaN"
