"""XGBoostRegModel — XGBoost regression model for the AI Trading Pipeline.

Implements ``fit()`` with strict input validation, config-driven hyperparameters,
and the tabular adapter ``flatten_seq_to_tab``.

Task #060 (WS-XGB-2), Task #062 (WS-XGB-3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xgboost as xgb

from ai_trading.data.dataset import flatten_seq_to_tab
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
        """Train the XGBoost regressor on flattened tabular data.

        Validates inputs, flattens 3D sequences to 2D via ``flatten_seq_to_tab``,
        instantiates ``XGBRegressor`` with config-driven hyperparameters and
        imposed parameters, then fits with ``eval_set`` for early stopping.

        Task #062 (WS-XGB-3).
        """
        # --- Strict input validation ---
        if X_train.ndim != 3:
            raise ValueError(
                f"X_train must be 3D (N, L, F), got {X_train.ndim}D "
                f"with shape {X_train.shape}."
            )
        if X_val.ndim != 3:
            raise ValueError(
                f"X_val must be 3D (N, L, F), got {X_val.ndim}D "
                f"with shape {X_val.shape}."
            )
        if y_train.ndim != 1:
            raise ValueError(
                f"y_train must be 1D (N,), got {y_train.ndim}D "
                f"with shape {y_train.shape}."
            )
        if y_val.ndim != 1:
            raise ValueError(
                f"y_val must be 1D (N,), got {y_val.ndim}D "
                f"with shape {y_val.shape}."
            )
        if X_train.shape[0] == 0:
            raise ValueError("X_train must have at least 1 sample, got 0.")
        if X_val.shape[0] == 0:
            raise ValueError("X_val must have at least 1 sample, got 0.")
        if X_train.shape[0] != y_train.shape[0]:
            raise ValueError(
                f"X_train and y_train sample count mismatch: "
                f"X_train has {X_train.shape[0]}, y_train has {y_train.shape[0]}."
            )
        if X_val.shape[0] != y_val.shape[0]:
            raise ValueError(
                f"X_val and y_val sample count mismatch: "
                f"X_val has {X_val.shape[0]}, y_val has {y_val.shape[0]}."
            )
        if X_train.dtype != np.float32:
            raise TypeError(
                f"X_train must be float32, got {X_train.dtype}."
            )
        if X_val.dtype != np.float32:
            raise TypeError(
                f"X_val must be float32, got {X_val.dtype}."
            )
        if y_train.dtype != np.float32:
            raise TypeError(
                f"y_train must be float32, got {y_train.dtype}."
            )
        if y_val.dtype != np.float32:
            raise TypeError(
                f"y_val must be float32, got {y_val.dtype}."
            )

        # --- Flatten 3D → 2D via adapter ---
        n_features = X_train.shape[2]
        feature_names = [f"f{i}" for i in range(n_features)]
        x_tab_train, _ = flatten_seq_to_tab(X_train, feature_names)
        x_tab_val, _ = flatten_seq_to_tab(X_val, feature_names)

        # --- Instantiate XGBRegressor (config-driven + imposed params) ---
        xgb_cfg = config.models.xgboost
        self._model = xgb.XGBRegressor(
            max_depth=xgb_cfg.max_depth,
            n_estimators=xgb_cfg.n_estimators,
            learning_rate=xgb_cfg.learning_rate,
            subsample=xgb_cfg.subsample,
            colsample_bytree=xgb_cfg.colsample_bytree,
            reg_alpha=xgb_cfg.reg_alpha,
            reg_lambda=xgb_cfg.reg_lambda,
            objective="reg:squarederror",
            tree_method="hist",
            booster="gbtree",
            random_state=config.reproducibility.global_seed,
            early_stopping_rounds=config.training.early_stopping_patience,
            verbosity=0,
        )

        # --- Fit with eval_set for early stopping ---
        self._model.fit(
            x_tab_train, y_train,
            eval_set=[(x_tab_val, y_val)],
            verbose=False,
        )

        return {
            "best_iteration": self._model.best_iteration,
            "best_score": self._model.best_score,
        }

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
