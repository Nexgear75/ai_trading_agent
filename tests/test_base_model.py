"""Tests for BaseModel ABC and MODEL_REGISTRY — Task #024 (WS-6).

Covers:
- Abstract class enforcement (cannot instantiate BaseModel directly)
- Incomplete subclass raises TypeError
- Complete subclass instantiation
- output_type mandatory (enforced by __init_subclass__)
- output_type invalid value
- execution_mode default and override
- MODEL_REGISTRY empty after cleanup
- @register_model decorator
- get_model_class resolution
- get_model_class unknown name raises ValueError
- Duplicate registration raises ValueError
- Non-BaseModel registration raises TypeError
- fit/predict signature optional params
- save/load abstract
"""

from __future__ import annotations

import inspect
from typing import Literal

import pytest

from ai_trading.models.base import (
    MODEL_REGISTRY,
    BaseModel,
    get_model_class,
    register_model,
)


# ---------------------------------------------------------------------------
# Registry cleanup fixture (mirrors FEATURE_REGISTRY pattern)
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
# Concrete helper used across tests
# ---------------------------------------------------------------------------


class _ConcreteModel(BaseModel):
    output_type: Literal["regression", "signal"] = "regression"

    def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
            meta_train=None, meta_val=None, ohlcv=None):
        return {}

    def predict(self, X, meta=None, ohlcv=None):
        return X[:, 0, 0]

    def save(self, path):
        pass

    def load(self, path):
        pass


# ---------------------------------------------------------------------------
# Tests — Abstract class enforcement
# ---------------------------------------------------------------------------


class TestBaseModelAbstract:
    """#024 — BaseModel cannot be instantiated directly."""

    def test_base_model_is_abstract(self):
        with pytest.raises(TypeError):
            BaseModel()

    def test_incomplete_subclass_raises_typeerror(self):
        """A subclass missing abstract methods raises TypeError at instantiation."""

        class _Incomplete(BaseModel):
            output_type: Literal["regression", "signal"] = "regression"

        with pytest.raises(TypeError):
            _Incomplete()

    def test_complete_subclass_instantiation(self):
        """A fully-implementing subclass can be instantiated."""
        model = _ConcreteModel()
        assert isinstance(model, BaseModel)


# ---------------------------------------------------------------------------
# Tests — output_type mandatory
# ---------------------------------------------------------------------------


class TestOutputType:
    """#024 — output_type must be declared in subclass __dict__."""

    def test_output_type_mandatory(self):
        """Subclass without output_type in __dict__ raises TypeError at class creation."""
        with pytest.raises(TypeError, match="output_type"):

            class _NoOutputType(BaseModel):
                def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
                        meta_train=None, meta_val=None, ohlcv=None):
                    return {}

                def predict(self, X, meta=None, ohlcv=None):
                    return X[:, 0, 0]

                def save(self, path):
                    pass

                def load(self, path):
                    pass

    def test_output_type_invalid_value(self):
        """output_type with an invalid value raises ValueError at class creation."""
        with pytest.raises(ValueError, match="output_type"):

            class _BadOutputType(BaseModel):
                output_type = "invalid_type"

                def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
                        meta_train=None, meta_val=None, ohlcv=None):
                    return {}

                def predict(self, X, meta=None, ohlcv=None):
                    return X[:, 0, 0]

                def save(self, path):
                    pass

                def load(self, path):
                    pass


# ---------------------------------------------------------------------------
# Tests — execution_mode
# ---------------------------------------------------------------------------


class TestExecutionMode:
    """#024 — execution_mode default and override."""

    def test_execution_mode_default(self):
        """BaseModel defines execution_mode = 'standard' as default."""
        model = _ConcreteModel()
        assert model.execution_mode == "standard"

    def test_execution_mode_override(self):
        """Subclass can override execution_mode to 'single_trade'."""

        class _SingleTrade(BaseModel):
            output_type: Literal["regression", "signal"] = "signal"
            execution_mode: Literal["standard", "single_trade"] = "single_trade"

            def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
                    meta_train=None, meta_val=None, ohlcv=None):
                return {}

            def predict(self, X, meta=None, ohlcv=None):
                return X[:, 0, 0]

            def save(self, path):
                pass

            def load(self, path):
                pass

        model = _SingleTrade()
        assert model.execution_mode == "single_trade"

    def test_execution_mode_invalid_value(self):
        """execution_mode with an invalid value raises ValueError at class creation."""
        with pytest.raises(ValueError, match="execution_mode"):

            class _BadExecMode(BaseModel):
                output_type: Literal["regression", "signal"] = "regression"
                execution_mode = "batch"

                def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
                        meta_train=None, meta_val=None, ohlcv=None):
                    return {}

                def predict(self, X, meta=None, ohlcv=None):
                    return X[:, 0, 0]

                def save(self, path):
                    pass

                def load(self, path):
                    pass


