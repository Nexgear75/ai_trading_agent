"""NoTradeBaseline — zero-signal baseline for backtest comparison.

Always predicts 0 (no-go), producing zero trades, flat equity, and zero PnL.
Serves as the lower performance bound for Go/No-Go comparison.

Task #037 — WS-9.
Spec reference: §13.1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ai_trading.baselines._base import BaselinePersistenceMixin
from ai_trading.models.base import BaseModel, register_model


@register_model("no_trade")
class NoTradeBaseline(BaselinePersistenceMixin, BaseModel):
    """Baseline that never trades — predict() always returns zeros."""

    output_type = "signal"
    execution_mode = "standard"
    _model_filename = "no_trade_baseline.json"
    _model_name = "no_trade"

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
