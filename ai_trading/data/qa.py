"""OHLCV quality assurance checks.

Performs mandatory QA controls on an OHLCV DataFrame before any feature
computation. Detects structural anomalies: irregular timestamps, missing
candles, negative prices, OHLC inconsistencies, and prolonged zero volume.

Reference: spec §4.2 — Contrôles qualité (QA) obligatoires.
"""

from dataclasses import dataclass, field

import pandas as pd

# Mapping from timeframe strings to pandas Timedelta
_TIMEFRAME_DELTA: dict[str, pd.Timedelta] = {
    "1m": pd.Timedelta(minutes=1),
    "3m": pd.Timedelta(minutes=3),
    "5m": pd.Timedelta(minutes=5),
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(hours=1),
    "2h": pd.Timedelta(hours=2),
    "4h": pd.Timedelta(hours=4),
    "6h": pd.Timedelta(hours=6),
    "8h": pd.Timedelta(hours=8),
    "12h": pd.Timedelta(hours=12),
    "1d": pd.Timedelta(days=1),
    "3d": pd.Timedelta(days=3),
    "1w": pd.Timedelta(weeks=1),
}

_REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
_PRICE_COLUMNS = ["open", "high", "low", "close"]

# Minimum consecutive zero-volume bars to count as a "prolonged" streak
_ZERO_VOLUME_MIN_STREAK = 2


@dataclass
class QAReport:
    """Structured report of all QA check results.

    Attributes
    ----------
    passed : bool
        True if all checks passed with no anomalies.
    duplicate_count : int
        Number of duplicate timestamps found.
    missing_timestamps : list[pd.Timestamp]
        List of expected timestamps that are absent from the data.
    negative_price_count : int
        Number of rows with at least one negative price column.
    ohlc_inconsistency_count : int
        Number of rows violating H >= max(O,C) and L <= min(O,C).
    zero_volume_streak_count : int
        Number of separate streaks of >= _ZERO_VOLUME_MIN_STREAK consecutive
        zero-volume bars.
    irregular_delta_count : int
        Number of timestamp pairs whose delta does not match the expected Δ
        and is not a multiple of Δ (i.e. not a simple gap).
    """

    passed: bool
    duplicate_count: int
    missing_timestamps: list = field(default_factory=list)
    negative_price_count: int = 0
    ohlc_inconsistency_count: int = 0
    zero_volume_streak_count: int = 0
    irregular_delta_count: int = 0


def _validate_inputs(df: pd.DataFrame, timeframe: str) -> pd.Timedelta:
    """Validate DataFrame structure and timeframe, return expected delta.

    Raises
    ------
    ValueError
        If the DataFrame is empty, missing required columns, or timeframe
        is unsupported.
    """
    if df.empty:
        raise ValueError("Empty DataFrame: cannot run QA checks on empty data.")

    missing_cols = _REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(
            f"Column(s) missing from DataFrame: {sorted(missing_cols)}. "
            f"Required: {sorted(_REQUIRED_COLUMNS)}"
        )

    expected_delta = _TIMEFRAME_DELTA.get(timeframe)
    if expected_delta is None:
        raise ValueError(
            f"Timeframe '{timeframe}' is not supported. "
            f"Supported: {sorted(_TIMEFRAME_DELTA)}"
        )

    return expected_delta


def _check_negative_prices(df: pd.DataFrame) -> int:
    """Check for negative prices and raise if any found.

    Raises
    ------
    ValueError
        If any price column contains a negative value.
    """
    neg_mask = (df[_PRICE_COLUMNS] < 0).any(axis=1)
    count = int(neg_mask.sum())
    if count > 0:
        raise ValueError(
            f"Negative price detected in {count} row(s). "
            "All price columns (open, high, low, close) must be >= 0."
        )
    return 0


def _check_duplicates(timestamps: pd.Series) -> int:
    """Count duplicate timestamps."""
    return int(timestamps.duplicated().sum())


def _check_missing_candles(
    timestamps: pd.Series,
    expected_delta: pd.Timedelta,
) -> list:
    """Identify missing candle timestamps based on expected delta.

    Returns the list of timestamps that should exist but are absent.
    """
    if len(timestamps) < 2:
        return []

    ts_sorted = timestamps.sort_values().reset_index(drop=True)
    first = ts_sorted.iloc[0]
    last = ts_sorted.iloc[-1]

    # Build the full expected grid
    expected_grid = pd.date_range(start=first, end=last, freq=expected_delta)
    existing_set = set(ts_sorted)
    missing = [ts for ts in expected_grid if ts not in existing_set]
    return missing