# ---------------------------------------------------------------------------
# Tests — MODEL_REGISTRY
# ---------------------------------------------------------------------------


class TestModelRegistry:
    """#024 — MODEL_REGISTRY and @register_model."""

    def test_registry_empty_initially(self):
        """After cleanup, MODEL_REGISTRY is empty."""
        assert len(MODEL_REGISTRY) == 0

    def test_register_model_decorator(self):
        """@register_model('test_model') registers the class."""

        @register_model("test_model")
        class _TestModel(BaseModel):
            output_type: Literal["regression", "signal"] = "regression"

            def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
                    meta_train=None, meta_val=None, ohlcv=None):
                return {}

            def predict(self, X, meta=None, ohlcv=None):
                return X[:, 0, 0]

            def save(self, path):
                pass

            def load(self, path):
                pass

        assert "test_model" in MODEL_REGISTRY
        assert MODEL_REGISTRY["test_model"] is _TestModel

    def test_get_model_class_known(self):
        """get_model_class resolves a registered name."""

        @register_model("known_model")
        class _KnownModel(BaseModel):
            output_type: Literal["regression", "signal"] = "regression"

            def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
                    meta_train=None, meta_val=None, ohlcv=None):
                return {}

            def predict(self, X, meta=None, ohlcv=None):
                return X[:, 0, 0]

            def save(self, path):
                pass

            def load(self, path):
                pass

        result = get_model_class("known_model")
        assert result is _KnownModel

    def test_get_model_class_unknown(self):
        """get_model_class raises ValueError for unknown name."""
        with pytest.raises(ValueError, match="unknown_model"):
            get_model_class("unknown_model")

    def test_register_duplicate_raises_valueerror(self):
        """Registering same name twice raises ValueError."""

        @register_model("dup_model")
        class _DupModel1(BaseModel):
            output_type: Literal["regression", "signal"] = "regression"

            def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
                    meta_train=None, meta_val=None, ohlcv=None):
                return {}

            def predict(self, X, meta=None, ohlcv=None):
                return X[:, 0, 0]

            def save(self, path):
                pass

            def load(self, path):
                pass

        with pytest.raises(ValueError, match="dup_model"):

            @register_model("dup_model")
            class _DupModel2(BaseModel):
                output_type: Literal["regression", "signal"] = "regression"

                def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
                        meta_train=None, meta_val=None, ohlcv=None):
                    return {}

                def predict(self, X, meta=None, ohlcv=None):
                    return X[:, 0, 0]

                def save(self, path):
                    pass

                def load(self, path):
                    pass

    def test_register_non_basemodel_raises_typeerror(self):
        """@register_model on a non-BaseModel class raises TypeError."""
        with pytest.raises(TypeError):

            @register_model("not_a_model")
            class _NotAModel:
                pass


# ---------------------------------------------------------------------------
# Tests — Signatures
# ---------------------------------------------------------------------------


class TestSignatures:
    """#024 — fit/predict/save/load signatures."""

    def test_fit_signature_optional_params(self):
        """fit() signature has meta_train, meta_val, ohlcv as optional (default None)."""
        sig = inspect.signature(BaseModel.fit)
        for param_name in ("meta_train", "meta_val", "ohlcv"):
            param = sig.parameters[param_name]
            assert param.default is None, (
                f"fit() param '{param_name}' should default to None"
            )

    def test_predict_signature_optional_params(self):
        """predict() signature has meta, ohlcv as optional (default None)."""
        sig = inspect.signature(BaseModel.predict)
        for param_name in ("meta", "ohlcv"):
            param = sig.parameters[param_name]
            assert param.default is None, (
                f"predict() param '{param_name}' should default to None"
            )

    def test_save_load_abstract(self):
        """save() and load() are abstract methods."""

        class _NoSaveLoad(BaseModel):
            output_type: Literal["regression", "signal"] = "regression"

            def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
                    meta_train=None, meta_val=None, ohlcv=None):
                return {}

            def predict(self, X, meta=None, ohlcv=None):
                return X[:, 0, 0]

        with pytest.raises(TypeError):
            _NoSaveLoad()
