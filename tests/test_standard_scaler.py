"""Tests for StandardScaler (WS-5.1).

Task #021 — Standard scaler (fit-on-train).
Covers nominal, error, edge, and anti-leak scenarios.
"""

import logging

import numpy as np
import pytest

from ai_trading.config import load_config
from ai_trading.data.scaler import CONSTANT_FEATURE_SIGMA_THRESHOLD, StandardScaler

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config_epsilon(default_config_path):
    """Load epsilon from the real config."""
    cfg = load_config(str(default_config_path))
    return cfg.scaling.epsilon


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def x_train_3d(rng):
    """Shape (20, 5, 3): 20 samples, lookback 5, 3 features."""
    return rng.standard_normal((20, 5, 3)).astype(np.float32)


@pytest.fixture
def x_val_3d(rng):
    """Shape (8, 5, 3)."""
    return rng.standard_normal((8, 5, 3)).astype(np.float32)


@pytest.fixture
def x_test_3d(rng):
    """Shape (5, 5, 3)."""
    return rng.standard_normal((5, 5, 3)).astype(np.float32)


@pytest.fixture
def config_epsilon(default_config_path):
    return _make_config_epsilon(default_config_path)


# ===========================================================================
# Nominal
# ===========================================================================

class TestNominal:
    """#021 — Nominal scenarios for StandardScaler."""

    def test_fit_sets_mean_and_std(self, x_train_3d, config_epsilon):
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)

        assert scaler.mean_ is not None
        assert scaler.std_ is not None
        assert scaler.mean_.shape == (3,)
        assert scaler.std_.shape == (3,)

    def test_train_mean_approx_zero(self, x_train_3d, config_epsilon):
        """After fit_transform on train, mean per feature ≈ 0."""
        scaler = StandardScaler(epsilon=config_epsilon)
        x_scaled = scaler.fit_transform(x_train_3d)

        # Reshape to (N*L, F) and check mean per feature
        flat = x_scaled.reshape(-1, x_scaled.shape[-1])
        np.testing.assert_allclose(flat.mean(axis=0), 0.0, atol=1e-5)

    def test_train_std_approx_one(self, x_train_3d, config_epsilon):
        """After fit_transform on train, std per feature ≈ 1."""
        scaler = StandardScaler(epsilon=config_epsilon)
        x_scaled = scaler.fit_transform(x_train_3d)

        flat = x_scaled.reshape(-1, x_scaled.shape[-1])
        np.testing.assert_allclose(flat.std(axis=0), 1.0, atol=1e-5)

    def test_transform_preserves_shape(self, x_train_3d, x_val_3d, config_epsilon):
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)

        x_val_scaled = scaler.transform(x_val_3d)
        assert x_val_scaled.shape == x_val_3d.shape

    def test_params_stored_in_float64(self, x_train_3d, config_epsilon):
        """#021 — Scaler params (mean_, std_) must be float64 (convention P-02)."""
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)

        assert scaler.mean_.dtype == np.float64
        assert scaler.std_.dtype == np.float64

    def test_transform_preserves_float32(self, x_train_3d, x_val_3d, config_epsilon):
        """#021 — Transform output must be float32."""
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)

        x_val_scaled = scaler.transform(x_val_3d)
        assert x_val_scaled.dtype == np.float32

    def test_fit_transform_same_as_fit_then_transform(
        self, x_train_3d, config_epsilon
    ):
        scaler1 = StandardScaler(epsilon=config_epsilon)
        x1 = scaler1.fit_transform(x_train_3d)

        scaler2 = StandardScaler(epsilon=config_epsilon)
        scaler2.fit(x_train_3d)
        x2 = scaler2.transform(x_train_3d)

        np.testing.assert_array_equal(x1, x2)

    def test_epsilon_from_config(self, default_config_path):
        """#021 — epsilon must be read from config, not hardcoded."""
        cfg = load_config(str(default_config_path))
        assert cfg.scaling.epsilon == 1e-12

    def test_val_test_not_centered(
        self, x_train_3d, x_val_3d, x_test_3d, config_epsilon
    ):
        """Val/test sets are NOT expected to have mean=0, std=1
        (since scaler is fit on train only)."""
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)

        x_val_scaled = scaler.transform(x_val_3d)
        val_flat = x_val_scaled.reshape(-1, x_val_scaled.shape[-1])
        # They likely won't be exactly 0/1 — just ensure transform runs
        assert val_flat.shape[0] == 8 * 5


# ===========================================================================
# Anti-leak
# ===========================================================================

