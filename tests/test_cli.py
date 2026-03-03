"""Tests for CLI entry point — python -m ai_trading.

Task #050 — WS-12.
"""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from ai_trading.__main__ import build_parser, main

# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


class TestBuildParser:
    """Tests for argparse parser construction."""

    def test_parser_returns_argparse_parser(self):
        """build_parser() returns an ArgumentParser."""
        import argparse

        parser = build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_parser_has_config_argument(self):
        """Parser accepts --config with default configs/default.yaml."""
        parser = build_parser()
        args = parser.parse_args(["run"])
        assert args.config == "configs/default.yaml"

    def test_parser_config_custom(self):
        """--config overrides the default."""
        parser = build_parser()
        args = parser.parse_args(["run", "--config", "my/config.yaml"])
        assert args.config == "my/config.yaml"

    def test_parser_strategy_argument(self):
        """--strategy sets strategy shortcut."""
        parser = build_parser()
        args = parser.parse_args(["run", "--strategy", "dummy"])
        assert args.strategy == "dummy"

    def test_parser_output_dir_argument(self):
        """--output-dir sets output directory."""
        parser = build_parser()
        args = parser.parse_args(["run", "--output-dir", "/tmp/out"])
        assert args.output_dir == "/tmp/out"

    def test_parser_set_single(self):
        """--set accepts a single key=value override."""
        parser = build_parser()
        args = parser.parse_args(["run", "--set", "strategy.name=dummy"])
        assert args.set == ["strategy.name=dummy"]

    def test_parser_set_multiple(self):
        """--set accepts multiple overrides."""
        parser = build_parser()
        args = parser.parse_args([
            "run",
            "--set", "strategy.name=dummy",
            "--set", "logging.level=DEBUG",
        ])
        assert args.set == ["strategy.name=dummy", "logging.level=DEBUG"]


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


class TestSubcommands:
    """Tests for the three subcommands: run, fetch, qa."""

    def test_subcommand_run(self):
        """'run' subcommand is recognised."""
        parser = build_parser()
        args = parser.parse_args(["run"])
        assert args.command == "run"

    def test_subcommand_fetch(self):
        """'fetch' subcommand is recognised."""
        parser = build_parser()
        args = parser.parse_args(["fetch"])
        assert args.command == "fetch"

    def test_subcommand_qa(self):
        """'qa' subcommand is recognised."""
        parser = build_parser()
        args = parser.parse_args(["qa"])
        assert args.command == "qa"

    def test_default_subcommand_is_run(self):
        """No subcommand defaults to 'run'."""
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command == "run"

    def test_default_subcommand_has_config(self):
        """No subcommand still populates --config with default value."""
        parser = build_parser()
        args = parser.parse_args([])
        assert args.config == "configs/default.yaml"

    def test_default_subcommand_accepts_config(self):
        """--config works without explicit subcommand."""
        parser = build_parser()
        args = parser.parse_args(["--config", "custom.yaml"])
        assert args.command == "run"
        assert args.config == "custom.yaml"

    def test_default_subcommand_accepts_all_common_args(self):
        """All common args (--config, --strategy, --output-dir, --set) work without subcommand."""
        parser = build_parser()
        args = parser.parse_args([
            "--config", "custom.yaml",
            "--strategy", "dummy",
            "--output-dir", "/tmp/out",
            "--set", "logging.level=DEBUG",
        ])
        assert args.command == "run"
        assert args.config == "custom.yaml"
        assert args.strategy == "dummy"
        assert args.output_dir == "/tmp/out"
        assert args.set == ["logging.level=DEBUG"]


# ---------------------------------------------------------------------------
# Overrides merging (_build_overrides)
# ---------------------------------------------------------------------------


class TestBuildOverrides:
    """Tests for merging --strategy, --output-dir, and --set into overrides."""

    def test_strategy_shortcut_produces_override(self):
        """--strategy dummy → override strategy.name=dummy."""
        from ai_trading.__main__ import _build_overrides

        parser = build_parser()
        args = parser.parse_args(["run", "--strategy", "dummy"])
        overrides = _build_overrides(args)
        assert "strategy.name=dummy" in overrides

    def test_output_dir_shortcut_produces_override(self):
        """--output-dir /tmp/out → override artifacts.output_dir=/tmp/out."""
        from ai_trading.__main__ import _build_overrides

        parser = build_parser()
        args = parser.parse_args(["run", "--output-dir", "/tmp/out"])
        overrides = _build_overrides(args)
        assert "artifacts.output_dir=/tmp/out" in overrides

    def test_set_overrides_forwarded(self):
        """--set values are forwarded as-is."""
        from ai_trading.__main__ import _build_overrides

        parser = build_parser()
        args = parser.parse_args(["run", "--set", "logging.level=DEBUG"])
        overrides = _build_overrides(args)
        assert "logging.level=DEBUG" in overrides

    def test_all_overrides_combined(self):
        """--strategy, --output-dir, --set are combined into single list."""
        from ai_trading.__main__ import _build_overrides

        parser = build_parser()
        args = parser.parse_args([
            "run",
            "--strategy", "dummy",
            "--output-dir", "/tmp/out",
            "--set", "logging.level=DEBUG",
        ])
        overrides = _build_overrides(args)
        assert len(overrides) == 3
        assert "strategy.name=dummy" in overrides
        assert "artifacts.output_dir=/tmp/out" in overrides
        assert "logging.level=DEBUG" in overrides

    def test_no_overrides_returns_empty_list(self):
        """No CLI overrides → empty list."""
        from ai_trading.__main__ import _build_overrides

        parser = build_parser()
        args = parser.parse_args(["run"])
        overrides = _build_overrides(args)
        assert overrides == []


