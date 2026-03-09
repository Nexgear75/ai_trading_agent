"""Fold trainer — orchestrates scaling, fitting, and prediction per fold."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from lib.config import PipelineConfig
from lib.models import BaseModelABC
from lib.scaler import create_scaler


class FoldTrainer:
    def __init__(self, config: PipelineConfig) -> None:
        self._config = config

    def train_fold(
        self,
        model: BaseModelABC,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        X_test: np.ndarray,
        run_dir: Path,
        meta_train: Any = None,
        meta_val: Any = None,
        meta_test: Any = None,
        ohlcv: Any = None,
    ) -> dict[str, Any]:
        run_dir.mkdir(parents=True, exist_ok=True)

        scaler = create_scaler(self._config.scaling)
        scaler.fit(X_train)
        x_train_scaled = scaler.transform(X_train)
        x_val_scaled = scaler.transform(X_val)
        x_test_scaled = scaler.transform(X_test)

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

        y_hat_val = model.predict(X=x_val_scaled, meta=meta_val, ohlcv=ohlcv)
        y_hat_test = model.predict(X=x_test_scaled, meta=meta_test, ohlcv=ohlcv)

        model.save(run_dir / "model")

        return {
            "y_hat_val": y_hat_val,
            "y_hat_test": y_hat_test,
            "artifacts": artifacts,
            "scaler": scaler,
        }
