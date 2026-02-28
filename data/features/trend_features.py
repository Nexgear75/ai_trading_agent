"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd


def add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add trend features to a DataFrame containing price data.

    Calculates Exponential Moving Average (EMA) ratios for multiple periods.
    The ratio is computed as EMA divided by the close price to show
    whether price is above or below the moving average.

    Args:
        df: DataFrame with a 'close' column

    Returns:
        DataFrame with added columns: 'ema9_ratio', 'ema21_ratio',
        'ema50_ratio', 'ema100_ratio'
    """
    df = df.copy()

    for span in [9, 21, 50, 100]:
        ema = df["close"].ewm(span=span, adjust=False).mean()
        df[f"ema{span}_ratio"] = ema / df["close"]

    return df
