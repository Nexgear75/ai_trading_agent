"""Tests for bypass calibration θ for signal models (#033 WS-7).

Covers:
- output_type == "signal" → calibration θ totally bypassed
- output_type == "regression" → normal calibration
- Bypass return: method="none", theta=None, quantile=None
- Binary signals (0/1) passed through without transformation
- No branching on strategy.name — only on output_type
- Edge cases: all-zero signals, all-one signals
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from ai_trading.calibration.threshold import calibrate_threshold
from ai_trading.models.base import BaseModel

# ---------------------------------------------------------------------------
# Helpers — signal model stub
# ---------------------------------------------------------------------------


class _SignalModelStub(BaseModel):
    """Fake model with output_type='signal' for testing bypass."""

    output_type = "signal"

    def __init__(self, predictions: np.ndarray) -> None:
        self._predictions = predictions

    def fit(
        self,
        X_train: np.ndarray,  # noqa: N803
        y_train: np.ndarray,
        X_val: np.ndarray,  # noqa: N803
        y_val: np.ndarray,
        config: Any,
        run_dir: Path,
        meta_train: Any = None,
        meta_val: Any = None,
        ohlcv: Any = None,
    ) -> dict:
        return {}

    def predict(
        self,
        X: np.ndarray,  # noqa: N803
        meta: Any = None,
        ohlcv: Any = None,
    ) -> np.ndarray:
        return self._predictions

    def save(self, path: Path) -> None:
        pass

    def load(self, path: Path) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers — OHLCV builder
# ---------------------------------------------------------------------------

HORIZON = 4


def _make_ohlcv(n: int, start: str = "2024-01-01") -> pd.DataFrame:
    """Synthetic OHLCV with deterministic prices."""
    idx = pd.date_range(start, periods=n, freq="1h")
    rng = np.random.default_rng(42)
    close = 100.0 + np.cumsum(rng.standard_normal(n) * 0.5)
    close = np.abs(close) + 50.0
    opens = close + rng.standard_normal(n) * 0.1
    opens = np.abs(opens) + 50.0
    return pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, close) + 0.5,
            "low": np.minimum(opens, close) - 0.5,
            "close": close,
            "volume": rng.uniform(100, 1000, n),
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# Tests — bypass for signal models
# ---------------------------------------------------------------------------


class TestCalibrateThetaBypassSignal:
    """#033 — output_type='signal' → calibration θ totally bypassed."""

    def test_bypass_returns_method_none(self) -> None:
        """Bypass returns method='none'."""
        n = 50
        y_hat = np.array([0, 1, 1, 0, 1] * 10, dtype=np.float32)
        ohlcv = _make_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.15,
            min_trades=1,
            output_type="signal",
        )

        assert result["method"] == "none"

    def test_bypass_returns_theta_none(self) -> None:
        """Bypass returns theta=None."""
        n = 50
        y_hat = np.array([0, 1, 1, 0, 1] * 10, dtype=np.float32)
        ohlcv = _make_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.15,
            min_trades=1,
            output_type="signal",
        )

        assert result["theta"] is None

    def test_bypass_returns_quantile_none(self) -> None:
        """Bypass returns quantile=None."""
        n = 50
        y_hat = np.array([0, 1, 1, 0, 1] * 10, dtype=np.float32)
        ohlcv = _make_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.15,
            min_trades=1,
            output_type="signal",
        )

        assert result["quantile"] is None

    def test_bypass_no_details(self) -> None:
        """Bypass result has no quantile details (no grid evaluation)."""
        n = 50
        y_hat = np.array([0, 1, 1, 0, 1] * 10, dtype=np.float32)
        ohlcv = _make_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.15,
            min_trades=1,
            output_type="signal",
        )

        assert result["details"] is None

    def test_bypass_all_zero_signals(self) -> None:
        """All-zero signals: bypass still works, returning method='none'."""
        n = 50
        y_hat = np.zeros(n, dtype=np.float32)
        ohlcv = _make_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.15,
            min_trades=1,
            output_type="signal",
        )

        assert result["method"] == "none"
        assert result["theta"] is None

    def test_bypass_all_one_signals(self) -> None:
        """All-one signals: bypass still works, returning method='none'."""
        n = 50
        y_hat = np.ones(n, dtype=np.float32)
        ohlcv = _make_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.15,
            min_trades=1,
            output_type="signal",
        )

        assert result["method"] == "none"
        assert result["theta"] is None


