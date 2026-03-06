"""Tests for equity curve + fold metrics logic in run_detail_logic.py.

Task #081 — WS-D-3: Page 2 — equity curve stitchée et métriques par fold.
Spec refs: §6.3 equity curve, §6.4 métriques par fold, §9.3 conventions.

Tests cover:
- build_fold_metrics_table: table construction from metrics.json folds
- Threshold object access (method, theta, selected_quantile)
- method="none" → theta displayed as "—"
- Sharpe/trade formatting with ⚠️ warning for n_trades ≤ 2
- Null values → "—"
- equity curve absent → returns None
- Bar chart data extraction
"""

from __future__ import annotations

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers — synthetic data fixtures
# ---------------------------------------------------------------------------


def _make_equity_df(
    *,
    n_rows: int = 10,
    start_equity: float = 1000.0,
    step: float = 10.0,
    n_folds: int = 2,
) -> pd.DataFrame:
    """Build a minimal equity curve DataFrame."""
    equities = [start_equity + i * step for i in range(n_rows)]
    folds = [i // (n_rows // n_folds) for i in range(n_rows)]
    return pd.DataFrame({
        "time_utc": [f"2026-01-01T{i:02d}:00:00" for i in range(n_rows)],
        "equity": equities,
        "in_trade": [i % 3 == 0 for i in range(n_rows)],
        "fold": folds,
    })


def _make_fold_entry(
    *,
    fold_id: int = 0,
    method: str = "quantile_grid",
    theta: float | None = 0.005,
    selected_quantile: float | None = 0.9,
    net_pnl: float | None = 0.05,
    sharpe: float | None = 1.5,
    max_drawdown: float | None = 0.08,
    hit_rate: float | None = 0.55,
    n_trades: int | None = 15,
    mae: float | None = 0.015,
    rmse: float | None = 0.022,
    directional_accuracy: float | None = 0.52,
    spearman_ic: float | None = 0.10,
    sharpe_per_trade: float | None = 0.10,
) -> dict:
    """Build a single fold entry as in metrics.json."""
    return {
        "fold_id": fold_id,
        "threshold": {
            "method": method,
            "theta": theta,
            "selected_quantile": selected_quantile,
        },
        "prediction": {
            "mae": mae,
            "rmse": rmse,
            "directional_accuracy": directional_accuracy,
            "spearman_ic": spearman_ic,
        },
        "trading": {
            "net_pnl": net_pnl,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "hit_rate": hit_rate,
            "n_trades": n_trades,
            "sharpe_per_trade": sharpe_per_trade,
        },
    }


def _make_metrics_with_folds(folds: list[dict]) -> dict:
    """Wrap fold entries into a metrics.json-like dict."""
    return {
        "run_id": "20260301_120000_test",
        "strategy": {"name": "test", "strategy_type": "model"},
        "folds": folds,
        "aggregate": {"trading": {"mean": {}, "std": {}}},
    }


# ---------------------------------------------------------------------------
# §6.4 — build_fold_metrics_table
# ---------------------------------------------------------------------------


class TestBuildFoldMetricsTable:
    """#081 — Fold metrics table construction (§6.4)."""

    def test_nominal_columns(self) -> None:
        """#081 — Table has all §6.4 columns."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0), _make_fold_entry(fold_id=1)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)

        expected_cols = [
            "Fold", "θ", "Method", "Quantile",
            "Net PnL", "Sharpe", "MDD", "Win Rate",
            "N Trades", "MAE", "RMSE", "DA", "IC", "Sharpe/Trade",
        ]
        assert list(table.columns) == expected_cols

    def test_nominal_row_count(self) -> None:
        """#081 — One row per fold."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=i) for i in range(3)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert len(table) == 3

    def test_theta_from_threshold_object(self) -> None:
        """#081 — θ accessed from fold.threshold.theta (not direct float)."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, theta=0.0032)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        # θ should be formatted, containing "0.0032" or similar
        assert "0.0032" in table["θ"].iloc[0]

    def test_method_displayed(self) -> None:
        """#081 — threshold.method is displayed in Method column."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, method="quantile_grid")]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert table["Method"].iloc[0] == "quantile_grid"

    def test_quantile_displayed(self) -> None:
        """#081 — threshold.selected_quantile is displayed."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, selected_quantile=0.9)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "0.90" in table["Quantile"].iloc[0]

    def test_method_none_theta_em_dash(self) -> None:
        """#081 — method='none' → θ displayed as '—' (§6.4)."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(
            fold_id=0, method="none", theta=None, selected_quantile=None,
        )]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert table["θ"].iloc[0] == "—"

    def test_method_none_quantile_em_dash(self) -> None:
        """#081 — method='none' → Quantile displayed as '—'."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(
            fold_id=0, method="none", theta=None, selected_quantile=None,
        )]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert table["Quantile"].iloc[0] == "—"

    def test_sharpe_per_trade_warning_low_trades(self) -> None:
        """#081 — ⚠️ appended for folds with n_trades ≤ 2 (§6.4)."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, n_trades=2, sharpe_per_trade=0.5)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "⚠️" in table["Sharpe/Trade"].iloc[0]

    def test_sharpe_per_trade_no_warning_high_trades(self) -> None:
        """#081 — No ⚠️ for folds with n_trades > 2."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, n_trades=10, sharpe_per_trade=0.5)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "⚠️" not in table["Sharpe/Trade"].iloc[0]

    def test_sharpe_per_trade_scientific_notation(self) -> None:
        """#081 — |sharpe_per_trade| > 1000 uses scientific notation."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(
            fold_id=0, n_trades=5, sharpe_per_trade=1500.0,
        )]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "e+" in table["Sharpe/Trade"].iloc[0].lower()

    def test_null_trading_values_em_dash(self) -> None:
        """#081 — null trading values → '—' (§6.4, §9.3)."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(
            fold_id=0,
            net_pnl=None, sharpe=None, max_drawdown=None,
            hit_rate=None, n_trades=None, sharpe_per_trade=None,
        )]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert table["Net PnL"].iloc[0] == "—"
        assert table["Sharpe"].iloc[0] == "—"
        assert table["MDD"].iloc[0] == "—"
        assert table["Win Rate"].iloc[0] == "—"
        assert table["N Trades"].iloc[0] == "—"
        assert table["Sharpe/Trade"].iloc[0] == "—"

    def test_null_prediction_values_em_dash(self) -> None:
        """#081 — null prediction values → '—'."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(
            fold_id=0,
            mae=None, rmse=None,
            directional_accuracy=None, spearman_ic=None,
        )]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert table["MAE"].iloc[0] == "—"
        assert table["RMSE"].iloc[0] == "—"
        assert table["DA"].iloc[0] == "—"
        assert table["IC"].iloc[0] == "—"

    def test_empty_folds_empty_table(self) -> None:
        """#081 — Empty folds list → empty DataFrame with correct columns."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        metrics = _make_metrics_with_folds([])
        table = build_fold_metrics_table(metrics)
        assert len(table) == 0
        assert "Fold" in table.columns


# ---------------------------------------------------------------------------
# §6.4 — build_pnl_bar_data
# ---------------------------------------------------------------------------


class TestBuildPnlBarData:
    """#081 — PnL bar chart data extraction."""

    def test_nominal_extracts_fold_and_pnl(self) -> None:
        """#081 — Extracts fold labels and net_pnl for bar chart."""
        from scripts.dashboard.pages.run_detail_logic import build_pnl_bar_data

        folds = [
            _make_fold_entry(fold_id=0, net_pnl=0.05),
            _make_fold_entry(fold_id=1, net_pnl=-0.02),
        ]
        metrics = _make_metrics_with_folds(folds)
        data = build_pnl_bar_data(metrics)
        assert len(data) == 2
        assert data[0]["fold"] == 0
        assert data[0]["net_pnl"] == pytest.approx(0.05)
        assert data[1]["fold"] == 1
        assert data[1]["net_pnl"] == pytest.approx(-0.02)

    def test_null_pnl_uses_zero(self) -> None:
        """#081 — Null net_pnl treated as 0 for bar chart."""
        from scripts.dashboard.pages.run_detail_logic import build_pnl_bar_data

        folds = [_make_fold_entry(fold_id=0, net_pnl=None)]
        metrics = _make_metrics_with_folds(folds)
        data = build_pnl_bar_data(metrics)
        assert data[0]["net_pnl"] == 0.0

    def test_empty_folds(self) -> None:
        """#081 — Empty folds → empty list."""
        from scripts.dashboard.pages.run_detail_logic import build_pnl_bar_data

        metrics = _make_metrics_with_folds([])
        data = build_pnl_bar_data(metrics)
        assert data == []


