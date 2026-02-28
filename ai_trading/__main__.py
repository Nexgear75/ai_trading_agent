"""CLI entry point: python -m ai_trading."""

import logging
import sys

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the AI Trading pipeline."""
    # WS-12.3 will implement CLI argument parsing and pipeline runner.
    # Tracked in docs/tasks/ — no action needed here until WS-12.
    version = __import__("ai_trading").__version__
    logger.info("ai_trading v%s", version)
    logger.info("Pipeline not yet implemented. See docs/plan/implementation.md for roadmap.")
    sys.exit(0)


if __name__ == "__main__":
    main()