class TestAntiLeak:
    """#021 — Verify scaler never sees val/test data."""

    def test_fit_only_uses_train(self, x_train_3d, x_val_3d, config_epsilon):
        """Fit on X_train, then verify stats match only X_train."""
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)

        x_flat = x_train_3d.reshape(-1, x_train_3d.shape[-1])
        expected_mean = x_flat.mean(axis=0)
        expected_std = x_flat.std(axis=0)

        np.testing.assert_allclose(scaler.mean_, expected_mean, atol=1e-6)
        np.testing.assert_allclose(scaler.std_, expected_std, atol=1e-6)

    def test_stats_change_if_different_train(self, rng, config_epsilon):
        """Different train data → different stats (no leakage from previous fit)."""
        x1 = rng.standard_normal((10, 5, 3)).astype(np.float32)
        x2 = rng.standard_normal((10, 5, 3)).astype(np.float32) + 10.0

        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x1)
        mean1 = scaler.mean_.copy()

        scaler.fit(x2)
        mean2 = scaler.mean_.copy()

        # Means should be significantly different
        assert not np.allclose(mean1, mean2, atol=1.0)


# ===========================================================================
# Errors
# ===========================================================================

class TestErrors:
    """#021 — Error cases for StandardScaler."""

    def test_nan_in_train_raises(self, x_train_3d, config_epsilon):
        """NaN in X_train → ValueError."""
        x_train_3d[5, 2, 1] = np.nan
        scaler = StandardScaler(epsilon=config_epsilon)
        with pytest.raises(ValueError, match="NaN"):
            scaler.fit(x_train_3d)

    def test_non_3d_input_fit_raises(self, config_epsilon):
        """Fit with 2D input → ValueError."""
        x_2d = np.ones((10, 5), dtype=np.float32)
        scaler = StandardScaler(epsilon=config_epsilon)
        with pytest.raises(ValueError, match="3D"):
            scaler.fit(x_2d)

    def test_non_3d_input_transform_raises(self, x_train_3d, config_epsilon):
        """Transform with 2D input → ValueError."""
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)
        x_2d = np.ones((10, 5), dtype=np.float32)
        with pytest.raises(ValueError, match="3D"):
            scaler.transform(x_2d)

    def test_transform_before_fit_raises(self, config_epsilon):
        """Transform without fit → error."""
        scaler = StandardScaler(epsilon=config_epsilon)
        x = np.ones((5, 3, 2), dtype=np.float32)
        with pytest.raises(RuntimeError, match="fit"):
            scaler.transform(x)

    def test_1d_input_raises(self, config_epsilon):
        """1D input → ValueError."""
        scaler = StandardScaler(epsilon=config_epsilon)
        with pytest.raises(ValueError, match="3D"):
            scaler.fit(np.ones(10, dtype=np.float32))

    def test_4d_input_raises(self, config_epsilon):
        """4D input → ValueError."""
        scaler = StandardScaler(epsilon=config_epsilon)
        with pytest.raises(ValueError, match="3D"):
            scaler.fit(np.ones((2, 3, 4, 5), dtype=np.float32))

    def test_negative_epsilon_raises(self):
        """Negative epsilon → ValueError."""
        with pytest.raises(ValueError, match="epsilon"):
            StandardScaler(epsilon=-1e-12)

    def test_nan_epsilon_raises(self):
        """NaN epsilon → ValueError."""
        with pytest.raises(ValueError, match="epsilon"):
            StandardScaler(epsilon=float("nan"))

    def test_inf_epsilon_raises(self):
        """Inf epsilon → ValueError."""
        with pytest.raises(ValueError, match="epsilon"):
            StandardScaler(epsilon=float("inf"))


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:
    """#021 — Edge cases for StandardScaler."""

    def test_constant_feature_returns_zero(self, config_epsilon):
        """Feature with σ < 1e-8 → output = 0.0 after scaling."""
        # Feature 0: constant, Feature 1: variable
        x_train = np.zeros((10, 5, 2), dtype=np.float32)
        x_train[:, :, 1] = np.arange(50, dtype=np.float32).reshape(10, 5)

        scaler = StandardScaler(epsilon=config_epsilon)
        x_scaled = scaler.fit_transform(x_train)

        # Constant feature → all zeros
        np.testing.assert_array_equal(x_scaled[:, :, 0], 0.0)
        # Variable feature → scaled normally (not all zeros)
        assert not np.all(x_scaled[:, :, 1] == 0.0)

    def test_constant_feature_emits_warning(self, config_epsilon, caplog):
        """Feature with σ < 1e-8 → warning via logging."""
        x_train = np.ones((10, 5, 2), dtype=np.float32)
        x_train[:, :, 1] = np.arange(50, dtype=np.float32).reshape(10, 5)

        scaler = StandardScaler(epsilon=config_epsilon)
        with caplog.at_level(logging.WARNING):
            scaler.fit_transform(x_train)

        assert any("constant" in r.message.lower() for r in caplog.records)

    def test_single_sample(self, config_epsilon):
        """N=1: single sample should still work (σ=0 for all → output 0.0)."""
        x = np.array([[[1.0, 2.0, 3.0]]], dtype=np.float32)  # (1, 1, 3)
        scaler = StandardScaler(epsilon=config_epsilon)
        x_scaled = scaler.fit_transform(x)

        # All features are constant (1 sample) → all 0.0
        np.testing.assert_array_equal(x_scaled, 0.0)

    def test_single_feature(self, rng, config_epsilon):
        """F=1: single feature."""
        x = rng.standard_normal((15, 5, 1)).astype(np.float32)
        scaler = StandardScaler(epsilon=config_epsilon)
        x_scaled = scaler.fit_transform(x)
        assert x_scaled.shape == (15, 5, 1)
        flat = x_scaled.reshape(-1, 1)
        np.testing.assert_allclose(flat.mean(), 0.0, atol=1e-5)

    def test_large_epsilon_affects_result(self):
        """Larger epsilon → different scaling result."""
        rng = np.random.default_rng(99)
        x = rng.standard_normal((10, 5, 2)).astype(np.float32)

        scaler_small = StandardScaler(epsilon=1e-12)
        x1 = scaler_small.fit_transform(x.copy())

        scaler_large = StandardScaler(epsilon=1.0)
        x2 = scaler_large.fit_transform(x.copy())

        # With epsilon=1.0, denominator is larger → values are smaller
        assert not np.allclose(x1, x2)

    def test_lookback_1(self, rng, config_epsilon):
        """L=1: lookback of 1 should work."""
        x = rng.standard_normal((20, 1, 3)).astype(np.float32)
        scaler = StandardScaler(epsilon=config_epsilon)
        x_scaled = scaler.fit_transform(x)
        assert x_scaled.shape == (20, 1, 3)

    def test_constant_feature_sigma_threshold_value(self):
        """The constant feature threshold should be 1e-8."""
        assert CONSTANT_FEATURE_SIGMA_THRESHOLD == 1e-8


