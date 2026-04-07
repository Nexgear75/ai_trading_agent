"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd


def add_volume_features(
    df: pd.DataFrame,
    volume_window: int = 20,
    vol_window: int = 14,
) -> pd.DataFrame:
    """
    Add volume-based features to a DataFrame containing OHLCV data.

    Computes volume ratio relative to rolling average, volume return,
    and price volatility.

    Args:
        df: DataFrame with 'volume' and 'close' columns
        volume_window: Rolling window for volume ratio. Default 20 (1d).
                       For 1h use 480 (20×24).
        vol_window: Rolling window for volatility std. Default 14 (1d).
                    For 1h use 336 (14×24).

    Returns:
        DataFrame with added columns: 'volume_ratio', 'volume_return', 'volatility'
    """
    df = df.copy()

    df["volume_ratio"] = df["volume"] / df["volume"].rolling(volume_window).mean()
    df["volume_return"] = df["volume"].pct_change()
    df["volatility"] = df["close"].pct_change().rolling(vol_window).std()

    return df
