"""Tests for quantile-grid threshold calibration (#030 WS-7).

Covers:
- compute_quantile_thresholds: median, min, max, full grid, errors
- apply_threshold: positive, negative, boundary, shape, errors
- Config integration: q_grid from ThresholdingConfig
"""

import numpy as np
import pytest

from ai_trading.calibration.threshold import apply_threshold, compute_quantile_thresholds
from ai_trading.config import load_config

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def y_hat_val() -> np.ndarray:
    """Deterministic predictions for validation (100 values, 0..99)."""
    return np.arange(100, dtype=np.float64)


@pytest.fixture()
def default_config():
    """Load default pipeline config."""
    return load_config("configs/default.yaml")


# ---------------------------------------------------------------------------
# compute_quantile_thresholds — nominal
# ---------------------------------------------------------------------------

class TestComputeQuantileThresholds:
    """Tests for compute_quantile_thresholds."""

    def test_quantile_median(self, y_hat_val: np.ndarray) -> None:
        """q=0.5 gives median of y_hat_val."""
        result = compute_quantile_thresholds(y_hat_val, [0.5])
        expected = float(np.median(y_hat_val))
        assert result[0.5] == pytest.approx(expected)

    def test_quantile_min(self, y_hat_val: np.ndarray) -> None:
        """q=0.0 gives min of y_hat_val."""
        result = compute_quantile_thresholds(y_hat_val, [0.0])
        assert result[0.0] == pytest.approx(float(np.min(y_hat_val)))

    def test_quantile_max(self, y_hat_val: np.ndarray) -> None:
        """q=1.0 gives max of y_hat_val."""
        result = compute_quantile_thresholds(y_hat_val, [1.0])
        assert result[1.0] == pytest.approx(float(np.max(y_hat_val)))

    def test_full_grid(self, y_hat_val: np.ndarray) -> None:
        """Complete grid computed correctly for all quantiles."""
        q_grid = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        result = compute_quantile_thresholds(y_hat_val, q_grid)
        assert len(result) == len(q_grid)
        for q in q_grid:
            expected = float(np.quantile(y_hat_val, q))
            assert result[q] == pytest.approx(expected), f"Mismatch for q={q}"

    def test_return_type_float64(self, y_hat_val: np.ndarray) -> None:
        """Threshold values are Python floats (float64 precision)."""
        result = compute_quantile_thresholds(y_hat_val, [0.5])
        assert isinstance(result[0.5], float)

    def test_single_element_y_hat_val(self) -> None:
        """Single-element array: all quantiles return same value."""
        y = np.array([42.0])
        result = compute_quantile_thresholds(y, [0.0, 0.5, 1.0])
        for q in [0.0, 0.5, 1.0]:
            assert result[q] == pytest.approx(42.0)

    def test_all_identical_values(self) -> None:
        """All-identical values: all quantiles return same value."""
        y = np.full(50, 7.7)
        result = compute_quantile_thresholds(y, [0.0, 0.25, 0.5, 0.75, 1.0])
        for q in result:
            assert result[q] == pytest.approx(7.7)


# ---------------------------------------------------------------------------
# compute_quantile_thresholds — errors
# ---------------------------------------------------------------------------

class TestComputeQuantileThresholdsErrors:
    """Error cases for compute_quantile_thresholds."""

    def test_empty_y_hat_val_raises(self) -> None:
        """Empty y_hat_val raises ValueError."""
        with pytest.raises(ValueError, match="y_hat_val"):
            compute_quantile_thresholds(np.array([], dtype=np.float64), [0.5])

    def test_empty_q_grid_raises(self) -> None:
        """Empty q_grid raises ValueError."""
        with pytest.raises(ValueError, match="q_grid"):
            compute_quantile_thresholds(np.arange(10, dtype=np.float64), [])

    def test_2d_y_hat_val_raises(self) -> None:
        """2D y_hat_val raises ValueError."""
        with pytest.raises(ValueError, match="1D"):
            compute_quantile_thresholds(
                np.arange(10, dtype=np.float64).reshape(2, 5), [0.5]
            )

    def test_q_out_of_range_low_raises(self) -> None:
        """q < 0 raises ValueError."""
        with pytest.raises(ValueError, match="q_grid"):
            compute_quantile_thresholds(np.arange(10, dtype=np.float64), [-0.1])

    def test_q_out_of_range_high_raises(self) -> None:
        """q > 1 raises ValueError."""
        with pytest.raises(ValueError, match="q_grid"):
            compute_quantile_thresholds(np.arange(10, dtype=np.float64), [1.1])


# ---------------------------------------------------------------------------
# apply_threshold — nominal
# ---------------------------------------------------------------------------

class TestApplyThreshold:
    """Tests for apply_threshold."""

    def test_apply_threshold_positive(self) -> None:
        """y_hat > theta → 1."""
        y_hat = np.array([1.0, 2.0, 3.0])
        signals = apply_threshold(y_hat, 0.5)
        np.testing.assert_array_equal(signals, np.array([1, 1, 1]))

    def test_apply_threshold_negative(self) -> None:
        """y_hat <= theta → 0."""
        y_hat = np.array([0.1, 0.2, 0.3])
        signals = apply_threshold(y_hat, 0.5)
        np.testing.assert_array_equal(signals, np.array([0, 0, 0]))

    def test_apply_threshold_mixed(self) -> None:
        """Mixed case: some above, some below."""
        y_hat = np.array([0.1, 0.6, 0.3, 0.9])
        signals = apply_threshold(y_hat, 0.5)
        np.testing.assert_array_equal(signals, np.array([0, 1, 0, 1]))

    def test_apply_threshold_boundary(self) -> None:
        """y_hat == theta → 0 (strict >)."""
        y_hat = np.array([0.5, 0.5, 0.5])
        signals = apply_threshold(y_hat, 0.5)
        np.testing.assert_array_equal(signals, np.array([0, 0, 0]))

    def test_apply_threshold_same_shape(self) -> None:
        """Output shape matches input shape."""
        y_hat = np.arange(50, dtype=np.float64)
        signals = apply_threshold(y_hat, 25.0)
        assert signals.shape == y_hat.shape

    def test_apply_threshold_dtype_int32(self) -> None:
        """Output dtype is int32."""
        y_hat = np.array([0.1, 0.9])
        signals = apply_threshold(y_hat, 0.5)
        assert signals.dtype == np.int32


# ---------------------------------------------------------------------------
# apply_threshold — errors
# ---------------------------------------------------------------------------

class TestApplyThresholdErrors:
    """Error cases for apply_threshold."""

    def test_2d_y_hat_raises(self) -> None:
        """2D y_hat raises ValueError."""
        with pytest.raises(ValueError, match="1D"):
            apply_threshold(np.arange(10, dtype=np.float64).reshape(2, 5), 0.5)


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------

class TestConfigIntegration:
    """Test q_grid parameters read from config."""

    def test_q_grid_from_config(self, default_config) -> None:
        """q_grid from config can be used with compute_quantile_thresholds."""
        q_grid = default_config.thresholding.q_grid
        y = np.arange(100, dtype=np.float64)
        result = compute_quantile_thresholds(y, q_grid)
        assert len(result) == len(q_grid)
        for q in q_grid:
            assert q in result

    def test_config_q_grid_values(self, default_config) -> None:
        """Config q_grid matches expected default values."""
        expected = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
        assert default_config.thresholding.q_grid == expected
