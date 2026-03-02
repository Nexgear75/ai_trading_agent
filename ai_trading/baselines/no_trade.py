"""NoTradeBaseline — zero-signal baseline for backtest comparison.

Always predicts 0 (no-go), producing zero trades, flat equity, and zero PnL.
Serves as the lower performance bound for Go/No-Go comparison.

Task #037 — WS-9.
Spec reference: §13.1.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ai_trading.models.base import BaseModel, register_model

_MODEL_FILENAME = "no_trade_baseline.json"


@register_model("no_trade")
class NoTradeBaseline(BaseModel):
    """Baseline that never trades — predict() always returns zeros."""

    output_type = "signal"
    execution_mode = "standard"

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
        """No-op — NoTradeBaseline has nothing to learn."""
        return {}

    def predict(
        self,
        X: np.ndarray,  # noqa: N803
        meta: Any = None,
        ohlcv: Any = None,
    ) -> np.ndarray:
        """Return all-zero signals: no trade is ever triggered.

        Parameters
        ----------
        X : np.ndarray
            Input features, shape ``(N, L, F)``, dtype float32.

        Returns
        -------
        np.ndarray
            Zeros of shape ``(N,)``, dtype float32.
        """
        n = X.shape[0]
        return np.zeros(n, dtype=np.float32)

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
        resolved.write_text(json.dumps({"model": "no_trade"}))

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
