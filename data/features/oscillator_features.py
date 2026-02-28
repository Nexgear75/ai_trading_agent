"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute the Relative Strength Index (RSI) for a price series.

    RSI is a momentum oscillator that measures the speed and change of price
    movements on a scale of 0 to 100.

    Args:
        series: Price series (typically close prices)
        period: Lookback period for RSI calculation (default: 14)

    Returns:
        RSI values as a Series (0-100 scale)
    """
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)

    return 100 - (100 / (1 + rs))


def add_oscillator_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add oscillator features to a DataFrame containing price data.

    Computes RSI (normalized to 0-1 scale) and MACD indicator with
    signal line and histogram.

    Args:
        df: DataFrame with a 'close' column

    Returns:
        DataFrame with added columns: 'rsi', 'macd', 'macd_signal', 'macd_hist'
    """
    df = df.copy()

    # ----- Normalized RSI between 0 and 1 ----- #
    df["rsi"] = compute_rsi(df["close"], 14) / 100

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = (ema12 - ema26) / df["close"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df
