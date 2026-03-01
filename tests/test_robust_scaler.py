"""Tests for RobustScaler and create_scaler factory (WS-5.2).

Task #022 — Robust scaler (option).
Covers nominal, error, edge, anti-leak, save/load and factory scenarios.
"""

import logging

import numpy as np
import pytest

from ai_trading.config import load_config
from ai_trading.data.scaler import (
    RobustScaler,
    StandardScaler,
    create_scaler,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_scaling_config(default_config_path):
    """Return the scaling sub-config from default.yaml."""
    cfg = load_config(str(default_config_path))
    return cfg.scaling


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def x_train_3d(rng):
    """Shape (20, 5, 3): 20 samples, lookback 5, 3 features."""
    return rng.standard_normal((20, 5, 3)).astype(np.float32)


@pytest.fixture
def x_val_3d(rng):
    """Shape (8, 5, 3)."""
    return rng.standard_normal((8, 5, 3)).astype(np.float32)


@pytest.fixture
def scaling_cfg(default_config_path):
    return _load_scaling_config(default_config_path)


@pytest.fixture
def config_epsilon(scaling_cfg):
    return scaling_cfg.epsilon


@pytest.fixture
def config_quantile_low(scaling_cfg):
    return scaling_cfg.robust_quantile_low


@pytest.fixture
def config_quantile_high(scaling_cfg):
    return scaling_cfg.robust_quantile_high


# ===========================================================================
# Nominal
# ===========================================================================


class TestRobustNominal:
    """#022 — Nominal scenarios for RobustScaler."""

    def test_fit_sets_median_and_iqr(
        self, x_train_3d, config_epsilon, config_quantile_low, config_quantile_high
    ):
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler.fit(x_train_3d)

        assert scaler.median_ is not None
        assert scaler.iqr_ is not None
        assert scaler.median_.shape == (3,)
        assert scaler.iqr_.shape == (3,)

    def test_train_median_centered(
        self, x_train_3d, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """After fit_transform on train, median per feature ≈ 0."""
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        x_scaled = scaler.fit_transform(x_train_3d)
        flat = x_scaled.reshape(-1, x_scaled.shape[-1])
        medians = np.median(flat, axis=0)
        np.testing.assert_allclose(medians, 0.0, atol=1e-5)

    def test_transform_preserves_shape(
        self, x_train_3d, x_val_3d, config_epsilon,
        config_quantile_low, config_quantile_high
    ):
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler.fit(x_train_3d)
        x_val_scaled = scaler.transform(x_val_3d)
        assert x_val_scaled.shape == x_val_3d.shape

    def test_transform_preserves_float32(
        self, x_train_3d, x_val_3d, config_epsilon,
        config_quantile_low, config_quantile_high
    ):
        """#022 — Transform output must be float32."""
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler.fit(x_train_3d)
        x_val_scaled = scaler.transform(x_val_3d)
        assert x_val_scaled.dtype == np.float32

    def test_fit_transform_same_as_fit_then_transform(
        self, x_train_3d, config_epsilon, config_quantile_low, config_quantile_high
    ):
        scaler1 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        x1 = scaler1.fit_transform(x_train_3d)

        scaler2 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler2.fit(x_train_3d)
        x2 = scaler2.transform(x_train_3d)

        np.testing.assert_array_equal(x1, x2)

    def test_quantiles_from_config(self, default_config_path):
        """#022 — robust_quantile_low/high must come from config."""
        cfg = load_config(str(default_config_path))
        assert cfg.scaling.robust_quantile_low == 0.005
        assert cfg.scaling.robust_quantile_high == 0.995


# ===========================================================================
# Outlier clipping
# ===========================================================================


class TestRobustClipping:
    """#022 — Verify that extreme outliers are clipped."""

    def test_outliers_are_clipped(
        self, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """Extreme outlier values should be clipped to quantile bounds."""
        rng = np.random.default_rng(123)
        # Normal data + extreme outliers
        x_train = rng.standard_normal((50, 5, 2)).astype(np.float32)
        x_train[0, 0, 0] = 100.0  # extreme outlier
        x_train[1, 0, 0] = -100.0  # extreme outlier

        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler.fit(x_train)

        # Create test data with an extreme value
        x_test = np.zeros((1, 5, 2), dtype=np.float32)
        x_test[0, 0, 0] = 1000.0  # way beyond any quantile

        x_scaled = scaler.transform(x_test)
        # The clipped value should not exceed the quantile bounds computed from train
        assert scaler.clip_high_ is not None
        assert x_scaled[0, 0, 0] == scaler.clip_high_[0]

    def test_values_within_bounds_unchanged(
        self, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """Values within clip bounds should not be clipped (only centered/scaled)."""
        rng = np.random.default_rng(77)
        x_train = rng.standard_normal((100, 5, 2)).astype(np.float32)

        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler.fit(x_train)

        # Transform the median value (should be ≈ 0 after centering)
        assert scaler.median_ is not None
        x_median = np.zeros((1, 5, 2), dtype=np.float32)
        for j in range(2):
            x_median[0, :, j] = scaler.median_[j]

        x_scaled = scaler.transform(x_median)
        np.testing.assert_allclose(x_scaled, 0.0, atol=1e-5)


# ===========================================================================
# Anti-leak
# ===========================================================================


class TestRobustAntiLeak:
    """#022 — Verify scaler never sees val/test data."""

    def test_fit_only_uses_train(
        self, x_train_3d, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """Stats should match manual computation on X_train only."""
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler.fit(x_train_3d)

        flat = x_train_3d.reshape(-1, x_train_3d.shape[-1])
        expected_median = np.median(flat, axis=0).astype(np.float32)
        q_low = np.quantile(flat, config_quantile_low, axis=0).astype(np.float32)
        q_high = np.quantile(flat, config_quantile_high, axis=0).astype(np.float32)
        expected_iqr = (q_high - q_low).astype(np.float32)

        assert scaler.median_ is not None
        assert scaler.iqr_ is not None
        np.testing.assert_allclose(scaler.median_, expected_median, atol=1e-6)
        np.testing.assert_allclose(scaler.iqr_, expected_iqr, atol=1e-6)


# ===========================================================================
# Errors
# ===========================================================================


class TestRobustErrors:
    """#022 — Error cases for RobustScaler."""

    def test_nan_in_train_raises(
        self, x_train_3d, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """NaN in X_train → ValueError."""
        x_train_3d[5, 2, 1] = np.nan
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        with pytest.raises(ValueError, match="NaN"):
            scaler.fit(x_train_3d)

    def test_non_3d_input_fit_raises(
        self, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """Fit with 2D input → ValueError."""
        x_2d = np.ones((10, 5), dtype=np.float32)
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        with pytest.raises(ValueError, match="3D"):
            scaler.fit(x_2d)

    def test_non_3d_input_transform_raises(
        self, x_train_3d, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """Transform with 2D input → ValueError."""
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler.fit(x_train_3d)
        x_2d = np.ones((10, 5), dtype=np.float32)
        with pytest.raises(ValueError, match="3D"):
            scaler.transform(x_2d)

    def test_transform_before_fit_raises(
        self, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """Transform without fit → error."""
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        x = np.ones((5, 3, 2), dtype=np.float32)
        with pytest.raises(RuntimeError, match="fit"):
            scaler.transform(x)

    def test_negative_epsilon_raises(self):
        with pytest.raises(ValueError, match="epsilon"):
            RobustScaler(epsilon=-1e-12, quantile_low=0.005, quantile_high=0.995)

    def test_quantile_low_ge_quantile_high_raises(self):
        """quantile_low >= quantile_high → ValueError."""
        with pytest.raises(ValueError, match="quantile"):
            RobustScaler(epsilon=1e-12, quantile_low=0.995, quantile_high=0.005)

    def test_quantile_low_equal_quantile_high_raises(self):
        """quantile_low == quantile_high → ValueError."""
        with pytest.raises(ValueError, match="quantile"):
            RobustScaler(epsilon=1e-12, quantile_low=0.5, quantile_high=0.5)


# ===========================================================================
# Edge cases
# ===========================================================================


class TestRobustEdgeCases:
    """#022 — Edge cases for RobustScaler."""

    def test_constant_feature_returns_zero(
        self, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """Feature with IQR ≈ 0 → output = 0.0 after scaling."""
        x_train = np.zeros((10, 5, 2), dtype=np.float32)
        x_train[:, :, 1] = np.arange(50, dtype=np.float32).reshape(10, 5)

        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        x_scaled = scaler.fit_transform(x_train)

        # Constant feature → all zeros
        np.testing.assert_array_equal(x_scaled[:, :, 0], 0.0)
        # Variable feature → scaled normally (not all zeros)
        assert not np.all(x_scaled[:, :, 1] == 0.0)

    def test_constant_feature_emits_warning(
        self, config_epsilon, config_quantile_low, config_quantile_high, caplog
    ):
        """Feature with IQR ≈ 0 → warning via logging."""
        x_train = np.ones((10, 5, 2), dtype=np.float32)
        x_train[:, :, 1] = np.arange(50, dtype=np.float32).reshape(10, 5)

        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        with caplog.at_level(logging.WARNING):
            scaler.fit(x_train)

        assert any("constant" in r.message.lower() for r in caplog.records)

    def test_single_sample(
        self, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """N=1: single sample → IQR=0 for all → output 0.0."""
        x = np.array([[[1.0, 2.0, 3.0]]], dtype=np.float32)  # (1, 1, 3)
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        x_scaled = scaler.fit_transform(x)
        np.testing.assert_array_equal(x_scaled, 0.0)

    def test_single_feature(
        self, rng, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """F=1: single feature."""
        x = rng.standard_normal((15, 5, 1)).astype(np.float32)
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        x_scaled = scaler.fit_transform(x)
        assert x_scaled.shape == (15, 5, 1)

    def test_lookback_1(
        self, rng, config_epsilon, config_quantile_low, config_quantile_high
    ):
        """L=1: lookback of 1 should work."""
        x = rng.standard_normal((20, 1, 3)).astype(np.float32)
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        x_scaled = scaler.fit_transform(x)
        assert x_scaled.shape == (20, 1, 3)


# ===========================================================================
# Save / Load
# ===========================================================================


class TestRobustSaveLoad:
    """#022 — Serialization of RobustScaler parameters."""

    def test_save_and_load_roundtrip(
        self, x_train_3d, x_val_3d, config_epsilon,
        config_quantile_low, config_quantile_high, tmp_path
    ):
        """Save params, load into new scaler, transform gives same result."""
        scaler1 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler1.fit(x_train_3d)
        x_ref = scaler1.transform(x_val_3d)

        path = tmp_path / "robust_params.npz"
        scaler1.save(path)

        scaler2 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler2.load(path)
        x_loaded = scaler2.transform(x_val_3d)

        np.testing.assert_array_equal(x_ref, x_loaded)

    def test_load_restores_params(
        self, x_train_3d, config_epsilon,
        config_quantile_low, config_quantile_high, tmp_path
    ):
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler.fit(x_train_3d)
        path = tmp_path / "params.npz"
        scaler.save(path)

        scaler2 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler2.load(path)

        np.testing.assert_array_equal(scaler.median_, scaler2.median_)
        np.testing.assert_array_equal(scaler.iqr_, scaler2.iqr_)

    def test_save_before_fit_raises(
        self, config_epsilon, config_quantile_low, config_quantile_high, tmp_path
    ):
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        with pytest.raises(RuntimeError, match="fit"):
            scaler.save(tmp_path / "params.npz")

    def test_load_nonexistent_file_raises(
        self, config_epsilon, config_quantile_low, config_quantile_high, tmp_path
    ):
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        with pytest.raises(FileNotFoundError):
            scaler.load(tmp_path / "nonexistent.npz")

    def test_load_epsilon_mismatch_raises(
        self, x_train_3d, config_epsilon,
        config_quantile_low, config_quantile_high, tmp_path
    ):
        scaler1 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler1.fit(x_train_3d)
        path = tmp_path / "params.npz"
        scaler1.save(path)

        scaler2 = RobustScaler(
            epsilon=1e-6,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        with pytest.raises(ValueError, match="mismatch"):
            scaler2.load(path)

    def test_load_quantile_low_mismatch_raises(
        self, x_train_3d, config_epsilon,
        config_quantile_low, config_quantile_high, tmp_path
    ):
        """Load with different quantile_low → ValueError."""
        scaler1 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler1.fit(x_train_3d)
        path = tmp_path / "params.npz"
        scaler1.save(path)

        scaler2 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=0.01,
            quantile_high=config_quantile_high,
        )
        with pytest.raises(ValueError, match="quantile_low mismatch"):
            scaler2.load(path)

    def test_load_quantile_high_mismatch_raises(
        self, x_train_3d, config_epsilon,
        config_quantile_low, config_quantile_high, tmp_path
    ):
        """Load with different quantile_high → ValueError."""
        scaler1 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler1.fit(x_train_3d)
        path = tmp_path / "params.npz"
        scaler1.save(path)

        scaler2 = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=0.99,
        )
        with pytest.raises(ValueError, match="quantile_high mismatch"):
            scaler2.load(path)


# ===========================================================================
# Float32 consistency
# ===========================================================================


class TestRobustFloat32:
    """#022 — Verify float32 consistency in stats and output."""

    def test_median_iqr_are_float32(
        self, x_train_3d, config_epsilon, config_quantile_low, config_quantile_high
    ):
        scaler = RobustScaler(
            epsilon=config_epsilon,
            quantile_low=config_quantile_low,
            quantile_high=config_quantile_high,
        )
        scaler.fit(x_train_3d)
        assert scaler.median_ is not None
        assert scaler.iqr_ is not None
        assert scaler.median_.dtype == np.float32
        assert scaler.iqr_.dtype == np.float32


# ===========================================================================
# Factory: create_scaler
# ===========================================================================


class TestCreateScaler:
    """#022 — Factory function to select scaler by config."""

    def test_create_standard_scaler(self, default_config_path):
        """config.scaling.method='standard' → StandardScaler."""
        cfg = load_config(str(default_config_path))
        scaler = create_scaler(cfg.scaling)
        assert isinstance(scaler, StandardScaler)

    def test_create_robust_scaler(self, default_config_path, tmp_yaml, default_yaml_data):
        """config.scaling.method='robust' → RobustScaler."""
        default_yaml_data["scaling"]["method"] = "robust"
        path = tmp_yaml(default_yaml_data)
        cfg = load_config(path)
        scaler = create_scaler(cfg.scaling)
        assert isinstance(scaler, RobustScaler)

    def test_unknown_method_raises(self, default_config_path, tmp_yaml, default_yaml_data):
        """Unknown scaling method → ValueError."""
        default_yaml_data["scaling"]["method"] = "minmax"
        path = tmp_yaml(default_yaml_data)
        # The config validator rejects rolling_zscore but not unknown strings
        # So we test the factory directly with an unknown method
        cfg = load_config(path)
        with pytest.raises(ValueError, match="Unknown scaling method"):
            create_scaler(cfg.scaling)

    def test_factory_scaler_is_functional(
        self, default_config_path, tmp_yaml, default_yaml_data, rng
    ):
        """Factory-created robust scaler should work end-to-end."""
        default_yaml_data["scaling"]["method"] = "robust"
        path = tmp_yaml(default_yaml_data)
        cfg = load_config(path)
        scaler = create_scaler(cfg.scaling)

        x = rng.standard_normal((10, 5, 3)).astype(np.float32)
        x_scaled = scaler.fit_transform(x)
        assert x_scaled.shape == x.shape
        assert x_scaled.dtype == np.float32
