"""Tests for scripts/dashboard/utils.py — formatting utilities and color palette.

Task #076 — WS-D-1: Utilitaires de formatage et palette de couleurs.
Spec refs: §9.2 palette, §9.3 display conventions, §6.2 color thresholds, §6.4 Sharpe/trade.
"""

from datetime import datetime, timezone

import pytest


# ---------------------------------------------------------------------------
# Palette constants (§9.2)
# ---------------------------------------------------------------------------
class TestColorPalette:
    """#076 — Palette de couleurs conforme à §9.2."""

    def test_color_profit(self):
        from scripts.dashboard.utils import COLOR_PROFIT

        assert COLOR_PROFIT == "#2ecc71"

    def test_color_loss(self):
        from scripts.dashboard.utils import COLOR_LOSS

        assert COLOR_LOSS == "#e74c3c"

    def test_color_neutral(self):
        from scripts.dashboard.utils import COLOR_NEUTRAL

        assert COLOR_NEUTRAL == "#3498db"

    def test_color_warning(self):
        from scripts.dashboard.utils import COLOR_WARNING

        assert COLOR_WARNING == "#f39c12"

    def test_color_drawdown(self):
        from scripts.dashboard.utils import COLOR_DRAWDOWN

        assert COLOR_DRAWDOWN == "rgba(231, 76, 60, 0.15)"

    def test_color_fold_border(self):
        from scripts.dashboard.utils import COLOR_FOLD_BORDER

        assert COLOR_FOLD_BORDER == "#95a5a6"


# ---------------------------------------------------------------------------
# format_pct (§9.3)
# ---------------------------------------------------------------------------
class TestFormatPct:
    """#076 — format_pct conforme à §9.3."""

    def test_normal_value(self):
        from scripts.dashboard.utils import format_pct

        assert format_pct(0.0345) == "3.45%"

    def test_none_returns_dash(self):
        from scripts.dashboard.utils import format_pct

        assert format_pct(None) == "—"

    def test_zero(self):
        from scripts.dashboard.utils import format_pct

        assert format_pct(0.0) == "0.00%"

    def test_negative(self):
        from scripts.dashboard.utils import format_pct

        assert format_pct(-0.1234) == "-12.34%"

    def test_custom_decimals(self):
        from scripts.dashboard.utils import format_pct

        assert format_pct(0.12345, decimals=4) == "12.3450%"

    def test_large_value(self):
        from scripts.dashboard.utils import format_pct

        assert format_pct(10.0) == "1000.00%"


# ---------------------------------------------------------------------------
# format_float (§9.3)
# ---------------------------------------------------------------------------
class TestFormatFloat:
    """#076 — format_float conforme à §9.3."""

    def test_normal_value(self):
        from scripts.dashboard.utils import format_float

        assert format_float(1.23) == "1.23"

    def test_none_returns_dash(self):
        from scripts.dashboard.utils import format_float

        assert format_float(None) == "—"

    def test_zero(self):
        from scripts.dashboard.utils import format_float

        assert format_float(0.0) == "0.00"

    def test_negative(self):
        from scripts.dashboard.utils import format_float

        assert format_float(-3.456) == "-3.46"

    def test_custom_decimals(self):
        from scripts.dashboard.utils import format_float

        assert format_float(1.23456, decimals=4) == "1.2346"


# ---------------------------------------------------------------------------
# format_int (§9.3)
# ---------------------------------------------------------------------------
class TestFormatInt:
    """#076 — format_int conforme à §9.3."""

    def test_normal_value(self):
        from scripts.dashboard.utils import format_int

        assert format_int(1234) == "1,234"

    def test_none_returns_dash(self):
        from scripts.dashboard.utils import format_int

        assert format_int(None) == "—"

    def test_zero(self):
        from scripts.dashboard.utils import format_int

        assert format_int(0) == "0"

    def test_negative(self):
        from scripts.dashboard.utils import format_int

        assert format_int(-5678) == "-5,678"

    def test_large_value(self):
        from scripts.dashboard.utils import format_int

        assert format_int(1000000) == "1,000,000"


# ---------------------------------------------------------------------------
# format_timestamp (§9.3)
# ---------------------------------------------------------------------------
class TestFormatTimestamp:
    """#076 — format_timestamp conforme à §9.3."""

    def test_normal_datetime(self):
        from scripts.dashboard.utils import format_timestamp

        ts = datetime(2025, 6, 15, 14, 0, tzinfo=timezone.utc)
        assert format_timestamp(ts) == "2025-06-15 14:00"

    def test_none_returns_dash(self):
        from scripts.dashboard.utils import format_timestamp

        assert format_timestamp(None) == "—"

    def test_naive_datetime(self):
        from scripts.dashboard.utils import format_timestamp

        ts = datetime(2025, 1, 1, 0, 30)
        assert format_timestamp(ts) == "2025-01-01 00:30"

    def test_midnight(self):
        from scripts.dashboard.utils import format_timestamp

        ts = datetime(2025, 12, 31, 0, 0, tzinfo=timezone.utc)
        assert format_timestamp(ts) == "2025-12-31 00:00"


