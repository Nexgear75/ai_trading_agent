"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd


def add_candle_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add candlestick features to a DataFrame containing OHLCV data.

    Calculates body size, upper wick, lower wick, and range as percentages
    relative to the open price.

    Args:
        df: DataFrame with columns 'open', 'high', 'low', 'close'

    Returns:
        DataFrame with added columns: 'body', 'upper_wick', 'lower_wick', 'range'
    """
    df = df.copy()

    high_open = df[["open", "close"]].max(axis=1)
    low_open = df[["open", "close"]].min(axis=1)

    df["body"] = (df["close"] - df["open"]) / df["open"]
    df["upper_wick"] = (df["high"] - high_open) / df["open"]
    df["lower_wick"] = (low_open - df["low"]) / df["open"]
    df["range"] = (df["high"] - df["low"]) / df["open"]

    return df
