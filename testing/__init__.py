"""
Testing module for AI Trading Agent.

Contains backtesting and realtime testing utilities.
"""

from .backtesting import run_backtest, BacktestResult, Trade

__all__ = [
    "run_backtest",
    "BacktestResult",
    "Trade",
]
