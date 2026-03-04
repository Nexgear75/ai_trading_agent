"""Utility helpers for the AI Trading dashboard.

Fonctions utilitaires : formatage de nombres et pourcentages,
palettes de couleurs, gestion du cache Streamlit.

Ref: §10.2 — utils.py, §9.2 palette, §9.3 display conventions,
§6.2 color thresholds, §6.4 Sharpe/trade.
"""

from __future__ import annotations

from datetime import datetime

# ---------------------------------------------------------------------------
# Palette de couleurs (§9.2)
# ---------------------------------------------------------------------------
COLOR_PROFIT: str = "#2ecc71"
COLOR_LOSS: str = "#e74c3c"
COLOR_NEUTRAL: str = "#3498db"
COLOR_WARNING: str = "#f39c12"
COLOR_DRAWDOWN: str = "rgba(231, 76, 60, 0.15)"
COLOR_FOLD_BORDER: str = "#95a5a6"

# Em dash for null values (§9.3)
_NULL_DISPLAY: str = "—"


# ---------------------------------------------------------------------------
# Formatting functions (§9.3)
# ---------------------------------------------------------------------------
def format_pct(value: float | None, decimals: int = 2) -> str:
    """Format a ratio as percentage. None → '—'."""
    if value is None:
        return _NULL_DISPLAY
    return f"{value:.{decimals}%}"


def format_float(value: float | None, decimals: int = 2) -> str:
    """Format a float with fixed decimals. None → '—'."""
    if value is None:
        return _NULL_DISPLAY
    return f"{value:.{decimals}f}"


def format_int(value: int | None) -> str:
    """Format an integer with thousands separator. None → '—'."""
    if value is None:
        return _NULL_DISPLAY
    return f"{value:,d}"


def format_timestamp(ts: datetime | None) -> str:
    """Format a datetime as 'YYYY-MM-DD HH:MM'. None → '—'."""
    if ts is None:
        return _NULL_DISPLAY
    return ts.strftime("%Y-%m-%d %H:%M")


def format_mean_std(
    mean: float | None,
    std: float,
    fmt_type: str,
    n_contributing: int | None = None,
    n_total: int | None = None,
) -> str:
    """Format 'mean ± std' with optional fold count (§6.2).

    Parameters
    ----------
    mean : float or None
        Mean value. None → '—'.
    std : float
        Standard deviation.
    fmt_type : str
        'pct' for percentage format, 'float' for decimal format.
    n_contributing, n_total : int or None
        If both provided and n_contributing < n_total, appends '(n/N folds)'.
    """
    if mean is None:
        return _NULL_DISPLAY
    result = f"{mean:.2%} ± {std:.2%}" if fmt_type == "pct" else f"{mean:.2f} ± {std:.2f}"
    if (
        n_contributing is not None
        and n_total is not None
        and n_contributing < n_total
    ):
        result += f" ({n_contributing}/{n_total} folds)"
    return result


# ---------------------------------------------------------------------------
# Color threshold functions (§6.2)
# ---------------------------------------------------------------------------
def pnl_color(value: float | None) -> str:
    """Return color for Net PnL: green if > 0, red otherwise. None → neutral."""
    if value is None:
        return COLOR_NEUTRAL
    return COLOR_PROFIT if value > 0 else COLOR_LOSS


def sharpe_color(value: float | None) -> str:
    """Return color for Sharpe: green if > 1, orange if > 0, red otherwise."""
    if value is None:
        return COLOR_NEUTRAL
    if value > 1:
        return COLOR_PROFIT
    if value > 0:
        return COLOR_WARNING
    return COLOR_LOSS


def mdd_color(value: float | None) -> str:
    """Return color for MDD: green if < 10%, orange if < 25%, red otherwise."""
    if value is None:
        return COLOR_NEUTRAL
    if value < 0.10:
        return COLOR_PROFIT
    if value < 0.25:
        return COLOR_WARNING
    return COLOR_LOSS


def hit_rate_color(value: float | None) -> str:
    """Return color for Hit Rate: green if > 55%, orange if > 50%, red else."""
    if value is None:
        return COLOR_NEUTRAL
    if value > 0.55:
        return COLOR_PROFIT
    if value > 0.50:
        return COLOR_WARNING
    return COLOR_LOSS


def profit_factor_color(value: float | None) -> str:
    """Return color for Profit Factor: green if > 1, red otherwise."""
    if value is None:
        return COLOR_NEUTRAL
    return COLOR_PROFIT if value > 1 else COLOR_LOSS


# ---------------------------------------------------------------------------
# Special formatting (§6.4)
# ---------------------------------------------------------------------------
def format_sharpe_per_trade(value: float | None, n_trades: int) -> str:
    """Format Sharpe per trade with scientific notation and warning.

    - None → '—'
    - |value| > 1000 → scientific notation
    - n_trades ≤ 2 → append ⚠️
    """
    if value is None:
        return _NULL_DISPLAY
    result = f"{value:.2e}" if abs(value) > 1000 else f"{value:.2f}"
    if n_trades <= 2:
        result += " ⚠️"
    return result
