"""BuyHoldBaseline — permanent Go signal for buy & hold backtest.

Always predicts 1 (Go), combined with ``execution_mode = "single_trade"``
to produce a single trade: entry at ``Open[first_bar]``, exit at
``Close[last_bar]``.  Serves as an upper-activity baseline.

Task #038 — WS-9.
Spec reference: §12.5, §13.2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ai_trading.models.base import BaseModel, register_model

_MODEL_FILENAME = "buy_hold_baseline.json"


@register_model("buy_hold")
class BuyHoldBaseline(BaseModel):
    """Baseline that always goes long — predict() always returns ones."""

    output_type = "signal"
    execution_mode = "single_trade"

    def fit(
        self,
        X_train: np.ndarray,  # noqa: N803
        y_train: np.ndarray,
        X_val: np.ndarray,  # noqa: N803
        y_val: np.ndarray,
        config: Any,
        run_dir: Path,
        meta_train: Any = None,
        meta_val: Any = None,
        ohlcv: Any = None,
    ) -> dict:
        """No-op — BuyHoldBaseline has nothing to learn."""
        return {}

    def predict(
        self,
        X: np.ndarray,  # noqa: N803
        meta: Any = None,
        ohlcv: Any = None,
    ) -> np.ndarray:
        """Return all-one signals: permanent Go.

        Parameters
        ----------
        X : np.ndarray
            Input features, shape ``(N, L, F)``, dtype float32.

        Returns
        -------
        np.ndarray
            Ones of shape ``(N,)``, dtype float32.
        """
        n = X.shape[0]
        return np.ones(n, dtype=np.float32)

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
        """Persist (minimal) state to a JSON file."""
        resolved = self._resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(json.dumps({"model": "buy_hold"}))

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
        json.loads(resolved.read_text())
