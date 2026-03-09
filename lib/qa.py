"""Data quality checks for OHLCV data."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from lib.timeframes import TIMEFRAME_DELTA

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = {"timestamp_utc", "open", "high", "low", "close", "volume"}
_PRICE_COLUMNS = ["open", "high", "low", "close"]


@dataclass
class QAReport:
    passed: bool
    duplicate_count: int
    missing_timestamps: list[pd.Timestamp]
    ohlc_inconsistency_count: int
    zero_volume_streak_count: int
    irregular_delta_count: int


def _qa_validate_inputs(df: pd.DataFrame, timeframe: str) -> pd.Timedelta:
    if df.empty:
        raise ValueError("Empty DataFrame: cannot run QA checks on empty data.")
    missing_cols = _REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"Column(s) missing from DataFrame: {sorted(missing_cols)}. "
            f"Required: {sorted(_REQUIRED_COLUMNS)}"
        )
    expected_delta = TIMEFRAME_DELTA.get(timeframe)
    if expected_delta is None:
        raise ValueError(
            f"Timeframe '{timeframe}' is not supported. "
            f"Supported: {sorted(TIMEFRAME_DELTA)}"
        )
    return expected_delta


def _check_negative_prices(df: pd.DataFrame) -> None:
    neg_mask = (df[_PRICE_COLUMNS] < 0).any(axis=1)
    count = int(neg_mask.sum())
    if count > 0:
        raise ValueError(
            f"Negative price detected in {count} row(s). "
            "All price columns (open, high, low, close) must be >= 0."
        )
    zero_close_mask = df["close"] <= 0
    zero_close_count = int(zero_close_mask.sum())
    if zero_close_count > 0:
        raise ValueError(
            f"Zero or negative close price detected in {zero_close_count} row(s). "
            "Close must be strictly > 0 (required for log-return computation)."
        )


def _check_duplicates(timestamps: pd.Series) -> int:
    return int(timestamps.duplicated().sum())


def _check_missing_candles(
    timestamps: pd.Series,
    expected_delta: pd.Timedelta,
) -> list[pd.Timestamp]:
    if len(timestamps) < 2:
        return []
    ts_sorted = timestamps.sort_values().reset_index(drop=True)
    first = ts_sorted.iloc[0]
    last = ts_sorted.iloc[-1]
    expected_grid = pd.date_range(
        start=first, end=last, freq=expected_delta, tz=first.tzinfo
    )
    existing_set = set(ts_sorted)
    return [ts for ts in expected_grid if ts not in existing_set]


def _check_ohlc_consistency(df: pd.DataFrame) -> int:
    high_violation = df["high"] < df[["open", "close"]].max(axis=1)
    low_violation = df["low"] > df[["open", "close"]].min(axis=1)
    violated = high_violation | low_violation
    return int(violated.sum())


def _check_zero_volume_streaks(df: pd.DataFrame, min_streak: int) -> int:
    is_zero = (df["volume"] == 0).astype(int)
    streak_id = (is_zero != is_zero.shift(1)).cumsum()
    streak_count = 0
    for _sid, group in is_zero.groupby(streak_id):
        if group.iloc[0] == 1 and len(group) >= min_streak:
            streak_count += 1
    return streak_count


def _check_irregular_delta(
    timestamps: pd.Series,
    expected_delta: pd.Timedelta,
) -> int:
    if len(timestamps) < 2:
        return 0
    ts_sorted = timestamps.drop_duplicates().sort_values().reset_index(drop=True)
    if len(ts_sorted) < 2:
        return 0
    diffs = ts_sorted.diff().dropna()
    ratio = diffs / expected_delta
    positive = ratio > 0
    irregular = (ratio - ratio.round()).abs() > 1e-9
    return int((positive & irregular).sum())


def run_qa_checks(
    df: pd.DataFrame,
    timeframe: str,
    zero_volume_min_streak: int,
) -> QAReport:
    if zero_volume_min_streak < 1:
        raise ValueError(
            f"zero_volume_min_streak must be >= 1, got {zero_volume_min_streak}"
        )
    expected_delta = _qa_validate_inputs(df, timeframe)
    _check_negative_prices(df)
    duplicate_count = _check_duplicates(df["timestamp_utc"])
    ts_deduped = df["timestamp_utc"].drop_duplicates()
    missing_timestamps = _check_missing_candles(ts_deduped, expected_delta)
    ohlc_inconsistency_count = _check_ohlc_consistency(df)
    zero_volume_streak_count = _check_zero_volume_streaks(df, zero_volume_min_streak)
    irregular_delta_count = _check_irregular_delta(df["timestamp_utc"], expected_delta)
    passed = (
        duplicate_count == 0
        and len(missing_timestamps) == 0
        and ohlc_inconsistency_count == 0
        and zero_volume_streak_count == 0
        and irregular_delta_count == 0
    )
    return QAReport(
        passed=passed,
        duplicate_count=duplicate_count,
        missing_timestamps=missing_timestamps,
        ohlc_inconsistency_count=ohlc_inconsistency_count,
        zero_volume_streak_count=zero_volume_streak_count,
        irregular_delta_count=irregular_delta_count,
    )
