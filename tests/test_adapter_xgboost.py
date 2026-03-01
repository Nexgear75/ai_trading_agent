"""Tests for XGBoost tabular adapter — flatten_seq_to_tab.

Task #017 — WS-4: flatten 3D tensor (N, L, F) to 2D (N, L*F) for XGBoost.
"""

from __future__ import annotations

import numpy as np
import pytest

from ai_trading.data.dataset import flatten_seq_to_tab

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_x_seq(
    n_samples: int, seq_len: int, n_features: int, seed: int = 42
) -> np.ndarray:
    """Create a synthetic 3D float32 tensor (N, L, F)."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal((n_samples, seq_len, n_features)).astype(np.float32)


# ---------------------------------------------------------------------------
# Test: nominal — shape correctness
# ---------------------------------------------------------------------------


class TestNominalShape:
    """#017 — Verify output shape (N, L*F)."""

    def test_shape_basic(self):
        """Shape should be (N, L*F) for basic input."""
        x_seq = _make_x_seq(10, 4, 3)
        feature_names = ["logret", "vol", "rsi"]
        x_tab, _ = flatten_seq_to_tab(x_seq, feature_names)
        assert x_tab.shape == (10, 4 * 3)

    def test_shape_spec_example(self):
        """Shape with L=128, F=9 must yield 1152 columns."""
        x_seq = _make_x_seq(5, 128, 9)
        feature_names = [f"feat_{i}" for i in range(9)]
        x_tab, col_names = flatten_seq_to_tab(x_seq, feature_names)
        assert x_tab.shape == (5, 128 * 9)
        assert len(col_names) == 1152

    def test_single_sample(self):
        """N=1 should produce shape (1, L*F)."""
        x_seq = _make_x_seq(1, 4, 2)
        x_tab, _ = flatten_seq_to_tab(x_seq, ["a", "b"])
        assert x_tab.shape == (1, 8)


# ---------------------------------------------------------------------------
# Test: nominal — column naming convention
# ---------------------------------------------------------------------------


class TestColumnNaming:
    """#017 — Verify column names follow {feature}_{lag} convention."""

    def test_column_names_c_order(self):
        """Columns must be in C-order: iterating lag first, then features."""
        x_seq = _make_x_seq(3, 2, 3)
        feature_names = ["logret", "vol", "rsi"]
        _, col_names = flatten_seq_to_tab(x_seq, feature_names)
        # C-order: for each row in (L, F), flatten means lag varies slowest
        # np.reshape(x[i], (L*F,)) in C-order: [lag0_feat0, lag0_feat1, lag0_feat2, lag1_feat0, ...]
        expected = [
            "logret_0", "vol_0", "rsi_0",
            "logret_1", "vol_1", "rsi_1",
        ]
        assert col_names == expected

    def test_column_names_longer(self):
        """Verify naming with L=3, F=2."""
        x_seq = _make_x_seq(2, 3, 2)
        feature_names = ["a", "b"]
        _, col_names = flatten_seq_to_tab(x_seq, feature_names)
        expected = ["a_0", "b_0", "a_1", "b_1", "a_2", "b_2"]
        assert col_names == expected

    def test_column_count_matches_shape(self):
        """Number of column names must match X_tab.shape[1]."""
        x_seq = _make_x_seq(4, 5, 7)
        feature_names = [f"f{i}" for i in range(7)]
        x_tab, col_names = flatten_seq_to_tab(x_seq, feature_names)
        assert len(col_names) == x_tab.shape[1]


# ---------------------------------------------------------------------------
# Test: nominal — values match C-order reshape
# ---------------------------------------------------------------------------


class TestValues:
    """#017 — Verify values are identical to np.reshape C-order."""

    def test_values_match_reshape(self):
        """X_tab values must match np.reshape(X_seq, (N, L*F))."""
        x_seq = _make_x_seq(8, 4, 3)
        feature_names = ["a", "b", "c"]
        x_tab, _ = flatten_seq_to_tab(x_seq, feature_names)
        expected = np.reshape(x_seq, (8, 4 * 3))
        np.testing.assert_array_equal(x_tab, expected)

    def test_values_single_feature(self):
        """F=1: X_tab should be X_seq squeezed on last axis."""
        x_seq = _make_x_seq(5, 3, 1)
        x_tab, _ = flatten_seq_to_tab(x_seq, ["only"])
        expected = np.reshape(x_seq, (5, 3))
        np.testing.assert_array_equal(x_tab, expected)

    def test_values_single_lag(self):
        """L=1: X_tab should be X_seq squeezed on lag axis."""
        x_seq = _make_x_seq(5, 1, 4)
        x_tab, _ = flatten_seq_to_tab(x_seq, ["a", "b", "c", "d"])
        expected = np.reshape(x_seq, (5, 4))
        np.testing.assert_array_equal(x_tab, expected)


