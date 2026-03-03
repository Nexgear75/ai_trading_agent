"""DummyModel — trivial BaseModel subclass for integration testing.

Produces reproducible random predictions via ``numpy.random.default_rng(seed)``.
Serializes state as minimal JSON (``{"seed": <int>}``).

Task #025 (WS-6).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ai_trading.models.base import BaseModel, register_model

_MODEL_FILENAME = "dummy_model.json"


@register_model("dummy")
class DummyModel(BaseModel):
    """Dummy model that returns random float32 predictions from a fixed seed."""

    output_type = "regression"

    def __init__(self, seed: int) -> None:
        self._seed = seed

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        config: Any,
        run_dir: Path,
        meta_train: Any = None,
        meta_val: Any = None,
        ohlcv: Any = None,
    ) -> dict:
        """No-op training — DummyModel has nothing to learn."""
        return {}

    def predict(
        self,
        X: np.ndarray,
        meta: Any = None,
        ohlcv: Any = None,
    ) -> np.ndarray:
        """Return reproducible random predictions of shape ``(N,)`` float32."""
        n = X.shape[0]
        rng = np.random.default_rng(self._seed)
        return rng.standard_normal(n).astype(np.float32)

    @staticmethod
    def _resolve_path(path: Path) -> Path:
        """Resolve *path* to a concrete file path.

        If *path* is an existing directory, append the default model filename.
        Otherwise treat *path* as a file path.
        """
        path = Path(path)
        if path.is_dir():
            return path / _MODEL_FILENAME
        return path

    def save(self, path: Path) -> None:
        """Persist seed to a JSON file."""
        resolved = self._resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(json.dumps({"seed": self._seed}))

    def load(self, path: Path) -> None:
        """Restore seed from a JSON file.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        json.JSONDecodeError
            If file content is not valid JSON.
        KeyError
            If JSON does not contain ``"seed"`` key.
        """
        resolved = self._resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Model file not found: {resolved}")
        data = json.loads(resolved.read_text())
        self._seed = data["seed"]
