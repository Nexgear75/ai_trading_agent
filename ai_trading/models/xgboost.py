"""XGBoostRegModel — XGBoost regression model for the AI Trading Pipeline.

Stub implementation: all methods raise ``NotImplementedError``.
Full implementation will come in WS-XGB-3/4/5.

Task #060 (WS-XGB-2).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ai_trading.models.base import BaseModel, register_model


@register_model("xgboost_reg")
class XGBoostRegModel(BaseModel):
    """XGBoost regression model registered as ``"xgboost_reg"``."""

    output_type = "regression"

    def __init__(self) -> None:
        self._model = None

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
        """Not implemented yet — stub for WS-XGB-3."""
        raise NotImplementedError("XGBoostRegModel.fit() is not implemented yet.")

    def predict(
        self,
        X: np.ndarray,  # noqa: N803
        meta: Any = None,
        ohlcv: Any = None,
    ) -> np.ndarray:
        """Not implemented yet — stub for WS-XGB-4."""
        raise NotImplementedError("XGBoostRegModel.predict() is not implemented yet.")

    def save(self, path: Path) -> None:
        """Not implemented yet — stub for WS-XGB-5."""
        raise NotImplementedError("XGBoostRegModel.save() is not implemented yet.")

    def load(self, path: Path) -> None:
        """Not implemented yet — stub for WS-XGB-5."""
        raise NotImplementedError("XGBoostRegModel.load() is not implemented yet.")