# ---------------------------------------------------------------------------
# main() integration: run subcommand
# ---------------------------------------------------------------------------


class TestMainRun:
    """Tests for main() with the 'run' subcommand."""

    @patch("ai_trading.__main__.run_pipeline")
    @patch("ai_trading.__main__.load_config")
    @patch("ai_trading.__main__.setup_logging")
    def test_run_no_subcommand_calls_pipeline(
        self, mock_logging, mock_load, mock_run, tmp_path,
    ):
        """main() without explicit subcommand defaults to 'run' and calls run_pipeline."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.touch()
        mock_config = MagicMock()
        mock_load.return_value = mock_config
        mock_run.return_value = tmp_path / "runs" / "test_run"

        with patch("sys.argv", ["ai_trading", "--config", str(cfg_path)]):
            main()

        mock_load.assert_called_once()
        mock_run.assert_called_once_with(mock_config)

    @patch("ai_trading.__main__.run_pipeline")
    @patch("ai_trading.__main__.load_config")
    @patch("ai_trading.__main__.setup_logging")
    def test_run_calls_pipeline(self, mock_logging, mock_load, mock_run, tmp_path):
        """'run' subcommand loads config and calls run_pipeline."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.touch()
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.format = "text"
        mock_load.return_value = mock_config
        mock_run.return_value = tmp_path / "runs" / "test_run"

        with patch("sys.argv", ["ai_trading", "run", "--config", str(cfg_path)]):
            main()

        mock_load.assert_called_once()
        mock_run.assert_called_once_with(mock_config)

    @patch("ai_trading.__main__.run_pipeline")
    @patch("ai_trading.__main__.load_config")
    @patch("ai_trading.__main__.setup_logging")
    def test_run_passes_overrides(self, mock_logging, mock_load, mock_run, tmp_path):
        """--set overrides are forwarded to load_config."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.touch()
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.format = "text"
        mock_load.return_value = mock_config
        mock_run.return_value = tmp_path / "runs" / "test_run"

        with patch(
            "sys.argv",
            ["ai_trading", "run", "--config", str(cfg_path), "--set", "strategy.name=dummy"],
        ):
            main()

        call_args = mock_load.call_args
        assert "strategy.name=dummy" in call_args[1]["overrides"]


# ---------------------------------------------------------------------------
# main() integration: fetch subcommand
# ---------------------------------------------------------------------------


class TestMainFetch:
    """Tests for main() with the 'fetch' subcommand."""

    @patch("ai_trading.__main__.fetch_ohlcv")
    @patch("ai_trading.__main__.load_config")
    @patch("ai_trading.__main__.setup_logging")
    def test_fetch_calls_ingestion(self, mock_logging, mock_load, mock_fetch, tmp_path):
        """'fetch' subcommand loads config and calls fetch_ohlcv."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.touch()
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.format = "text"
        mock_load.return_value = mock_config

        with patch("sys.argv", ["ai_trading", "fetch", "--config", str(cfg_path)]):
            main()

        mock_load.assert_called_once()
        mock_fetch.assert_called_once_with(mock_config)


# ---------------------------------------------------------------------------
# main() integration: qa subcommand
# ---------------------------------------------------------------------------


