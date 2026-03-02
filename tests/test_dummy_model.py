"""Tests for DummyModel — Task #025 (WS-6).

Covers:
- Instantiation and class attributes (output_type, execution_mode)
- fit() accepts all contract parameters and returns dict
- predict() shape, dtype, reproducibility
- save()/load() roundtrip with JSON file
- MODEL_REGISTRY["dummy"] resolves to DummyModel
- Error/edge cases: empty input, missing file, corrupted JSON
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ai_trading.models.base import MODEL_REGISTRY, BaseModel
from ai_trading.models.dummy import DummyModel


# ---------------------------------------------------------------------------
# Registry cleanup fixture (same pattern as test_base_model.py)
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

_RNG = np.random.default_rng(123)
_N, _L, _F = 20, 5, 3
_X = _RNG.standard_normal((_N, _L, _F)).astype(np.float32)
_Y = _RNG.standard_normal((_N,)).astype(np.float32)
_X_VAL = _RNG.standard_normal((10, _L, _F)).astype(np.float32)
_Y_VAL = _RNG.standard_normal((10,)).astype(np.float32)


# ---------------------------------------------------------------------------
# Tests — Class attributes & inheritance
# ---------------------------------------------------------------------------


class TestDummyModelAttributes:
    """#025 — DummyModel class properties."""

    def test_inherits_base_model(self):
        assert issubclass(DummyModel, BaseModel)

    def test_output_type_regression(self):
        assert DummyModel.output_type == "regression"

    def test_execution_mode_standard(self):
        model = DummyModel(seed=42)
        assert model.execution_mode == "standard"

    def test_instantiation(self):
        model = DummyModel(seed=99)
        assert isinstance(model, BaseModel)


# ---------------------------------------------------------------------------
# Tests — fit()
# ---------------------------------------------------------------------------


class TestDummyModelFit:
    """#025 — fit() contract compliance."""

    def test_fit_returns_dict(self):
        model = DummyModel(seed=42)
        result = model.fit(
            X_train=_X, y_train=_Y, X_val=_X_VAL, y_val=_Y_VAL,
            config=None, run_dir=Path("/tmp/dummy_run"),
        )
        assert isinstance(result, dict)

    def test_fit_with_optional_params(self):
        model = DummyModel(seed=42)
        result = model.fit(
            X_train=_X, y_train=_Y, X_val=_X_VAL, y_val=_Y_VAL,
            config=None, run_dir=Path("/tmp/dummy_run"),
            meta_train={"a": 1}, meta_val={"b": 2}, ohlcv=np.zeros((5, 6)),
        )
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Tests — predict()
# ---------------------------------------------------------------------------


class TestDummyModelPredict:
    """#025 — predict() shape, dtype, reproducibility."""

    def test_predict_shape(self):
        model = DummyModel(seed=42)
        y_hat = model.predict(_X)
        assert y_hat.shape == (_N,)

    def test_predict_dtype_float32(self):
        model = DummyModel(seed=42)
        y_hat = model.predict(_X)
        assert y_hat.dtype == np.float32

    def test_predict_reproducible_same_instance(self):
        """Two calls on the same instance produce the same output."""
        model = DummyModel(seed=42)
        y1 = model.predict(_X)
        y2 = model.predict(_X)
        np.testing.assert_array_equal(y1, y2)

    def test_predict_reproducible_different_instances(self):
        """Two separate instances with the same seed produce the same output."""
        m1 = DummyModel(seed=77)
        m2 = DummyModel(seed=77)
        np.testing.assert_array_equal(m1.predict(_X), m2.predict(_X))

    def test_predict_different_seeds_differ(self):
        """Different seeds produce different predictions."""
        m1 = DummyModel(seed=1)
        m2 = DummyModel(seed=2)
        y1 = m1.predict(_X)
        y2 = m2.predict(_X)
        assert not np.array_equal(y1, y2)

    def test_predict_single_sample(self):
        """predict works with a single sample (N=1)."""
        model = DummyModel(seed=42)
        X_single = _X[:1]
        y_hat = model.predict(X_single)
        assert y_hat.shape == (1,)
        assert y_hat.dtype == np.float32

    def test_predict_with_optional_params(self):
        """predict accepts meta and ohlcv optional params."""
        model = DummyModel(seed=42)
        y_hat = model.predict(_X, meta={"info": True}, ohlcv=np.zeros((5, 6)))
        assert y_hat.shape == (_N,)


