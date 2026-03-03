"""Tests for XGBoostRegModel — Task #060 (WS-XGB-2), Task #062 (WS-XGB-3).

Covers:
- Registration in MODEL_REGISTRY under "xgboost_reg"
- Class attributes: output_type, execution_mode
- Inheritance from BaseModel
- Stub methods (predict, save, load) raise NotImplementedError
- Import via ai_trading.models works without error
- #062: fit() validation, config-driven hyperparams, imposed params, nominal training
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
    """#060 — Remaining stub methods must raise NotImplementedError."""

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
        """Importing ai_trading.models from clean slate registers xgboost_reg."""
        import sys

        # Remove the package and submodules (but keep .base so MODEL_REGISTRY
        # is the same dict object referenced by the test module).
        keys_to_remove = [
            k for k in sys.modules
            if k == "ai_trading.models" or (
                k.startswith("ai_trading.models.") and k != "ai_trading.models.base"
            )
        ]
        saved_modules = {k: sys.modules.pop(k) for k in keys_to_remove}
        try:
            # MODEL_REGISTRY is already cleared by the autouse fixture.
            # Fresh import of ai_trading.models should trigger xgboost
            # registration via `from . import xgboost` in __init__.py.
            import ai_trading.models  # noqa: F811, F401

            assert "xgboost_reg" in MODEL_REGISTRY
        finally:
            # Restore modules so other tests are not affected
            sys.modules.update(saved_modules)


# ---------------------------------------------------------------------------
# Synthetic data for fit tests (#062)
# ---------------------------------------------------------------------------

_RNG_FIT = np.random.default_rng(62)
_N_FIT, _L_FIT, _F_FIT = 100, 10, 5
_X_TRAIN_FIT = _RNG_FIT.standard_normal((_N_FIT, _L_FIT, _F_FIT)).astype(np.float32)
_Y_TRAIN_FIT = _RNG_FIT.standard_normal((_N_FIT,)).astype(np.float32)
_X_VAL_FIT = _RNG_FIT.standard_normal((30, _L_FIT, _F_FIT)).astype(np.float32)
_Y_VAL_FIT = _RNG_FIT.standard_normal((30,)).astype(np.float32)


def _make_xgb_model():
    """Create a fresh XGBoostRegModel instance (no registry dependency)."""
    from ai_trading.models.xgboost import XGBoostRegModel

    return XGBoostRegModel()


# ---------------------------------------------------------------------------
# Tests — fit() (#062)
# ---------------------------------------------------------------------------


