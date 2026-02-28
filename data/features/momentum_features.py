"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd


def add_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add momentum features to a DataFrame containing price data.

    Calculates returns over multiple periods (1, 3, 7, 14, 21 days)
    as percentage change of the close price.

    Args:
        df: DataFrame with a 'close' column

    Returns:
        DataFrame with added columns: 'return_1d', 'return_3d', 'return_7d',
        'return_14d', 'return_21d'
    """
    df = df.copy()

    for period in [1, 3, 7, 14, 21]:
        df[f"return_{period}d"] = df["close"].pct_change(period)

    return df
