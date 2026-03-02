"""Tests for NoTradeBaseline — Task #037 (WS-9).

Covers:
- Inheritance from BaseModel, output_type, execution_mode
- fit() is a no-op returning empty dict
- predict() returns np.zeros(N, dtype=float32)
- save()/load() roundtrip
- Registry: "no_trade" resolves via get_model_class
- Backtest integration: 0 trades, equity constant 1.0, net_pnl=0, MDD=0
- Edge cases: empty input, single sample
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_trading.models.base import MODEL_REGISTRY, BaseModel, get_model_class

# ---------------------------------------------------------------------------
# Registry cleanup fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_model_registry():
    """Save, clear, and restore MODEL_REGISTRY around each test."""
    saved = dict(MODEL_REGISTRY)
    MODEL_REGISTRY.clear()
    yield
    MODEL_REGISTRY.clear()
    MODEL_REGISTRY.update(saved)


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

_RNG = np.random.default_rng(777)
_N, _L, _F = 30, 5, 3
_X = _RNG.standard_normal((_N, _L, _F)).astype(np.float32)
_Y = _RNG.standard_normal((_N,)).astype(np.float32)
_X_VAL = _RNG.standard_normal((10, _L, _F)).astype(np.float32)
_Y_VAL = _RNG.standard_normal((10,)).astype(np.float32)


def _import_no_trade():
    """Import the no_trade module to trigger registration."""
    import importlib

    import ai_trading.baselines.no_trade as mod

    # Ensure key is absent before reload (reload re-executes @register_model)
    MODEL_REGISTRY.pop("no_trade", None)
    importlib.reload(mod)
    return mod.NoTradeBaseline


# ---------------------------------------------------------------------------
# Tests — Class attributes & inheritance
# ---------------------------------------------------------------------------


class TestNoTradeAttributes:
    """#037 — NoTradeBaseline class attributes and inheritance."""

    def test_inherits_base_model(self):
        """NoTradeBaseline must be a subclass of BaseModel."""
        cls = _import_no_trade()
        assert issubclass(cls, BaseModel)

    def test_output_type_is_signal(self):
        """output_type must be 'signal'."""
        cls = _import_no_trade()
        assert cls.output_type == "signal"

    def test_execution_mode_is_standard(self):
        """execution_mode must be 'standard'."""
        cls = _import_no_trade()
        assert cls.execution_mode == "standard"


# ---------------------------------------------------------------------------
# Tests — Registry
# ---------------------------------------------------------------------------


class TestNoTradeRegistry:
    """#037 — NoTradeBaseline is registered as 'no_trade'."""

    def test_registered_in_model_registry(self):
        """After import, 'no_trade' must be in MODEL_REGISTRY."""
        cls = _import_no_trade()
        assert "no_trade" in MODEL_REGISTRY
        assert MODEL_REGISTRY["no_trade"] is cls

    def test_get_model_class_resolves(self):
        """get_model_class('no_trade') must return NoTradeBaseline."""
        cls = _import_no_trade()
        resolved = get_model_class("no_trade")
        assert resolved is cls


# ---------------------------------------------------------------------------
# Tests — fit()
# ---------------------------------------------------------------------------


class TestNoTradeFit:
    """#037 — fit() is a no-op."""

    def test_fit_returns_empty_dict(self, tmp_path):
        """fit() must return an empty dict (no artifacts)."""
        cls = _import_no_trade()
        model = cls()
        result = model.fit(
            X_train=_X,
            y_train=_Y,
            X_val=_X_VAL,
            y_val=_Y_VAL,
            config=None,
            run_dir=tmp_path,
        )
        assert result == {}

    def test_fit_does_not_modify_state(self, tmp_path):
        """fit() must not alter any internal state."""
        cls = _import_no_trade()
        model = cls()
        # Call fit twice — predict should be the same both times
        model.fit(_X, _Y, _X_VAL, _Y_VAL, config=None, run_dir=tmp_path)
        pred1 = model.predict(_X)
        model.fit(_X, _Y, _X_VAL, _Y_VAL, config=None, run_dir=tmp_path)
        pred2 = model.predict(_X)
        np.testing.assert_array_equal(pred1, pred2)


# ---------------------------------------------------------------------------
# Tests — predict()
# ---------------------------------------------------------------------------


class TestNoTradePredict:
    """#037 — predict() returns zeros."""

    def test_predict_returns_zeros(self):
        """predict(X) must return np.zeros(N, dtype=float32)."""
        cls = _import_no_trade()
        model = cls()
        y_hat = model.predict(_X)
        expected = np.zeros(_N, dtype=np.float32)
        np.testing.assert_array_equal(y_hat, expected)

    def test_predict_dtype_float32(self):
        """predict output must be float32."""
        cls = _import_no_trade()
        model = cls()
        y_hat = model.predict(_X)
        assert y_hat.dtype == np.float32

    def test_predict_shape(self):
        """predict output must have shape (N,)."""
        cls = _import_no_trade()
        model = cls()
        y_hat = model.predict(_X)
        assert y_hat.shape == (_N,)

    def test_predict_empty_input(self):
        """predict with N=0 must return shape (0,)."""
        cls = _import_no_trade()
        model = cls()
        x_empty = np.zeros((0, _L, _F), dtype=np.float32)
        y_hat = model.predict(x_empty)
        assert y_hat.shape == (0,)
        assert y_hat.dtype == np.float32

    def test_predict_single_sample(self):
        """predict works with N=1."""
        cls = _import_no_trade()
        model = cls()
        x_single = np.zeros((1, _L, _F), dtype=np.float32)
        y_hat = model.predict(x_single)
        assert y_hat.shape == (1,)
        assert y_hat[0] == 0.0

    def test_predict_large_batch(self):
        """predict with large N returns correct shape and all zeros."""
        cls = _import_no_trade()
        model = cls()
        n_large = 10000
        x_large = np.ones((n_large, _L, _F), dtype=np.float32)
        y_hat = model.predict(x_large)
        assert y_hat.shape == (n_large,)
        assert np.all(y_hat == 0.0)

    def test_predict_independent_of_input_values(self):
        """predict should return zeros regardless of input values."""
        cls = _import_no_trade()
        model = cls()
        x_ones = np.ones((_N, _L, _F), dtype=np.float32)
        x_neg = -99.0 * np.ones((_N, _L, _F), dtype=np.float32)
        np.testing.assert_array_equal(model.predict(x_ones), model.predict(x_neg))


