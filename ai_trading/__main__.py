"""CLI entry point: python -m ai_trading.

Exposes three subcommands:
- ``run``   — full pipeline (default)
- ``fetch`` — OHLCV ingestion only
- ``qa``    — quality-assurance checks only

Common arguments: ``--config``, ``--strategy``, ``--output-dir``, ``--set``.

Task #050 — WS-12.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ai_trading.config import PipelineConfig, load_config
from ai_trading.data.ingestion import fetch_ohlcv
from ai_trading.data.qa import QAReport, run_qa_checks
from ai_trading.pipeline.runner import run_pipeline
from ai_trading.utils.logging import setup_logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common CLI arguments to *parser*."""
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Path to the YAML configuration file (default: configs/default.yaml).",
    )
    parser.add_argument(
        "--strategy",
        default=None,
        help="Shortcut for --set strategy.name=<value>.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Shortcut for --set artifacts.output_dir=<value>.",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=None,
        dest="set",
        metavar="KEY=VALUE",
        help="Override a config key (dot-notation). Repeatable.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="ai_trading",
        description="AI Trading Pipeline — CLI entry point.",
    )

    # Common arguments on the main parser so they work without a subcommand.
    _add_common_arguments(parser)

    # Parent parser for subcommands (same arguments).
    common = argparse.ArgumentParser(add_help=False)
    _add_common_arguments(common)

    subparsers = parser.add_subparsers(dest="command")
    parser.set_defaults(command="run")

    subparsers.add_parser(
        "run",
        parents=[common],
        help="Run the full pipeline (default).",
    )
    subparsers.add_parser(
        "fetch",
        parents=[common],
        help="Fetch OHLCV data (ingestion only).",
    )
    subparsers.add_parser(
        "qa",
        parents=[common],
        help="Run quality-assurance checks on raw data.",
    )

    return parser


# ---------------------------------------------------------------------------
# Override merger
# ---------------------------------------------------------------------------


def _build_overrides(args: argparse.Namespace) -> list[str]:
    """Merge --strategy, --output-dir, and --set into a single override list."""
    overrides: list[str] = []
    if args.strategy is not None:
        overrides.append(f"strategy.name={args.strategy}")
    if args.output_dir is not None:
        overrides.append(f"artifacts.output_dir={args.output_dir}")
    if args.set is not None:
        overrides.extend(args.set)
    return overrides


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _run_qa_command(config: PipelineConfig) -> QAReport:
    """Run QA checks on the raw OHLCV data for the first configured symbol."""
    import pandas as pd

    symbol = config.dataset.symbols[0]
    timeframe = config.dataset.timeframe
    raw_dir = Path(config.dataset.raw_dir)
    parquet_path = raw_dir / f"{symbol}_{timeframe}.parquet"

    if not parquet_path.is_file():
        raise FileNotFoundError(
            f"Raw OHLCV file not found: {parquet_path}. "
            f"Run 'fetch' first."
        )

    df = pd.read_parquet(parquet_path)
    report = run_qa_checks(
        df=df,
        timeframe=timeframe,
        zero_volume_min_streak=config.qa.zero_volume_min_streak,
    )
    logger.info("QA report: passed=%s", report.passed)
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for the AI Trading pipeline."""
    # Phase 1 logging: INFO/text before config is available.
    setup_logging("INFO", "text")

    parser = build_parser()
    args = parser.parse_args()

    # Validate config file existence early (strict: no silent fallback).
    config_path = Path(args.config)
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Config file not found: {args.config}"
        )

    overrides = _build_overrides(args)
    config = load_config(
        yaml_path=args.config,
        overrides=overrides or None,
    )

    command = args.command

    if command == "run":
        run_dir = run_pipeline(config)
        logger.info("Pipeline complete. Artefacts in %s", run_dir)
    elif command == "fetch":
        result = fetch_ohlcv(config)
        logger.info("Ingestion complete: %s (%d rows)", result.path, result.row_count)
    elif command == "qa":
        _run_qa_command(config)


if __name__ == "__main__":
    main()
