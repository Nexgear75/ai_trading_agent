from __future__ import annotations

import torch

from config import DEFAULT_TIMEFRAME
from models.bilstm.evaluation import load_model
from models.supervised_predictor import SupervisedPredictor


class BiLSTMPredictor(SupervisedPredictor):
    def __init__(self, timeframe: str = "1h") -> None:
        super().__init__(timeframe)
        self._model = None
        self._device = torch.device("mps" if torch.mps.is_available() else "cpu")

    @property
    def name(self) -> str:
        return f"BiLSTM-{self._timeframe}"

    def _load_model(self, checkpoint_path: str) -> None:
        self._model, _ = load_model(checkpoint_path, self._device)

    def _forward(self, scaled_window) -> float:
        import torch
        x = torch.tensor(scaled_window[None], dtype=torch.float32, device=self._device)
        with torch.no_grad():
            return float(self._model(x).cpu().numpy().ravel()[0])

    def _predict_batch_scaled(self, X_scaled):
        import numpy as np
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        dataset = TensorDataset(torch.tensor(X_scaled, dtype=torch.float32))
        loader = DataLoader(dataset, batch_size=64, shuffle=False)
        preds = []
        with torch.no_grad():
            for (batch,) in loader:
                preds.append(self._model(batch.to(self._device)).cpu().numpy())
        return np.concatenate(preds).ravel()
