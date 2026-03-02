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


@register_model("dummy")
class DummyModel(BaseModel):
    """Dummy model that returns random float32 predictions from a fixed seed."""

    output_type = "regression"

    def __init__(self, seed: int = 42) -> None:
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

    def save(self, path: Path) -> None:
        """Persist seed to a JSON file."""
        path = Path(path)
        path.write_text(json.dumps({"seed": self._seed}))

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
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        data = json.loads(path.read_text())
        self._seed = data["seed"]
