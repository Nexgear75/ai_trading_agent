"""Tests for prediction metrics module (ai_trading.metrics.prediction).

Task #040 — WS-10: Prediction metrics (MAE, RMSE, DA, Spearman IC).
Spec §14.1.
"""

import numpy as np
import pytest
from scipy import stats

from ai_trading.metrics.prediction import (
    compute_directional_accuracy,
    compute_mae,
    compute_prediction_metrics,
    compute_rmse,
    compute_spearman_ic,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_vectors():
    """Known y_true / y_hat for deterministic checks."""
    y_true = np.array([1.0, -2.0, 3.0, -4.0, 5.0], dtype=np.float64)
    y_hat = np.array([1.5, -1.5, 2.5, -3.5, 4.5], dtype=np.float64)
    return y_true, y_hat


@pytest.fixture
def perfect_vectors():
    """Perfect predictions."""
    y = np.array([1.0, -2.0, 3.0], dtype=np.float64)
    return y, y.copy()


# ===========================================================================
# compute_mae
# ===========================================================================


class TestComputeMAE:
    """#040 — MAE: mean(|y - ŷ|)."""

    def test_known_values(self, simple_vectors):
        """MAE on known vectors = mean(|0.5, 0.5, 0.5, 0.5, 0.5|) = 0.5."""
        y_true, y_hat = simple_vectors
        result = compute_mae(y_true, y_hat)
        assert result == pytest.approx(0.5)

    def test_perfect_prediction(self, perfect_vectors):
        """MAE = 0 when predictions are perfect."""
        y_true, y_hat = perfect_vectors
        assert compute_mae(y_true, y_hat) == pytest.approx(0.0)

    def test_single_element(self):
        """MAE works with a single element."""
        y_true = np.array([2.0], dtype=np.float64)
        y_hat = np.array([5.0], dtype=np.float64)
        assert compute_mae(y_true, y_hat) == pytest.approx(3.0)

    def test_float64_output(self, simple_vectors):
        """MAE output is float64."""
        y_true, y_hat = simple_vectors
        result = compute_mae(y_true, y_hat)
        assert isinstance(result, float)

    def test_empty_raises(self):
        """MAE raises on empty arrays."""
        y_true = np.array([], dtype=np.float64)
        y_hat = np.array([], dtype=np.float64)
        with pytest.raises(ValueError):
            compute_mae(y_true, y_hat)

    def test_mismatched_lengths_raises(self):
        """MAE raises when lengths differ."""
        y_true = np.array([1.0, 2.0], dtype=np.float64)
        y_hat = np.array([1.0], dtype=np.float64)
        with pytest.raises(ValueError):
            compute_mae(y_true, y_hat)

    def test_nan_in_input_raises(self):
        """MAE raises if NaN present in input."""
        y_true = np.array([1.0, np.nan], dtype=np.float64)
        y_hat = np.array([1.0, 2.0], dtype=np.float64)
        with pytest.raises(ValueError):
            compute_mae(y_true, y_hat)

    def test_inf_in_input_raises(self):
        """MAE raises if inf present in input."""
        y_true = np.array([1.0, np.inf], dtype=np.float64)
        y_hat = np.array([1.0, 2.0], dtype=np.float64)
        with pytest.raises(ValueError):
            compute_mae(y_true, y_hat)


# ===========================================================================
# compute_rmse
# ===========================================================================


class TestComputeRMSE:
    """#040 — RMSE: sqrt(mean((y - ŷ)²))."""

    def test_known_values(self, simple_vectors):
        """RMSE on known vectors = sqrt(mean(0.25*5)) = 0.5."""
        y_true, y_hat = simple_vectors
        result = compute_rmse(y_true, y_hat)
        assert result == pytest.approx(0.5)

    def test_perfect_prediction(self, perfect_vectors):
        """RMSE = 0 when predictions are perfect."""
        y_true, y_hat = perfect_vectors
        assert compute_rmse(y_true, y_hat) == pytest.approx(0.0)

    def test_single_element(self):
        """RMSE works with a single element."""
        y_true = np.array([2.0], dtype=np.float64)
        y_hat = np.array([5.0], dtype=np.float64)
        assert compute_rmse(y_true, y_hat) == pytest.approx(3.0)

    def test_float64_output(self, simple_vectors):
        """RMSE output is float64."""
        y_true, y_hat = simple_vectors
        result = compute_rmse(y_true, y_hat)
        assert isinstance(result, float)

    def test_empty_raises(self):
        """RMSE raises on empty arrays."""
        with pytest.raises(ValueError):
            compute_rmse(
                np.array([], dtype=np.float64),
                np.array([], dtype=np.float64),
            )

    def test_mismatched_lengths_raises(self):
        """RMSE raises when lengths differ."""
        with pytest.raises(ValueError):
            compute_rmse(
                np.array([1.0, 2.0], dtype=np.float64),
                np.array([1.0], dtype=np.float64),
            )

    def test_nan_in_input_raises(self):
        """RMSE raises if NaN present."""
        with pytest.raises(ValueError):
            compute_rmse(
                np.array([1.0, 2.0], dtype=np.float64),
                np.array([1.0, np.nan], dtype=np.float64),
            )


# ===========================================================================
# compute_directional_accuracy
# ===========================================================================


class TestComputeDirectionalAccuracy:
    """#040 — DA: mean(1[sign(y)==sign(ŷ)]) excluding y==0 or ŷ==0."""

    def test_all_same_direction(self):
        """DA = 1.0 when all signs match."""
        y_true = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        y_hat = np.array([0.5, 0.1, 10.0], dtype=np.float64)
        assert compute_directional_accuracy(y_true, y_hat) == pytest.approx(1.0)

    def test_all_wrong_direction(self):
        """DA = 0.0 when no signs match."""
        y_true = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        y_hat = np.array([-0.5, -0.1, -10.0], dtype=np.float64)
        assert compute_directional_accuracy(y_true, y_hat) == pytest.approx(0.0)

    def test_mixed_directions(self):
        """DA on mixed signs."""
        y_true = np.array([1.0, -2.0, 3.0, -4.0], dtype=np.float64)
        y_hat = np.array([0.5, -0.1, -1.0, -0.5], dtype=np.float64)
        # matches: idx 0 (+,+), idx 1 (-,-), idx 3 (-,-) → 3/4 = 0.75
        assert compute_directional_accuracy(y_true, y_hat) == pytest.approx(0.75)

    def test_da_in_01_range(self, simple_vectors):
        """DA ∈ [0, 1] on normal data."""
        y_true, y_hat = simple_vectors
        result = compute_directional_accuracy(y_true, y_hat)
        assert 0.0 <= result <= 1.0

    def test_excludes_y_true_zero(self):
        """Samples with y_true == 0 are excluded."""
        y_true = np.array([0.0, 1.0, -1.0], dtype=np.float64)
        y_hat = np.array([1.0, 1.0, -1.0], dtype=np.float64)
        # Only idx 1 and 2 are eligible, both match → DA = 1.0
        assert compute_directional_accuracy(y_true, y_hat) == pytest.approx(1.0)

    def test_excludes_y_hat_zero(self):
        """Samples with y_hat == 0 are excluded."""
        y_true = np.array([1.0, -1.0, 2.0], dtype=np.float64)
        y_hat = np.array([0.0, -1.0, 2.0], dtype=np.float64)
        # idx 0 excluded (ŷ=0), idx 1 (-,-) match, idx 2 (+,+) match → DA = 1.0
        assert compute_directional_accuracy(y_true, y_hat) == pytest.approx(1.0)

    def test_excludes_both_zero(self):
        """Samples with y_true == 0 AND y_hat == 0 are excluded."""
        y_true = np.array([0.0, 1.0, -1.0], dtype=np.float64)
        y_hat = np.array([0.0, -1.0, -1.0], dtype=np.float64)
        # idx 0 excluded, idx 1 (+,-) no match, idx 2 (-,-) match → 1/2 = 0.5
        assert compute_directional_accuracy(y_true, y_hat) == pytest.approx(0.5)

    def test_all_excluded_returns_none(self):
        """DA returns None if all samples are excluded."""
        y_true = np.array([0.0, 0.0], dtype=np.float64)
        y_hat = np.array([1.0, 2.0], dtype=np.float64)
        assert compute_directional_accuracy(y_true, y_hat) is None

    def test_all_y_hat_zero_returns_none(self):
        """DA returns None if all ŷ are zero."""
        y_true = np.array([1.0, 2.0], dtype=np.float64)
        y_hat = np.array([0.0, 0.0], dtype=np.float64)
        assert compute_directional_accuracy(y_true, y_hat) is None

    def test_float64_output(self):
        """DA output is float (or None)."""
        y_true = np.array([1.0, -1.0], dtype=np.float64)
        y_hat = np.array([1.0, -1.0], dtype=np.float64)
        result = compute_directional_accuracy(y_true, y_hat)
        assert isinstance(result, float)

    def test_empty_raises(self):
        """DA raises on empty arrays."""
        with pytest.raises(ValueError):
            compute_directional_accuracy(
                np.array([], dtype=np.float64),
                np.array([], dtype=np.float64),
            )

    def test_mismatched_lengths_raises(self):
        """DA raises when lengths differ."""
        with pytest.raises(ValueError):
            compute_directional_accuracy(
                np.array([1.0, 2.0], dtype=np.float64),
                np.array([1.0], dtype=np.float64),
            )


# ===========================================================================
# compute_spearman_ic
# ===========================================================================


class TestComputeSpearmanIC:
    """#040 — Spearman IC: corr_spearman(y, ŷ)."""

    def test_perfect_positive_correlation(self):
        """Spearman IC = 1.0 for monotonically increasing pair."""
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        y_hat = np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float64)
        result = compute_spearman_ic(y_true, y_hat)
        assert result == pytest.approx(1.0)

    def test_perfect_negative_correlation(self):
        """Spearman IC = -1.0 for monotonically decreasing pair."""
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        y_hat = np.array([50.0, 40.0, 30.0, 20.0, 10.0], dtype=np.float64)
        result = compute_spearman_ic(y_true, y_hat)
        assert result == pytest.approx(-1.0)

    def test_known_values(self):
        """Spearman IC matches scipy reference."""
        y_true = np.array([1.0, 3.0, 2.0, 5.0, 4.0], dtype=np.float64)
        y_hat = np.array([2.0, 4.0, 1.0, 5.0, 3.0], dtype=np.float64)
        expected = stats.spearmanr(y_true, y_hat).statistic
        result = compute_spearman_ic(y_true, y_hat)
        assert result == pytest.approx(expected)

    def test_float64_output(self):
        """Spearman IC output is float64."""
        y_true = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        y_hat = np.array([3.0, 2.0, 1.0], dtype=np.float64)
        result = compute_spearman_ic(y_true, y_hat)
        assert isinstance(result, float)

    def test_empty_raises(self):
        """Spearman IC raises on empty arrays."""
        with pytest.raises(ValueError):
            compute_spearman_ic(
                np.array([], dtype=np.float64),
                np.array([], dtype=np.float64),
            )

    def test_single_element_raises(self):
        """Spearman IC raises on single-element arrays (undefined correlation)."""
        with pytest.raises(ValueError):
            compute_spearman_ic(
                np.array([1.0], dtype=np.float64),
                np.array([2.0], dtype=np.float64),
            )

    def test_mismatched_lengths_raises(self):
        """Spearman IC raises when lengths differ."""
        with pytest.raises(ValueError):
            compute_spearman_ic(
                np.array([1.0, 2.0], dtype=np.float64),
                np.array([1.0], dtype=np.float64),
            )

    def test_constant_input_raises(self):
        """Spearman IC raises when one input is constant (zero variance)."""
        with pytest.raises(ValueError):
            compute_spearman_ic(
                np.array([1.0, 1.0, 1.0], dtype=np.float64),
                np.array([1.0, 2.0, 3.0], dtype=np.float64),
            )


