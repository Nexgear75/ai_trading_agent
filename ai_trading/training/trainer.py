"""Fold trainer — orchestrates scale → fit → predict → save per fold.

Responsibilities:
1. Create and fit the scaler on X_train only (anti-leak).
2. Transform X_train, X_val, X_test via the fitted scaler.
3. Call model.fit() with scaled data, config, run_dir, meta, ohlcv.
4. Call model.predict() on scaled X_val and X_test.
5. Call model.save(run_dir / "model").
6. Return structured result dict.

The trainer does NOT implement the epoch loop — that is the model's
responsibility.  The trainer does NOT generate prediction CSV files —
that is the orchestrator's responsibility (WS-12.2).

Task #028 (WS-6).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ai_trading.config import PipelineConfig
from ai_trading.data.scaler import create_scaler
from ai_trading.models.base import BaseModel


class FoldTrainer:
    """Orchestrate a single fold: scale → fit → predict → save.

    Parameters
    ----------
    config : PipelineConfig
        Full pipeline configuration (Pydantic model).
    """

    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    def train_fold(
        self,
        model: BaseModel,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        X_test: np.ndarray,
        run_dir: Path,
        meta_train: Any = None,
        meta_val: Any = None,
        ohlcv: Any = None,
    ) -> dict[str, Any]:
        """Run the full fold workflow.

        Parameters
        ----------
        model : BaseModel
            Model instance to train and evaluate.
        X_train : np.ndarray
            Training features, shape ``(N_train, L, F)``, float32.
        y_train : np.ndarray
            Training labels, shape ``(N_train,)``, float32.
        X_val : np.ndarray
            Validation features, shape ``(N_val, L, F)``, float32.
        y_val : np.ndarray
            Validation labels, shape ``(N_val,)``, float32.
        X_test : np.ndarray
            Test features, shape ``(N_test, L, F)``, float32.
        run_dir : Path
            Directory for run artifacts.
        meta_train : Any, optional
            Metadata for training samples (passed to model). Default ``None``.
        meta_val : Any, optional
            Metadata for validation samples (passed to model). Default ``None``.
        ohlcv : Any, optional
            Raw OHLCV data (passed to model for RL context). Default ``None``.

        Returns
        -------
        dict
            Keys: ``y_hat_val``, ``y_hat_test``, ``artifacts``, ``scaler``.
        """
        run_dir.mkdir(parents=True, exist_ok=True)

        # --- 1. Scaling (trainer is sole owner) ---
        scaler = create_scaler(self._config.scaling)
        scaler.fit(X_train)
        x_train_scaled = scaler.transform(X_train)
        x_val_scaled = scaler.transform(X_val)
        x_test_scaled = scaler.transform(X_test)

        # --- 2. Fit ---
        artifacts = model.fit(
            X_train=x_train_scaled,
            y_train=y_train,
            X_val=x_val_scaled,
            y_val=y_val,
            config=self._config,
            run_dir=run_dir,
            meta_train=meta_train,
            meta_val=meta_val,
            ohlcv=ohlcv,
        )

        # --- 3. Predict ---
        y_hat_val = model.predict(X=x_val_scaled, meta=meta_val, ohlcv=ohlcv)
        y_hat_test = model.predict(X=x_test_scaled, ohlcv=ohlcv)

        # --- 4. Save ---
        model.save(run_dir / "model")

        return {
            "y_hat_val": y_hat_val,
            "y_hat_test": y_hat_test,
            "artifacts": artifacts,
            "scaler": scaler,
        }
