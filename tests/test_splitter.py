"""Tests for the walk-forward splitter (WS-4.5, task #019).

Covers:
- parse_timeframe helper
- Walk-forward fold computation with MVP parameters
- Fold disjointness (no shared timestamps between train/val/test)
- Truncation policy (fold with test_end > dataset end → excluded)
- Non-multiple period (total_days not a multiple of step_days)
- Date-based bounds (gaps don't shift bounds)
- min_samples filtering
- Zero valid folds → ValueError
- Logging of fold counters
- Config-driven parameters
"""

import logging
import math
from datetime import timedelta

import pandas as pd
import pytest

from ai_trading.data.splitter import WalkForwardSplitter, parse_timeframe

# ---------------------------------------------------------------------------
# parse_timeframe tests
# ---------------------------------------------------------------------------


class TestParseTimeframe:
    """Tests for parse_timeframe helper (#019)."""

    def test_parse_1h(self):
        assert parse_timeframe("1h") == timedelta(hours=1)

    def test_parse_4h(self):
        assert parse_timeframe("4h") == timedelta(hours=4)

    def test_parse_1d(self):
        assert parse_timeframe("1d") == timedelta(days=1)

    def test_parse_1m(self):
        assert parse_timeframe("1m") == timedelta(minutes=1)

    def test_parse_15m(self):
        assert parse_timeframe("15m") == timedelta(minutes=15)

    def test_parse_1w(self):
        assert parse_timeframe("1w") == timedelta(weeks=1)

    def test_parse_invalid_raises(self):
        with pytest.raises(ValueError, match="invalid"):
            parse_timeframe("invalid")

    def test_parse_empty_raises(self):
        with pytest.raises(ValueError):
            parse_timeframe("")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_timestamps(start: str, days: int, freq: str = "1h") -> pd.DatetimeIndex:
    """Create hourly timestamps over a date range (UTC)."""
    start_dt = pd.Timestamp(start, tz="UTC")
    end_dt = start_dt + pd.Timedelta(days=days)
    # Exclusive end → generate up to end - freq
    return pd.date_range(start=start_dt, end=end_dt - pd.Timedelta(freq), freq=freq)


def _make_mvp_splits_config():
    """Return a minimal splits-like config namespace for MVP defaults."""

    class _Cfg:
        train_days = 180
        test_days = 30
        step_days = 30
        val_frac_in_train = 0.2
        embargo_bars = 4
        min_samples_train = 100
        min_samples_test = 1

    return _Cfg()


# ---------------------------------------------------------------------------
# WalkForwardSplitter — MVP nominal
# ---------------------------------------------------------------------------


class TestWalkForwardSplitterMVP:
    """Nominal tests with MVP parameters (#019)."""

    @pytest.fixture
    def mvp_timestamps(self):
        """~730 days of hourly data starting 2024-01-01 UTC."""
        return _make_timestamps("2024-01-01", days=730, freq="1h")

    @pytest.fixture
    def splitter(self):
        return WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )

    @pytest.fixture
    def folds(self, splitter, mvp_timestamps):
        return splitter.split(mvp_timestamps)

    def test_at_least_one_fold(self, folds):
        assert len(folds) >= 1

    def test_n_folds_upper_bound(self, folds, mvp_timestamps):
        """n_folds_valid <= theoretical upper bound."""
        total_days = (mvp_timestamps[-1] - mvp_timestamps[0]).days + 1
        # Approximate: floor((total_days - train_days) / step_days)
        n_max = math.floor((total_days - 180) / 30)
        assert len(folds) <= n_max

    def test_fold0_train_start(self, folds):
        """Fold k=0: train_start == dataset.start (2024-01-01 00:00 UTC)."""
        expected = pd.Timestamp("2024-01-01 00:00", tz="UTC")
        assert folds[0].train_start == expected

    def test_fold0_train_val_end(self, folds):
        """Fold k=0: train_val_end = start + 180d - 1h = 2024-06-28 23:00."""
        expected = pd.Timestamp("2024-06-28 23:00", tz="UTC")
        assert folds[0].train_val_end == expected

    def test_fold0_val_start(self, folds):
        """Fold k=0: val_start = start + (180 - 36)d = 2024-05-24 00:00."""
        expected = pd.Timestamp("2024-05-24 00:00", tz="UTC")
        assert folds[0].val_start == expected

    def test_fold0_train_only_end(self, folds):
        """Fold k=0: train_only_end = val_start - 1h = 2024-05-23 23:00."""
        expected = pd.Timestamp("2024-05-23 23:00", tz="UTC")
        assert folds[0].train_only_end == expected

    def test_fold0_test_start(self, folds):
        """Fold k=0: test_start = start + 180d + 4*1h = 2024-06-29 04:00."""
        expected = pd.Timestamp("2024-06-29 04:00", tz="UTC")
        assert folds[0].test_start == expected

    def test_fold0_test_end(self, folds):
        """Fold k=0: test_end = test_start + 30d - 1h = 2024-07-29 03:00."""
        expected = pd.Timestamp("2024-07-29 03:00", tz="UTC")
        assert folds[0].test_end == expected

    def test_val_days_computation(self, folds):
        """val_days = floor(180 * 0.2) = 36."""
        fold0 = folds[0]
        val_days = (fold0.train_val_end - fold0.val_start).days + 1
        # val covers from val_start to train_val_end inclusive
        # val_start = 2024-05-24, train_val_end = 2024-06-28 23:00
        # That's 36 days (from day 144 to day 179)
        assert val_days == 36


