"""
Data preparation for LSTM model.

Reuses the same data pipeline as CNN since both models
expect the same input format: (batch, window_size, n_features).
"""

from models.cnn.data_preparator import prepare_data

__all__ = ["prepare_data"]