# ---------------------------------------------------------------------------
# Tests — save() / load()
# ---------------------------------------------------------------------------


class TestNoTradeSaveLoad:
    """#037 — save/load roundtrip."""

    def test_save_load_roundtrip(self, tmp_path):
        """save then load produces identical predictions."""
        cls = _import_no_trade()
        model = cls()
        model.save(tmp_path)

        model2 = cls()
        model2.load(tmp_path)
        np.testing.assert_array_equal(model.predict(_X), model2.predict(_X))

    def test_save_creates_file(self, tmp_path):
        """save() must create at least one file in the directory."""
        cls = _import_no_trade()
        model = cls()
        model.save(tmp_path)
        files = list(tmp_path.iterdir())
        assert len(files) >= 1

    def test_save_load_roundtrip_file_path(self, tmp_path):
        """save/load with an explicit file path (not directory)."""
        cls = _import_no_trade()
        model = cls()
        file_path = tmp_path / "model.json"
        model.save(file_path)
        assert file_path.exists()

        model2 = cls()
        model2.load(file_path)
        np.testing.assert_array_equal(model.predict(_X), model2.predict(_X))

    def test_load_nonexistent_raises(self, tmp_path):
        """load() from a nonexistent path must raise FileNotFoundError."""
        cls = _import_no_trade()
        model = cls()
        with pytest.raises(FileNotFoundError):
            model.load(tmp_path / "nonexistent_dir")


# ---------------------------------------------------------------------------
# Tests — Backtest integration: 0 trades
# ---------------------------------------------------------------------------


class TestNoTradeBacktestIntegration:
    """#037 — No-trade signals produce 0 trades and flat equity."""

    def _make_ohlcv(self, n: int) -> pd.DataFrame:
        """Build a simple OHLCV DataFrame with n bars."""
        idx = pd.date_range("2024-01-01", periods=n, freq="1h")
        rng = np.random.default_rng(42)
        close = 100.0 + np.cumsum(rng.standard_normal(n) * 0.5)
        close = np.abs(close) + 50.0
        return pd.DataFrame(
            {
                "open": close + 0.1,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": np.full(n, 1000.0),
            },
            index=idx,
        )

    def test_zero_signals_produce_zero_trades(self):
        """All-zero signals → execute_trades returns empty list."""
        from ai_trading.backtest.engine import execute_trades

        n = 50
        ohlcv = self._make_ohlcv(n)
        signals = np.zeros(n, dtype=np.int32)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="standard")
        assert trades == []

    def test_equity_constant_with_no_trades(self):
        """build_equity_curve with no trades → equity = 1.0 everywhere."""
        from ai_trading.backtest.engine import build_equity_curve

        n = 50
        ohlcv = self._make_ohlcv(n)
        equity = build_equity_curve(
            [], ohlcv, initial_equity=1.0, position_fraction=1.0
        )
        assert len(equity) == n
        np.testing.assert_array_equal(equity["equity"].values, np.ones(n))

    def test_net_pnl_zero_with_no_trades(self):
        """No trades → net_pnl = 0."""
        # net_pnl = final equity - initial_equity
        from ai_trading.backtest.engine import build_equity_curve

        n = 50
        ohlcv = self._make_ohlcv(n)
        equity = build_equity_curve(
            [], ohlcv, initial_equity=1.0, position_fraction=1.0
        )
        net_pnl = float(equity["equity"].iloc[-1]) - 1.0
        assert net_pnl == 0.0

    def test_n_trades_zero(self):
        """Zero-signal predict → n_trades = 0."""
        from ai_trading.backtest.engine import execute_trades

        cls = _import_no_trade()
        model = cls()
        n = 50
        x = np.zeros((n, _L, _F), dtype=np.float32)
        signals = model.predict(x).astype(np.int32)
        ohlcv = self._make_ohlcv(n)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="standard")
        assert len(trades) == 0

    def test_mdd_zero_with_no_trades(self):
        """No trades → equity flat → MDD = 0."""
        from ai_trading.backtest.engine import build_equity_curve

        n = 50
        ohlcv = self._make_ohlcv(n)
        equity = build_equity_curve(
            [], ohlcv, initial_equity=1.0, position_fraction=1.0
        )
        eq_values = equity["equity"].values
        running_max = np.maximum.accumulate(eq_values)
        drawdowns = (eq_values - running_max) / running_max
        mdd = float(np.min(drawdowns))
        assert mdd == 0.0


# ---------------------------------------------------------------------------
# Tests — Baselines __init__ export
# ---------------------------------------------------------------------------


class TestBaselinesInit:
    """#037 — ai_trading.baselines exposes NoTradeBaseline."""

    def test_import_from_baselines_package(self):
        """NoTradeBaseline should be importable from ai_trading.baselines."""
        from ai_trading.baselines.no_trade import NoTradeBaseline

        assert issubclass(NoTradeBaseline, BaseModel)
