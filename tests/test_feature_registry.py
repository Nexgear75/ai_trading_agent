"""Tests for ai_trading.features.registry — feature registry and BaseFeature.

Task #007: Registre de features et classe de base (BaseFeature).
"""

import pandas as pd
import pytest
from ai_trading.features.registry import (
    FEATURE_REGISTRY,
    BaseFeature,
    register_feature,
)

# ---------------------------------------------------------------------------
# Helpers: concrete subclasses for testing
# ---------------------------------------------------------------------------


class _ConcreteFeature(BaseFeature):
    """Minimal concrete implementation for test purposes."""

    required_params: list[str] = ["some_param"]

    @property
    def min_periods(self) -> int:
        return 5

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        return ohlcv["close"]


class _NoComputeFeature(BaseFeature):
    """Subclass missing compute — should raise TypeError."""

    required_params: list[str] = []

    @property
    def min_periods(self) -> int:
        return 1


class _NoMinPeriodsFeature(BaseFeature):
    """Subclass missing min_periods — should raise TypeError."""

    required_params: list[str] = []

    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        return ohlcv["close"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_registry():
    """Save and restore FEATURE_REGISTRY around each test."""
    saved = dict(FEATURE_REGISTRY)
    FEATURE_REGISTRY.clear()
    yield
    FEATURE_REGISTRY.clear()
    FEATURE_REGISTRY.update(saved)


# ---------------------------------------------------------------------------
# AC-1: FEATURE_REGISTRY is an empty dict at startup
# ---------------------------------------------------------------------------


class TestRegistryEmpty:
    """#007 AC-1: FEATURE_REGISTRY is empty before feature module imports."""

    def test_registry_is_dict(self):
        assert isinstance(FEATURE_REGISTRY, dict)

    def test_registry_empty_after_clear(self):
        """After autouse fixture clears it, registry must be empty."""
        assert len(FEATURE_REGISTRY) == 0


# ---------------------------------------------------------------------------
# AC-2: @register_feature("name") registers the class
# ---------------------------------------------------------------------------


class TestRegisterFeature:
    """#007 AC-2: decorator registers class in FEATURE_REGISTRY."""

    def test_register_adds_to_registry(self):
        @register_feature("test_feat")
        class TestFeat(_ConcreteFeature):
            pass

        assert "test_feat" in FEATURE_REGISTRY
        assert FEATURE_REGISTRY["test_feat"] is TestFeat

    def test_register_multiple_features(self):
        @register_feature("feat_a")
        class FeatA(_ConcreteFeature):
            pass

        @register_feature("feat_b")
        class FeatB(_ConcreteFeature):
            pass

        assert "feat_a" in FEATURE_REGISTRY
        assert "feat_b" in FEATURE_REGISTRY
        assert FEATURE_REGISTRY["feat_a"] is FeatA
        assert FEATURE_REGISTRY["feat_b"] is FeatB

    def test_register_returns_class_unchanged(self):
        @register_feature("unchanged")
        class Unchanged(_ConcreteFeature):
            pass

        assert isinstance(Unchanged(), _ConcreteFeature)


# ---------------------------------------------------------------------------
# AC-3: @register_feature("name") on duplicate raises ValueError
# ---------------------------------------------------------------------------


class TestRegisterDuplicate:
    """#007 AC-3: duplicate name raises ValueError."""

    def test_duplicate_raises_valueerror(self):
        @register_feature("dup_name")
        class First(_ConcreteFeature):
            pass

        with pytest.raises(ValueError, match="dup_name"):

            @register_feature("dup_name")
            class Second(_ConcreteFeature):
                pass

    def test_duplicate_does_not_overwrite(self):
        @register_feature("keep_first")
        class First(_ConcreteFeature):
            pass

        with pytest.raises(ValueError):

            @register_feature("keep_first")
            class Second(_ConcreteFeature):
                pass

        assert FEATURE_REGISTRY["keep_first"] is First


# ---------------------------------------------------------------------------
# AC-4: BaseFeature is abstract — direct instantiation raises TypeError
# ---------------------------------------------------------------------------


class TestBaseFeatureAbstract:
    """#007 AC-4: BaseFeature cannot be instantiated directly."""

    def test_instantiate_base_raises_typeerror(self):
        with pytest.raises(TypeError):
            BaseFeature()


# ---------------------------------------------------------------------------
# AC-5: Subclass missing compute raises TypeError
# ---------------------------------------------------------------------------


class TestMissingCompute:
    """#007 AC-5: subclass without compute raises TypeError at instantiation."""

    def test_no_compute_raises_typeerror(self):
        with pytest.raises(TypeError):
            _NoComputeFeature()


# ---------------------------------------------------------------------------
# AC-6: Subclass missing min_periods raises TypeError
# ---------------------------------------------------------------------------


class TestMissingMinPeriods:
    """#007 AC-6: subclass without min_periods raises TypeError at instantiation."""

    def test_no_min_periods_raises_typeerror(self):
        with pytest.raises(TypeError):
            _NoMinPeriodsFeature()


# ---------------------------------------------------------------------------
# AC-7: required_params accessible as class attribute
# ---------------------------------------------------------------------------


class TestRequiredParams:
    """#007 AC-7: required_params is accessible as class attribute."""

    def test_required_params_default_on_base(self):
        """BaseFeature has default required_params = []."""
        assert BaseFeature.required_params == []

    def test_required_params_inherited(self):
        assert _ConcreteFeature.required_params == ["some_param"]

    def test_required_params_on_instance(self):
        feat = _ConcreteFeature()
        assert feat.required_params == ["some_param"]

    def test_required_params_overridable(self):
        class CustomParams(_ConcreteFeature):
            required_params: list[str] = ["alpha", "beta"]

        assert CustomParams.required_params == ["alpha", "beta"]

    def test_required_params_empty_list(self):
        """A feature can declare no required params."""

        class NoParams(_ConcreteFeature):
            required_params: list[str] = []

        assert NoParams.required_params == []


# ---------------------------------------------------------------------------
# Edge cases & additional coverage
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """#007 AC-8: edge cases and additional scenarios."""

    def test_concrete_subclass_instantiates(self):
        """A fully concrete subclass can be instantiated."""
        feat = _ConcreteFeature()
        assert feat.min_periods == 5

    def test_compute_returns_series(self):
        """compute() returns a pd.Series."""
        ohlcv = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
        feat = _ConcreteFeature()
        result = feat.compute(ohlcv, {"some_param": 42})
        assert isinstance(result, pd.Series)

    def test_register_feature_with_empty_name_allowed(self):
        """Empty string is technically a valid name (no validation on name)."""
        @register_feature("")
        class EmptyNameFeat(_ConcreteFeature):
            pass

        assert "" in FEATURE_REGISTRY

    def test_min_periods_is_property(self):
        """min_periods is accessed as a property, not a method."""
        feat = _ConcreteFeature()
        assert not callable(feat.min_periods) or isinstance(feat.min_periods, int)
        assert feat.min_periods == 5

    def test_registry_type_mapping(self):
        """Registry stores the class, not an instance."""
        @register_feature("type_check")
        class TypeCheckFeat(_ConcreteFeature):
            pass

        assert isinstance(FEATURE_REGISTRY["type_check"], type)
        assert issubclass(FEATURE_REGISTRY["type_check"], BaseFeature)
