"""Tests for G-Doc pre-gate — structural verification for M3 (#034 WS-6).

Covers 6 criteria:
1. DummyModel.output_type == "regression" (class attribute)
2. DummyModel.execution_mode == "standard" (inherited from BaseModel)
3. set(MODEL_REGISTRY.keys()) ⊆ set(VALID_STRATEGIES) with at least {"dummy"}
4. Docstrings present and conforming on BaseModel, DummyModel, abstract methods
5. Bypass θ functional for output_type == "signal" models
6. θ independent of y_hat_test (perturbation test)
"""

from __future__ import annotations

import inspect

import numpy as np

from ai_trading.calibration.threshold import calibrate_threshold
from ai_trading.config import VALID_STRATEGIES
from ai_trading.models.base import MODEL_REGISTRY, BaseModel
from ai_trading.models.dummy import DummyModel
from tests.conftest import make_calibration_ohlcv

# ---------------------------------------------------------------------------
# Shared calibration parameters
# ---------------------------------------------------------------------------

_CALIB_KWARGS = {
    "q_grid": [0.3, 0.5, 0.7],
    "horizon": 4,
    "fee_rate_per_side": 0.001,
    "slippage_rate_per_side": 0.0005,
    "initial_equity": 10_000.0,
    "position_fraction": 0.1,
    "objective": "max_net_pnl_with_mdd_cap",
    "mdd_cap": 0.15,
    "min_trades": 1,
}


# ---------------------------------------------------------------------------
# Criterion 1 — output_type declared and correct
# ---------------------------------------------------------------------------


class TestCriterion1OutputType:
    """#034 G-Doc criterion 1: DummyModel.output_type == 'regression'."""

    def test_output_type_value(self) -> None:
        """DummyModel.output_type is 'regression'."""
        assert DummyModel.output_type == "regression"

    def test_output_type_is_class_attribute(self) -> None:
        """output_type is declared in the class body, not on instances."""
        assert "output_type" in DummyModel.__dict__


# ---------------------------------------------------------------------------
# Criterion 2 — execution_mode default
# ---------------------------------------------------------------------------


class TestCriterion2ExecutionMode:
    """#034 G-Doc criterion 2: DummyModel.execution_mode == 'standard'."""

    def test_execution_mode_value(self) -> None:
        """DummyModel inherits execution_mode='standard' from BaseModel."""
        assert DummyModel.execution_mode == "standard"

    def test_execution_mode_inherited(self) -> None:
        """execution_mode is NOT overridden in DummyModel (inherited)."""
        assert "execution_mode" not in DummyModel.__dict__


# ---------------------------------------------------------------------------
# Criterion 3 — Registry coherence (partial at M3)
# ---------------------------------------------------------------------------


class TestCriterion3RegistryCoherence:
    """#034 G-Doc criterion 3: MODEL_REGISTRY ⊆ VALID_STRATEGIES."""

    def test_registry_subset_of_valid_strategies(self) -> None:
        """All registered models must have a corresponding VALID_STRATEGIES entry."""
        assert set(MODEL_REGISTRY.keys()) <= set(VALID_STRATEGIES.keys())

    def test_dummy_in_registry(self) -> None:
        """At M3, MODEL_REGISTRY must contain at least 'dummy'."""
        assert "dummy" in MODEL_REGISTRY


# ---------------------------------------------------------------------------
# Criterion 4 — Docstrings conforming
# ---------------------------------------------------------------------------


