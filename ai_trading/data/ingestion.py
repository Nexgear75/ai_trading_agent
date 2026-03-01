"""OHLCV data ingestion from Binance via ccxt.

Downloads candle data for a configured symbol/timeframe/period and stores
it as a Parquet file with canonical columns.  Supports pagination, retry
with exponential backoff, and local cache (idempotent mode).

Reference: spec §4.1, §17.4.
"""

import hashlib
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import ccxt
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ai_trading.config import PipelineConfig
from ai_trading.data.timeframes import TIMEFRAME_DELTA as _TIMEFRAME_DELTA

logger = logging.getLogger(__name__)

# Derive millisecond mapping from the single source of truth (timeframes.py)
_TIMEFRAME_MS: dict[str, int] = {
    k: int(v.total_seconds() * 1000) for k, v in _TIMEFRAME_DELTA.items()
}

# Canonical OHLCV column names (single source of truth within this module)
_OHLCV_RAW_COLUMNS = ("timestamp_ms", "open", "high", "low", "close", "volume")
_PRICE_VOLUME_COLUMNS = ("open", "high", "low", "close", "volume")
_OHLCV_CANONICAL_COLUMNS = ("timestamp_utc", "open", "high", "low", "close", "volume", "symbol")

# Buffer size for streaming file hashing (SHA-256)
_HASH_CHUNK_BYTES = 65_536

# Supported exchanges (MVP: binance only)
_SUPPORTED_EXCHANGES: dict[str, type] = {
    "binance": ccxt.binance,
}


@dataclass(frozen=True)
class IngestionResult:
    """Result of an OHLCV fetch operation."""

    path: Path
    sha256: str
    row_count: int


def _create_exchange(exchange_name: str) -> ccxt.Exchange:
    """Instantiate a ccxt exchange object.

    Raises
    ------
    ValueError
        If the exchange is not in the supported list.
    """
    exchange_cls = _SUPPORTED_EXCHANGES.get(exchange_name)
    if exchange_cls is None:
        raise ValueError(
            f"Exchange '{exchange_name}' is not supported. "
            f"Supported: {sorted(_SUPPORTED_EXCHANGES)}"
        )
    return exchange_cls()


def _resolve_symbol(exchange: ccxt.Exchange, symbol_config: str) -> str:
    """Resolve the configured symbol (e.g. 'BTCUSDT') to the ccxt market id.

    Tries direct lookup and slash-separated variant (BTC/USDT).

    Raises
    ------
    ValueError
        If the symbol cannot be found in the exchange markets.
    """
    exchange.load_markets()

    # Direct match (e.g. 'BTC/USDT')
    if symbol_config in exchange.markets:
        return symbol_config

    # Try inserting a slash for common patterns like BTCUSDT -> BTC/USDT
    # Try splitting at common base lengths (3, 4).
    # Limitation: does not handle crypto symbols with base > 4 chars
    # (e.g. PEPEUSDT, SHIBUSDT, DOGEUSDT). For such symbols, use the
    # slash-separated form directly (e.g. "DOGE/USDT").
    for base_len in (3, 4):
        candidate = f"{symbol_config[:base_len]}/{symbol_config[base_len:]}"
        if candidate in exchange.markets:
            return candidate

    raise ValueError(
        f"Symbol '{symbol_config}' not found on exchange. "
        f"Available markets: {len(exchange.markets)}"
    )


def _fetch_page_with_retry(
    exchange: ccxt.Exchange,
    symbol: str,
    timeframe: str,
    since: int,
    limit: int,
    max_retries: int,
    base_backoff_s: float,
) -> list[list]:
    """Fetch a single page of OHLCV data with retry + exponential backoff.

    Raises
    ------
    ConnectionError, ccxt.NetworkError, etc.
        After *max_retries* exhausted.
    """
    last_exc: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return exchange.fetch_ohlcv(
                symbol, timeframe, since=since, limit=limit
            )
        except (ConnectionError, ccxt.NetworkError, ccxt.ExchangeNotAvailable) as exc:
            last_exc = exc
            wait = base_backoff_s * (2 ** attempt)
            logger.warning(
                "Fetch attempt %d/%d failed (%s), retrying in %.1fs",
                attempt + 1,
                max_retries,
                exc,
                wait,
            )
            time.sleep(wait)

    # All retries exhausted — re-raise the last exception
    if last_exc is None:
        raise RuntimeError("max_retries must be >= 1")
    raise last_exc


def _fetch_all_pages(
    exchange: ccxt.Exchange,
    symbol: str,
    timeframe: str,
    start_ms: int,
    end_ms: int,
    page_limit: int,
    max_retries: int,
    base_backoff_s: float,
) -> list[list]:
    """Paginate through the exchange API to fetch all candles in [start, end[.

    Returns raw ccxt rows: [[timestamp, O, H, L, C, V], ...].
    """
    tf_ms = _TIMEFRAME_MS.get(timeframe)
    if tf_ms is None:
        raise ValueError(
            f"Timeframe '{timeframe}' is not recognised. "
            f"Supported: {sorted(_TIMEFRAME_MS)}"
        )

    all_rows: list[list] = []
    since = start_ms

    while since < end_ms:
        page = _fetch_page_with_retry(
            exchange, symbol, timeframe, since, page_limit,
            max_retries=max_retries,
            base_backoff_s=base_backoff_s,
        )
        if not page:
            if since < end_ms:
                logger.warning(
                    "Pagination stopped: exchange returned empty page at %d ms "
                    "but end_ms=%d not reached. Data may be truncated.",
                    since,
                    end_ms,
                )
            break

        # Filter to [start, end[
        for row in page:
            if row[0] >= end_ms:
                break
            if row[0] >= start_ms:
                all_rows.append(row)

        # Advance cursor past the last received timestamp
        last_ts = page[-1][0]
        next_since = last_ts + tf_ms
        if next_since <= since:
            # Safety: avoid infinite loop if exchange returns stale data
            break
        since = next_since

    return all_rows


