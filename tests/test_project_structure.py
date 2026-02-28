"""Tests for task #001 — Project structure, dependencies and logging.

Covers:
- Package importability and version
- setup_logging() phase 1 (stdout)
- add_file_handler() phase 2 (file)
- Text and JSON log formats
- Invalid format raises ValueError
- Edge cases (duplicate handlers, missing dir)
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# 1. Package import & version
# ---------------------------------------------------------------------------

class TestPackageStructure:
    """#001 — Verify package import and version."""

    def test_import_ai_trading(self):
        """ai_trading is importable."""
        import ai_trading  # noqa: F401

    def test_version_is_1_0_0(self):
        """ai_trading.__version__ returns '1.0.0'."""
        import ai_trading

        assert ai_trading.__version__ == "1.0.0"

    def test_pip_install_editable(self):
        """pip install -e . succeeds (already installed in dev env)."""
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps", "--quiet"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent,
        )
        assert result.returncode == 0, f"pip install -e . failed: {result.stderr}"


# ---------------------------------------------------------------------------
# 2. setup_logging — Phase 1 (stdout only)
# ---------------------------------------------------------------------------

class TestSetupLogging:
    """#001 — setup_logging() configures root logger to stdout."""

    def setup_method(self):
        """Reset root logger before each test."""
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)

    def teardown_method(self):
        """Clean up root logger after each test."""
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)

    def test_setup_logging_exists(self):
        """Module ai_trading.utils.logging exposes setup_logging."""
        from ai_trading.utils.logging import setup_logging

        assert callable(setup_logging)

    def test_setup_logging_sets_level_debug(self):
        """setup_logging(level='DEBUG') sets root logger to DEBUG."""
        from ai_trading.utils.logging import setup_logging

        setup_logging(level="DEBUG", fmt="text")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_setup_logging_sets_level_info(self):
        """setup_logging(level='INFO') sets root logger to INFO."""
        from ai_trading.utils.logging import setup_logging

        setup_logging(level="INFO", fmt="text")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_setup_logging_sets_level_warning(self):
        """setup_logging(level='WARNING') sets root logger to WARNING."""
        from ai_trading.utils.logging import setup_logging

        setup_logging(level="WARNING", fmt="text")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_setup_logging_sets_level_error(self):
        """setup_logging(level='ERROR') sets root logger to ERROR."""
        from ai_trading.utils.logging import setup_logging

        setup_logging(level="ERROR", fmt="text")
        root = logging.getLogger()
        assert root.level == logging.ERROR

    def test_setup_logging_adds_stdout_handler(self):
        """setup_logging adds exactly one StreamHandler to root."""
        from ai_trading.utils.logging import setup_logging

        setup_logging(level="INFO", fmt="text")
        root = logging.getLogger()
        stream_handlers = [
            h for h in root.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(stream_handlers) == 1

    def test_setup_logging_text_format_output(self, capsys):
        """Text format produces human-readable log lines."""
        from ai_trading.utils.logging import setup_logging

        setup_logging(level="INFO", fmt="text")
        logger = logging.getLogger("test.text")
        logger.info("hello text")

        # The handler writes to stderr by default for StreamHandler,
        # but we check the handler's formatter is set correctly
        root = logging.getLogger()
        handler = root.handlers[0]
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        formatted = handler.formatter.format(record)
        # Text format should NOT be valid JSON
        with pytest.raises((json.JSONDecodeError, TypeError)):
            json.loads(formatted)

    def test_setup_logging_json_format_output(self):
        """JSON format produces valid JSON log lines."""
        from ai_trading.utils.logging import setup_logging

        setup_logging(level="INFO", fmt="json")
        root = logging.getLogger()
        handler = root.handlers[0]
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        formatted = handler.formatter.format(record)
        parsed = json.loads(formatted)
        assert "message" in parsed or "msg" in parsed
        assert "level" in parsed or "levelname" in parsed

    def test_setup_logging_invalid_format_raises(self):
        """Unknown format raises ValueError."""
        from ai_trading.utils.logging import setup_logging

        with pytest.raises(ValueError, match="format"):
            setup_logging(level="INFO", fmt="xml")

    def test_setup_logging_invalid_level_raises(self):
        """Invalid log level raises ValueError."""
        from ai_trading.utils.logging import setup_logging

        with pytest.raises(ValueError, match="level"):
            setup_logging(level="INVALID", fmt="text")


# ---------------------------------------------------------------------------
# 3. add_file_handler — Phase 2 (file handler)
# ---------------------------------------------------------------------------

class TestAddFileHandler:
    """#001 — add_file_handler() adds a FileHandler dynamically."""

    def setup_method(self):
        """Reset root logger before each test."""
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)

    def teardown_method(self):
        """Clean up root logger and close file handlers."""
        root = logging.getLogger()
        for h in root.handlers[:]:
            if isinstance(h, logging.FileHandler):
                h.close()
        root.handlers.clear()
        root.setLevel(logging.WARNING)

    def test_add_file_handler_exists(self):
        """Module ai_trading.utils.logging exposes add_file_handler."""
        from ai_trading.utils.logging import add_file_handler

        assert callable(add_file_handler)

    def test_add_file_handler_creates_file(self, tmp_path):
        """add_file_handler creates log file in run_dir."""
        from ai_trading.utils.logging import add_file_handler, setup_logging

        setup_logging(level="INFO", fmt="text")
        add_file_handler(run_dir=tmp_path, filename="pipeline.log")

        logger = logging.getLogger("test.file")
        logger.info("file test message")

        # Flush handlers
        for h in logging.getLogger().handlers:
            h.flush()

        log_file = tmp_path / "pipeline.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "file test message" in content

    def test_add_file_handler_adds_file_handler_to_root(self, tmp_path):
        """add_file_handler adds exactly one FileHandler to root logger."""
        from ai_trading.utils.logging import add_file_handler, setup_logging

        setup_logging(level="INFO", fmt="text")
        add_file_handler(run_dir=tmp_path, filename="pipeline.log")

        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1

    def test_add_file_handler_respects_current_format(self, tmp_path):
        """File handler uses the same format as the current setup."""
        from ai_trading.utils.logging import add_file_handler, setup_logging

        setup_logging(level="INFO", fmt="json")
        add_file_handler(run_dir=tmp_path, filename="pipeline.log")

        logger = logging.getLogger("test.json_file")
        logger.info("json file message")

        for h in logging.getLogger().handlers:
            h.flush()

        log_file = tmp_path / "pipeline.log"
        lines = [line for line in log_file.read_text().strip().split("\n") if line]
        assert len(lines) >= 1
        parsed = json.loads(lines[-1])
        assert "message" in parsed or "msg" in parsed

    def test_add_file_handler_nonexistent_dir_raises(self):
        """add_file_handler raises if run_dir does not exist."""
        from ai_trading.utils.logging import add_file_handler, setup_logging

        setup_logging(level="INFO", fmt="text")
        fake_dir = Path("/nonexistent/path/that/does/not/exist")
        with pytest.raises((FileNotFoundError, OSError)):
            add_file_handler(run_dir=fake_dir, filename="pipeline.log")

    def test_add_file_handler_uses_text_format_by_default(self, tmp_path):
        """When setup was text, file handler also uses text format."""
        from ai_trading.utils.logging import add_file_handler, setup_logging

        setup_logging(level="DEBUG", fmt="text")
        add_file_handler(run_dir=tmp_path, filename="test.log")

        logger = logging.getLogger("test.text_file")
        logger.debug("debug text file")

        for h in logging.getLogger().handlers:
            h.flush()

        log_file = tmp_path / "test.log"
        content = log_file.read_text()
        assert "debug text file" in content
        # Should NOT be JSON
        for line in content.strip().split("\n"):
            if line.strip():
                with pytest.raises((json.JSONDecodeError, TypeError)):
                    json.loads(line)


# ---------------------------------------------------------------------------
# 4. Ruff compliance (meta-test)
# ---------------------------------------------------------------------------

class TestRuffCompliance:
    """#001 — ruff check passes on ai_trading/ and tests/."""

    def test_ruff_check(self):
        """ruff check ai_trading/ tests/ exits cleanly."""
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "ai_trading/", "tests/"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent,
        )
        assert result.returncode == 0, f"ruff check failed:\n{result.stdout}\n{result.stderr}"