# ---------------------------------------------------------------------------
# §6.4 — Formatting details
# ---------------------------------------------------------------------------


class TestFormattingDetails:
    """#081 — Formatting specifics for fold metrics table."""

    def test_net_pnl_pct_format(self) -> None:
        """#081 — Net PnL formatted as percentage."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, net_pnl=0.0534)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "5.34%" in table["Net PnL"].iloc[0]

    def test_sharpe_float_format(self) -> None:
        """#081 — Sharpe formatted as float with 2 decimals."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, sharpe=1.567)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "1.57" in table["Sharpe"].iloc[0]

    def test_mdd_pct_format(self) -> None:
        """#081 — MDD formatted as percentage."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, max_drawdown=0.123)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "12.30%" in table["MDD"].iloc[0]

    def test_hit_rate_pct_format(self) -> None:
        """#081 — Win Rate formatted as percentage."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, hit_rate=0.556)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "55.60%" in table["Win Rate"].iloc[0]

    def test_n_trades_integer_format(self) -> None:
        """#081 — N Trades formatted as integer."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, n_trades=42)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert table["N Trades"].iloc[0] == "42"

    def test_theta_float_format(self) -> None:
        """#081 — θ formatted with enough precision."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, theta=0.00317)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        # Should show enough precision
        assert "0.0032" in table["θ"].iloc[0] or "0.00317" in table["θ"].iloc[0]

    def test_fold_id_label(self) -> None:
        """#081 — Fold column shows fold_id."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=5)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert table["Fold"].iloc[0] == 5

    def test_sharpe_per_trade_warning_boundary_n_trades_1(self) -> None:
        """#081 — n_trades=1 also gets ⚠️."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, n_trades=1, sharpe_per_trade=0.3)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "⚠️" in table["Sharpe/Trade"].iloc[0]

    def test_sharpe_per_trade_boundary_n_trades_3_no_warning(self) -> None:
        """#081 — n_trades=3 does NOT get ⚠️ (boundary: ≤ 2)."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(fold_id=0, n_trades=3, sharpe_per_trade=0.3)]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert "⚠️" not in table["Sharpe/Trade"].iloc[0]

    def test_n_trades_null_sharpe_per_trade_null(self) -> None:
        """#081 — Both n_trades and sharpe_per_trade null → '—' no crash."""
        from scripts.dashboard.pages.run_detail_logic import (
            build_fold_metrics_table,
        )

        folds = [_make_fold_entry(
            fold_id=0, n_trades=None, sharpe_per_trade=None,
        )]
        metrics = _make_metrics_with_folds(folds)
        table = build_fold_metrics_table(metrics)
        assert table["Sharpe/Trade"].iloc[0] == "—"