class TestXGBoostRegModelFit:
    """#062 — XGBoostRegModel.fit() validation, training, and config-driven."""

    # --- Validation: shape errors ---

    def test_fit_raises_valueerror_x_train_not_3d(self, default_config, tmp_path):
        """ValueError if X_train is 2D instead of 3D."""
        model = _make_xgb_model()
        x_2d = _X_TRAIN_FIT.reshape(_N_FIT, -1)  # (N, L*F)
        with pytest.raises(ValueError, match="X_train"):
            model.fit(
                X_train=x_2d,
                y_train=_Y_TRAIN_FIT,
                X_val=_X_VAL_FIT,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_valueerror_x_train_1d(self, default_config, tmp_path):
        """ValueError if X_train is 1D."""
        model = _make_xgb_model()
        with pytest.raises(ValueError, match="X_train"):
            model.fit(
                X_train=np.ones(10, dtype=np.float32),
                y_train=_Y_TRAIN_FIT,
                X_val=_X_VAL_FIT,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_valueerror_x_val_not_3d(self, default_config, tmp_path):
        """ValueError if X_val is 2D instead of 3D."""
        model = _make_xgb_model()
        x_val_2d = _X_VAL_FIT.reshape(30, -1)
        with pytest.raises(ValueError, match="X_val"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=_Y_TRAIN_FIT,
                X_val=x_val_2d,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_valueerror_x_train_y_train_shape_mismatch(
        self, default_config, tmp_path
    ):
        """ValueError if X_train.shape[0] != y_train.shape[0]."""
        model = _make_xgb_model()
        y_bad = _Y_TRAIN_FIT[:50]  # 50 != 100
        with pytest.raises(ValueError, match="X_train.*y_train"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=y_bad,
                X_val=_X_VAL_FIT,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_valueerror_x_val_y_val_shape_mismatch(
        self, default_config, tmp_path
    ):
        """ValueError if X_val.shape[0] != y_val.shape[0]."""
        model = _make_xgb_model()
        y_val_bad = _Y_VAL_FIT[:10]  # 10 != 30
        with pytest.raises(ValueError, match="X_val.*y_val"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=_Y_TRAIN_FIT,
                X_val=_X_VAL_FIT,
                y_val=y_val_bad,
                config=default_config,
                run_dir=tmp_path,
            )

    # --- Validation: dtype errors ---

    def test_fit_raises_typeerror_x_train_not_float32(self, default_config, tmp_path):
        """TypeError if X_train.dtype is float64."""
        model = _make_xgb_model()
        x_f64 = _X_TRAIN_FIT.astype(np.float64)
        with pytest.raises(TypeError, match="X_train.*float32"):
            model.fit(
                X_train=x_f64,
                y_train=_Y_TRAIN_FIT,
                X_val=_X_VAL_FIT,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_typeerror_x_val_not_float32(self, default_config, tmp_path):
        """TypeError if X_val.dtype is float64."""
        model = _make_xgb_model()
        x_val_f64 = _X_VAL_FIT.astype(np.float64)
        with pytest.raises(TypeError, match="X_val.*float32"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=_Y_TRAIN_FIT,
                X_val=x_val_f64,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_typeerror_y_train_not_float32(self, default_config, tmp_path):
        """#062 FIX — TypeError if y_train.dtype is float64."""
        model = _make_xgb_model()
        y_f64 = _Y_TRAIN_FIT.astype(np.float64)
        with pytest.raises(TypeError, match="y_train.*float32"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=y_f64,
                X_val=_X_VAL_FIT,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_typeerror_y_val_not_float32(self, default_config, tmp_path):
        """#062 FIX — TypeError if y_val.dtype is float64."""
        model = _make_xgb_model()
        y_val_f64 = _Y_VAL_FIT.astype(np.float64)
        with pytest.raises(TypeError, match="y_val.*float32"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=_Y_TRAIN_FIT,
                X_val=_X_VAL_FIT,
                y_val=y_val_f64,
                config=default_config,
                run_dir=tmp_path,
            )

    # --- Boundary: N=0 and N=1 ---

    def test_fit_boundary_n_train_zero(self, default_config, tmp_path):
        """#062 FIX — fit() with N_train=0 raises ValueError (empty training set)."""
        model = _make_xgb_model()
        x_empty = np.empty((0, _L_FIT, _F_FIT), dtype=np.float32)
        y_empty = np.empty((0,), dtype=np.float32)
        with pytest.raises(ValueError, match="X_train.*at least 1 sample"):
            model.fit(
                X_train=x_empty,
                y_train=y_empty,
                X_val=_X_VAL_FIT,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_boundary_n_val_zero(self, default_config, tmp_path):
        """#062 FIX — fit() with N_val=0 raises ValueError (empty val set)."""
        model = _make_xgb_model()
        x_val_empty = np.empty((0, _L_FIT, _F_FIT), dtype=np.float32)
        y_val_empty = np.empty((0,), dtype=np.float32)
        with pytest.raises(ValueError, match="X_val.*at least 1 sample"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=_Y_TRAIN_FIT,
                X_val=x_val_empty,
                y_val=y_val_empty,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_boundary_n_train_one(self, default_config, tmp_path):
        """#062 FIX — fit() with N_train=1 runs without error."""
        rng = np.random.default_rng(6201)
        x1 = rng.standard_normal((1, _L_FIT, _F_FIT)).astype(np.float32)
        y1 = rng.standard_normal((1,)).astype(np.float32)
        x_val = rng.standard_normal((1, _L_FIT, _F_FIT)).astype(np.float32)
        y_val = rng.standard_normal((1,)).astype(np.float32)
        model = _make_xgb_model()
        model.fit(
            X_train=x1,
            y_train=y1,
            X_val=x_val,
            y_val=y_val,
            config=default_config,
            run_dir=tmp_path,
        )
        assert model._model is not None

    # --- Nominal training ---

    def test_fit_nominal_no_error(self, default_config, tmp_path):
        """#062 — fit() runs without error on valid synthetic data (N=100, L=10, F=5)."""
        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_FIT,
            y_train=_Y_TRAIN_FIT,
            X_val=_X_VAL_FIT,
            y_val=_Y_VAL_FIT,
            config=default_config,
            run_dir=tmp_path,
        )

    def test_fit_model_is_xgbregressor(self, default_config, tmp_path):
        """#062 — After fit(), self._model is an xgboost.XGBRegressor instance."""
        import xgboost as xgb

        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_FIT,
            y_train=_Y_TRAIN_FIT,
            X_val=_X_VAL_FIT,
            y_val=_Y_VAL_FIT,
            config=default_config,
            run_dir=tmp_path,
        )
        assert isinstance(model._model, xgb.XGBRegressor)

    def test_fit_returns_dict(self, default_config, tmp_path):
        """#062 — fit() returns a dict."""
        model = _make_xgb_model()
        result = model.fit(
            X_train=_X_TRAIN_FIT,
            y_train=_Y_TRAIN_FIT,
            X_val=_X_VAL_FIT,
            y_val=_Y_VAL_FIT,
            config=default_config,
            run_dir=tmp_path,
        )
        assert isinstance(result, dict)

    # --- Config-driven: 7 hyperparams from config ---

    def test_fit_hyperparams_from_config(self, default_config, tmp_path):
        """#062 — 7 hyperparams are read from config.models.xgboost, not hardcoded."""
        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_FIT,
            y_train=_Y_TRAIN_FIT,
            X_val=_X_VAL_FIT,
            y_val=_Y_VAL_FIT,
            config=default_config,
            run_dir=tmp_path,
        )
        xgb_cfg = default_config.models.xgboost
        xgb_model = model._model
        assert xgb_model.max_depth == xgb_cfg.max_depth
        assert xgb_model.n_estimators == xgb_cfg.n_estimators
        assert xgb_model.learning_rate == xgb_cfg.learning_rate
        assert xgb_model.subsample == xgb_cfg.subsample
        assert xgb_model.colsample_bytree == xgb_cfg.colsample_bytree
        assert xgb_model.reg_alpha == xgb_cfg.reg_alpha
        assert xgb_model.reg_lambda == xgb_cfg.reg_lambda

    def test_fit_random_state_from_config(self, default_config, tmp_path):
        """#062 — random_state is config.reproducibility.global_seed."""
        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_FIT,
            y_train=_Y_TRAIN_FIT,
            X_val=_X_VAL_FIT,
            y_val=_Y_VAL_FIT,
            config=default_config,
            run_dir=tmp_path,
        )
        assert model._model.random_state == default_config.reproducibility.global_seed

    def test_fit_imposed_params(self, default_config, tmp_path):
        """#062 — objective, tree_method, booster, verbosity are imposed values."""
        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_FIT,
            y_train=_Y_TRAIN_FIT,
            X_val=_X_VAL_FIT,
            y_val=_Y_VAL_FIT,
            config=default_config,
            run_dir=tmp_path,
        )
        xgb_model = model._model
        assert xgb_model.objective == "reg:squarederror"
        assert xgb_model.tree_method == "hist"
        assert xgb_model.booster == "gbtree"
        assert xgb_model.verbosity == 0

    def test_fit_early_stopping_from_config(self, default_config, tmp_path):
        """#062 — early_stopping_rounds is config.training.early_stopping_patience."""
        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_FIT,
            y_train=_Y_TRAIN_FIT,
            X_val=_X_VAL_FIT,
            y_val=_Y_VAL_FIT,
            config=default_config,
            run_dir=tmp_path,
        )
        assert (
            model._model.early_stopping_rounds
            == default_config.training.early_stopping_patience
        )