class TestMainQA:
    """Tests for main() with the 'qa' subcommand."""

    @patch("ai_trading.__main__._run_qa_command")
    @patch("ai_trading.__main__.load_config")
    @patch("ai_trading.__main__.setup_logging")
    def test_qa_calls_qa_command(self, mock_logging, mock_load, mock_qa, tmp_path):
        """'qa' subcommand loads config and runs QA checks."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.touch()
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.format = "text"
        mock_load.return_value = mock_config

        with patch("sys.argv", ["ai_trading", "qa", "--config", str(cfg_path)]):
            main()

        mock_load.assert_called_once()
        mock_qa.assert_called_once_with(mock_config)


# ---------------------------------------------------------------------------
# _run_qa_command unit tests
# ---------------------------------------------------------------------------


class TestRunQACommand:
    """Unit tests for _run_qa_command internal logic."""

    def test_nominal_runs_qa_checks(self, tmp_path):
        """_run_qa_command reads parquet, calls run_qa_checks, returns QAReport."""
        import pandas as pd

        from ai_trading.__main__ import _run_qa_command

        # Create a minimal OHLCV parquet file.
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100, freq="1h"),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 10.0,
        })
        parquet_path = raw_dir / "BTCUSDT_1h.parquet"
        df.to_parquet(parquet_path)

        # Build a mock config pointing to the temp directory.
        config = MagicMock()
        config.dataset.symbols = ["BTCUSDT"]
        config.dataset.timeframe = "1h"
        config.dataset.raw_dir = str(raw_dir)
        config.qa.zero_volume_min_streak = 5

        with patch("ai_trading.__main__.run_qa_checks") as mock_qa:
            mock_report = MagicMock()
            mock_report.passed = True
            mock_qa.return_value = mock_report

            report = _run_qa_command(config)

        mock_qa.assert_called_once()
        call_kw = mock_qa.call_args[1]
        assert call_kw["timeframe"] == "1h"
        assert call_kw["zero_volume_min_streak"] == 5
        assert len(call_kw["df"]) == 100
        assert report.passed is True

    def test_missing_parquet_raises(self, tmp_path):
        """_run_qa_command raises FileNotFoundError when parquet file is absent."""
        from ai_trading.__main__ import _run_qa_command

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        config = MagicMock()
        config.dataset.symbols = ["BTCUSDT"]
        config.dataset.timeframe = "1h"
        config.dataset.raw_dir = str(raw_dir)

        with pytest.raises(FileNotFoundError, match="BTCUSDT_1h.parquet"):
            _run_qa_command(config)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for strict error handling."""

    def test_missing_config_file_raises(self, tmp_path):
        """main() raises FileNotFoundError when config file does not exist."""
        nonexistent = str(tmp_path / "nonexistent.yaml")
        with (
            patch("sys.argv", ["ai_trading", "run", "--config", nonexistent]),
            pytest.raises(FileNotFoundError, match="nonexistent.yaml"),
        ):
            main()

    @patch("ai_trading.__main__.load_config")
    @patch("ai_trading.__main__.setup_logging")
    def test_invalid_set_key_raises(self, mock_logging, mock_load, tmp_path):
        """--set with invalid key propagates KeyError from load_config."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.touch()
        mock_load.side_effect = KeyError("Override key 'bogus' not found")

        with (
            patch(
                "sys.argv",
                ["ai_trading", "run", "--config", str(cfg_path), "--set", "bogus=42"],
            ),
            pytest.raises(KeyError, match="bogus"),
        ):
            main()


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


class TestLoggingSetup:
    """Tests for phase 1 logging setup."""

    @patch("ai_trading.__main__.run_pipeline")
    @patch("ai_trading.__main__.load_config")
    @patch("ai_trading.__main__.setup_logging")
    def test_setup_logging_called_before_load_config(
        self, mock_logging, mock_load, mock_run, tmp_path,
    ):
        """setup_logging is called with INFO/text before loading config."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.touch()
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.format = "text"
        mock_load.return_value = mock_config
        mock_run.return_value = tmp_path / "runs" / "run1"

        with patch("sys.argv", ["ai_trading", "run", "--config", str(cfg_path)]):
            main()

        # Phase 1 logging: called with defaults before config is loaded
        mock_logging.assert_called()
        first_call = mock_logging.call_args_list[0]
        assert first_call[0][0] == "INFO"  # level
        assert first_call[0][1] == "text"  # format


# ---------------------------------------------------------------------------
# --strategy shortcut
# ---------------------------------------------------------------------------


class TestStrategyShortcut:
    """Tests for --strategy as a shortcut for --set strategy.name=<value>."""

    @patch("ai_trading.__main__.run_pipeline")
    @patch("ai_trading.__main__.load_config")
    @patch("ai_trading.__main__.setup_logging")
    def test_strategy_shortcut_applies(
        self, mock_logging, mock_load, mock_run, tmp_path,
    ):
        """--strategy dummy results in strategy.name=dummy override."""
        cfg_path = tmp_path / "config.yaml"
        cfg_path.touch()
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.format = "text"
        mock_load.return_value = mock_config
        mock_run.return_value = tmp_path / "runs" / "run1"

        with patch(
            "sys.argv",
            ["ai_trading", "run", "--config", str(cfg_path), "--strategy", "dummy"],
        ):
            main()

        call_args = mock_load.call_args
        assert "strategy.name=dummy" in call_args[1]["overrides"]


# ---------------------------------------------------------------------------
# Module invocation (python -m ai_trading)
# ---------------------------------------------------------------------------


class TestModuleInvocation:
    """Test that `python -m ai_trading --help` works via subprocess."""

    def test_help_exits_zero(self):
        """python -m ai_trading --help exits 0 and shows usage information."""
        result = subprocess.run(
            [sys.executable, "-m", "ai_trading", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "Usage" in result.stdout

    def test_help_shows_subcommands(self):
        """Help output mentions run, fetch, qa subcommands."""
        result = subprocess.run(
            [sys.executable, "-m", "ai_trading", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert "run" in result.stdout
        assert "fetch" in result.stdout
        assert "qa" in result.stdout

    def test_run_help(self):
        """python -m ai_trading run --help exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "ai_trading", "run", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--config" in result.stdout

    def test_fetch_help(self):
        """python -m ai_trading fetch --help exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "ai_trading", "fetch", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0

    def test_qa_help(self):
        """python -m ai_trading qa --help exits 0."""
        result = subprocess.run(
            [sys.executable, "-m", "ai_trading", "qa", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