# ---------------------------------------------------------------------------
# Test: dtype preservation
# ---------------------------------------------------------------------------


class TestDtype:
    """#017 — Verify dtype is preserved (float32)."""

    def test_dtype_float32_preserved(self):
        """Input float32 → output float32."""
        x_seq = _make_x_seq(3, 2, 2)
        assert x_seq.dtype == np.float32
        x_tab, _ = flatten_seq_to_tab(x_seq, ["a", "b"])
        assert x_tab.dtype == np.float32

    def test_dtype_float64_preserved(self):
        """Input float64 → output float64."""
        x_seq = _make_x_seq(3, 2, 2).astype(np.float64)
        x_tab, _ = flatten_seq_to_tab(x_seq, ["a", "b"])
        assert x_tab.dtype == np.float64


# ---------------------------------------------------------------------------
# Test: error — non-3D input
# ---------------------------------------------------------------------------


class TestErrorNon3D:
    """#017 — X_seq must be 3D, otherwise ValueError."""

    def test_2d_raises(self):
        """2D array should raise ValueError."""
        x_2d = np.ones((5, 3), dtype=np.float32)
        with pytest.raises(ValueError, match="3D"):
            flatten_seq_to_tab(x_2d, ["a", "b", "c"])

    def test_1d_raises(self):
        """1D array should raise ValueError."""
        x_1d = np.ones((10,), dtype=np.float32)
        with pytest.raises(ValueError, match="3D"):
            flatten_seq_to_tab(x_1d, ["a"])

    def test_4d_raises(self):
        """4D array should raise ValueError."""
        x_4d = np.ones((2, 3, 4, 5), dtype=np.float32)
        with pytest.raises(ValueError, match="3D"):
            flatten_seq_to_tab(x_4d, ["a", "b", "c", "d"])


# ---------------------------------------------------------------------------
# Test: error — feature_names size mismatch
# ---------------------------------------------------------------------------


class TestErrorFeatureNamesMismatch:
    """#017 — feature_names must have exactly F elements."""

    def test_too_few_names(self):
        """Fewer feature names than F should raise ValueError."""
        x_seq = _make_x_seq(3, 2, 4)
        with pytest.raises(ValueError, match="feature_names"):
            flatten_seq_to_tab(x_seq, ["a", "b"])

    def test_too_many_names(self):
        """More feature names than F should raise ValueError."""
        x_seq = _make_x_seq(3, 2, 2)
        with pytest.raises(ValueError, match="feature_names"):
            flatten_seq_to_tab(x_seq, ["a", "b", "c"])

    def test_empty_names_for_nonzero_features(self):
        """Empty feature_names with F>0 should raise ValueError."""
        x_seq = _make_x_seq(3, 2, 2)
        with pytest.raises(ValueError, match="feature_names"):
            flatten_seq_to_tab(x_seq, [])


# ---------------------------------------------------------------------------
# Test: boundary — edge cases
# ---------------------------------------------------------------------------


class TestBoundary:
    """#017 — Edge cases: N=0, L=1, F=1."""

    def test_zero_samples(self):
        """N=0 should produce (0, L*F) shape."""
        x_seq = np.empty((0, 4, 3), dtype=np.float32)
        x_tab, col_names = flatten_seq_to_tab(x_seq, ["a", "b", "c"])
        assert x_tab.shape == (0, 12)
        assert len(col_names) == 12

    def test_l1_f1(self):
        """L=1, F=1 should produce (N, 1)."""
        x_seq = _make_x_seq(5, 1, 1)
        x_tab, col_names = flatten_seq_to_tab(x_seq, ["only"])
        assert x_tab.shape == (5, 1)
        assert col_names == ["only_0"]
        np.testing.assert_array_equal(x_tab, x_seq.reshape(5, 1))
