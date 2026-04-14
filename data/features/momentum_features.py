"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd


def add_momentum_features(df: pd.DataFrame, periods: list = None) -> pd.DataFrame:
    """
    Add momentum features to a DataFrame containing price data.

    Calculates returns over multiple periods as percentage change of the close price.

    Args:
        df: DataFrame with a 'close' column
        periods: Lookback periods. Defaults to [1, 3, 7, 14, 21] (1d standard).
                 For 1h use [1, 6, 12, 24, 48] (1h to 2 days).

    Returns:
        DataFrame with added columns: 'return_{period}d' for each period
    """
    df = df.copy()

    if periods is None:
        periods = [1, 3, 7, 14, 21]

    for period in periods:
        df[f"return_{period}d"] = df["close"].pct_change(period)

    return df