# ===========================================================================
# compute_prediction_metrics — aggregated
# ===========================================================================


class TestComputePredictionMetrics:
    """#040 — compute_prediction_metrics(y_true, y_hat, output_type)."""

    def test_signal_returns_all_none(self):
        """output_type='signal' → all metrics None."""
        y_true = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        y_hat = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        result = compute_prediction_metrics(y_true, y_hat, output_type="signal")
        assert result["mae"] is None
        assert result["rmse"] is None
        assert result["directional_accuracy"] is None
        assert result["spearman_ic"] is None

    def test_regression_computes_all(self, simple_vectors):
        """output_type='regression' → all metrics computed."""
        y_true, y_hat = simple_vectors
        result = compute_prediction_metrics(y_true, y_hat, output_type="regression")
        assert result["mae"] is not None
        assert result["rmse"] is not None
        assert result["directional_accuracy"] is not None
        assert result["spearman_ic"] is not None

    def test_regression_values_correct(self, simple_vectors):
        """output_type='regression' → computed values match individual functions."""
        y_true, y_hat = simple_vectors
        result = compute_prediction_metrics(y_true, y_hat, output_type="regression")
        assert result["mae"] == pytest.approx(compute_mae(y_true, y_hat))
        assert result["rmse"] == pytest.approx(compute_rmse(y_true, y_hat))
        assert result["directional_accuracy"] == pytest.approx(
            compute_directional_accuracy(y_true, y_hat)
        )
        assert result["spearman_ic"] == pytest.approx(
            compute_spearman_ic(y_true, y_hat)
        )

    def test_regression_dict_keys(self, simple_vectors):
        """Result dict has exactly the expected keys."""
        y_true, y_hat = simple_vectors
        result = compute_prediction_metrics(y_true, y_hat, output_type="regression")
        assert set(result.keys()) == {"mae", "rmse", "directional_accuracy", "spearman_ic"}

    def test_regression_float64_values(self, simple_vectors):
        """All non-None metric values are float."""
        y_true, y_hat = simple_vectors
        result = compute_prediction_metrics(y_true, y_hat, output_type="regression")
        for key, val in result.items():
            if val is not None:
                assert isinstance(val, float), f"{key} should be float, got {type(val)}"

    def test_invalid_output_type_raises(self):
        """Invalid output_type raises ValueError."""
        y_true = np.array([1.0], dtype=np.float64)
        y_hat = np.array([1.0], dtype=np.float64)
        with pytest.raises(ValueError):
            compute_prediction_metrics(y_true, y_hat, output_type="invalid")

    def test_da_none_propagated(self):
        """DA=None propagated when all y_true samples are zero (excluded from DA)."""
        # y_true has zeros mixed with non-zeros: zeros excluded from DA only
        y_true = np.array([0.0, 0.0, 1.0, -1.0], dtype=np.float64)
        y_hat = np.array([1.0, 2.0, 0.0, 0.0], dtype=np.float64)
        # DA: eligible = idx 2 (y=1, ŷ=0 → excluded), idx 3 (y=-1, ŷ=0 → excluded)
        # idx 0, 1: y=0 → excluded. All excluded → DA = None
        result = compute_prediction_metrics(y_true, y_hat, output_type="regression")
        assert result["mae"] is not None
        assert result["rmse"] is not None
        assert result["directional_accuracy"] is None
        assert result["spearman_ic"] is not None

    def test_signal_ignores_inputs(self):
        """output_type='signal' returns None even with valid vectors."""
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        y_hat = np.array([5.0, 4.0, 3.0, 2.0, 1.0], dtype=np.float64)
        result = compute_prediction_metrics(y_true, y_hat, output_type="signal")
        for val in result.values():
            assert val is None
