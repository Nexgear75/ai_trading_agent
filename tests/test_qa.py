"""Tests for OHLCV quality assurance checks.

Task #005 — WS-2: Contrôles qualité (QA) obligatoires.
Covers all acceptance criteria: clean data pass, duplicate timestamps,
missing candles, negative prices, OHLC inconsistency, prolonged zero
volume, irregular delta, and structured QAReport.
"""

import pandas as pd
import pytest
from ai_trading.data.qa import QAReport, run_qa_checks

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(
    n: int = 10,
    timeframe: str = "1h",
    start: str = "2024-01-01",
) -> pd.DataFrame:
    """Create a clean synthetic OHLCV DataFrame with uniform timestamps."""
    freq_map = {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1D",
    }
    freq = freq_map[timeframe]
    timestamps = pd.date_range(start=start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": [100.0 + i for i in range(n)],
        "high": [105.0 + i for i in range(n)],
        "low": [95.0 + i for i in range(n)],
        "close": [102.0 + i for i in range(n)],
        "volume": [1000.0 + i * 10 for i in range(n)],
    })


# ===========================================================================
# Acceptance criterion: Données propres → QA passe (statut global = pass)
# ===========================================================================

class TestCleanDataPass:
    """#005 — Clean data must pass all QA checks."""

    def test_clean_data_returns_pass(self):
        """Clean OHLCV data should produce a QAReport with passed=True."""
        df = _make_ohlcv(n=20, timeframe="1h")
        report = run_qa_checks(df, timeframe="1h")
        assert isinstance(report, QAReport)
        assert report.passed is True

    def test_clean_data_no_anomalies(self):
        """Clean data should report no anomalies in any check."""
        df = _make_ohlcv(n=20, timeframe="1h")
        report = run_qa_checks(df, timeframe="1h")
        assert report.duplicate_count == 0
        assert len(report.missing_timestamps) == 0
        assert report.negative_price_count == 0
        assert report.ohlc_inconsistency_count == 0
        assert report.zero_volume_streak_count == 0
        assert report.irregular_delta_count == 0

    def test_clean_data_different_timeframes(self):
        """Clean data with different timeframes should all pass."""
        for tf in ("1m", "5m", "15m", "1h", "4h", "1d"):
            df = _make_ohlcv(n=10, timeframe=tf)
            report = run_qa_checks(df, timeframe=tf)
            assert report.passed is True, f"Failed for timeframe {tf}"


# ===========================================================================
# Acceptance criterion: Doublons de timestamp détectés et signalés
# ===========================================================================

class TestDuplicateTimestamps:
    """#005 — Duplicate timestamps must be detected and reported."""

    def test_single_duplicate_detected(self):
        """A single duplicate timestamp is detected."""
        df = _make_ohlcv(n=10, timeframe="1h")
        # Duplicate the second row's timestamp
        df.loc[2, "timestamp"] = df.loc[1, "timestamp"]
        report = run_qa_checks(df, timeframe="1h")
        assert report.duplicate_count >= 1
        assert report.passed is False

    def test_multiple_duplicates_count(self):
        """Multiple duplicates are counted correctly."""
        df = _make_ohlcv(n=10, timeframe="1h")
        df.loc[2, "timestamp"] = df.loc[1, "timestamp"]
        df.loc[4, "timestamp"] = df.loc[3, "timestamp"]
        report = run_qa_checks(df, timeframe="1h")
        assert report.duplicate_count >= 2


# ===========================================================================
# Acceptance criterion: Trous (missing candles) détectés avec la liste des
#                       timestamps manquants
# ===========================================================================

class TestMissingCandles:
    """#005 — Missing candles must be detected with their timestamps."""

    def test_single_gap_detected(self):
        """Removing one candle should detect the missing timestamp."""
        df = _make_ohlcv(n=10, timeframe="1h")
        # Remove row at index 5 to create a gap
        df = df.drop(index=5).reset_index(drop=True)
        report = run_qa_checks(df, timeframe="1h")
        assert len(report.missing_timestamps) == 1
        assert report.passed is False

    def test_multiple_gaps_detected(self):
        """Removing multiple candles detects all missing timestamps."""
        df = _make_ohlcv(n=20, timeframe="1h")
        # Remove rows 5 and 10 to create two gaps
        df = df.drop(index=[5, 10]).reset_index(drop=True)
        report = run_qa_checks(df, timeframe="1h")
        assert len(report.missing_timestamps) == 2

    def test_consecutive_gaps(self):
        """Removing consecutive candles detects all missing timestamps."""
        df = _make_ohlcv(n=20, timeframe="1h")
        # Remove 3 consecutive rows (5, 6, 7)
        df = df.drop(index=[5, 6, 7]).reset_index(drop=True)
        report = run_qa_checks(df, timeframe="1h")
        assert len(report.missing_timestamps) == 3

    def test_missing_timestamps_are_correct(self):
        """The returned missing timestamps match expected values."""
        df = _make_ohlcv(n=10, timeframe="1h")
        expected_missing = df.loc[5, "timestamp"]
        df = df.drop(index=5).reset_index(drop=True)
        report = run_qa_checks(df, timeframe="1h")
        assert expected_missing in report.missing_timestamps


