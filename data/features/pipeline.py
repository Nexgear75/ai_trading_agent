"""
Created on 19 febuary 2026

@author: Alex Fougeroux
"""

import pandas as pd
from config import DEFAULT_TIMEFRAME
from data.features.candle_features import add_candle_features
from data.features.momentum_features import add_momentum_features
from data.features.trend_features import add_trend_features
from data.features.oscillator_features import add_oscillator_features
from data.features.volume_features import add_volume_features
from data.features.volatility_features import add_volatility_features
from data.features.temporal_features import add_temporal_features

# ----- Feature columns par timeframe -----

# Pipeline standard 1d (22 features)
FEATURE_COLUMNS = [
    "body",
    "upper_wick",
    "lower_wick",
    "range",
    "green_ratio",
    "return_1d",
    "ema9_ratio",
    "ema21_ratio",
    "ema50_ratio",
    "ema100_ratio",
    "price_vs_ma50",
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "bollinger_position",
    "volume_ratio",
    "volume_return",
    "volatility",
    "obv_normalized",
    "volume_directional",
    "atr_normalized",
]

# Pipeline optimisé 1h (30 features) — périodes natives + features temporelles
FEATURE_COLUMNS_1H = [
    "body",
    "upper_wick",
    "lower_wick",
    "range",
    "green_ratio",
    "return_1d",
    "return_3d",
    "return_6d",
    "return_12d",
    "return_24d",
    "ema9_ratio",
    "ema21_ratio",
    "ema50_ratio",
    "ema100_ratio",
    "price_vs_ma50",
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "bollinger_position",
    "volume_ratio",
    "volume_return",
    "volatility",
    "obv_normalized",
    "volume_directional",
    "atr_normalized",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
]


def get_feature_columns(timeframe: str = DEFAULT_TIMEFRAME) -> list:
    """Retourne la liste des feature columns pour le timeframe donné."""
    if timeframe == "1h":
        return FEATURE_COLUMNS_1H
    return FEATURE_COLUMNS


def build_features(df: pd.DataFrame, timeframe: str = DEFAULT_TIMEFRAME) -> pd.DataFrame:
    """
    Build all technical features for a DataFrame containing OHLCV data.

    Dispatches to the appropriate feature pipeline based on timeframe:
    - Default (1d): standard 22-feature pipeline
    - 1h: optimised 30-feature pipeline with day-equivalent indicator periods
          and intraday temporal features

    Args:
        df: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
        timeframe: Target timeframe, controls which feature pipeline is used.

    Returns:
        DataFrame with all technical features added and NaN rows removed
    """
    df = add_candle_features(df)

    if timeframe == "1h":
        # ----- Pipeline 1h — périodes natives (varient dans la fenêtre de 72 barres) -----
        df = add_momentum_features(df, periods=[1, 3, 6, 12, 24])
        df = add_trend_features(df, periods=[9, 21, 50, 100])
        df = add_oscillator_features(df, rsi_period=14, macd_fast=12,
                                     macd_slow=26, macd_sig=9)
        df = add_volume_features(df, volume_window=20, vol_window=14)
        df = add_volatility_features(df, atr_period=14)
        df = add_temporal_features(df)
    else:
        # ----- Pipeline standard 1d (inchangé) -----
        df = add_momentum_features(df)
        df = add_trend_features(df)
        df = add_oscillator_features(df)
        df = add_volume_features(df)
        df = add_volatility_features(df)

    # ----- Delete Nan ----- #
    df.dropna(inplace=True)

    return df
