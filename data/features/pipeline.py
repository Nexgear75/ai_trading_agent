"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd
from data.features.candle_features import add_candle_features
from data.features.momentum_features import add_momentum_features
from data.features.trend_features import add_trend_features
from data.features.oscillator_features import add_oscillator_features
from data.features.volume_features import add_volume_features

FEATURE_COLUMNS = [
    "body",
    "upper_wick",
    "lower_wick",
    "range",
    "return_1d",
    "return_3d",
    "return_7d",
    "return_14d",
    "return_21d",
    "ema9_ratio",
    "ema21_ratio",
    "ema50_ratio",
    "ema100_ratio",
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "volume_ratio",
    "volume_return",
    "volatility",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build all technical features for a DataFrame containing OHLCV data.

    Applies all feature modules in sequence: candle features, momentum,
    trend, oscillator, and volume features. Removes rows with NaN values.

    Args:
        df: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns

    Returns:
        DataFrame with all technical features added and NaN rows removed
    """
    df = add_candle_features(df)
    df = add_momentum_features(df)
    df = add_trend_features(df)
    df = add_oscillator_features(df)
    df = add_volume_features(df)

    # ----- Delete Nan ----- #
    df.dropna(inplace=True)

    return df
