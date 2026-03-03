"""Tests for JSON schema validation — Task #047 (WS-11).

Validates ai_trading.artifacts.validation module:
- validate_manifest(data) / validate_metrics(data) against Draft 2020-12 schemas.
- _load_schema(schema_name) utility for loading JSON schema files.
"""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError

from ai_trading.artifacts.validation import (
    _load_schema,
    validate_manifest,
    validate_metrics,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures — load example data from docs/specifications/
# ---------------------------------------------------------------------------


@pytest.fixture()
def example_manifest():
    """Load the example manifest from docs/specifications/example_manifest.json."""
    path = PROJECT_ROOT / "docs" / "specifications" / "example_manifest.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture()
def example_metrics():
    """Load the example metrics from docs/specifications/example_metrics.json."""
    path = PROJECT_ROOT / "docs" / "specifications" / "example_metrics.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# AC: Module importable — validate_manifest, validate_metrics, _load_schema
# ---------------------------------------------------------------------------


class TestModuleImportable:
    """#047 — AC: Le module ai_trading/artifacts/validation.py existe et est importable."""

    def test_validate_manifest_callable(self):
        assert callable(validate_manifest)

    def test_validate_metrics_callable(self):
        assert callable(validate_metrics)

    def test_load_schema_callable(self):
        assert callable(_load_schema)


# ---------------------------------------------------------------------------
# AC: _load_schema loads JSON schema files
# ---------------------------------------------------------------------------


class TestLoadSchema:
    """#047 — _load_schema correctly loads JSON schema files."""

    def test_load_manifest_schema(self):
        schema = _load_schema("manifest.schema.json")
        assert isinstance(schema, dict)
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        assert "properties" in schema

    def test_load_metrics_schema(self):
        schema = _load_schema("metrics.schema.json")
        assert isinstance(schema, dict)
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        assert "properties" in schema

    def test_load_nonexistent_schema_raises(self):
        with pytest.raises(FileNotFoundError):
            _load_schema("nonexistent.schema.json")


# ---------------------------------------------------------------------------
# AC: Examples pass validation without error
# ---------------------------------------------------------------------------


class TestNominalValidation:
    """#047 — AC: Les exemples fournis passent la validation sans erreur."""

    def test_example_manifest_valid(self, example_manifest):
        validate_manifest(example_manifest)  # should not raise

    def test_example_metrics_valid(self, example_metrics):
        validate_metrics(example_metrics)  # should not raise


# ---------------------------------------------------------------------------
# AC: Draft 2020-12 is used
# ---------------------------------------------------------------------------


class TestDraft202012:
    """#047 — AC: La validation utilise Draft 2020-12 de JSON Schema."""

    def test_manifest_schema_uses_draft_2020_12(self):
        schema = _load_schema("manifest.schema.json")
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    def test_metrics_schema_uses_draft_2020_12(self):
        schema = _load_schema("metrics.schema.json")
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


# ---------------------------------------------------------------------------
# AC: Violation — missing required field → explicit error
# ---------------------------------------------------------------------------


class TestMissingRequiredField:
    """#047 — AC: Un champ requis manquant → erreur explicite avec message clair."""

    def test_manifest_missing_run_id(self, example_manifest):
        data = copy.deepcopy(example_manifest)
        del data["run_id"]
        with pytest.raises(ValidationError, match="run_id"):
            validate_manifest(data)

    def test_manifest_missing_dataset(self, example_manifest):
        data = copy.deepcopy(example_manifest)
        del data["dataset"]
        with pytest.raises(ValidationError, match="dataset"):
            validate_manifest(data)

    def test_metrics_missing_run_id(self, example_metrics):
        data = copy.deepcopy(example_metrics)
        del data["run_id"]
        with pytest.raises(ValidationError, match="run_id"):
            validate_metrics(data)

    def test_metrics_missing_folds(self, example_metrics):
        data = copy.deepcopy(example_metrics)
        del data["folds"]
        with pytest.raises(ValidationError, match="folds"):
            validate_metrics(data)

    def test_manifest_missing_nested_required(self, example_manifest):
        """Missing a required field inside a nested object (dataset.exchange)."""
        data = copy.deepcopy(example_manifest)
        del data["dataset"]["exchange"]
        with pytest.raises(ValidationError, match="exchange"):
            validate_manifest(data)


# ---------------------------------------------------------------------------
# AC: Violation — incorrect type → explicit error
# ---------------------------------------------------------------------------


class TestIncorrectType:
    """#047 — AC: Un type incorrect → erreur explicite."""

    def test_manifest_run_id_not_string(self, example_manifest):
        data = copy.deepcopy(example_manifest)
        data["run_id"] = 12345
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_manifest_dataset_symbols_not_array(self, example_manifest):
        data = copy.deepcopy(example_manifest)
        data["dataset"]["symbols"] = "BTCUSDT"  # should be array
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_metrics_fold_id_not_integer(self, example_metrics):
        data = copy.deepcopy(example_metrics)
        data["folds"][0]["fold_id"] = "zero"
        with pytest.raises(ValidationError):
            validate_metrics(data)

    def test_metrics_n_trades_not_integer(self, example_metrics):
        data = copy.deepcopy(example_metrics)
        data["folds"][0]["trading"]["n_trades"] = 3.5
        with pytest.raises(ValidationError):
            validate_metrics(data)


# ---------------------------------------------------------------------------
# AC: Violation — value out of enum → explicit error
# ---------------------------------------------------------------------------


class TestEnumViolation:
    """#047 — AC: Une valeur hors enum → erreur explicite."""

    def test_manifest_exchange_invalid_enum(self, example_manifest):
        data = copy.deepcopy(example_manifest)
        data["dataset"]["exchange"] = "kraken"
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_manifest_strategy_type_invalid_enum(self, example_manifest):
        data = copy.deepcopy(example_manifest)
        data["strategy"]["strategy_type"] = "ensemble"
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_manifest_cost_model_invalid_enum(self, example_manifest):
        data = copy.deepcopy(example_manifest)
        data["costs"]["cost_model"] = "flat_fee"
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_metrics_strategy_type_invalid_enum(self, example_metrics):
        data = copy.deepcopy(example_metrics)
        data["strategy"]["strategy_type"] = "hybrid"
        with pytest.raises(ValidationError):
            validate_metrics(data)

    def test_metrics_threshold_method_invalid_enum(self, example_metrics):
        data = copy.deepcopy(example_metrics)
        data["folds"][0]["threshold"]["method"] = "percentile"
        with pytest.raises(ValidationError):
            validate_metrics(data)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """#047 — Edge cases and boundary scenarios."""

    def test_validate_manifest_empty_dict(self):
        with pytest.raises(ValidationError):
            validate_manifest({})

    def test_validate_metrics_empty_dict(self):
        with pytest.raises(ValidationError):
            validate_metrics({})

    def test_manifest_additional_property_rejected(self, example_manifest):
        """Schema has additionalProperties: false at top level."""
        data = copy.deepcopy(example_manifest)
        data["unexpected_field"] = "surprise"
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_metrics_additional_property_rejected(self, example_metrics):
        """Schema has additionalProperties: false at top level."""
        data = copy.deepcopy(example_metrics)
        data["unexpected_field"] = "surprise"
        with pytest.raises(ValidationError):
            validate_metrics(data)

    def test_manifest_empty_symbols_array(self, example_manifest):
        """minItems: 1 on symbols array."""
        data = copy.deepcopy(example_manifest)
        data["dataset"]["symbols"] = []
        with pytest.raises(ValidationError):
            validate_manifest(data)

    def test_metrics_empty_folds_array(self, example_metrics):
        """minItems: 1 on folds array."""
        data = copy.deepcopy(example_metrics)
        data["folds"] = []
        with pytest.raises(ValidationError):
            validate_metrics(data)

    def test_manifest_negative_horizon(self, example_manifest):
        """horizon_H_bars minimum: 1."""
        data = copy.deepcopy(example_manifest)
        data["label"]["horizon_H_bars"] = 0
        with pytest.raises(ValidationError):
            validate_manifest(data)
