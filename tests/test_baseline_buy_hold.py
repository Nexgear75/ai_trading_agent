"""Tests for BuyHoldBaseline — Task #038 (WS-9).

Covers:
- Inheritance from BaseModel, output_type, execution_mode
- fit() is a no-op returning empty dict
- predict() returns np.ones(N, dtype=float32)
- save()/load() roundtrip
- Registry: "buy_hold" resolves via get_model_class
- Backtest integration: single_trade → 1 trade, correct net_return
- exposure_time_frac = 1.0 (Note I-08)
- Edge cases: empty input, single sample
"""

from __future__ import annotations

import importlib

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

_RNG = np.random.default_rng(888)
_N, _L, _F = 30, 5, 3
_X = _RNG.standard_normal((_N, _L, _F)).astype(np.float32)
_Y = _RNG.standard_normal((_N,)).astype(np.float32)
_X_VAL = _RNG.standard_normal((10, _L, _F)).astype(np.float32)
_Y_VAL = _RNG.standard_normal((10,)).astype(np.float32)


def _import_buy_hold() -> type:
    """Import the buy_hold module to trigger registration."""
    import ai_trading.baselines.buy_hold as mod

    MODEL_REGISTRY.pop("buy_hold", None)
    importlib.reload(mod)
    return mod.BuyHoldBaseline


def _make_ohlcv(n: int, open_start: float = 100.0) -> pd.DataFrame:
    """Build a simple OHLCV DataFrame with n bars and deterministic prices."""
    idx = pd.date_range("2024-01-01", periods=n, freq="1h")
    rng = np.random.default_rng(42)
    close = open_start + np.cumsum(rng.standard_normal(n) * 0.5)
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


# ---------------------------------------------------------------------------
# Tests — Class attributes & inheritance
# ---------------------------------------------------------------------------


class TestBuyHoldAttributes:
    """#038 — BuyHoldBaseline class attributes and inheritance."""

    def test_inherits_base_model(self):
        """BuyHoldBaseline must be a subclass of BaseModel."""
        cls = _import_buy_hold()
        assert issubclass(cls, BaseModel)

    def test_output_type_is_signal(self):
        """output_type must be 'signal'."""
        cls = _import_buy_hold()
        assert cls.output_type == "signal"

    def test_execution_mode_is_single_trade(self):
        """execution_mode must be 'single_trade'."""
        cls = _import_buy_hold()
        assert cls.execution_mode == "single_trade"


# ---------------------------------------------------------------------------
# Tests — Registry
# ---------------------------------------------------------------------------


class TestBuyHoldRegistry:
    """#038 — BuyHoldBaseline is registered as 'buy_hold'."""

    def test_registered_in_model_registry(self):
        """After import, 'buy_hold' must be in MODEL_REGISTRY."""
        cls = _import_buy_hold()
        assert "buy_hold" in MODEL_REGISTRY
        assert MODEL_REGISTRY["buy_hold"] is cls

    def test_get_model_class_resolves(self):
        """get_model_class('buy_hold') must return BuyHoldBaseline."""
        cls = _import_buy_hold()
        resolved = get_model_class("buy_hold")
        assert resolved is cls


# ---------------------------------------------------------------------------
# Tests — fit()
# ---------------------------------------------------------------------------


class TestBuyHoldFit:
    """#038 — fit() is a no-op."""

    def test_fit_returns_empty_dict(self, tmp_path):
        """fit() must return an empty dict (no artifacts)."""
        cls = _import_buy_hold()
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
        cls = _import_buy_hold()
        model = cls()
        model.fit(_X, _Y, _X_VAL, _Y_VAL, config=None, run_dir=tmp_path)
        pred1 = model.predict(_X)
        model.fit(_X, _Y, _X_VAL, _Y_VAL, config=None, run_dir=tmp_path)
        pred2 = model.predict(_X)
        np.testing.assert_array_equal(pred1, pred2)


# ---------------------------------------------------------------------------
# Tests — predict()
# ---------------------------------------------------------------------------


