"""JSON Schema validation for manifest and metrics artifacts.

Uses Draft 2020-12 JSON Schema validation via the ``jsonschema`` library.
Schemas are loaded from ``docs/specifications/`` relative to the project root.
"""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

# Project root: two levels up from ai_trading/artifacts/validation.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SCHEMAS_DIR = _PROJECT_ROOT / "docs" / "specifications"


def _load_schema(schema_name: str) -> dict:
    """Load a JSON schema file from ``docs/specifications/``.

    Parameters
    ----------
    schema_name : str
        File name of the schema (e.g. ``"manifest.schema.json"``).

    Returns
    -------
    dict
        Parsed JSON schema.

    Raises
    ------
    FileNotFoundError
        If the schema file does not exist.
    """
    schema_path = _SCHEMAS_DIR / schema_name
    if not schema_path.is_file():
        raise FileNotFoundError(
            f"Schema file not found: {schema_path}"
        )
    with open(schema_path) as f:
        return json.load(f)


def _validate(data: dict, schema_name: str) -> None:
    """Validate *data* against the named JSON schema (Draft 2020-12).

    Raises
    ------
    jsonschema.ValidationError
        If *data* does not conform to the schema.  The exception message
        contains the path and description of the first violation.
    """
    schema = _load_schema(schema_name)
    validator = Draft202012Validator(schema)
    validator.validate(data)


def validate_manifest(data: dict) -> None:
    """Validate a manifest dictionary against ``manifest.schema.json``.

    Raises
    ------
    jsonschema.ValidationError
        With a clear message identifying the failing property.
    """
    _validate(data, "manifest.schema.json")


def validate_metrics(data: dict) -> None:
    """Validate a metrics dictionary against ``metrics.schema.json``.

    Raises
    ------
    jsonschema.ValidationError
        With a clear message identifying the failing property.
    """
    _validate(data, "metrics.schema.json")
