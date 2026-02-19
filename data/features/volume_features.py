"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd


def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add volume-based features to a DataFrame containing OHLCV data.

    Computes volume ratio relative to 20-period moving average,
    volume return percentage change, and price volatility.

    Args:
        df: DataFrame with 'volume' and 'close' columns

    Returns:
        DataFrame with added columns: 'volume_ratio', 'volume_return', 'volatility'
    """
    df = df.copy()

    df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()
    df["volume_return"] = df["volume"].pct_change()
    df["volatility"] = df["close"].pct_change().rolling(14).std()

    return df