def _check_ohlc_consistency(df: pd.DataFrame) -> int:
    """Check OHLC invariant: H >= max(O,C) and L <= min(O,C).

    Returns the count of rows violating the invariant.
    """
    high_violation = df["high"] < df[["open", "close"]].max(axis=1)
    low_violation = df["low"] > df[["open", "close"]].min(axis=1)
    violated = high_violation | low_violation
    return int(violated.sum())


def _check_zero_volume_streaks(df: pd.DataFrame) -> int:
    """Count streaks of consecutive zero-volume bars >= _ZERO_VOLUME_MIN_STREAK.

    Returns the number of separate prolonged zero-volume streaks.
    """
    is_zero = (df["volume"] == 0).astype(int)
    # Detect streak boundaries using diff
    streak_id = (is_zero != is_zero.shift(1)).cumsum()
    # Group by streak and filter zero-volume streaks with sufficient length
    streak_count = 0
    for _sid, group in is_zero.groupby(streak_id):
        if group.iloc[0] == 1 and len(group) >= _ZERO_VOLUME_MIN_STREAK:
            streak_count += 1
    return streak_count


def _check_irregular_delta(
    timestamps: pd.Series,
    expected_delta: pd.Timedelta,
) -> int:
    """Count timestamp pairs with irregular spacing.

    A pair is irregular if the delta is not an exact multiple of expected_delta
    (i.e. it's neither a normal step nor a clean gap of N missing candles).
    Duplicates (delta=0) are handled separately.

    Returns the count of irregular intervals.
    """
    if len(timestamps) < 2:
        return 0

    ts_sorted = timestamps.drop_duplicates().sort_values().reset_index(drop=True)
    if len(ts_sorted) < 2:
        return 0

    diffs = ts_sorted.diff().dropna()
    # A diff is regular if it's an exact positive multiple of expected_delta
    ratio = diffs / expected_delta
    positive = ratio > 0
    irregular = (ratio - ratio.round()).abs() > 1e-9
    return int((positive & irregular).sum())


def run_qa_checks(df: pd.DataFrame, timeframe: str) -> QAReport:
    """Run all mandatory QA checks on an OHLCV DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV DataFrame with columns: timestamp, open, high, low, close, volume.
    timeframe : str
        Expected candle interval (e.g. "1h", "4h", "1d").

    Returns
    -------
    QAReport
        Structured report with results of each check.

    Raises
    ------
    ValueError
        If the DataFrame is empty, missing required columns, timeframe is
        unsupported, or negative prices are detected.
    """
    expected_delta = _validate_inputs(df, timeframe)

    # Check 1: Negative prices — raises immediately
    negative_price_count = _check_negative_prices(df)

    # Check 2: Duplicate timestamps
    duplicate_count = _check_duplicates(df["timestamp"])

    # Check 3: Missing candles
    # Only meaningful on deduplicated timestamps
    ts_deduped = df["timestamp"].drop_duplicates()
    missing_timestamps = _check_missing_candles(ts_deduped, expected_delta)

    # Check 4: OHLC consistency
    ohlc_inconsistency_count = _check_ohlc_consistency(df)

    # Check 5: Zero volume streaks
    zero_volume_streak_count = _check_zero_volume_streaks(df)

    # Check 6: Irregular delta
    irregular_delta_count = _check_irregular_delta(df["timestamp"], expected_delta)

    # Global pass/fail
    passed = (
        duplicate_count == 0
        and len(missing_timestamps) == 0
        and negative_price_count == 0
        and ohlc_inconsistency_count == 0
        and zero_volume_streak_count == 0
        and irregular_delta_count == 0
    )

    return QAReport(
        passed=passed,
        duplicate_count=duplicate_count,
        missing_timestamps=missing_timestamps,
        negative_price_count=negative_price_count,
        ohlc_inconsistency_count=ohlc_inconsistency_count,
        zero_volume_streak_count=zero_volume_streak_count,
        irregular_delta_count=irregular_delta_count,
    )
