"""Tests for XGBoostRegModel — Task #060 (WS-XGB-2).

Covers:
- Registration in MODEL_REGISTRY under "xgboost_reg"
- Class attributes: output_type, execution_mode
- Inheritance from BaseModel
- Stub methods (fit, predict, save, load) raise NotImplementedError
- Import via ai_trading.models works without error
"""

from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np
import pytest

from ai_trading.models.base import MODEL_REGISTRY, BaseModel


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

_RNG = np.random.default_rng(60)
_N, _L, _F = 10, 5, 3
_X_TRAIN = _RNG.standard_normal((_N, _L, _F)).astype(np.float32)
_Y_TRAIN = _RNG.standard_normal((_N,)).astype(np.float32)
_X_VAL = _RNG.standard_normal((5, _L, _F)).astype(np.float32)
_Y_VAL = _RNG.standard_normal((5,)).astype(np.float32)


# ---------------------------------------------------------------------------
# Helper: import and register the module
# ---------------------------------------------------------------------------


def _reload_xgboost_module():
    """Reload ai_trading.models.xgboost to trigger @register_model side-effect."""
    import ai_trading.models.xgboost as xgb_mod

    importlib.reload(xgb_mod)
    return xgb_mod


# ---------------------------------------------------------------------------
# Tests — Registration
# ---------------------------------------------------------------------------


class TestXGBoostRegModelRegistry:
    """#060 — XGBoostRegModel registration in MODEL_REGISTRY."""

    def test_registered_under_xgboost_reg(self):
        """xgboost_reg key is present in MODEL_REGISTRY after import."""
        _reload_xgboost_module()
        assert "xgboost_reg" in MODEL_REGISTRY

    def test_registry_maps_to_correct_class(self):
        """MODEL_REGISTRY['xgboost_reg'] resolves to XGBoostRegModel."""
        mod = _reload_xgboost_module()
        assert MODEL_REGISTRY["xgboost_reg"] is mod.XGBoostRegModel


# ---------------------------------------------------------------------------
# Tests — Class attributes & inheritance
# ---------------------------------------------------------------------------


class TestXGBoostRegModelAttributes:
    """#060 — XGBoostRegModel class properties."""

    def test_inherits_base_model(self):
        mod = _reload_xgboost_module()
        assert issubclass(mod.XGBoostRegModel, BaseModel)

    def test_output_type_regression(self):
        mod = _reload_xgboost_module()
        assert mod.XGBoostRegModel.output_type == "regression"

    def test_execution_mode_standard(self):
        mod = _reload_xgboost_module()
        model = mod.XGBoostRegModel()
        assert model.execution_mode == "standard"

    def test_instantiation(self):
        mod = _reload_xgboost_module()
        model = mod.XGBoostRegModel()
        assert isinstance(model, BaseModel)

    def test_model_attribute_initialized_none(self):
        mod = _reload_xgboost_module()
        model = mod.XGBoostRegModel()
        assert model._model is None


# ---------------------------------------------------------------------------
# Tests — Stub methods raise NotImplementedError
# ---------------------------------------------------------------------------


class TestXGBoostRegModelStubs:
    """#060 — Stub methods must raise NotImplementedError."""

    def test_fit_raises_not_implemented(self, tmp_path: Path):
        mod = _reload_xgboost_module()
        model = mod.XGBoostRegModel()
        with pytest.raises(NotImplementedError):
            model.fit(
                X_train=_X_TRAIN,
                y_train=_Y_TRAIN,
                X_val=_X_VAL,
                y_val=_Y_VAL,
                config=None,
                run_dir=tmp_path,
            )

    def test_predict_raises_not_implemented(self):
        mod = _reload_xgboost_module()
        model = mod.XGBoostRegModel()
        with pytest.raises(NotImplementedError):
            model.predict(X=_X_TRAIN)

    def test_save_raises_not_implemented(self, tmp_path: Path):
        mod = _reload_xgboost_module()
        model = mod.XGBoostRegModel()
        with pytest.raises(NotImplementedError):
            model.save(path=tmp_path / "model.json")

    def test_load_raises_not_implemented(self, tmp_path: Path):
        mod = _reload_xgboost_module()
        model = mod.XGBoostRegModel()
        with pytest.raises(NotImplementedError):
            model.load(path=tmp_path / "model.json")

    def test_fit_with_optional_params_raises_not_implemented(self, tmp_path: Path):
        """fit() with meta_train, meta_val, ohlcv also raises."""
        mod = _reload_xgboost_module()
        model = mod.XGBoostRegModel()
        with pytest.raises(NotImplementedError):
            model.fit(
                X_train=_X_TRAIN,
                y_train=_Y_TRAIN,
                X_val=_X_VAL,
                y_val=_Y_VAL,
                config=None,
                run_dir=tmp_path,
                meta_train={"example": 1},
                meta_val={"example": 2},
                ohlcv=None,
            )

    def test_predict_with_optional_params_raises_not_implemented(self):
        """predict() with meta and ohlcv also raises."""
        mod = _reload_xgboost_module()
        model = mod.XGBoostRegModel()
        with pytest.raises(NotImplementedError):
            model.predict(X=_X_TRAIN, meta={"example": 1}, ohlcv=None)


# ---------------------------------------------------------------------------
# Tests — Import via package
# ---------------------------------------------------------------------------


class TestXGBoostRegModelImport:
    """#060 — Module import via ai_trading.models works."""

    def test_import_via_models_package(self):
        """Importing ai_trading.models registers xgboost_reg."""
        import ai_trading.models as models_pkg

        importlib.reload(models_pkg)
        # After reloading the package, xgboost_reg should be registered
        assert "xgboost_reg" in MODEL_REGISTRY