# ---------------------------------------------------------------------------
# Disjointness
# ---------------------------------------------------------------------------


class TestFoldDisjointness:
    """No shared timestamps between train/val/test within a fold (#019)."""

    @pytest.fixture
    def folds(self):
        ts = _make_timestamps("2024-01-01", days=730, freq="1h")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        return splitter.split(ts)

    def test_train_val_test_disjoint(self, folds):
        """For each fold, train/val/test index sets must be disjoint."""
        for fold in folds:
            train_set = set(fold.train_indices)
            val_set = set(fold.val_indices)
            test_set = set(fold.test_indices)
            assert train_set.isdisjoint(val_set), f"train∩val not empty (fold {fold})"
            assert train_set.isdisjoint(test_set), f"train∩test not empty (fold {fold})"
            assert val_set.isdisjoint(test_set), f"val∩test not empty (fold {fold})"

    def test_temporal_ordering(self, folds):
        """train < val < test temporally (max train < min val < min test)."""
        for fold in folds:
            assert fold.train_only_end < fold.val_start
            assert fold.train_val_end < fold.test_start


# ---------------------------------------------------------------------------
# Truncation policy
# ---------------------------------------------------------------------------


class TestTruncationPolicy:
    """Folds with test_end > dataset.end are excluded (#019)."""

    def test_truncation_short_dataset(self):
        """Dataset just barely fits 1 fold, second fold truncated."""
        # train=180d, test=30d, step=30d, embargo=4bars*1h
        # Minimum for 1 fold: 180d + 4h + 30d = ~210 days + 4h
        # With 215 days, fold k=0 fits, fold k=1 does not
        ts = _make_timestamps("2024-01-01", days=215, freq="1h")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        folds = splitter.split(ts)
        assert len(folds) == 1
        # test_end of fold 0 must be <= dataset end
        dataset_end = ts[-1]
        assert folds[0].test_end <= dataset_end

    def test_no_fold_beyond_dataset_end(self):
        """All folds have test_end within dataset bounds."""
        ts = _make_timestamps("2024-01-01", days=400, freq="1h")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        folds = splitter.split(ts)
        dataset_end = ts[-1]
        for fold in folds:
            assert fold.test_end <= dataset_end


# ---------------------------------------------------------------------------
# Non-multiple period
# ---------------------------------------------------------------------------


class TestNonMultiplePeriod:
    """Period not a multiple of step_days → formula still correct (#019)."""

    def test_non_multiple_total_days(self):
        """With 365 days (not multiple of 30), folds are correct."""
        ts = _make_timestamps("2024-01-01", days=365, freq="1h")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        folds = splitter.split(ts)
        assert len(folds) >= 1
        for fold in folds:
            assert fold.test_end <= ts[-1]


# ---------------------------------------------------------------------------
# Date-based bounds (data gap doesn't shift bounds)
# ---------------------------------------------------------------------------


class TestDateBasedBounds:
    """Bounds are date-based, not sample-count-based (#019)."""

    def test_gap_does_not_shift_bounds(self):
        """A gap in data reduces sample count but doesn't shift UTC bounds."""
        # Full timestamps
        ts_full = _make_timestamps("2024-01-01", days=730, freq="1h")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        folds_full = splitter.split(ts_full)

        # Create timestamps with a gap (remove 48h of data)
        gap_start = pd.Timestamp("2024-03-01 00:00", tz="UTC")
        gap_end = pd.Timestamp("2024-03-03 00:00", tz="UTC")
        ts_gap = ts_full[(ts_full < gap_start) | (ts_full >= gap_end)]

        folds_gap = splitter.split(ts_gap)

        # Same number of folds (bounds are the same, only sample counts differ)
        assert len(folds_gap) == len(folds_full)
        # Bounds unchanged for fold 0
        assert folds_gap[0].train_start == folds_full[0].train_start
        assert folds_gap[0].test_start == folds_full[0].test_start
        assert folds_gap[0].test_end == folds_full[0].test_end
        # But sample count is reduced
        assert folds_gap[0].n_train < folds_full[0].n_train


