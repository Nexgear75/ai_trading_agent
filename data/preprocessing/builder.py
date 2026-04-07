"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import numpy as np
import pandas as pd
from data.features.pipeline import FEATURE_COLUMNS


def build_windows(df: pd.DataFrame, window_size: int = None):
    """
    Build sliding windows from time series data for machine learning.

    Creates sequences of window_size length from feature columns
    with corresponding labels and dates for supervised learning.

    Args:
        df: DataFrame containing FEATURE_COLUMNS and 'label' column
        window_size: Number of periods in each window. If None, uses
                     WINDOW_SIZE from config (legacy behavior).

    Returns:
        Tuple of (X, y, idx) where:
            - X: 3D array of shape (n_samples, window_size, n_features)
            - y: 1D array of labels
            - idx: 1D array of timestamps
    """
    # Import here to avoid circular dependencies
    if window_size is None:
        from config import WINDOW_SIZE as _window_size
        window_size = _window_size

    data = df[FEATURE_COLUMNS].values
    labels = df["label"].values
    dates = df.index

    X, y, idx = [], [], []

    for i in range(window_size, len(data)):
        X.append(data[i - window_size : i])
        y.append(labels[i])
        idx.append(dates[i])

    return np.array(X), np.array(y), np.array(idx)