# ---------------------------------------------------------------------------
# format_mean_std (§9.3 + §6.2)
# ---------------------------------------------------------------------------
class TestFormatMeanStd:
    """#076 — format_mean_std conforme à §9.3 et §6.2."""

    def test_pct_type(self):
        from scripts.dashboard.utils import format_mean_std

        result = format_mean_std(0.0345, 0.012, "pct")
        assert result == "3.45% ± 1.20%"

    def test_float_type(self):
        from scripts.dashboard.utils import format_mean_std

        result = format_mean_std(1.23, 0.34, "float")
        assert result == "1.23 ± 0.34"

    def test_none_mean_returns_dash(self):
        from scripts.dashboard.utils import format_mean_std

        assert format_mean_std(None, 0.5, "float") == "—"

    def test_with_count_partial(self):
        from scripts.dashboard.utils import format_mean_std

        result = format_mean_std(1.31, 0.12, "float", n_contributing=8, n_total=10)
        assert result == "1.31 ± 0.12 (8/10 folds)"

    def test_with_count_all_folds(self):
        from scripts.dashboard.utils import format_mean_std

        result = format_mean_std(1.31, 0.12, "float", n_contributing=10, n_total=10)
        assert result == "1.31 ± 0.12"

    def test_pct_with_count(self):
        from scripts.dashboard.utils import format_mean_std

        result = format_mean_std(0.0345, 0.012, "pct", n_contributing=3, n_total=5)
        assert result == "3.45% ± 1.20% (3/5 folds)"


# ---------------------------------------------------------------------------
# pnl_color (§6.2)
# ---------------------------------------------------------------------------
class TestPnlColor:
    """#076 — pnl_color thresholds conformes à §6.2."""

    def test_positive(self):
        from scripts.dashboard.utils import COLOR_PROFIT, pnl_color

        assert pnl_color(100.0) == COLOR_PROFIT

    def test_negative(self):
        from scripts.dashboard.utils import COLOR_LOSS, pnl_color

        assert pnl_color(-50.0) == COLOR_LOSS

    def test_zero(self):
        from scripts.dashboard.utils import COLOR_LOSS, pnl_color

        assert pnl_color(0.0) == COLOR_LOSS

    def test_none(self):
        from scripts.dashboard.utils import COLOR_NEUTRAL, pnl_color

        assert pnl_color(None) == COLOR_NEUTRAL


# ---------------------------------------------------------------------------
# sharpe_color (§6.2)
# ---------------------------------------------------------------------------
class TestSharpeColor:
    """#076 — sharpe_color thresholds conformes à §6.2."""

    def test_above_one(self):
        from scripts.dashboard.utils import COLOR_PROFIT, sharpe_color

        assert sharpe_color(1.5) == COLOR_PROFIT

    def test_exactly_one(self):
        from scripts.dashboard.utils import COLOR_WARNING, sharpe_color

        # > 1 → profit, == 1 → not > 1, but > 0 → warning
        assert sharpe_color(1.0) == COLOR_WARNING

    def test_positive_below_one(self):
        from scripts.dashboard.utils import COLOR_WARNING, sharpe_color

        assert sharpe_color(0.5) == COLOR_WARNING

    def test_zero(self):
        from scripts.dashboard.utils import COLOR_LOSS, sharpe_color

        assert sharpe_color(0.0) == COLOR_LOSS

    def test_negative(self):
        from scripts.dashboard.utils import COLOR_LOSS, sharpe_color

        assert sharpe_color(-0.5) == COLOR_LOSS

    def test_none(self):
        from scripts.dashboard.utils import COLOR_NEUTRAL, sharpe_color

        assert sharpe_color(None) == COLOR_NEUTRAL