# ---------------------------------------------------------------------------
# min_samples filtering
# ---------------------------------------------------------------------------


class TestMinSamplesFiltering:
    """Folds with too few samples are excluded (#019)."""

    def test_min_samples_train_excludes_fold(self):
        """Fold with n_train < min_samples_train is excluded."""

        class _Cfg:
            train_days = 180
            test_days = 30
            step_days = 30
            val_frac_in_train = 0.2
            embargo_bars = 4
            min_samples_train = 999999  # impossibly high
            min_samples_test = 1

        ts = _make_timestamps("2024-01-01", days=730, freq="1h")
        splitter = WalkForwardSplitter(splits_config=_Cfg(), timeframe="1h")
        with pytest.raises(ValueError, match="excluded"):
            splitter.split(ts)

    def test_min_samples_test_excludes_fold(self):
        """Fold with n_test < min_samples_test is excluded."""

        class _Cfg:
            train_days = 180
            test_days = 30
            step_days = 30
            val_frac_in_train = 0.2
            embargo_bars = 4
            min_samples_train = 100
            min_samples_test = 999999  # impossibly high

        ts = _make_timestamps("2024-01-01", days=730, freq="1h")
        splitter = WalkForwardSplitter(splits_config=_Cfg(), timeframe="1h")
        with pytest.raises(ValueError, match="excluded"):
            splitter.split(ts)

    def test_partial_exclusion_with_warning(self, caplog):
        """Some folds excluded by min_samples, warning logged."""
        # Create data with a large gap that makes early folds have few
        # train samples, but later folds are fine.
        # Alternatively, use a very sparse dataset for early period.
        # Simpler: use min_samples_train just above the count for 1 fold.
        ts = _make_timestamps("2024-01-01", days=730, freq="1h")
        # Count approximate samples in 144 days (train_only) * 24 = 3456
        # Set min_samples_train to 3457 → fold 0 excluded, but others may not
        # Actually all folds have similar train count. Use a gap approach.

        # Create data where first fold region has a gap
        gap_start = pd.Timestamp("2024-01-02 00:00", tz="UTC")
        gap_end = pd.Timestamp("2024-06-01 00:00", tz="UTC")
        ts_sparse = ts[(ts < gap_start) | (ts >= gap_end)]

        class _Cfg:
            train_days = 180
            test_days = 30
            step_days = 30
            val_frac_in_train = 0.2
            embargo_bars = 4
            min_samples_train = 100
            min_samples_test = 1

        splitter = WalkForwardSplitter(splits_config=_Cfg(), timeframe="1h")
        with caplog.at_level(logging.WARNING):
            folds = splitter.split(ts_sparse)
        # At least one fold should remain valid (later ones with data)
        assert len(folds) >= 1
        # Verify that exclusion warnings were actually emitted
        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_msgs) > 0, "Expected at least one exclusion warning"
        assert any("excluded" in str(m) for m in warning_msgs)


# ---------------------------------------------------------------------------
# Zero valid folds → ValueError
# ---------------------------------------------------------------------------


class TestZeroValidFolds:
    """No valid folds → ValueError (#019)."""

    def test_dataset_too_short(self):
        """Dataset shorter than train_days + test_days → ValueError."""
        ts = _make_timestamps("2024-01-01", days=100, freq="1h")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        with pytest.raises(
            ValueError,
            match="No valid folds: dataset too short",
        ):
            splitter.split(ts)

    def test_all_folds_filtered_out(self):
        """All folds excluded by min_samples → error mentions filtering."""

        class _Cfg:
            train_days = 180
            test_days = 30
            step_days = 30
            val_frac_in_train = 0.2
            embargo_bars = 4
            min_samples_train = 999999
            min_samples_test = 1

        ts = _make_timestamps("2024-01-01", days=730, freq="1h")
        splitter = WalkForwardSplitter(splits_config=_Cfg(), timeframe="1h")
        with pytest.raises(ValueError, match="excluded"):
            splitter.split(ts)

    def test_empty_timestamps(self):
        """Empty DatetimeIndex → ValueError."""
        ts = pd.DatetimeIndex([], dtype="datetime64[ns, UTC]")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        with pytest.raises(ValueError, match="timestamps must not be empty"):
            splitter.split(ts)

    def test_val_days_zero_raises(self):
        """train_days too small for val_frac → ValueError."""

        class _Cfg:
            train_days = 1
            test_days = 1
            step_days = 1
            val_frac_in_train = 0.2  # floor(1 * 0.2) = 0
            embargo_bars = 0
            min_samples_train = 1
            min_samples_test = 1

        ts = _make_timestamps("2024-01-01", days=10, freq="1h")
        splitter = WalkForwardSplitter(splits_config=_Cfg(), timeframe="1h")
        with pytest.raises(ValueError, match="validation window is empty"):
            splitter.split(ts)