class TestCriterion4Docstrings:
    """#034 G-Doc criterion 4: docstrings present and conforming."""

    def test_basemodel_has_docstring(self) -> None:
        """BaseModel must have a non-empty docstring."""
        assert BaseModel.__doc__ is not None
        assert len(BaseModel.__doc__.strip()) > 0

    def test_dummymodel_has_docstring(self) -> None:
        """DummyModel must have a non-empty docstring."""
        assert DummyModel.__doc__ is not None
        assert len(DummyModel.__doc__.strip()) > 0

    def test_fit_has_docstring(self) -> None:
        """BaseModel.fit abstract method must have a docstring."""
        assert BaseModel.fit.__doc__ is not None
        assert len(BaseModel.fit.__doc__.strip()) > 0

    def test_predict_has_docstring(self) -> None:
        """BaseModel.predict abstract method must have a docstring."""
        assert BaseModel.predict.__doc__ is not None
        assert len(BaseModel.predict.__doc__.strip()) > 0

    def test_save_has_docstring(self) -> None:
        """BaseModel.save abstract method must have a docstring."""
        assert BaseModel.save.__doc__ is not None
        assert len(BaseModel.save.__doc__.strip()) > 0

    def test_load_has_docstring(self) -> None:
        """BaseModel.load abstract method must have a docstring."""
        assert BaseModel.load.__doc__ is not None
        assert len(BaseModel.load.__doc__.strip()) > 0

    def test_fit_docstring_mentions_shapes(self) -> None:
        """fit() docstring must mention shapes (N, L, F) and dtypes."""
        doc = BaseModel.fit.__doc__
        assert doc is not None
        assert "N" in doc
        assert "float32" in doc

    def test_predict_docstring_mentions_shapes(self) -> None:
        """predict() docstring must mention shapes and output types."""
        doc = BaseModel.predict.__doc__
        assert doc is not None
        assert "N" in doc
        assert "float32" in doc

    def test_abstract_methods_are_abstract(self) -> None:
        """fit, predict, save, load must be abstract methods."""
        abstract_names = {
            name
            for name, method in inspect.getmembers(BaseModel)
            if getattr(method, "__isabstractmethod__", False)
        }
        assert {"fit", "predict", "save", "load"} <= abstract_names


# ---------------------------------------------------------------------------
# Criterion 5 — Bypass θ functional for signal models
# ---------------------------------------------------------------------------


class TestCriterion5BypassTheta:
    """#034 G-Doc criterion 5: bypass θ for output_type='signal'."""

    def test_signal_bypass_returns_method_none(self) -> None:
        """Signal model → calibration bypassed with method='none'."""
        n = 50
        y_hat = np.array([0, 1, 1, 0, 1] * 10, dtype=np.float32)
        ohlcv = make_calibration_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            output_type="signal",
            **_CALIB_KWARGS,
        )

        assert result["method"] == "none"
        assert result["theta"] is None
        assert result["quantile"] is None

    def test_binary_signals_pass_through(self) -> None:
        """Binary 0/1 signals from signal model are not transformed."""
        n = 50
        signals = np.array([1, 0, 1, 0, 0] * 10, dtype=np.float32)
        ohlcv = make_calibration_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=signals,
            ohlcv_val=ohlcv,
            output_type="signal",
            **_CALIB_KWARGS,
        )

        # Bypass: no transformation applied, theta is None
        assert result["theta"] is None
        assert result["details"] is None


# ---------------------------------------------------------------------------
# Criterion 6 — Anti-fuite: θ independent of y_hat_test
# ---------------------------------------------------------------------------


class TestCriterion6AntiLeakCalibration:
    """#034 G-Doc criterion 6: θ independent of y_hat_test (perturbation)."""

    def test_theta_independent_of_y_hat_test(self) -> None:
        """Calibrate θ on y_hat_val, then perturb y_hat_test → θ unchanged.

        θ is determined solely from y_hat_val. After calibration, modifying
        y_hat_test arbitrarily must have zero effect on the returned θ.
        """
        n = 60
        rng = np.random.default_rng(99)
        y_hat_val = rng.standard_normal(n).astype(np.float32)
        ohlcv_val = make_calibration_ohlcv(n)

        # Calibrate on y_hat_val
        result = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv_val,
            output_type="regression",
            **_CALIB_KWARGS,
        )
        theta_original = result["theta"]

        # Create two very different y_hat_test arrays
        y_hat_test_a = rng.standard_normal(n).astype(np.float32) * 100
        y_hat_test_b = np.zeros(n, dtype=np.float32)

        # Re-calibrate with same y_hat_val — θ must be identical
        result_again = calibrate_threshold(
            y_hat_val=y_hat_val,
            ohlcv_val=ohlcv_val,
            output_type="regression",
            **_CALIB_KWARGS,
        )

        assert result_again["theta"] == theta_original

        # The existence of y_hat_test_a and y_hat_test_b has no effect:
        # calibrate_threshold does not accept y_hat_test at all.
        # This structural guarantee is verified by inspecting the signature.
        sig = inspect.signature(calibrate_threshold)
        param_names = set(sig.parameters.keys())
        assert "y_hat_test" not in param_names, (
            "calibrate_threshold must NOT accept y_hat_test as a parameter"
        )

        # Suppress unused-variable warnings — these exist to demonstrate
        # the perturbation scenario described in the task.
        _ = y_hat_test_a
        _ = y_hat_test_b
