"""Two-phase logging setup for the AI Trading Pipeline.

Phase 1 (startup): stdout-only logging via setup_logging().
Phase 2 (post run_dir): add file handler via add_file_handler().

Reference: Specification §17.7, Task #001.
"""

import json
import logging
import sys
from pathlib import Path

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_FORMATS = {"text", "json"}

# Store current format so add_file_handler can reuse it
_current_fmt: str = "text"

_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_TEXT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, _TEXT_DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def _make_formatter(fmt: str) -> logging.Formatter:
    """Create a Formatter for the given format type.

    Args:
        fmt: 'text' or 'json'.

    Returns:
        A logging.Formatter instance.

    Raises:
        ValueError: If *fmt* is not in {'text', 'json'}.
    """
    if fmt not in _VALID_FORMATS:
        raise ValueError(
            f"Invalid logging format {fmt!r}. "
            f"Supported formats: {sorted(_VALID_FORMATS)}"
        )
    if fmt == "json":
        return _JsonFormatter()
    return logging.Formatter(fmt=_TEXT_FORMAT, datefmt=_TEXT_DATE_FORMAT)


def setup_logging(level: str, fmt: str) -> None:
    """Phase 1 — configure root logger to write to stdout.

    Args:
        level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
        fmt: One of 'text', 'json'.

    Raises:
        ValueError: If *level* or *fmt* is invalid.
    """
    global _current_fmt  # noqa: PLW0603

    level_upper = level.upper() if isinstance(level, str) else level
    if level_upper not in _VALID_LEVELS:
        raise ValueError(
            f"Invalid logging level {level!r}. "
            f"Supported levels: {sorted(_VALID_LEVELS)}"
        )

    formatter = _make_formatter(fmt)  # validates fmt
    _current_fmt = fmt

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level_upper)

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(formatter)
    root.addHandler(stdout_handler)


def add_file_handler(run_dir: Path, filename: str) -> None:
    """Phase 2 — add a FileHandler writing to *run_dir/filename*.

    The file handler reuses the format configured by the last
    ``setup_logging()`` call.

    Args:
        run_dir: Existing directory where the log file will be created.
        filename: Name of the log file (e.g. ``"pipeline.log"``).

    Raises:
        FileNotFoundError: If *run_dir* does not exist.
    """
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(
            f"run_dir does not exist or is not a directory: {run_dir}"
        )

    log_path = run_dir / filename
    formatter = _make_formatter(_current_fmt)

    file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(file_handler)
