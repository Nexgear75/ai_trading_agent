"""CLI entry point: python -m ai_trading."""

import sys


def main() -> None:
    """Run the AI Trading pipeline."""
    # TODO: WS-12.3 — implement CLI argument parsing and pipeline runner
    print(f"ai_trading v{__import__('ai_trading').__version__}")
    print("Pipeline not yet implemented. See docs/plan/implementation.md for roadmap.")
    sys.exit(0)


if __name__ == "__main__":
    main()