# ===========================================================================
# Acceptance criterion: Prix négatif → erreur explicite
# ===========================================================================

class TestNegativePrices:
    """#005 — Negative prices must raise an explicit error."""

    def test_negative_open_raises(self):
        """Negative open price raises ValueError."""
        df = _make_ohlcv(n=10, timeframe="1h")
        df.loc[3, "open"] = -1.0
        with pytest.raises(ValueError, match="[Nn]egative.*price"):
            run_qa_checks(df, timeframe="1h")

    def test_negative_high_raises(self):
        """Negative high price raises ValueError."""
        df = _make_ohlcv(n=10, timeframe="1h")
        df.loc[3, "high"] = -5.0
        with pytest.raises(ValueError, match="[Nn]egative.*price"):
            run_qa_checks(df, timeframe="1h")

    def test_negative_low_raises(self):
        """Negative low price raises ValueError."""
        df = _make_ohlcv(n=10, timeframe="1h")
        df.loc[3, "low"] = -10.0
        with pytest.raises(ValueError, match="[Nn]egative.*price"):
            run_qa_checks(df, timeframe="1h")

    def test_negative_close_raises(self):
        """Negative close price raises ValueError."""
        df = _make_ohlcv(n=10, timeframe="1h")
        df.loc[3, "close"] = -0.01
        with pytest.raises(ValueError, match="[Nn]egative.*price"):
            run_qa_checks(df, timeframe="1h")

    def test_negative_price_count_in_error(self):
        """Error message for negative prices includes count info."""
        df = _make_ohlcv(n=10, timeframe="1h")
        df.loc[2, "open"] = -1.0
        df.loc[5, "close"] = -2.0
        with pytest.raises(ValueError, match="2 row"):
            run_qa_checks(df, timeframe="1h")


# ===========================================================================
# Acceptance criterion: OHLC incohérent (high < open ou low > close) →
#                       détecté et signalé
# ===========================================================================

class TestOHLCInconsistency:
    """#005 — OHLC inconsistencies must be detected and reported."""

    def test_high_less_than_open(self):
        """high < open is detected as OHLC inconsistency."""
        df = _make_ohlcv(n=10, timeframe="1h")
        # open=103, high should be >= 103, set it lower
        df.loc[3, "high"] = 90.0
        report = run_qa_checks(df, timeframe="1h")
        assert report.ohlc_inconsistency_count >= 1
        assert report.passed is False

    def test_high_less_than_close(self):
        """high < close is detected as OHLC inconsistency."""
        df = _make_ohlcv(n=10, timeframe="1h")
        # close=105, set high=100 which is < close
        df.loc[3, "high"] = 100.0
        df.loc[3, "close"] = 110.0
        report = run_qa_checks(df, timeframe="1h")
        assert report.ohlc_inconsistency_count >= 1
        assert report.passed is False

    def test_low_greater_than_open(self):
        """low > open is detected as OHLC inconsistency."""
        df = _make_ohlcv(n=10, timeframe="1h")
        # open=103, set low=110
        df.loc[3, "low"] = 110.0
        report = run_qa_checks(df, timeframe="1h")
        assert report.ohlc_inconsistency_count >= 1
        assert report.passed is False

    def test_low_greater_than_close(self):
        """low > close is detected as OHLC inconsistency."""
        df = _make_ohlcv(n=10, timeframe="1h")
        # close=105, set low=110
        df.loc[3, "close"] = 100.0
        df.loc[3, "low"] = 110.0
        report = run_qa_checks(df, timeframe="1h")
        assert report.ohlc_inconsistency_count >= 1

    def test_multiple_inconsistencies_counted(self):
        """Multiple OHLC inconsistencies are all counted."""
        df = _make_ohlcv(n=10, timeframe="1h")
        # Two rows with high < open
        df.loc[2, "high"] = 90.0
        df.loc[5, "high"] = 90.0
        report = run_qa_checks(df, timeframe="1h")
        assert report.ohlc_inconsistency_count >= 2


# ===========================================================================
# Acceptance criterion: Volume nul prolongé → détecté et reporté
# ===========================================================================