# ---------------------------------------------------------------------------
# Tests — normal calibration for regression models
# ---------------------------------------------------------------------------


class TestCalibrateThetaRegressionNormal:
    """#033 — output_type='regression' → normal calibration executed."""

    def test_regression_calibration_has_method_quantile_grid(self) -> None:
        """Regression model: calibration returns method != 'none'."""
        n = 50
        rng = np.random.default_rng(123)
        y_hat = rng.standard_normal(n).astype(np.float64)
        ohlcv = _make_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.50,
            min_trades=0,
            output_type="regression",
        )

        # Method must not be "none" — it should be quantile_grid or a fallback
        assert result["method"] != "none"

    def test_regression_calibration_has_theta_float(self) -> None:
        """Regression model: calibration returns a numeric theta."""
        n = 50
        rng = np.random.default_rng(123)
        y_hat = rng.standard_normal(n).astype(np.float64)
        ohlcv = _make_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.50,
            min_trades=0,
            output_type="regression",
        )

        assert result["theta"] is not None
        assert isinstance(result["theta"], float)

    def test_regression_calibration_has_details(self) -> None:
        """Regression model: calibration returns details list."""
        n = 50
        rng = np.random.default_rng(123)
        y_hat = rng.standard_normal(n).astype(np.float64)
        ohlcv = _make_ohlcv(n)

        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.50,
            min_trades=0,
            output_type="regression",
        )

        assert result["details"] is not None
        assert isinstance(result["details"], list)
        assert len(result["details"]) == 3  # one per quantile


# ---------------------------------------------------------------------------
# Tests — output_type validation
# ---------------------------------------------------------------------------


class TestCalibrateThetaOutputTypeValidation:
    """#033 — output_type param is validated."""

    def test_invalid_output_type_raises(self) -> None:
        """Invalid output_type raises ValueError."""
        n = 50
        y_hat = np.zeros(n, dtype=np.float32)
        ohlcv = _make_ohlcv(n)

        with pytest.raises(ValueError, match="output_type"):
            calibrate_threshold(
                y_hat_val=y_hat,
                ohlcv_val=ohlcv,
                q_grid=[0.5],
                horizon=HORIZON,
                fee_rate_per_side=0.001,
                slippage_rate_per_side=0.0005,
                initial_equity=10000.0,
                position_fraction=0.1,
                objective="max_net_pnl_with_mdd_cap",
                mdd_cap=0.15,
                min_trades=1,
                output_type="invalid_type",
            )

    def test_default_output_type_is_regression(self) -> None:
        """When output_type not provided, default behavior is regression calibration."""
        n = 50
        rng = np.random.default_rng(123)
        y_hat = rng.standard_normal(n).astype(np.float64)
        ohlcv = _make_ohlcv(n)

        # Call without output_type → should behave as regression (backward compat)
        result = calibrate_threshold(
            y_hat_val=y_hat,
            ohlcv_val=ohlcv,
            q_grid=[0.5, 0.7, 0.9],
            horizon=HORIZON,
            fee_rate_per_side=0.001,
            slippage_rate_per_side=0.0005,
            initial_equity=10000.0,
            position_fraction=0.1,
            objective="max_net_pnl_with_mdd_cap",
            mdd_cap=0.50,
            min_trades=0,
        )

        assert result["method"] != "none"


# ---------------------------------------------------------------------------
# Tests — signal model stub verifies output_type attribute
# ---------------------------------------------------------------------------


class TestSignalModelStubIntegration:
    """#033 — Verify _SignalModelStub has output_type='signal'."""

    def test_signal_model_output_type(self) -> None:
        """Signal model stub declares output_type='signal'."""
        model = _SignalModelStub(np.array([0, 1], dtype=np.float32))
        assert model.output_type == "signal"

    def test_signal_model_predictions_are_binary(self) -> None:
        """Signal model stub returns binary predictions unchanged."""
        preds = np.array([0, 1, 1, 0], dtype=np.float32)
        model = _SignalModelStub(preds)
        x_dummy = np.zeros((4, 5, 3), dtype=np.float32)
        y_hat = model.predict(x_dummy)
        np.testing.assert_array_equal(y_hat, preds)


class TestDummyModelRegressionCalibration:
    """#033 — DummyModel (output_type='regression') → normal calibration."""

    def test_dummy_model_is_regression(self) -> None:
        """DummyModel declares output_type='regression'."""
        from ai_trading.models.dummy import DummyModel

        model = DummyModel()
        assert model.__class__.__dict__["output_type"] == "regression"
