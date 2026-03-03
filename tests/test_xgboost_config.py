"""Tests for XGBoostModelConfig Pydantic validation constraints.

Task #061 — WS-XGB-6: Validate that XGBoostModelConfig enforces
field constraints from spec §11.1.
"""

import pytest
from pydantic import ValidationError

from ai_trading.config import XGBoostModelConfig

# ---------------------------------------------------------------------------
# Fixture: valid defaults for all 7 fields
# ---------------------------------------------------------------------------

VALID_KWARGS = {
    "max_depth": 5,
    "n_estimators": 500,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
}


def _make(**overrides):
    """Build XGBoostModelConfig with overrides applied to valid defaults."""
    kw = {**VALID_KWARGS, **overrides}
    return XGBoostModelConfig(**kw)


# ===========================================================================
# max_depth — Field(gt=0): strictly positive integer
# ===========================================================================


class TestMaxDepth:
    """#061 — max_depth must be > 0."""

    def test_max_depth_zero_rejected(self):
        with pytest.raises(ValidationError):
            _make(max_depth=0)

    def test_max_depth_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make(max_depth=-1)

    def test_max_depth_one_accepted(self):
        cfg = _make(max_depth=1)
        assert cfg.max_depth == 1


# ===========================================================================
# n_estimators — Field(gt=0): strictly positive integer
# ===========================================================================


class TestNEstimators:
    """#061 — n_estimators must be > 0."""

    def test_n_estimators_zero_rejected(self):
        with pytest.raises(ValidationError):
            _make(n_estimators=0)

    def test_n_estimators_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make(n_estimators=-1)

    def test_n_estimators_one_accepted(self):
        cfg = _make(n_estimators=1)
        assert cfg.n_estimators == 1


# ===========================================================================
# learning_rate — Field(gt=0, le=1): float in ]0, 1]
# ===========================================================================


class TestLearningRate:
    """#061 — learning_rate must be in ]0, 1]."""

    def test_learning_rate_zero_rejected(self):
        with pytest.raises(ValidationError):
            _make(learning_rate=0.0)

    def test_learning_rate_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make(learning_rate=-0.01)

    def test_learning_rate_above_one_rejected(self):
        with pytest.raises(ValidationError):
            _make(learning_rate=1.5)

    def test_learning_rate_one_accepted(self):
        cfg = _make(learning_rate=1.0)
        assert cfg.learning_rate == 1.0

    def test_learning_rate_small_positive_accepted(self):
        cfg = _make(learning_rate=0.001)
        assert cfg.learning_rate == 0.001


# ===========================================================================
# subsample — Field(gt=0, le=1): float in ]0, 1]
# ===========================================================================


class TestSubsample:
    """#061 — subsample must be in ]0, 1]."""

    def test_subsample_zero_rejected(self):
        with pytest.raises(ValidationError):
            _make(subsample=0.0)

    def test_subsample_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make(subsample=-0.1)

    def test_subsample_above_one_rejected(self):
        with pytest.raises(ValidationError):
            _make(subsample=1.1)

    def test_subsample_one_accepted(self):
        cfg = _make(subsample=1.0)
        assert cfg.subsample == 1.0


# ===========================================================================
# colsample_bytree — Field(gt=0, le=1): float in ]0, 1]
# ===========================================================================


class TestColsampleBytree:
    """#061 — colsample_bytree must be in ]0, 1]."""

    def test_colsample_bytree_zero_rejected(self):
        with pytest.raises(ValidationError):
            _make(colsample_bytree=0.0)

    def test_colsample_bytree_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make(colsample_bytree=-0.1)

    def test_colsample_bytree_above_one_rejected(self):
        with pytest.raises(ValidationError):
            _make(colsample_bytree=1.1)

    def test_colsample_bytree_one_accepted(self):
        cfg = _make(colsample_bytree=1.0)
        assert cfg.colsample_bytree == 1.0


# ===========================================================================
# reg_alpha — Field(ge=0): non-negative float
# ===========================================================================


class TestRegAlpha:
    """#061 — reg_alpha must be >= 0."""

    def test_reg_alpha_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make(reg_alpha=-0.1)

    def test_reg_alpha_zero_accepted(self):
        cfg = _make(reg_alpha=0.0)
        assert cfg.reg_alpha == 0.0

    def test_reg_alpha_positive_accepted(self):
        cfg = _make(reg_alpha=1.5)
        assert cfg.reg_alpha == 1.5

    def test_reg_alpha_inf_rejected(self):
        with pytest.raises(ValidationError):
            _make(reg_alpha=float("inf"))

    def test_reg_alpha_nan_rejected(self):
        with pytest.raises(ValidationError):
            _make(reg_alpha=float("nan"))


# ===========================================================================
# reg_lambda — Field(ge=0): non-negative float
# ===========================================================================


class TestRegLambda:
    """#061 — reg_lambda must be >= 0."""

    def test_reg_lambda_negative_rejected(self):
        with pytest.raises(ValidationError):
            _make(reg_lambda=-0.1)

    def test_reg_lambda_zero_accepted(self):
        cfg = _make(reg_lambda=0.0)
        assert cfg.reg_lambda == 0.0

    def test_reg_lambda_positive_accepted(self):
        cfg = _make(reg_lambda=10.0)
        assert cfg.reg_lambda == 10.0

    def test_reg_lambda_inf_rejected(self):
        with pytest.raises(ValidationError):
            _make(reg_lambda=float("inf"))

    def test_reg_lambda_nan_rejected(self):
        with pytest.raises(ValidationError):
            _make(reg_lambda=float("nan"))


# ===========================================================================
# Integration: default.yaml must parse without error
# ===========================================================================


class TestDefaultConfigIntegration:
    """#061 — configs/default.yaml must pass validation with new constraints."""

    def test_default_yaml_xgboost_block_valid(self, default_config):
        xgb = default_config.models.xgboost
        assert xgb.max_depth > 0
        assert xgb.n_estimators > 0
        assert 0 < xgb.learning_rate <= 1
        assert 0 < xgb.subsample <= 1
        assert 0 < xgb.colsample_bytree <= 1
        assert xgb.reg_alpha >= 0
        assert xgb.reg_lambda >= 0
