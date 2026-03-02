"""BuyHoldBaseline — permanent Go signal for buy & hold backtest.

Always predicts 1 (Go), combined with ``execution_mode = "single_trade"``
to produce a single trade: entry at ``Open[first_bar]``, exit at
``Close[last_bar]``.  Serves as an upper-activity baseline.

Task #038 — WS-9.
Spec reference: §12.5, §13.2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ai_trading.baselines._base import BaselinePersistenceMixin
from ai_trading.models.base import BaseModel, register_model


@register_model("buy_hold")
class BuyHoldBaseline(BaselinePersistenceMixin, BaseModel):
    """Baseline that always goes long — predict() always returns ones."""

    output_type = "signal"
    execution_mode = "single_trade"
    _model_filename = "buy_hold_baseline.json"
    _model_name = "buy_hold"

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