# ---------------------------------------------------------------------------
# Logging of fold counters
# ---------------------------------------------------------------------------


class TestFoldCounterLogging:
    """Verify fold counters are logged (#019)."""

    def test_counters_logged(self, caplog):
        ts = _make_timestamps("2024-01-01", days=730, freq="1h")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        with caplog.at_level(logging.INFO):
            splitter.split(ts)
        log_text = caplog.text
        assert "n_folds_theoretical" in log_text
        assert "n_folds_valid" in log_text
        assert "n_folds_excluded" in log_text

    def test_counters_sum(self, caplog):
        """n_folds_theoretical == n_folds_valid + n_folds_excluded."""
        ts = _make_timestamps("2024-01-01", days=730, freq="1h")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        with caplog.at_level(logging.INFO):
            result = splitter.split(ts)
        # Extract counters from splitter (returned or accessible)
        # The splitter should expose counters. Let's check via the log.
        # Parse from log: "n_folds_theoretical=X, n_folds_valid=Y, n_folds_excluded=Z"
        import re

        match = re.search(
            r"n_folds_theoretical=(\d+).*n_folds_valid=(\d+).*n_folds_excluded=(\d+)",
            caplog.text,
        )
        assert match is not None, f"Counter log not found in: {caplog.text}"
        n_theo = int(match.group(1))
        n_valid = int(match.group(2))
        n_excluded = int(match.group(3))
        assert n_theo == n_valid + n_excluded
        assert n_valid == len(result)


# ---------------------------------------------------------------------------
# Config-driven
# ---------------------------------------------------------------------------


class TestConfigDriven:
    """All parameters read from config (#019)."""

    def test_different_step_days(self):
        """Changing step_days changes number of folds."""

        class _Cfg60:
            train_days = 180
            test_days = 60
            step_days = 60
            val_frac_in_train = 0.2
            embargo_bars = 4
            min_samples_train = 100
            min_samples_test = 1

        ts = _make_timestamps("2024-01-01", days=730, freq="1h")
        splitter_30 = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        splitter_60 = WalkForwardSplitter(
            splits_config=_Cfg60(),
            timeframe="1h",
        )
        folds_30 = splitter_30.split(ts)
        folds_60 = splitter_60.split(ts)
        assert len(folds_30) > len(folds_60)

    def test_different_timeframe(self):
        """Changing timeframe to 4h adjusts embargo duration."""

        class _Cfg:
            train_days = 180
            test_days = 30
            step_days = 30
            val_frac_in_train = 0.2
            embargo_bars = 4
            min_samples_train = 1
            min_samples_test = 1

        ts_4h = _make_timestamps("2024-01-01", days=730, freq="4h")
        splitter = WalkForwardSplitter(
            splits_config=_Cfg(),
            timeframe="4h",
        )
        folds = splitter.split(ts_4h)
        # test_start should be offset by 4*4h = 16h from train end
        expected_test_start = (
            pd.Timestamp("2024-01-01", tz="UTC")
            + timedelta(days=180)
            + timedelta(hours=4 * 4)
        )
        assert folds[0].test_start == expected_test_start


# ---------------------------------------------------------------------------
# FoldInfo structure
# ---------------------------------------------------------------------------


class TestFoldInfoStructure:
    """FoldInfo contains all required fields (#019)."""

    @pytest.fixture
    def fold0(self):
        ts = _make_timestamps("2024-01-01", days=730, freq="1h")
        splitter = WalkForwardSplitter(
            splits_config=_make_mvp_splits_config(),
            timeframe="1h",
        )
        return splitter.split(ts)[0]

    def test_has_train_indices(self, fold0):
        assert hasattr(fold0, "train_indices")
        assert len(fold0.train_indices) > 0

    def test_has_val_indices(self, fold0):
        assert hasattr(fold0, "val_indices")
        assert len(fold0.val_indices) > 0

    def test_has_test_indices(self, fold0):
        assert hasattr(fold0, "test_indices")
        assert len(fold0.test_indices) > 0

    def test_has_utc_bounds(self, fold0):
        assert hasattr(fold0, "train_start")
        assert hasattr(fold0, "train_only_end")
        assert hasattr(fold0, "val_start")
        assert hasattr(fold0, "train_val_end")
        assert hasattr(fold0, "test_start")
        assert hasattr(fold0, "test_end")

    def test_has_counters(self, fold0):
        assert fold0.n_train == len(fold0.train_indices)
        assert fold0.n_val == len(fold0.val_indices)
        assert fold0.n_test == len(fold0.test_indices)