class TestZeroVolume:
    """#005 — Prolonged zero volume must be detected and reported."""

    def test_single_zero_volume_not_prolonged(self):
        """A single zero-volume bar should not be flagged as prolonged."""
        df = _make_ohlcv(n=10, timeframe="1h")
        df.loc[5, "volume"] = 0.0
        report = run_qa_checks(df, timeframe="1h")
        assert report.zero_volume_streak_count == 0

    def test_prolonged_zero_volume_detected(self):
        """Multiple consecutive zero-volume bars are detected."""
        df = _make_ohlcv(n=20, timeframe="1h")
        # Set 3 consecutive bars to zero volume
        for i in range(5, 8):
            df.loc[i, "volume"] = 0.0
        report = run_qa_checks(df, timeframe="1h")
        assert report.zero_volume_streak_count >= 1
        assert report.passed is False

    def test_two_zero_volume_consecutive_detected(self):
        """Two consecutive zero-volume bars (minimum for prolonged)."""
        df = _make_ohlcv(n=10, timeframe="1h")
        df.loc[3, "volume"] = 0.0
        df.loc[4, "volume"] = 0.0
        report = run_qa_checks(df, timeframe="1h")
        assert report.zero_volume_streak_count >= 1

    def test_multiple_streaks_counted(self):
        """Multiple separate streaks of zero volume."""
        df = _make_ohlcv(n=20, timeframe="1h")
        # First streak: bars 3-4
        df.loc[3, "volume"] = 0.0
        df.loc[4, "volume"] = 0.0
        # Second streak: bars 10-11
        df.loc[10, "volume"] = 0.0
        df.loc[11, "volume"] = 0.0
        report = run_qa_checks(df, timeframe="1h")
        assert report.zero_volume_streak_count >= 2


# ===========================================================================
# Acceptance criterion: Pas Δ irrégulier (hors trous attendus) → détecté
# ===========================================================================

class TestIrregularDelta:
    """#005 — Irregular time delta must be detected."""

    def test_irregular_delta_detected(self):
        """A timestamp shifted by half Δ is detected as irregular."""
        df = _make_ohlcv(n=10, timeframe="1h")
        # Shift one timestamp by 30 minutes (half of 1h)
        df.loc[5, "timestamp"] = df.loc[5, "timestamp"] + pd.Timedelta(minutes=30)
        report = run_qa_checks(df, timeframe="1h")
        # Should detect irregular spacing
        assert report.irregular_delta_count >= 1
        assert report.passed is False


# ===========================================================================
# Acceptance criterion: QAReport retourné avec les détails structurés
# ===========================================================================

class TestQAReportStructure:
    """#005 — QAReport must be a structured dataclass with expected fields."""

    def test_report_is_dataclass(self):
        """QAReport should be a dataclass."""
        import dataclasses
        assert dataclasses.is_dataclass(QAReport)

    def test_report_has_required_fields(self):
        """QAReport must have all required fields."""
        df = _make_ohlcv(n=10, timeframe="1h")
        report = run_qa_checks(df, timeframe="1h")
        assert hasattr(report, "passed")
        assert hasattr(report, "duplicate_count")
        assert hasattr(report, "missing_timestamps")
        assert hasattr(report, "negative_price_count")
        assert hasattr(report, "ohlc_inconsistency_count")
        assert hasattr(report, "zero_volume_streak_count")
        assert hasattr(report, "irregular_delta_count")

    def test_report_types(self):
        """Fields have the correct types."""
        df = _make_ohlcv(n=10, timeframe="1h")
        report = run_qa_checks(df, timeframe="1h")
        assert isinstance(report.passed, bool)
        assert isinstance(report.duplicate_count, int)
        assert isinstance(report.missing_timestamps, list)
        assert isinstance(report.negative_price_count, int)
        assert isinstance(report.ohlc_inconsistency_count, int)
        assert isinstance(report.zero_volume_streak_count, int)
        assert isinstance(report.irregular_delta_count, int)


# ===========================================================================
# Edge cases and error handling
# ===========================================================================

class TestEdgeCases:
    """#005 — Edge cases for QA checks."""

    def test_empty_dataframe_raises(self):
        """An empty DataFrame raises ValueError."""
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        with pytest.raises(ValueError, match="[Ee]mpty"):
            run_qa_checks(df, timeframe="1h")

    def test_missing_columns_raises(self):
        """DataFrame missing required columns raises ValueError."""
        df = pd.DataFrame({"timestamp": [1, 2], "open": [1.0, 2.0]})
        with pytest.raises(ValueError, match="[Cc]olumn"):
            run_qa_checks(df, timeframe="1h")

    def test_unsupported_timeframe_raises(self):
        """Unsupported timeframe string raises ValueError."""
        df = _make_ohlcv(n=10, timeframe="1h")
        with pytest.raises(ValueError, match="[Tt]imeframe"):
            run_qa_checks(df, timeframe="2min")

    def test_single_row_passes(self):
        """Single-row DataFrame passes (no gaps or irregularity possible)."""
        df = _make_ohlcv(n=1, timeframe="1h")
        report = run_qa_checks(df, timeframe="1h")
        assert report.passed is True

    def test_all_zero_prices_raises(self):
        """All-zero prices (open=0) do not raise but zero is not negative."""
        df = _make_ohlcv(n=5, timeframe="1h")
        df["open"] = 0.0
        df["high"] = 0.0
        df["low"] = 0.0
        df["close"] = 0.0
        # Zero is not negative, so should not raise; but OHLC consistency
        # should still hold (0 >= max(0,0) and 0 <= min(0,0))
        report = run_qa_checks(df, timeframe="1h")
        assert report.negative_price_count == 0
