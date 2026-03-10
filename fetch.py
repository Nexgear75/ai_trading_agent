#!/usr/bin/env python3
"""fetch.py — Standalone OHLCV data ingestion script.

Downloads candle data from Binance via ccxt and stores it as Parquet.
Self-contained: no imports from the ``ai_trading`` package.

Usage:
    python fetch.py --config configs/default.yaml
    python fetch.py --help
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ccxt
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG (minimal subset needed for ingestion)
# ═══════════════════════════════════════════════════════════════════════════

TIMEFRAME_DELTA: dict[str, pd.Timedelta] = {
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

_TIMEFRAME_MS: dict[str, int] = {
    k: int(v.total_seconds() * 1000) for k, v in TIMEFRAME_DELTA.items()
}


class _StrictBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IngestionConfig(_StrictBase):
    page_limit: int = Field(ge=1)
    max_retries: int = Field(ge=1)
    base_backoff_s: float = Field(gt=0)


class DatasetConfig(_StrictBase):
    exchange: str
    symbols: list[str]
    timeframe: str
    start: str
    end: str
    timezone: str
    raw_dir: str
    ingestion: IngestionConfig


def _load_dataset_config(yaml_path: str) -> DatasetConfig:
    """Load only the ``dataset`` section from a YAML config file."""
    path = Path(yaml_path)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {yaml_path}")
    with open(path, encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected a YAML mapping at top level, got {type(raw).__name__}")
    if "dataset" not in raw:
        raise KeyError("Config file is missing the 'dataset' section.")
    return DatasetConfig(**raw["dataset"])


# ═══════════════════════════════════════════════════════════════════════════
# INGESTION
# ═══════════════════════════════════════════════════════════════════════════

_OHLCV_RAW_COLUMNS = ("timestamp_ms", "open", "high", "low", "close", "volume")
_PRICE_VOLUME_COLUMNS = ("open", "high", "low", "close", "volume")
_OHLCV_CANONICAL_COLUMNS = ("timestamp_utc", "open", "high", "low", "close", "volume", "symbol")
_HASH_CHUNK_BYTES = 65_536

_SUPPORTED_EXCHANGES: dict[str, type] = {
    "binance": ccxt.binance,
}


@dataclass(frozen=True)
class IngestionResult:
    path: Path
    sha256: str
    row_count: int


def _create_exchange(exchange_name: str) -> ccxt.Exchange:
    exchange_cls = _SUPPORTED_EXCHANGES.get(exchange_name)
    if exchange_cls is None:
        raise ValueError(
            f"Exchange '{exchange_name}' is not supported. "
            f"Supported: {sorted(_SUPPORTED_EXCHANGES)}"
        )
    return exchange_cls()


def _resolve_symbol(exchange: ccxt.Exchange, symbol_config: str) -> str:
    exchange.load_markets()
    if symbol_config in exchange.markets:
        return symbol_config
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
                attempt + 1, max_retries, exc, wait,
            )
            time.sleep(wait)
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
            max_retries=max_retries, base_backoff_s=base_backoff_s,
        )
        if not page:
            if since < end_ms:
                logger.warning(
                    "Pagination stopped: exchange returned empty page at %d ms "
                    "but end_ms=%d not reached. Data may be truncated.",
                    since, end_ms,
                )
            break
        for row in page:
            if row[0] >= end_ms:
                break
            if row[0] >= start_ms:
                all_rows.append(row)
        last_ts = page[-1][0]
        next_since = last_ts + tf_ms
        if next_since <= since:
            break
        since = next_since
    return all_rows


def _build_dataframe(rows: list[list], symbol: str) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=list(_OHLCV_RAW_COLUMNS))
    df["timestamp_utc"] = pd.to_datetime(
        df["timestamp_ms"], unit="ms", utc=True
    ).astype("datetime64[ns, UTC]")
    df = df.drop(columns=["timestamp_ms"])
    for col in _PRICE_VOLUME_COLUMNS:
        df[col] = df[col].astype("float64")
    df["symbol"] = symbol
    df = df.sort_values("timestamp_utc").reset_index(drop=True)
    df = df[list(_OHLCV_CANONICAL_COLUMNS)]
    return df


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_HASH_CHUNK_BYTES), b""):
            h.update(chunk)
    return h.hexdigest()


def _parquet_path(ds: DatasetConfig) -> Path:
    symbol = ds.symbols[0]
    timeframe = ds.timeframe
    return Path(ds.raw_dir) / f"{symbol}_{timeframe}.parquet"


def _cache_covers_period(
    parquet: Path, start_ms: int, end_ms: int, timeframe: str,
) -> bool:
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
    return file_start <= start_ms and file_end >= end_ms - tf_ms


def fetch_ohlcv(ds: DatasetConfig) -> IngestionResult:
    """Download OHLCV data for the configured symbol/period and save to Parquet."""
    os.makedirs(ds.raw_dir, exist_ok=True)
    parquet = _parquet_path(ds)
    start_ms = int(pd.Timestamp(ds.start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(ds.end, tz="UTC").timestamp() * 1000)

    if _cache_covers_period(parquet, start_ms, end_ms, ds.timeframe):
        logger.info("Cache hit: %s already covers period, skipping download.", parquet)
        sha = _sha256_file(parquet)
        row_count = pq.ParquetFile(parquet).metadata.num_rows
        return IngestionResult(path=parquet, sha256=sha, row_count=row_count)

    exchange = _create_exchange(ds.exchange)
    symbol_ccxt = _resolve_symbol(exchange, ds.symbols[0])

    logger.info(
        "Fetching %s %s from %s to %s ...",
        symbol_ccxt, ds.timeframe, ds.start, ds.end,
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

    df = _build_dataframe(rows, ds.symbols[0])
    logger.info("Fetched %d candles. Saving to %s", len(df), parquet)

    table = pa.Table.from_pandas(df, preserve_index=False)
    ts_field_idx = table.schema.get_field_index("timestamp_utc")
    ns_type = pa.timestamp("ns", tz="UTC")
    new_field = pa.field("timestamp_utc", ns_type)
    new_schema = table.schema.set(ts_field_idx, new_field)
    table = table.cast(new_schema)
    pq.write_table(table, str(parquet))

    sha = _sha256_file(parquet)
    logger.info("SHA-256: %s", sha)
    return IngestionResult(path=parquet, sha256=sha, row_count=len(df))


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Trading Pipeline — standalone OHLCV data fetcher",
    )
    parser.add_argument(
        "--config", required=True,
        help="Path to the YAML configuration file.",
    )
    args = parser.parse_args()

    ds = _load_dataset_config(args.config)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    result = fetch_ohlcv(ds)
    print(f"Ingestion complete: {result.path} ({result.row_count} rows, sha256={result.sha256})")


if __name__ == "__main__":
    main()
