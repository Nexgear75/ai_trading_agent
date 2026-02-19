"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import numpy as np
import pandas as pd
from data.features.pipeline import FEATURE_COLUMNS
from config import WINDOW_SIZE


def build_windows(df: pd.DataFrame):
    """
    Build sliding windows from time series data for machine learning.

    Creates sequences of WINDOW_SIZE length from feature columns
    with corresponding labels and dates for supervised learning.

    Args:
        df: DataFrame containing FEATURE_COLUMNS and 'label' column

    Returns:
        Tuple of (X, y, idx) where:
            - X: 3D array of shape (n_samples, WINDOW_SIZE, n_features)
            - y: 1D array of labels
            - idx: 1D array of timestamps
    """
    data = df[FEATURE_COLUMNS].values
    labels = df["label"].values
    dates = df.index

    X, y, idx = [], [], []

    for i in range(WINDOW_SIZE, len(data)):
        X.append(data[i - WINDOW_SIZE : i])
        y.append(labels[i])
        idx.append(dates[i])

    return np.array(X), np.array(y), np.array(idx)
