"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd


def add_trend_features(df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
    """
    Add trend features to a DataFrame containing price data.

    Calculates Exponential Moving Average (EMA) ratios for multiple periods.
    The ratio is computed as EMA divided by the close price to show
    whether price is above or below the moving average.

    Args:
        df: DataFrame with a 'close' column
        periods: EMA span values. Defaults to [9, 21, 50, 100] (1d standard).
                 For 1h use day-equivalent periods: [216, 504, 1200, 2400].

    Returns:
        DataFrame with added columns: 'ema{span}_ratio' for each span in periods
    """
    df = df.copy()

    if periods is None:
        periods = [9, 21, 50, 100]

    for span in periods:
        ema = df["close"].ewm(span=span, adjust=False).mean()
        df[f"ema{span}_ratio"] = ema / df["close"]

    # ----- Price vs SMA longue (positionnement par rapport à la plus grande MA) -----
    sma_period = max(periods)
    sma_long = df["close"].rolling(sma_period).mean()
    df["price_vs_ma50"] = df["close"] / sma_long - 1

    return df