# ===========================================================================
# Save / Load
# ===========================================================================

class TestSaveLoad:
    """#021 — Serialization of scaler parameters."""

    def test_save_and_load_roundtrip(
        self, x_train_3d, x_val_3d, config_epsilon, tmp_path
    ):
        """Save params, load into new scaler, transform gives same result."""
        scaler1 = StandardScaler(epsilon=config_epsilon)
        scaler1.fit(x_train_3d)
        x_ref = scaler1.transform(x_val_3d)

        path = tmp_path / "scaler_params.npz"
        scaler1.save(path)

        scaler2 = StandardScaler(epsilon=config_epsilon)
        scaler2.load(path)
        x_loaded = scaler2.transform(x_val_3d)

        np.testing.assert_array_equal(x_ref, x_loaded)

    def test_load_restores_mean_and_std(
        self, x_train_3d, config_epsilon, tmp_path
    ):
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)
        path = tmp_path / "params.npz"
        scaler.save(path)

        scaler2 = StandardScaler(epsilon=config_epsilon)
        scaler2.load(path)

        np.testing.assert_array_equal(scaler.mean_, scaler2.mean_)
        np.testing.assert_array_equal(scaler.std_, scaler2.std_)

    def test_save_before_fit_raises(self, config_epsilon, tmp_path):
        """Cannot save parameters before fitting."""
        scaler = StandardScaler(epsilon=config_epsilon)
        with pytest.raises(RuntimeError, match="fit"):
            scaler.save(tmp_path / "params.npz")

    def test_load_nonexistent_file_raises(self, config_epsilon, tmp_path):
        """Loading from nonexistent path → error."""
        scaler = StandardScaler(epsilon=config_epsilon)
        with pytest.raises(FileNotFoundError):
            scaler.load(tmp_path / "nonexistent.npz")

    def test_load_epsilon_mismatch_raises(
        self, x_train_3d, config_epsilon, tmp_path
    ):
        """Load with different epsilon → ValueError."""
        scaler1 = StandardScaler(epsilon=config_epsilon)
        scaler1.fit(x_train_3d)
        path = tmp_path / "params.npz"
        scaler1.save(path)

        scaler2 = StandardScaler(epsilon=1e-6)
        with pytest.raises(ValueError, match="mismatch"):
            scaler2.load(path)


# ===========================================================================
# Float32 consistency
# ===========================================================================

class TestFloat32:
    """#021 — Verify float64 params and float32 output."""

    def test_mean_std_are_float64(self, x_train_3d, config_epsilon):
        """Fitted mean_ and std_ must be float64 (convention P-02)."""
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)
        assert scaler.mean_.dtype == np.float64
        assert scaler.std_.dtype == np.float64


# ===========================================================================
# Inverse transform roundtrip
# ===========================================================================

class TestInverseRoundtrip:
    """#021 — Verify that scaling is reversible via manual inverse."""

    def test_inverse_transform_roundtrip(self, x_train_3d, config_epsilon):
        """(x_scaled * (σ + ε) + μ) must recover the original data."""
        scaler = StandardScaler(epsilon=config_epsilon)
        scaler.fit(x_train_3d)
        x_scaled = scaler.transform(x_train_3d)

        # Manual inverse
        x_recovered = x_scaled * (scaler.std_ + config_epsilon) + scaler.mean_

        # Exclude constant features where information is lost (set to 0.0)
        non_constant = scaler.std_ >= CONSTANT_FEATURE_SIGMA_THRESHOLD
        np.testing.assert_allclose(
            x_recovered[:, :, non_constant],
            x_train_3d[:, :, non_constant],
            atol=1e-4,
            rtol=1e-4,
        )
