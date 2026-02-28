"""Tests for OHLCV ingestion module — task #004.

Covers all acceptance criteria:
- Canonical columns and types
- Ascending sort by timestamp_utc
- SHA-256 stability (idempotent mode)
- Pagination across full period
- Retry with exponential backoff
- Local cache (no re-download)
- Explicit error on bad symbol / exchange
- [start, end[ bounds convention
- All tests use ccxt mocks (no network access)
"""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ai_trading.config import load_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CANONICAL_COLUMNS = [
    "timestamp_utc",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "symbol",
]


def _make_ohlcv_rows(start_ms: int, count: int, step_ms: int) -> list[list]:
    """Return ccxt-style OHLCV rows: [timestamp, O, H, L, C, V]."""
    rows = []
    for i in range(count):
        ts = start_ms + i * step_ms
        rows.append([ts, 100.0 + i, 105.0 + i, 95.0 + i, 102.0 + i, 10.0 + i])
    return rows


def _ts_ms(date_str: str) -> int:
    """Convert 'YYYY-MM-DD' to epoch milliseconds (UTC)."""
    return int(pd.Timestamp(date_str, tz="UTC").timestamp() * 1000)


HOUR_MS = 3_600_000


def _write_minimal_yaml(
    tmp_path: Path, default_config_path: Path, overrides: dict | None = None
) -> Path:
    """Write a minimal valid YAML config pointing raw_dir to tmp_path."""
    import yaml

    # Load default config, dump, override dataset section
    with open(default_config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data["dataset"]["raw_dir"] = str(tmp_path / "raw")
    data["dataset"]["symbols"] = ["BTCUSDT"]
    data["dataset"]["timeframe"] = "1h"
    data["dataset"]["start"] = "2024-01-01"
    data["dataset"]["end"] = "2024-01-02"
    data["dataset"]["exchange"] = "binance"

    if overrides:
        for dotpath, val in overrides.items():
            keys = dotpath.split(".")
            d = data
            for k in keys[:-1]:
                d = d[k]
            d[keys[-1]] = val

    yaml_path = tmp_path / "config.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
    return yaml_path


@pytest.fixture
def cfg(tmp_path, default_config_path):
    """Return a PipelineConfig with raw_dir pointing to tmp_path/raw."""
    yaml_path = _write_minimal_yaml(tmp_path, default_config_path)
    return load_config(yaml_path)


@pytest.fixture
def cfg_factory(tmp_path, default_config_path):
    """Factory returning PipelineConfig with arbitrary overrides."""

    def _make(**overrides):
        yaml_path = _write_minimal_yaml(tmp_path, default_config_path, overrides)
        return load_config(yaml_path)

    return _make


def _mock_exchange(ohlcv_rows: list[list], *, symbol: str = "BTC/USDT"):
    """Return a mock ccxt exchange whose fetch_ohlcv returns paginated data."""
    exchange = MagicMock()
    exchange.load_markets.return_value = {symbol: {"id": symbol}}
    exchange.markets = {symbol: {"id": symbol}}

    # Simulate pagination: return up to 1000 rows per call based on `since`
    def _fetch(sym, tf, since=None, limit=None):
        if sym != symbol:
            raise Exception(f"BadSymbol {sym}")
        start_ms = since if since else 0
        result = [r for r in ohlcv_rows if r[0] >= start_ms]
        if limit:
            result = result[:limit]
        return result

    exchange.fetch_ohlcv = MagicMock(side_effect=_fetch)
    return exchange


# ===========================================================================
# Canonical columns & types
# ===========================================================================


class TestCanonicalOutput:
    """#004 — Parquet output has canonical columns and correct types."""

    def test_canonical_columns_present(self, cfg, tmp_path):
        """#004 — All 7 canonical columns are in the output DataFrame."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        df = pd.read_parquet(result.path)
        for col in CANONICAL_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"

    def test_timestamp_utc_dtype(self, cfg, tmp_path):
        """#004 — timestamp_utc is datetime64[ns, UTC]."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        df = pd.read_parquet(result.path)
        assert str(df["timestamp_utc"].dtype) == "datetime64[ns, UTC]"

    def test_price_volume_dtypes_float64(self, cfg, tmp_path):
        """#004 — open, high, low, close, volume are float64."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        df = pd.read_parquet(result.path)
        for col in ["open", "high", "low", "close", "volume"]:
            assert df[col].dtype.name == "float64", f"{col} is not float64"

    def test_symbol_column_value(self, cfg, tmp_path):
        """#004 — symbol column contains the configured symbol."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        df = pd.read_parquet(result.path)
        assert (df["symbol"] == "BTCUSDT").all()


# ===========================================================================
# Sort order
# ===========================================================================


class TestSortOrder:
    """#004 — Data is sorted ascending by timestamp_utc."""

    def test_ascending_sort(self, cfg, tmp_path):
        """#004 — timestamp_utc strictly increasing."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        df = pd.read_parquet(result.path)
        diffs = df["timestamp_utc"].diff().dropna()
        assert (diffs > pd.Timedelta(0)).all()


# ===========================================================================
# SHA-256 stability (idempotent)
# ===========================================================================


class TestSHA256Stability:
    """#004 — SHA-256 is stable across re-runs (idempotent mode)."""

    def test_sha256_returned(self, cfg, tmp_path):
        """#004 — fetch_ohlcv returns a sha256 hex string."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        assert isinstance(result.sha256, str)
        assert len(result.sha256) == 64  # hex digest length

    def test_sha256_matches_file(self, cfg, tmp_path):
        """#004 — Returned SHA-256 matches actual file hash."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        actual_hash = hashlib.sha256(result.path.read_bytes()).hexdigest()
        assert result.sha256 == actual_hash

    def test_sha256_stable_on_rerun(self, cfg, tmp_path):
        """#004 — Same SHA-256 on second run (cache hit)."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            r1 = fetch_ohlcv(cfg)
            r2 = fetch_ohlcv(cfg)

        assert r1.sha256 == r2.sha256


# ===========================================================================
# Pagination
# ===========================================================================


class TestPagination:
    """#004 — Pagination covers entire requested period."""

    def test_pagination_multiple_pages(self, cfg, tmp_path):
        """#004 — If period requires >1000 candles, pagination fetches all."""
        start_ms = _ts_ms("2024-01-01")
        # 24 hours * 1h = 24 candles — small enough for test,
        # but we'll mock the exchange to return batches of 10 to test pagination.
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        # Override fetch_ohlcv to return max 10 per call
        original_side_effect = mock_ex.fetch_ohlcv.side_effect

        def _limited_fetch(sym, tf, since=None, limit=None):
            result = original_side_effect(sym, tf, since=since, limit=10)
            return result

        mock_ex.fetch_ohlcv.side_effect = _limited_fetch

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        df = pd.read_parquet(result.path)
        assert len(df) == 24
        # Multiple calls were made
        assert mock_ex.fetch_ohlcv.call_count > 1


# ===========================================================================
# Retry with backoff
# ===========================================================================


class TestRetryBackoff:
    """#004 — Retry with exponential backoff on transient errors."""

    def test_retry_on_network_error(self, cfg, tmp_path):
        """#004 — Transient error triggers retry, then succeeds."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)

        call_count = {"n": 0}

        def _flaky_fetch(sym, tf, since=None, limit=None):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                raise ConnectionError("Network error")
            start_filt = since if since else 0
            result = [r for r in rows if r[0] >= start_filt]
            if limit:
                result = result[:limit]
            return result

        mock_ex = MagicMock()
        mock_ex.load_markets.return_value = {"BTC/USDT": {"id": "BTC/USDT"}}
        mock_ex.markets = {"BTC/USDT": {"id": "BTC/USDT"}}
        mock_ex.fetch_ohlcv = MagicMock(side_effect=_flaky_fetch)

        with (
            patch(
                "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
            ),
            patch("time.sleep"),
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        df = pd.read_parquet(result.path)
        assert len(df) == 24

    def test_retry_exhausted_raises(self, cfg, tmp_path):
        """#004 — After max retries, raises explicitly."""
        mock_ex = MagicMock()
        mock_ex.load_markets.return_value = {"BTC/USDT": {"id": "BTC/USDT"}}
        mock_ex.markets = {"BTC/USDT": {"id": "BTC/USDT"}}
        mock_ex.fetch_ohlcv = MagicMock(
            side_effect=ConnectionError("Persistent error")
        )

        with (
            patch(
                "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
            ),
            patch("time.sleep"),
            pytest.raises(ConnectionError, match="Persistent error"),
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            fetch_ohlcv(cfg)


# ===========================================================================
# Local cache — no re-download
# ===========================================================================


class TestLocalCache:
    """#004 — No re-download if file already covers the period."""

    def test_cache_hit_no_fetch(self, cfg, tmp_path):
        """#004 — Second call doesn't call fetch_ohlcv on exchange."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            fetch_ohlcv(cfg)  # first call: download
            calls_after_first = mock_ex.fetch_ohlcv.call_count

            fetch_ohlcv(cfg)  # second call: cache hit
            calls_after_second = mock_ex.fetch_ohlcv.call_count

        # No additional fetch_ohlcv calls on cache hit
        assert calls_after_second == calls_after_first

    def test_single_row_cache_hit_no_fetch(self, cfg_factory, tmp_path):
        """#004 — Single-candle files can still be valid cache hits."""
        config = cfg_factory(
            **{
                "dataset.timeframe": "1d",
                "dataset.start": "2024-01-01",
                "dataset.end": "2024-01-02",
            }
        )

        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 1, 86_400_000)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            fetch_ohlcv(config)
            calls_after_first = mock_ex.fetch_ohlcv.call_count

            fetch_ohlcv(config)
            calls_after_second = mock_ex.fetch_ohlcv.call_count

        assert calls_after_second == calls_after_first


# ===========================================================================
# Error handling — bad symbol / exchange
# ===========================================================================


class TestErrorHandling:
    """#004 — Explicit errors on invalid symbol or exchange."""

    def test_invalid_exchange_raises(self, tmp_path, default_config_path):
        """#004 — Unknown exchange raises explicit error."""
        yaml_path = _write_minimal_yaml(
            tmp_path,
            default_config_path,
            {"dataset.exchange": "nonexistent_exchange"},
        )
        config = load_config(yaml_path)

        with pytest.raises(ValueError, match="[Ee]xchange"):
            from ai_trading.data.ingestion import fetch_ohlcv

            fetch_ohlcv(config)

    def test_invalid_symbol_raises(self, cfg, tmp_path):
        """#004 — Unknown symbol raises explicit error."""
        mock_ex = MagicMock()
        mock_ex.load_markets.return_value = {"BTC/USDT": {"id": "BTC/USDT"}}
        mock_ex.markets = {"BTC/USDT": {"id": "BTC/USDT"}}

        with (
            patch(
                "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
            ),
            pytest.raises(ValueError, match="[Ss]ymbol"),
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            # Config has BTCUSDT but market only has BTC/USDT with a
            # non-matching lookup — mock exchange doesn't list BTCUSDT
            # We need to set up the mock so symbol lookup fails
            mock_ex.markets = {}
            mock_ex.load_markets.return_value = {}
            fetch_ohlcv(cfg)


# ===========================================================================
# Bounds convention [start, end[
# ===========================================================================


class TestBoundsConvention:
    """#004 — [start, end[ convention: start inclusive, end exclusive."""

    def test_start_inclusive(self, cfg, tmp_path):
        """#004 — First candle timestamp >= start."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        df = pd.read_parquet(result.path)
        start_ts = pd.Timestamp("2024-01-01", tz="UTC")
        assert df["timestamp_utc"].iloc[0] >= start_ts

    def test_end_exclusive(self, cfg, tmp_path):
        """#004 — Last candle timestamp < end."""
        start_ms = _ts_ms("2024-01-01")
        # Generate 25 hours so one candle is at exactly 2024-01-02T00:00
        rows = _make_ohlcv_rows(start_ms, 25, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        df = pd.read_parquet(result.path)
        end_ts = pd.Timestamp("2024-01-02", tz="UTC")
        assert df["timestamp_utc"].iloc[-1] < end_ts


# ===========================================================================
# Output path convention
# ===========================================================================


class TestOutputPath:
    """#004 — Output Parquet file is in raw_dir with expected naming."""

    def test_parquet_in_raw_dir(self, cfg, tmp_path):
        """#004 — Output file is inside config.dataset.raw_dir."""
        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            result = fetch_ohlcv(cfg)

        raw_dir = Path(cfg.dataset.raw_dir)
        assert result.path.parent == raw_dir
        assert result.path.suffix == ".parquet"

    def test_raw_dir_created_automatically(self, cfg, tmp_path):
        """#004 — raw_dir is created if it doesn't exist."""
        raw_dir = Path(cfg.dataset.raw_dir)
        assert not raw_dir.exists()  # not yet

        start_ms = _ts_ms("2024-01-01")
        rows = _make_ohlcv_rows(start_ms, 24, HOUR_MS)
        mock_ex = _mock_exchange(rows)

        with patch(
            "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            fetch_ohlcv(cfg)

        assert raw_dir.exists()


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:
    """#004 — Edge case scenarios."""

    def test_empty_period_raises(self, tmp_path, default_config_path):
        """#004 — If exchange returns no data, raise explicitly."""
        yaml_path = _write_minimal_yaml(tmp_path, default_config_path)
        config = load_config(yaml_path)

        mock_ex = MagicMock()
        mock_ex.load_markets.return_value = {"BTC/USDT": {"id": "BTC/USDT"}}
        mock_ex.markets = {"BTC/USDT": {"id": "BTC/USDT"}}
        mock_ex.fetch_ohlcv = MagicMock(return_value=[])

        with (
            patch(
                "ai_trading.data.ingestion._create_exchange", return_value=mock_ex
            ),
            pytest.raises(ValueError, match="[Nn]o.*data|[Ee]mpty"),
        ):
            from ai_trading.data.ingestion import fetch_ohlcv

            fetch_ohlcv(config)