class TestBuyHoldPredict:
    """#038 — predict() returns ones (Go permanent)."""

    def test_predict_returns_ones(self):
        """predict(X) must return np.ones(N, dtype=float32)."""
        cls = _import_buy_hold()
        model = cls()
        y_hat = model.predict(_X)
        expected = np.ones(_N, dtype=np.float32)
        np.testing.assert_array_equal(y_hat, expected)

    def test_predict_dtype_float32(self):
        """predict output must be float32."""
        cls = _import_buy_hold()
        model = cls()
        y_hat = model.predict(_X)
        assert y_hat.dtype == np.float32

    def test_predict_shape(self):
        """predict output must have shape (N,)."""
        cls = _import_buy_hold()
        model = cls()
        y_hat = model.predict(_X)
        assert y_hat.shape == (_N,)

    def test_predict_empty_input(self):
        """predict with N=0 must return shape (0,) of ones (vacuously)."""
        cls = _import_buy_hold()
        model = cls()
        x_empty = np.zeros((0, _L, _F), dtype=np.float32)
        y_hat = model.predict(x_empty)
        assert y_hat.shape == (0,)
        assert y_hat.dtype == np.float32

    def test_predict_single_sample(self):
        """predict works with N=1, returns [1.0]."""
        cls = _import_buy_hold()
        model = cls()
        x_single = np.zeros((1, _L, _F), dtype=np.float32)
        y_hat = model.predict(x_single)
        assert y_hat.shape == (1,)
        assert y_hat[0] == 1.0

    def test_predict_large_batch(self):
        """predict with large N returns correct shape and all ones."""
        cls = _import_buy_hold()
        model = cls()
        n_large = 10000
        x_large = np.ones((n_large, _L, _F), dtype=np.float32)
        y_hat = model.predict(x_large)
        assert y_hat.shape == (n_large,)
        assert np.all(y_hat == 1.0)

    def test_predict_independent_of_input_values(self):
        """predict should return ones regardless of input values."""
        cls = _import_buy_hold()
        model = cls()
        x_ones = np.ones((_N, _L, _F), dtype=np.float32)
        x_neg = -99.0 * np.ones((_N, _L, _F), dtype=np.float32)
        np.testing.assert_array_equal(model.predict(x_ones), model.predict(x_neg))


# ---------------------------------------------------------------------------
# Tests — save() / load()
# ---------------------------------------------------------------------------


class TestBuyHoldSaveLoad:
    """#038 — save/load roundtrip."""

    def test_save_load_roundtrip(self, tmp_path):
        """save then load produces identical predictions."""
        cls = _import_buy_hold()
        model = cls()
        model.save(tmp_path)

        model2 = cls()
        model2.load(tmp_path)
        np.testing.assert_array_equal(model.predict(_X), model2.predict(_X))

    def test_save_creates_file(self, tmp_path):
        """save() must create at least one file in the directory."""
        cls = _import_buy_hold()
        model = cls()
        model.save(tmp_path)
        files = list(tmp_path.iterdir())
        assert len(files) >= 1

    def test_save_load_roundtrip_file_path(self, tmp_path):
        """save/load with an explicit file path (not directory)."""
        cls = _import_buy_hold()
        model = cls()
        file_path = tmp_path / "model.json"
        model.save(file_path)
        assert file_path.exists()

        model2 = cls()
        model2.load(file_path)
        np.testing.assert_array_equal(model.predict(_X), model2.predict(_X))

    def test_load_nonexistent_raises(self, tmp_path):
        """load() from a nonexistent path must raise FileNotFoundError."""
        cls = _import_buy_hold()
        model = cls()
        with pytest.raises(FileNotFoundError):
            model.load(tmp_path / "nonexistent_dir")


# ---------------------------------------------------------------------------
# Tests — Backtest integration: single_trade mode
# ---------------------------------------------------------------------------


