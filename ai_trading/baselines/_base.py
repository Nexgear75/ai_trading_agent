"""Shared persistence helpers for stateless baselines.

Provides ``BaselinePersistenceMixin`` with ``_resolve_path``, ``save``, and
``load`` implementations reusable by all stateless baselines (no_trade,
buy_hold, sma_rule, …).

Subclasses must define two class attributes:
- ``_model_filename``: default JSON filename (e.g. ``"no_trade_baseline.json"``).
- ``_model_name``: identifier written into the JSON payload (e.g. ``"no_trade"``).
"""

from __future__ import annotations

import json
from pathlib import Path


class BaselinePersistenceMixin:
    """Mixin providing save/load for stateless baselines.

    Subclass must set ``_model_filename`` and ``_model_name`` class attributes.
    """

    _model_filename: str
    _model_name: str

    @classmethod
    def _resolve_path(cls, path: Path) -> Path:
        """Resolve *path* to a concrete file path.

        If *path* is an existing directory, append the default model filename.
        Otherwise treat *path* as a file path.
        """
        path = Path(path)
        if path.is_dir():
            return path / cls._model_filename
        return path

    def save(self, path: Path) -> None:
        """Persist (minimal) state to a JSON file."""
        resolved = self._resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(json.dumps({"model": self._model_name}))

    def load(self, path: Path) -> None:
        """Restore state from a JSON file.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        """
        resolved = self._resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Model file not found: {resolved}")
        # Validate the file contains valid JSON (no state to restore).
        _ = json.loads(resolved.read_text())
