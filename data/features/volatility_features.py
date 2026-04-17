"""
Volatility features derived from OHLCV data.

@author: Alex Fougeroux
"""

import pandas as pd


def add_volatility_features(
    df: pd.DataFrame,
    atr_period: int = 14,
) -> pd.DataFrame:
    """
    Add volatility features to a DataFrame containing OHLCV data.

    Computes the Average True Range (ATR) normalized by close price,
    giving a scale-invariant measure of asset volatility.

    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        atr_period: Lookback period for ATR. Default 14 (1d).
                    For 1h use 336 (14x24).

    Returns:
        DataFrame with added column: 'atr_normalized'
    """
    df = df.copy()

    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.rolling(atr_period).mean()
    df["atr_normalized"] = atr / df["close"]

    return df