# ---------------------------------------------------------------------------
# mdd_color (§6.2)
# ---------------------------------------------------------------------------
class TestMddColor:
    """#076 — mdd_color thresholds conformes à §6.2."""

    def test_below_10pct(self):
        from scripts.dashboard.utils import COLOR_PROFIT, mdd_color

        assert mdd_color(0.05) == COLOR_PROFIT

    def test_exactly_10pct(self):
        from scripts.dashboard.utils import COLOR_WARNING, mdd_color

        # < 0.10 → profit, == 0.10 → not < 0.10, but < 0.25 → warning
        assert mdd_color(0.10) == COLOR_WARNING

    def test_between_10_and_25(self):
        from scripts.dashboard.utils import COLOR_WARNING, mdd_color

        assert mdd_color(0.20) == COLOR_WARNING

    def test_exactly_25pct(self):
        from scripts.dashboard.utils import COLOR_LOSS, mdd_color

        assert mdd_color(0.25) == COLOR_LOSS

    def test_above_25pct(self):
        from scripts.dashboard.utils import COLOR_LOSS, mdd_color

        assert mdd_color(0.50) == COLOR_LOSS

    def test_none(self):
        from scripts.dashboard.utils import COLOR_NEUTRAL, mdd_color

        assert mdd_color(None) == COLOR_NEUTRAL


# ---------------------------------------------------------------------------
# hit_rate_color (§6.2)
# ---------------------------------------------------------------------------
class TestHitRateColor:
    """#076 — hit_rate_color thresholds conformes à §6.2."""

    def test_above_55pct(self):
        from scripts.dashboard.utils import COLOR_PROFIT, hit_rate_color

        assert hit_rate_color(0.60) == COLOR_PROFIT

    def test_exactly_55pct(self):
        from scripts.dashboard.utils import COLOR_WARNING, hit_rate_color

        # > 0.55 → profit, == 0.55 → not > 0.55, but > 0.50 → warning
        assert hit_rate_color(0.55) == COLOR_WARNING

    def test_between_50_and_55(self):
        from scripts.dashboard.utils import COLOR_WARNING, hit_rate_color

        assert hit_rate_color(0.52) == COLOR_WARNING

    def test_exactly_50pct(self):
        from scripts.dashboard.utils import COLOR_LOSS, hit_rate_color

        assert hit_rate_color(0.50) == COLOR_LOSS

    def test_below_50pct(self):
        from scripts.dashboard.utils import COLOR_LOSS, hit_rate_color

        assert hit_rate_color(0.40) == COLOR_LOSS

    def test_none(self):
        from scripts.dashboard.utils import COLOR_NEUTRAL, hit_rate_color

        assert hit_rate_color(None) == COLOR_NEUTRAL


# ---------------------------------------------------------------------------
# profit_factor_color (§6.2)
# ---------------------------------------------------------------------------
class TestProfitFactorColor:
    """#076 — profit_factor_color thresholds conformes à §6.2."""

    def test_above_one(self):
        from scripts.dashboard.utils import COLOR_PROFIT, profit_factor_color

        assert profit_factor_color(1.5) == COLOR_PROFIT

    def test_exactly_one(self):
        from scripts.dashboard.utils import COLOR_LOSS, profit_factor_color

        assert profit_factor_color(1.0) == COLOR_LOSS

    def test_below_one(self):
        from scripts.dashboard.utils import COLOR_LOSS, profit_factor_color

        assert profit_factor_color(0.8) == COLOR_LOSS

    def test_none(self):
        from scripts.dashboard.utils import COLOR_NEUTRAL, profit_factor_color

        assert profit_factor_color(None) == COLOR_NEUTRAL


# ---------------------------------------------------------------------------
# format_sharpe_per_trade (§6.4)
# ---------------------------------------------------------------------------
class TestFormatSharpePerTrade:
    """#076 — format_sharpe_per_trade conforme à §6.4."""

    def test_normal_value(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        assert format_sharpe_per_trade(0.05, n_trades=50) == "0.05"

    def test_none_returns_dash(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        assert format_sharpe_per_trade(None, n_trades=10) == "—"

    def test_scientific_notation_large_positive(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        result = format_sharpe_per_trade(1500.0, n_trades=50)
        assert result == "1.50e+03"

    def test_scientific_notation_large_negative(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        result = format_sharpe_per_trade(-2000.0, n_trades=50)
        assert result == "-2.00e+03"

    def test_exactly_1000_no_scientific(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        # |value| > 1000 triggers scientific, |1000| is NOT > 1000
        assert format_sharpe_per_trade(1000.0, n_trades=50) == "1000.00"

    def test_warning_low_trades(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        result = format_sharpe_per_trade(0.05, n_trades=2)
        assert result == "0.05 ⚠️"

    def test_warning_one_trade(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        result = format_sharpe_per_trade(0.10, n_trades=1)
        assert result == "0.10 ⚠️"

    def test_scientific_with_warning(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        result = format_sharpe_per_trade(5000.0, n_trades=2)
        assert result == "5.00e+03 ⚠️"

    def test_zero_value(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        assert format_sharpe_per_trade(0.0, n_trades=10) == "0.00"

    def test_negative_normal(self):
        from scripts.dashboard.utils import format_sharpe_per_trade

        assert format_sharpe_per_trade(-0.5, n_trades=10) == "-0.50"