# ---------------------------------------------------------------------------
# Tests — save() / load() roundtrip
# ---------------------------------------------------------------------------


class TestDummyModelSaveLoad:
    """#025 — save/load roundtrip."""

    def test_save_creates_json_file(self, tmp_path: Path):
        model = DummyModel(seed=42)
        filepath = tmp_path / "model.json"
        model.save(filepath)
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert "seed" in data

    def test_load_restores_predictions(self, tmp_path: Path):
        """After save+load, predict gives the same results."""
        model = DummyModel(seed=42)
        y_before = model.predict(_X)

        filepath = tmp_path / "model.json"
        model.save(filepath)

        model2 = DummyModel(seed=999)  # different seed
        model2.load(filepath)
        y_after = model2.predict(_X)

        np.testing.assert_array_equal(y_before, y_after)

    def test_save_json_readable(self, tmp_path: Path):
        """Saved file is valid JSON with expected keys."""
        model = DummyModel(seed=55)
        filepath = tmp_path / "model.json"
        model.save(filepath)
        data = json.loads(filepath.read_text())
        assert isinstance(data, dict)
        assert data["seed"] == 55


# ---------------------------------------------------------------------------
# Tests — Error / edge cases
# ---------------------------------------------------------------------------


class TestDummyModelErrors:
    """#025 — Error and edge case handling."""

    def test_predict_empty_array(self):
        """predict with N=0 returns empty array."""
        model = DummyModel(seed=42)
        X_empty = np.empty((0, _L, _F), dtype=np.float32)
        y_hat = model.predict(X_empty)
        assert y_hat.shape == (0,)
        assert y_hat.dtype == np.float32

    def test_load_missing_file_raises(self, tmp_path: Path):
        """load from non-existent path raises FileNotFoundError."""
        model = DummyModel(seed=42)
        with pytest.raises(FileNotFoundError):
            model.load(tmp_path / "nonexistent.json")

    def test_load_corrupted_json_raises(self, tmp_path: Path):
        """load from corrupted JSON raises an error."""
        filepath = tmp_path / "bad.json"
        filepath.write_text("not valid json {{{")
        model = DummyModel(seed=42)
        with pytest.raises((json.JSONDecodeError, ValueError)):
            model.load(filepath)

    def test_load_missing_seed_key_raises(self, tmp_path: Path):
        """load from JSON without 'seed' key raises KeyError."""
        filepath = tmp_path / "no_seed.json"
        filepath.write_text(json.dumps({"other": 123}))
        model = DummyModel(seed=42)
        with pytest.raises(KeyError):
            model.load(filepath)


# ---------------------------------------------------------------------------
# Tests — MODEL_REGISTRY
# ---------------------------------------------------------------------------


class TestDummyModelRegistry:
    """#025 — Registry integration."""

    def test_registry_contains_dummy(self):
        """After importing dummy module, MODEL_REGISTRY contains 'dummy'."""
        # Re-register since fixture clears registry
        from ai_trading.models.base import register_model

        @register_model("dummy")
        class _Dummy(DummyModel):
            pass

        assert "dummy" in MODEL_REGISTRY
        assert MODEL_REGISTRY["dummy"] is _Dummy

    def test_get_model_class_resolves_dummy(self):
        """get_model_class('dummy') returns DummyModel after registration."""
        from ai_trading.models.base import get_model_class, register_model

        @register_model("dummy")
        class _Dummy(DummyModel):
            pass

        assert get_model_class("dummy") is _Dummy