class TestBuyHoldBacktestIntegration:
    """#038 — Buy & hold signals + single_trade → 1 trade, correct P&L."""

    def test_single_trade_produces_one_trade(self):
        """execute_trades in single_trade mode → exactly 1 trade."""
        from ai_trading.backtest.engine import execute_trades

        n = 50
        ohlcv = _make_ohlcv(n)
        signals = np.ones(n, dtype=np.int32)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="single_trade")
        assert len(trades) == 1

    def test_single_trade_entry_exit_prices(self):
        """Entry at Open[0], exit at Close[-1]."""
        from ai_trading.backtest.engine import execute_trades

        n = 50
        ohlcv = _make_ohlcv(n)
        signals = np.ones(n, dtype=np.int32)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="single_trade")
        trade = trades[0]
        assert trade["entry_price"] == pytest.approx(float(ohlcv["open"].iloc[0]))
        assert trade["exit_price"] == pytest.approx(float(ohlcv["close"].iloc[-1]))

    def test_single_trade_entry_exit_times(self):
        """Entry at first timestamp, exit at last timestamp."""
        from ai_trading.backtest.engine import execute_trades

        n = 50
        ohlcv = _make_ohlcv(n)
        signals = np.ones(n, dtype=np.int32)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="single_trade")
        trade = trades[0]
        assert trade["entry_time"] == ohlcv.index[0]
        assert trade["exit_time"] == ohlcv.index[-1]

    def test_net_return_formula(self):
        """net_return = (1-f)^2 * Close_end*(1-s) / (Open_start*(1+s)) - 1."""
        from ai_trading.backtest.costs import apply_cost_model
        from ai_trading.backtest.engine import execute_trades

        n = 50
        ohlcv = _make_ohlcv(n)
        signals = np.ones(n, dtype=np.int32)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="single_trade")

        f = 0.001
        s = 0.0005
        enriched = apply_cost_model(trades, fee_rate_per_side=f, slippage_rate_per_side=s)
        trade = enriched[0]

        open_start = float(ohlcv["open"].iloc[0])
        close_end = float(ohlcv["close"].iloc[-1])
        expected_net_return = (1 - f) ** 2 * close_end * (1 - s) / (open_start * (1 + s)) - 1

        assert trade["r_net"] == pytest.approx(expected_net_return, rel=1e-10)

    def test_net_return_zero_costs(self):
        """With f=0, s=0: net_return = Close_end / Open_start - 1."""
        from ai_trading.backtest.costs import apply_cost_model
        from ai_trading.backtest.engine import execute_trades

        n = 50
        ohlcv = _make_ohlcv(n)
        signals = np.ones(n, dtype=np.int32)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="single_trade")
        enriched = apply_cost_model(trades, fee_rate_per_side=0.0, slippage_rate_per_side=0.0)
        trade = enriched[0]

        open_start = float(ohlcv["open"].iloc[0])
        close_end = float(ohlcv["close"].iloc[-1])
        expected = close_end / open_start - 1
        assert trade["r_net"] == pytest.approx(expected, rel=1e-10)

    def test_equity_curve_single_trade(self):
        """build_equity_curve with 1 trade: in_trade=True everywhere, equity updated at exit."""
        from ai_trading.backtest.costs import apply_cost_model
        from ai_trading.backtest.engine import build_equity_curve, execute_trades

        n = 20
        ohlcv = _make_ohlcv(n)
        signals = np.ones(n, dtype=np.int32)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="single_trade")
        enriched = apply_cost_model(trades, fee_rate_per_side=0.001, slippage_rate_per_side=0.0005)
        equity_df = build_equity_curve(enriched, ohlcv, initial_equity=1.0, position_fraction=1.0)

        assert len(equity_df) == n
        # in_trade should be True for entire period (entry to exit inclusive)
        assert equity_df["in_trade"].all()

    def test_exposure_time_frac_is_one(self):
        """exposure_time_frac = sum(in_trade) / len(in_trade) == 1.0 (Note I-08)."""
        from ai_trading.backtest.costs import apply_cost_model
        from ai_trading.backtest.engine import build_equity_curve, execute_trades

        n = 50
        ohlcv = _make_ohlcv(n)
        signals = np.ones(n, dtype=np.int32)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="single_trade")
        enriched = apply_cost_model(trades, fee_rate_per_side=0.001, slippage_rate_per_side=0.0005)
        equity_df = build_equity_curve(enriched, ohlcv, initial_equity=1.0, position_fraction=1.0)

        exposure_time_frac = float(equity_df["in_trade"].sum()) / len(equity_df)
        assert exposure_time_frac == 1.0

    def test_n_trades_equals_one(self):
        """Full pipeline: predict → execute → exactly 1 trade."""
        from ai_trading.backtest.engine import execute_trades

        cls = _import_buy_hold()
        model = cls()
        n = 50
        x = np.zeros((n, _L, _F), dtype=np.float32)
        signals = model.predict(x).astype(np.int32)
        ohlcv = _make_ohlcv(n)
        trades = execute_trades(signals, ohlcv, horizon=4, execution_mode="single_trade")
        assert len(trades) == 1


# ---------------------------------------------------------------------------
# Tests — Baselines __init__ export
# ---------------------------------------------------------------------------


class TestBaselinesInitBuyHold:
    """#038 — ai_trading.baselines exposes BuyHoldBaseline."""

    def test_import_from_baselines_package(self):
        """BuyHoldBaseline should be importable from ai_trading.baselines."""
        from ai_trading.baselines import BuyHoldBaseline

        assert issubclass(BuyHoldBaseline, BaseModel)

    def test_buy_hold_module_imported_via_init(self):
        """Importing ai_trading.baselines triggers buy_hold registration."""
        _import_buy_hold()
        assert "buy_hold" in MODEL_REGISTRY
