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


def add_oscillator_features(
    df: pd.DataFrame,
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_sig: int = 9,
) -> pd.DataFrame:
    """
    Add oscillator features to a DataFrame containing price data.

    Computes RSI (normalized to 0-1 scale) and MACD indicator with
    signal line and histogram.

    Args:
        df: DataFrame with a 'close' column
        rsi_period: RSI lookback period. Default 14 (1d). For 1h use 336 (14×24).
        macd_fast: MACD fast EMA period. Default 12. For 1h use 288 (12×24).
        macd_slow: MACD slow EMA period. Default 26. For 1h use 624 (26×24).
        macd_sig: MACD signal EMA period. Default 9. For 1h use 216 (9×24).

    Returns:
        DataFrame with added columns: 'rsi', 'macd', 'macd_signal', 'macd_hist'
    """
    df = df.copy()

    # ----- Normalized RSI between 0 and 1 ----- #
    df["rsi"] = compute_rsi(df["close"], rsi_period) / 100

    ema_fast = df["close"].ewm(span=macd_fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=macd_slow, adjust=False).mean()
    df["macd"] = (ema_fast - ema_slow) / df["close"]
    df["macd_signal"] = df["macd"].ewm(span=macd_sig, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df
