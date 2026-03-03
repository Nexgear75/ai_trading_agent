"""Tests for XGBoostRegModel — Task #060 (WS-XGB-2), #062-#064 (WS-XGB-3).

Covers:
- Registration in MODEL_REGISTRY under "xgboost_reg"
- Class attributes: output_type, execution_mode
- Inheritance from BaseModel
- Stub methods (predict, save, load) raise NotImplementedError
- Import via ai_trading.models works without error
- #062: fit() validation, config-driven hyperparams, imposed params, nominal training
- #063: early stopping behavior: best_iteration, best_score, config-driven patience
- #064: fit() artifacts: n_features_in, all 3 required keys, correct types
"""

from __future__ import annotations

import copy
import importlib
import json
import math

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

    # --- Validation: y ndim errors ---

    def test_fit_raises_valueerror_y_train_scalar_0d(self, default_config, tmp_path):
        """#062 PR-FIX — ValueError if y_train is a 0D scalar."""
        model = _make_xgb_model()
        y_scalar = np.float32(1.0)  # 0D
        with pytest.raises(ValueError, match="y_train must be 1D"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=y_scalar,
                X_val=_X_VAL_FIT,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_valueerror_y_train_2d(self, default_config, tmp_path):
        """#062 PR-FIX — ValueError if y_train is 2D (N, 1)."""
        model = _make_xgb_model()
        y_2d = _Y_TRAIN_FIT.reshape(-1, 1)  # (N, 1)
        with pytest.raises(ValueError, match="y_train must be 1D"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=y_2d,
                X_val=_X_VAL_FIT,
                y_val=_Y_VAL_FIT,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_valueerror_y_val_scalar_0d(self, default_config, tmp_path):
        """#062 PR-FIX — ValueError if y_val is a 0D scalar."""
        model = _make_xgb_model()
        y_scalar = np.float32(1.0)  # 0D
        with pytest.raises(ValueError, match="y_val must be 1D"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=_Y_TRAIN_FIT,
                X_val=_X_VAL_FIT,
                y_val=y_scalar,
                config=default_config,
                run_dir=tmp_path,
            )

    def test_fit_raises_valueerror_y_val_2d(self, default_config, tmp_path):
        """#062 PR-FIX — ValueError if y_val is 2D (N, 1)."""
        model = _make_xgb_model()
        y_val_2d = _Y_VAL_FIT.reshape(-1, 1)  # (N, 1)
        with pytest.raises(ValueError, match="y_val must be 1D"):
            model.fit(
                X_train=_X_TRAIN_FIT,
                y_train=_Y_TRAIN_FIT,
                X_val=_X_VAL_FIT,
                y_val=y_val_2d,
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


# ---------------------------------------------------------------------------
# Larger synthetic data for early stopping tests (#063)
# ---------------------------------------------------------------------------

_RNG_ES = np.random.default_rng(63)
_N_ES = 200
_N_VAL_ES = 60
_L_ES, _F_ES = 10, 5
_X_TRAIN_ES = _RNG_ES.standard_normal((_N_ES, _L_ES, _F_ES)).astype(np.float32)
_Y_TRAIN_ES = _RNG_ES.standard_normal((_N_ES,)).astype(np.float32)
_X_VAL_ES = _RNG_ES.standard_normal((_N_VAL_ES, _L_ES, _F_ES)).astype(np.float32)
_Y_VAL_ES = _RNG_ES.standard_normal((_N_VAL_ES,)).astype(np.float32)


# ---------------------------------------------------------------------------
# Tests — Early stopping behavior (#063)
# ---------------------------------------------------------------------------


class TestXGBoostRegModelEarlyStopping:
    """#063 — Early stopping behavior: best_iteration, best_score, config-driven patience."""

    def test_best_iteration_is_nonneg_int(self, default_config, tmp_path):
        """#063 — After fit(), self._model.best_iteration is an integer >= 0."""
        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        bi = model._model.best_iteration
        assert isinstance(bi, int)
        assert bi >= 0

    def test_best_score_is_finite_float(self, default_config, tmp_path):
        """#063 — After fit(), self._model.best_score is a finite float."""
        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        bs = model._model.best_score
        assert isinstance(bs, float)
        assert math.isfinite(bs)

    def test_best_score_positive_rmse(self, default_config, tmp_path):
        """#063 — best_score (RMSE on eval_set) is > 0 for non-trivial data."""
        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        assert model._model.best_score > 0.0

    def test_early_stopping_triggers_on_synthetic_data(self, default_config, tmp_path):
        """#063 — best_iteration < n_estimators: early stopping actually triggers."""
        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        n_est = default_config.models.xgboost.n_estimators
        # best_iteration is 0-based, so < n_est - 1 proves early stopping triggered
        # before the last boosting round (< n_est would always pass).
        assert model._model.best_iteration < n_est - 1

    def test_patience_config_driven_different_value(
        self, default_yaml_data, tmp_yaml, tmp_path
    ):
        """#063 — Changing early_stopping_patience in config changes model behaviour."""
        from ai_trading.config import load_config

        data = copy.deepcopy(default_yaml_data)
        data["training"]["early_stopping_patience"] = 5
        cfg_path = tmp_yaml(data)
        cfg = load_config(cfg_path)

        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=cfg,
            run_dir=tmp_path,
        )
        assert model._model.early_stopping_rounds == 5

    def test_patience_config_driven_high_value(
        self, default_yaml_data, tmp_yaml, tmp_path
    ):
        """#063 — With patience=50, early_stopping_rounds picks up the value."""
        from ai_trading.config import load_config

        data = copy.deepcopy(default_yaml_data)
        data["training"]["early_stopping_patience"] = 50
        cfg_path = tmp_yaml(data)
        cfg = load_config(cfg_path)

        model = _make_xgb_model()
        model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=cfg,
            run_dir=tmp_path,
        )
        assert model._model.early_stopping_rounds == 50

    def test_fit_returns_best_iteration_in_result(self, default_config, tmp_path):
        """#063 — fit() returns best_iteration in result dict."""
        model = _make_xgb_model()
        result = model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        assert "best_iteration" in result
        assert result["best_iteration"] == model._model.best_iteration

    def test_fit_returns_best_score_in_result(self, default_config, tmp_path):
        """#063 — fit() returns best_score in result dict."""
        model = _make_xgb_model()
        result = model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        assert "best_score" in result
        assert result["best_score"] == model._model.best_score


# ---------------------------------------------------------------------------
# Tests — fit() artifacts (#064)
# ---------------------------------------------------------------------------


class TestXGBoostRegModelFitArtifacts:
    """#064 — fit() returns dict with all 3 required keys and correct types."""

    def test_fit_result_contains_n_features_in(self, default_config, tmp_path):
        """#064 — fit() result dict contains 'n_features_in' key."""
        model = _make_xgb_model()
        result = model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        assert "n_features_in" in result

    def test_fit_n_features_in_is_int(self, default_config, tmp_path):
        """#064 — n_features_in value is a Python int."""
        model = _make_xgb_model()
        result = model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        assert isinstance(result["n_features_in"], int)

    def test_fit_n_features_in_equals_l_times_f(self, default_config, tmp_path):
        """#064 — n_features_in == L * F (10 * 5 = 50 for test data)."""
        model = _make_xgb_model()
        result = model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        expected = _L_ES * _F_ES  # 10 * 5 = 50
        assert result["n_features_in"] == expected

    def test_fit_result_has_at_least_three_required_keys(self, default_config, tmp_path):
        """#064 — fit() result contains at least the 3 required keys."""
        model = _make_xgb_model()
        result = model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        required_keys = {"best_iteration", "best_score", "n_features_in"}
        assert required_keys.issubset(result.keys())

    def test_fit_best_iteration_type_in_result(self, default_config, tmp_path):
        """#064 — best_iteration in result dict is int >= 0."""
        model = _make_xgb_model()
        result = model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        assert isinstance(result["best_iteration"], int)
        assert result["best_iteration"] >= 0

    def test_fit_best_score_type_in_result(self, default_config, tmp_path):
        """#064 — best_score in result dict is a finite float."""
        model = _make_xgb_model()
        result = model.fit(
            X_train=_X_TRAIN_ES,
            y_train=_Y_TRAIN_ES,
            X_val=_X_VAL_ES,
            y_val=_Y_VAL_ES,
            config=default_config,
            run_dir=tmp_path,
        )
        assert isinstance(result["best_score"], float)
        assert math.isfinite(result["best_score"])

    def test_fit_n_features_in_with_different_dimensions(self, default_config, tmp_path):
        """#064 — n_features_in adapts to different L and F values (L=5, F=3 → 15)."""
        rng = np.random.default_rng(6400)
        seq_len, n_feat = 5, 3
        x_train = rng.standard_normal((50, seq_len, n_feat)).astype(np.float32)
        y_train = rng.standard_normal((50,)).astype(np.float32)
        x_val = rng.standard_normal((20, seq_len, n_feat)).astype(np.float32)
        y_val = rng.standard_normal((20,)).astype(np.float32)

        model = _make_xgb_model()
        result = model.fit(
            X_train=x_train,
            y_train=y_train,
            X_val=x_val,
            y_val=y_val,
            config=default_config,
            run_dir=tmp_path,
        )
        assert result["n_features_in"] == seq_len * n_feat  # 5 * 3 = 15


# ---------------------------------------------------------------------------
# Fixture: fitted model for predict tests (#065)
# ---------------------------------------------------------------------------

_RNG_PRED = np.random.default_rng(65)
_N_PRED, _L_PRED, _F_PRED = 80, 10, 5
_X_TRAIN_PRED = _RNG_PRED.standard_normal((_N_PRED, _L_PRED, _F_PRED)).astype(np.float32)
_Y_TRAIN_PRED = _RNG_PRED.standard_normal((_N_PRED,)).astype(np.float32)
_X_VAL_PRED = _RNG_PRED.standard_normal((25, _L_PRED, _F_PRED)).astype(np.float32)
_Y_VAL_PRED = _RNG_PRED.standard_normal((25,)).astype(np.float32)
_X_TEST_PRED = _RNG_PRED.standard_normal((15, _L_PRED, _F_PRED)).astype(np.float32)


@pytest.fixture()
def fitted_model(default_config, tmp_path):
    """Return a fitted XGBoostRegModel ready for predict() tests.

    Overrides n_estimators to 10 (from 500) for performance: predict tests
    do not depend on model quality, and this avoids 17+ slow fits.
    """
    default_config.models.xgboost.n_estimators = 10
    model = _make_xgb_model()
    model.fit(
        X_train=_X_TRAIN_PRED,
        y_train=_Y_TRAIN_PRED,
        X_val=_X_VAL_PRED,
        y_val=_Y_VAL_PRED,
        config=default_config,
        run_dir=tmp_path,
    )
    return model


# ---------------------------------------------------------------------------
# Tests — predict() (#065)
# ---------------------------------------------------------------------------


class TestXGBoostRegModelPredict:
    """#065 — XGBoostRegModel.predict() validation, output shape/dtype, determinism."""

    # --- Validation: not fitted ---

    def test_predict_raises_runtime_error_if_not_fitted(self):
        """#065 — RuntimeError if fit() has not been called."""
        model = _make_xgb_model()
        with pytest.raises(RuntimeError, match="Model not fitted"):
            model.predict(X=_X_TEST_PRED)

    def test_predict_raises_runtime_error_if_feature_names_none(self):
        """#065 PR-FIX — RuntimeError if _feature_names is None (e.g. after load)."""
        model = _make_xgb_model()
        # Simulate a loaded model with _model set but _feature_names still None
        model._model = object()  # non-None so the first guard passes
        with pytest.raises(RuntimeError, match="Feature names are not set"):
            model.predict(X=_X_TEST_PRED)

    # --- Validation: shape errors ---

    def test_predict_raises_valueerror_if_x_2d(self, fitted_model):
        """#065 — ValueError if X is 2D instead of 3D."""
        x_2d = _X_TEST_PRED.reshape(_X_TEST_PRED.shape[0], -1)
        with pytest.raises(ValueError, match="3D"):
            fitted_model.predict(X=x_2d)

    def test_predict_raises_valueerror_if_x_1d(self, fitted_model):
        """#065 — ValueError if X is 1D."""
        x_1d = np.ones(10, dtype=np.float32)
        with pytest.raises(ValueError, match="3D"):
            fitted_model.predict(X=x_1d)

    def test_predict_raises_valueerror_if_x_4d(self, fitted_model):
        """#065 — ValueError if X is 4D."""
        x_4d = np.ones((5, 10, 5, 1), dtype=np.float32)
        with pytest.raises(ValueError, match="3D"):
            fitted_model.predict(X=x_4d)

    # --- Validation: dtype errors ---

    def test_predict_raises_typeerror_if_x_float64(self, fitted_model):
        """#065 — TypeError if X.dtype is float64."""
        x_f64 = _X_TEST_PRED.astype(np.float64)
        with pytest.raises(TypeError, match="float32"):
            fitted_model.predict(X=x_f64)

    def test_predict_raises_typeerror_if_x_int32(self, fitted_model):
        """#065 — TypeError if X.dtype is int32."""
        x_int = _X_TEST_PRED.astype(np.int32)
        with pytest.raises(TypeError, match="float32"):
            fitted_model.predict(X=x_int)

    # --- Nominal: output shape and dtype ---

    def test_predict_returns_ndarray(self, fitted_model):
        """#065 — predict() returns a numpy ndarray."""
        y_hat = fitted_model.predict(X=_X_TEST_PRED)
        assert isinstance(y_hat, np.ndarray)

    def test_predict_output_shape_n(self, fitted_model):
        """#065 — predict() output shape is (N,)."""
        y_hat = fitted_model.predict(X=_X_TEST_PRED)
        assert y_hat.shape == (_X_TEST_PRED.shape[0],)

    def test_predict_output_dtype_float32(self, fitted_model):
        """#065 — predict() output dtype is float32 (cast from XGBoost float64)."""
        y_hat = fitted_model.predict(X=_X_TEST_PRED)
        assert y_hat.dtype == np.float32

    def test_predict_values_are_continuous(self, fitted_model):
        """#065 — Predictions are continuous floats (not bounded to 0/1)."""
        y_hat = fitted_model.predict(X=_X_TEST_PRED)
        # For regression on random data, not all values will be exactly 0 or 1
        assert not np.all(np.isin(y_hat, [0.0, 1.0]))

    def test_predict_values_are_finite(self, fitted_model):
        """#065 — All predictions are finite (no NaN or Inf)."""
        y_hat = fitted_model.predict(X=_X_TEST_PRED)
        assert np.all(np.isfinite(y_hat))

    # --- Determinism ---

    def test_predict_deterministic_same_result(self, fitted_model):
        """#065 — Multiple predict() calls with same data → identical results."""
        y1 = fitted_model.predict(X=_X_TEST_PRED)
        y2 = fitted_model.predict(X=_X_TEST_PRED)
        np.testing.assert_array_equal(y1, y2)

    # --- meta and ohlcv are ignored ---

    def test_predict_meta_ignored(self, fitted_model):
        """#065 — meta param is accepted but does not affect output."""
        y_no_meta = fitted_model.predict(X=_X_TEST_PRED)
        y_with_meta = fitted_model.predict(X=_X_TEST_PRED, meta={"key": "value"})
        np.testing.assert_array_equal(y_no_meta, y_with_meta)

    def test_predict_ohlcv_ignored(self, fitted_model):
        """#065 — ohlcv param is accepted but does not affect output."""
        y_no_ohlcv = fitted_model.predict(X=_X_TEST_PRED)
        y_with_ohlcv = fitted_model.predict(
            X=_X_TEST_PRED, ohlcv=np.ones((15, 5))
        )
        np.testing.assert_array_equal(y_no_ohlcv, y_with_ohlcv)

    def test_predict_meta_and_ohlcv_together(self, fitted_model):
        """#065 — Both meta and ohlcv together are accepted without error."""
        y_hat = fitted_model.predict(
            X=_X_TEST_PRED, meta={"a": 1}, ohlcv=np.zeros((15, 4))
        )
        assert y_hat.shape == (_X_TEST_PRED.shape[0],)
        assert y_hat.dtype == np.float32

    # --- Boundary: N=1 ---

    def test_predict_single_sample(self, fitted_model):
        """#065 — predict() works with a single sample (N=1)."""
        rng = np.random.default_rng(6501)
        x_single = rng.standard_normal((1, _L_PRED, _F_PRED)).astype(np.float32)
        y_hat = fitted_model.predict(X=x_single)
        assert y_hat.shape == (1,)
        assert y_hat.dtype == np.float32

    # --- Boundary: N=0 ---

    def test_predict_boundary_n_zero(self, fitted_model):
        """#065 — predict() with empty array (0, L, F) returns empty (0,) float32."""
        x_empty = np.empty((0, _L_PRED, _F_PRED), dtype=np.float32)
        y_hat = fitted_model.predict(X=x_empty)
        assert y_hat.shape == (0,)
        assert y_hat.dtype == np.float32


# ---------------------------------------------------------------------------
# Tests — save() (#066)
# ---------------------------------------------------------------------------


class TestXGBoostRegModelSave:
    """#066 — XGBoostRegModel.save() JSON persistence.

    Covers:
    - RuntimeError if model not fitted
    - Directory path resolves to xgboost_model.json
    - File path used as-is
    - Output file is valid JSON
    - Parent directories created automatically
    - _resolve_path static method behavior
    """

    # --- Error: not fitted ---

    def test_save_raises_runtime_error_if_not_fitted(self, tmp_path):
        """#066 — RuntimeError if save() called before fit()."""
        model = _make_xgb_model()
        with pytest.raises(RuntimeError, match="Model not fitted"):
            model.save(path=tmp_path / "model.json")

    # --- Nominal: directory path ---

    def test_save_creates_file_in_directory(self, fitted_model, tmp_path):
        """#066 — save(directory) creates xgboost_model.json inside it."""
        fitted_model.save(path=tmp_path)
        expected = tmp_path / "xgboost_model.json"
        assert expected.exists()
        assert expected.is_file()

    def test_save_file_is_valid_json_directory(self, fitted_model, tmp_path):
        """#066 — File created by save(directory) is parseable JSON."""
        fitted_model.save(path=tmp_path)
        content = (tmp_path / "xgboost_model.json").read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    # --- Nominal: explicit file path ---

    def test_save_uses_explicit_file_path(self, fitted_model, tmp_path):
        """#066 — save(file_path) uses the exact path, not appending default filename."""
        explicit = tmp_path / "my_model.json"
        fitted_model.save(path=explicit)
        assert explicit.exists()
        assert explicit.is_file()
        # Default filename should NOT be created
        assert not (tmp_path / "xgboost_model.json").exists()

    def test_save_explicit_path_is_valid_json(self, fitted_model, tmp_path):
        """#066 — File at explicit path is parseable JSON."""
        explicit = tmp_path / "custom_name.json"
        fitted_model.save(path=explicit)
        content = explicit.read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    # --- Parent directory creation ---

    def test_save_creates_parent_directories(self, fitted_model, tmp_path):
        """#066 — save() creates parent directories if they don't exist."""
        nested = tmp_path / "a" / "b" / "c" / "model.json"
        assert not nested.parent.exists()
        fitted_model.save(path=nested)
        assert nested.exists()

    # --- _resolve_path static method ---

    def test_resolve_path_directory_appends_filename(self, tmp_path):
        """#066 — _resolve_path(directory) appends xgboost_model.json."""
        from ai_trading.models.xgboost import XGBoostRegModel

        resolved = XGBoostRegModel._resolve_path(tmp_path)
        assert resolved == tmp_path / "xgboost_model.json"

    def test_resolve_path_file_returns_as_is(self, tmp_path):
        """#066 — _resolve_path(file_path) returns the path unchanged."""
        from ai_trading.models.xgboost import XGBoostRegModel

        file_path = tmp_path / "my_model.json"
        resolved = XGBoostRegModel._resolve_path(file_path)
        assert resolved == file_path

    # --- Boundary: save twice overwrites ---

    def test_save_twice_overwrites(self, fitted_model, tmp_path):
        """#066 — Calling save() twice to the same path overwrites without error."""
        fitted_model.save(path=tmp_path)
        fitted_model.save(path=tmp_path)
        assert (tmp_path / "xgboost_model.json").exists()


# ---------------------------------------------------------------------------
# Tests — load() (#067)
# ---------------------------------------------------------------------------


class TestXGBoostRegModelLoad:
    """#067 — XGBoostRegModel.load() JSON restoration.

    Covers:
    - load() restores a functional model (capable of predict())
    - Round-trip: save() → load() → predict() bit-exact
    - FileNotFoundError if file does not exist
    - Directory path resolves to xgboost_model.json
    - Explicit file path used as-is
    - predict() works after load() without fit()
    """

    # --- Error: file not found ---

    def test_load_raises_file_not_found_nonexistent_file(self, tmp_path):
        """#067 — FileNotFoundError if the file does not exist."""
        model = _make_xgb_model()
        nonexistent = tmp_path / "nonexistent_model.json"
        with pytest.raises(FileNotFoundError, match="Model file not found"):
            model.load(path=nonexistent)

    def test_load_raises_file_not_found_nonexistent_dir(self, tmp_path):
        """#067 — FileNotFoundError if directory exists but default file is absent."""
        model = _make_xgb_model()
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="Model file not found"):
            model.load(path=empty_dir)

    def test_load_raises_is_a_directory_error(self, tmp_path):
        """#067 — IsADirectoryError when resolved path exists but is a directory."""
        model = _make_xgb_model()
        # Create a directory at the path _resolve_path would return
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        fake_file = model_dir / "xgboost_model.json"
        fake_file.mkdir()  # directory instead of file
        with pytest.raises(IsADirectoryError, match="Expected a model file"):
            model.load(path=model_dir)

    # --- Nominal: load from directory path ---

    def test_load_from_directory_path(self, fitted_model, tmp_path):
        """#067 — load(directory) resolves to xgboost_model.json and loads."""
        fitted_model.save(path=tmp_path)
        new_model = _make_xgb_model()
        new_model._feature_names = fitted_model._feature_names
        new_model.load(path=tmp_path)
        assert new_model._model is not None

    # --- Nominal: load from explicit file path ---

    def test_load_from_explicit_file_path(self, fitted_model, tmp_path):
        """#067 — load(file_path) loads from the exact file path."""
        explicit = tmp_path / "custom_model.json"
        fitted_model.save(path=explicit)
        new_model = _make_xgb_model()
        new_model._feature_names = fitted_model._feature_names
        new_model.load(path=explicit)
        assert new_model._model is not None

    # --- Functional: predict after load ---

    def test_predict_works_after_load(self, fitted_model, tmp_path):
        """#067 — predict() works after load() without calling fit()."""
        fitted_model.save(path=tmp_path)
        new_model = _make_xgb_model()
        new_model._feature_names = fitted_model._feature_names
        new_model.load(path=tmp_path)
        y_hat = new_model.predict(X=_X_TEST_PRED)
        assert isinstance(y_hat, np.ndarray)
        assert y_hat.shape == (_X_TEST_PRED.shape[0],)
        assert y_hat.dtype == np.float32

    # --- Round-trip: bit-exact ---

    def test_round_trip_bit_exact_directory(self, fitted_model, tmp_path):
        """#067 — save(dir) → load(dir) → predict() is bit-exact."""
        y_before = fitted_model.predict(X=_X_TEST_PRED)
        fitted_model.save(path=tmp_path)

        new_model = _make_xgb_model()
        new_model._feature_names = fitted_model._feature_names
        new_model.load(path=tmp_path)
        y_after = new_model.predict(X=_X_TEST_PRED)

        np.testing.assert_array_equal(y_before, y_after)

    def test_round_trip_bit_exact_explicit_path(self, fitted_model, tmp_path):
        """#067 — save(file) → load(file) → predict() is bit-exact."""
        explicit = tmp_path / "my_model.json"
        y_before = fitted_model.predict(X=_X_TEST_PRED)
        fitted_model.save(path=explicit)

        new_model = _make_xgb_model()
        new_model._feature_names = fitted_model._feature_names
        new_model.load(path=explicit)
        y_after = new_model.predict(X=_X_TEST_PRED)

        np.testing.assert_array_equal(y_before, y_after)

    # --- Boundary: load overwrites previous _model ---

    def test_load_overwrites_existing_model(self, fitted_model, tmp_path):
        """#067 — load() on an already-fitted model replaces _model."""
        y_original = fitted_model.predict(X=_X_TEST_PRED)
        old_model_obj = fitted_model._model
        fitted_model.save(path=tmp_path)

        # Load into the already-fitted instance: should replace _model
        fitted_model.load(path=tmp_path)
        y_loaded = fitted_model.predict(X=_X_TEST_PRED)

        assert fitted_model._model is not old_model_obj
        np.testing.assert_array_equal(y_original, y_loaded)

    # --- Security: JSON only, no pickle ---

    def test_load_uses_json_format(self, fitted_model, tmp_path):
        """#067 — Loaded file is valid JSON (not pickle binary)."""
        fitted_model.save(path=tmp_path)
        model_file = tmp_path / "xgboost_model.json"
        content = model_file.read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)