def _build_dataframe(rows: list[list], symbol: str) -> pd.DataFrame:
    """Convert raw ccxt rows to a canonical DataFrame."""
    df = pd.DataFrame(
        rows,
        columns=list(_OHLCV_RAW_COLUMNS),
    )

    # Convert millisecond timestamps to datetime64[ns, UTC]
    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_ms"], unit="ms", utc=True
    ).astype("datetime64[ns, UTC]")
    df = df.drop(columns=["timestamp_ms"])

    # Ensure float64
    for col in _PRICE_VOLUME_COLUMNS:
        df[col] = df[col].astype("float64")

    df["symbol"] = symbol

    # Sort ascending by timestamp
    df = df.sort_values("timestamp_utc").reset_index(drop=True)

    # Canonical column order
    df = df[list(_OHLCV_CANONICAL_COLUMNS)]

    return df


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_HASH_CHUNK_BYTES), b""):
            h.update(chunk)
    return h.hexdigest()


def _parquet_path(config: PipelineConfig) -> Path:
    """Compute the canonical Parquet filename for standard naming."""
    symbol = config.dataset.symbols[0]
    timeframe = config.dataset.timeframe
    start = config.dataset.start
    end = config.dataset.end
    return Path(config.dataset.raw_dir) / f"{symbol}_{timeframe}_{start}_{end}.parquet"


def _cache_covers_period(
    parquet: Path, start_ms: int, end_ms: int, timeframe: str
) -> bool:
    """Check if an existing Parquet file covers [start_ms, end_ms[."""
    if not parquet.exists():
        return False

    df = pd.read_parquet(parquet, columns=["timestamp_utc"])
    if df.empty:
        return False

    file_start = int(df["timestamp_utc"].iloc[0].timestamp() * 1000)
    file_end = int(df["timestamp_utc"].iloc[-1].timestamp() * 1000)

    tf_ms = _TIMEFRAME_MS.get(timeframe)
    if tf_ms is None:
        raise ValueError(
            f"Timeframe '{timeframe}' is not recognised. "
            f"Supported: {sorted(_TIMEFRAME_MS)}"
        )

    # The file covers the period if its first candle <= start and
    # its last candle >= end - 1 timeframe interval
    return file_start <= start_ms and file_end >= end_ms - tf_ms


def fetch_ohlcv(config: PipelineConfig) -> IngestionResult:
    """Download OHLCV data for the configured symbol/period and save to Parquet.

    Parameters
    ----------
    config : PipelineConfig
        Pipeline configuration (uses ``config.dataset``).

    Returns
    -------
    IngestionResult
        Path to the Parquet file, its SHA-256 hash, and the row count.

    Raises
    ------
    ValueError
        If exchange/symbol is invalid, timeframe unknown, or no data returned.
    ConnectionError
        If all retries are exhausted.
    """
    ds = config.dataset

    # Create raw_dir if needed
    os.makedirs(ds.raw_dir, exist_ok=True)

    parquet = _parquet_path(config)

    start_ms = int(pd.Timestamp(ds.start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(ds.end, tz="UTC").timestamp() * 1000)

    # Cache check
    if _cache_covers_period(parquet, start_ms, end_ms, ds.timeframe):
        logger.info("Cache hit: %s already covers period, skipping download.", parquet)
        sha = _sha256_file(parquet)
        row_count = pq.ParquetFile(parquet).metadata.num_rows
        return IngestionResult(path=parquet, sha256=sha, row_count=row_count)

    # Create exchange
    exchange = _create_exchange(ds.exchange)

    # Resolve symbol
    symbol_ccxt = _resolve_symbol(exchange, ds.symbols[0])

    # Fetch all pages
    logger.info(
        "Fetching %s %s from %s to %s ...",
        symbol_ccxt,
        ds.timeframe,
        ds.start,
        ds.end,
    )
    rows = _fetch_all_pages(
        exchange, symbol_ccxt, ds.timeframe, start_ms, end_ms,
        page_limit=ds.ingestion.page_limit,
        max_retries=ds.ingestion.max_retries,
        base_backoff_s=ds.ingestion.base_backoff_s,
    )

    if not rows:
        raise ValueError(
            f"No data returned for {symbol_ccxt} on {ds.exchange} "
            f"between {ds.start} and {ds.end}."
        )

    # Build DataFrame
    df = _build_dataframe(rows, ds.symbols[0])

    logger.info("Fetched %d candles. Saving to %s", len(df), parquet)

    # Write Parquet (use pyarrow schema to preserve datetime64[ns, UTC])
    table = pa.Table.from_pandas(df, preserve_index=False)
    # Override timestamp column to ns precision
    ts_field_idx = table.schema.get_field_index("timestamp_utc")
    ns_type = pa.timestamp("ns", tz="UTC")
    new_field = pa.field("timestamp_utc", ns_type)
    new_schema = table.schema.set(ts_field_idx, new_field)
    table = table.cast(new_schema)
    pq.write_table(table, str(parquet))

    sha = _sha256_file(parquet)
    logger.info("SHA-256: %s", sha)

    return IngestionResult(path=parquet, sha256=sha, row_count=len(df))
