"""Tests for scripts/dashboard/charts.py — Plotly chart library.

Task #077 — WS-D-1: Bibliothèque de graphiques Plotly.
Spec refs: §6.3 equity curve, §6.4 PnL bar, §6.5 returns,
           §7.3 overlay, §7.4 radar, §8.2 fold equity, §8.3 scatter.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

# ---------------------------------------------------------------------------
# Fixtures — synthetic data for chart tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def equity_df() -> pd.DataFrame:
    """Equity curve DataFrame with time_utc, equity, in_trade, fold."""
    n = 100
    rng = np.random.default_rng(42)
    equity = 1000.0 + np.cumsum(rng.standard_normal(n))
    return pd.DataFrame(
        {
            "time_utc": pd.date_range("2024-01-01", periods=n, freq="h"),
            "equity": equity,
            "in_trade": [i % 5 == 0 for i in range(n)],
            "fold": [0] * 50 + [1] * 50,
        }
    )


@pytest.fixture()
def single_fold_equity_df() -> pd.DataFrame:
    """Equity curve with a single fold."""
    n = 20
    return pd.DataFrame(
        {
            "time_utc": pd.date_range("2024-01-01", periods=n, freq="h"),
            "equity": np.linspace(1000, 1100, n),
            "in_trade": [False] * n,
            "fold": [0] * n,
        }
    )


@pytest.fixture()
def fold_metrics() -> list[dict]:
    """Fold metrics list with mixed positive/negative PnL."""
    return [
        {"fold": 0, "net_pnl": 150.0},
        {"fold": 1, "net_pnl": -50.0},
        {"fold": 2, "net_pnl": 200.0},
    ]


@pytest.fixture()
def trades_df() -> pd.DataFrame:
    """Trades DataFrame with net_return, fold, entry/exit times."""
    rng = np.random.default_rng(42)
    n = 30
    returns = rng.standard_normal(n) * 0.02
    return pd.DataFrame(
        {
            "net_return": returns,
            "fold": [0] * 10 + [1] * 10 + [2] * 10,
            "entry_time_utc": pd.date_range("2024-01-01", periods=n, freq="2h"),
            "exit_time_utc": pd.date_range(
                "2024-01-01 01:00:00", periods=n, freq="2h"
            ),
        }
    )


@pytest.fixture()
def overlay_curves() -> dict[str, pd.DataFrame]:
    """Multi-run equity curves dict for overlay chart."""
    rng = np.random.default_rng(42)
    n = 50
    return {
        "run_a": pd.DataFrame(
            {"equity": 1000.0 + np.cumsum(rng.standard_normal(n))}
        ),
        "run_b": pd.DataFrame(
            {"equity": 2000.0 + np.cumsum(rng.standard_normal(n))}
        ),
    }


@pytest.fixture()
def radar_data() -> list[dict]:
    """Radar chart data with 3 runs."""
    return [
        {
            "label": "XGBoost",
            "net_pnl": 500.0,
            "sharpe": 1.5,
            "max_drawdown": 0.10,
            "hit_rate": 0.60,
            "profit_factor": 1.8,
        },
        {
            "label": "GRU",
            "net_pnl": 300.0,
            "sharpe": 0.9,
            "max_drawdown": 0.20,
            "hit_rate": 0.55,
            "profit_factor": 1.3,
        },
        {
            "label": "Buy&Hold",
            "net_pnl": 100.0,
            "sharpe": 0.5,
            "max_drawdown": 0.30,
            "hit_rate": 0.50,
            "profit_factor": 1.0,
        },
    ]


@pytest.fixture()
def preds_df() -> pd.DataFrame:
    """Predictions DataFrame with y_true and y_hat."""
    rng = np.random.default_rng(42)
    n = 50
    y_true = rng.standard_normal(n) * 0.01
    y_hat = y_true + rng.standard_normal(n) * 0.005
    return pd.DataFrame({"y_true": y_true, "y_hat": y_hat})


# ---------------------------------------------------------------------------
# Tests — chart_equity_curve (§6.3)
# ---------------------------------------------------------------------------


class TestChartEquityCurve:
    """#077 — Equity curve chart (§6.3)."""

    def test_returns_figure(self, equity_df):
        from scripts.dashboard.charts import chart_equity_curve

        fig = chart_equity_curve(equity_df)
        assert isinstance(fig, go.Figure)

    def test_has_equity_trace(self, equity_df):
        from scripts.dashboard.charts import chart_equity_curve

        fig = chart_equity_curve(equity_df)
        # At least one trace for the equity line
        assert len(fig.data) >= 1

    def test_fold_boundaries_present(self, equity_df):
        """Fold boundaries should be vertical lines at fold changes."""
        from scripts.dashboard.charts import chart_equity_curve

        fig = chart_equity_curve(equity_df, fold_boundaries=True)
        # shapes should include vertical lines
        shapes = fig.layout.shapes
        assert shapes is not None
        vlines = [s for s in shapes if s.type == "line"]
        assert len(vlines) >= 1

    def test_fold_boundaries_disabled(self, equity_df):
        from scripts.dashboard.charts import chart_equity_curve

        fig = chart_equity_curve(equity_df, fold_boundaries=False)
        shapes = fig.layout.shapes
        # No fold boundary lines
        vlines = [s for s in shapes if s.type == "line"] if shapes else []
        assert len(vlines) == 0

    def test_drawdown_trace(self, equity_df):
        """Drawdown enabled should add a fill trace."""
        from scripts.dashboard.charts import chart_equity_curve

        fig = chart_equity_curve(equity_df, drawdown=True)
        fill_traces = [t for t in fig.data if getattr(t, "fill", None)]
        assert len(fill_traces) >= 1

    def test_drawdown_disabled(self, equity_df):
        from scripts.dashboard.charts import chart_equity_curve

        fig = chart_equity_curve(equity_df, drawdown=False, in_trade_zones=False)
        # Only equity trace, no fill
        fill_traces = [t for t in fig.data if getattr(t, "fill", None)]
        assert len(fill_traces) == 0

    def test_in_trade_zones(self, equity_df):
        """In-trade zones should add colored area traces."""
        from scripts.dashboard.charts import chart_equity_curve

        fig = chart_equity_curve(equity_df, in_trade_zones=True)
        # Should have more traces than just equity + drawdown
        assert len(fig.data) >= 2

    def test_single_fold_no_boundary(self, single_fold_equity_df):
        """Single fold should produce no fold boundary lines."""
        from scripts.dashboard.charts import chart_equity_curve

        fig = chart_equity_curve(single_fold_equity_df, fold_boundaries=True)
        shapes = fig.layout.shapes
        vlines = [s for s in shapes if s.type == "line"] if shapes else []
        assert len(vlines) == 0


# ---------------------------------------------------------------------------
# Tests — chart_pnl_bar (§6.4)
# ---------------------------------------------------------------------------


class TestChartPnlBar:
    """#077 — PnL bar chart (§6.4)."""

    def test_returns_figure(self, fold_metrics):
        from scripts.dashboard.charts import chart_pnl_bar

        fig = chart_pnl_bar(fold_metrics)
        assert isinstance(fig, go.Figure)

    def test_bar_count_matches_folds(self, fold_metrics):
        from scripts.dashboard.charts import chart_pnl_bar

        fig = chart_pnl_bar(fold_metrics)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        total_bars = sum(len(t.x) for t in bar_traces)
        assert total_bars == len(fold_metrics)

    def test_colors_profit_loss(self, fold_metrics):
        """Positive PnL bars → green, negative → red."""
        from scripts.dashboard.charts import chart_pnl_bar
        from scripts.dashboard.utils import COLOR_LOSS, COLOR_PROFIT

        fig = chart_pnl_bar(fold_metrics)
        bar_traces = [t for t in fig.data if isinstance(t, go.Bar)]
        # Collect all marker colors
        colors = []
        for t in bar_traces:
            mc = t.marker.color
            if isinstance(mc, (list, tuple)):
                colors.extend(mc)
            else:
                colors.append(mc)
        assert COLOR_PROFIT in colors
        assert COLOR_LOSS in colors

    def test_empty_metrics(self):
        from scripts.dashboard.charts import chart_pnl_bar

        fig = chart_pnl_bar([])
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Tests — chart_returns_histogram (§6.5)
# ---------------------------------------------------------------------------


class TestChartReturnsHistogram:
    """#077 — Returns histogram (§6.5)."""

    def test_returns_figure(self, trades_df):
        from scripts.dashboard.charts import chart_returns_histogram

        fig = chart_returns_histogram(trades_df)
        assert isinstance(fig, go.Figure)

    def test_has_histogram_trace(self, trades_df):
        from scripts.dashboard.charts import chart_returns_histogram

        fig = chart_returns_histogram(trades_df)
        hist_traces = [t for t in fig.data if isinstance(t, go.Histogram)]
        assert len(hist_traces) == 1

    def test_empty_trades(self):
        from scripts.dashboard.charts import chart_returns_histogram

        empty_df = pd.DataFrame({"net_return": pd.Series([], dtype=float)})
        fig = chart_returns_histogram(empty_df)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# Tests — chart_returns_boxplot (§6.5)
# ---------------------------------------------------------------------------


class TestChartReturnsBoxplot:
    """#077 — Returns boxplot by fold (§6.5)."""

    def test_returns_figure(self, trades_df):
        from scripts.dashboard.charts import chart_returns_boxplot

        fig = chart_returns_boxplot(trades_df)
        assert isinstance(fig, go.Figure)

    def test_one_box_per_fold(self, trades_df):
        from scripts.dashboard.charts import chart_returns_boxplot

        fig = chart_returns_boxplot(trades_df)
        box_traces = [t for t in fig.data if isinstance(t, go.Box)]
        n_folds = trades_df["fold"].nunique()
        assert len(box_traces) == n_folds

    def test_single_fold(self):
        from scripts.dashboard.charts import chart_returns_boxplot

        df = pd.DataFrame({"net_return": [0.01, -0.02, 0.03], "fold": [0, 0, 0]})
        fig = chart_returns_boxplot(df)
        box_traces = [t for t in fig.data if isinstance(t, go.Box)]
        assert len(box_traces) == 1

    def test_empty_trades(self):
        """Empty trades DataFrame should produce a valid figure with no boxes."""
        from scripts.dashboard.charts import chart_returns_boxplot

        empty_df = pd.DataFrame(
            {"net_return": pd.Series([], dtype=float), "fold": pd.Series([], dtype=int)}
        )
        fig = chart_returns_boxplot(empty_df)
        assert isinstance(fig, go.Figure)
        box_traces = [t for t in fig.data if isinstance(t, go.Box)]
        assert len(box_traces) == 0


# ---------------------------------------------------------------------------
# Tests — chart_equity_overlay (§7.3)
# ---------------------------------------------------------------------------


class TestChartEquityOverlay:
    """#077 — Equity overlay multi-runs (§7.3)."""

    def test_returns_figure(self, overlay_curves):
        from scripts.dashboard.charts import chart_equity_overlay

        fig = chart_equity_overlay(overlay_curves)
        assert isinstance(fig, go.Figure)

    def test_one_trace_per_run(self, overlay_curves):
        from scripts.dashboard.charts import chart_equity_overlay

        fig = chart_equity_overlay(overlay_curves)
        assert len(fig.data) == len(overlay_curves)

    def test_normalization_starts_at_one(self, overlay_curves):
        """Each trace y-data should start at 1.0."""
        from scripts.dashboard.charts import chart_equity_overlay

        fig = chart_equity_overlay(overlay_curves)
        for trace in fig.data:
            assert pytest.approx(trace.y[0], abs=1e-9) == 1.0

    def test_legend_present(self, overlay_curves):
        from scripts.dashboard.charts import chart_equity_overlay

        fig = chart_equity_overlay(overlay_curves)
        for trace in fig.data:
            assert trace.name in overlay_curves

    def test_empty_curves(self):
        from scripts.dashboard.charts import chart_equity_overlay

        fig = chart_equity_overlay({})
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0


# ---------------------------------------------------------------------------
# Tests — chart_radar (§7.4)
# ---------------------------------------------------------------------------


class TestChartRadar:
    """#077 — Radar chart (§7.4)."""

    def test_returns_figure(self, radar_data):
        from scripts.dashboard.charts import chart_radar

        fig = chart_radar(radar_data)
        assert isinstance(fig, go.Figure)

    def test_one_trace_per_run(self, radar_data):
        from scripts.dashboard.charts import chart_radar

        fig = chart_radar(radar_data)
        assert len(fig.data) == len(radar_data)

    def test_five_axes(self, radar_data):
        """Radar should have 5 theta values (+ closing point)."""
        from scripts.dashboard.charts import chart_radar

        fig = chart_radar(radar_data)
        for trace in fig.data:
            # Scatterpolar theta has 6 values (5 axes + close)
            assert len(trace.theta) == 6
            assert trace.theta[0] == trace.theta[-1]

    def test_values_normalized_0_1(self, radar_data):
        """All r values should be in [0, 1] after min-max normalization."""
        from scripts.dashboard.charts import chart_radar

        fig = chart_radar(radar_data)
        for trace in fig.data:
            for v in trace.r:
                assert 0.0 <= v <= 1.0 + 1e-9

    def test_single_run(self):
        """Single run should still produce a valid radar."""
        from scripts.dashboard.charts import chart_radar

        data = [
            {
                "label": "Only",
                "net_pnl": 100.0,
                "sharpe": 1.0,
                "max_drawdown": 0.15,
                "hit_rate": 0.55,
                "profit_factor": 1.2,
            }
        ]
        fig = chart_radar(data)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1

    def test_equal_values_normalize_to_half(self):
        """When all runs have identical metrics, all r values should be 0.5."""
        from scripts.dashboard.charts import chart_radar

        data = [
            {
                "label": "Run A",
                "net_pnl": 200.0,
                "sharpe": 1.0,
                "max_drawdown": 0.15,
                "hit_rate": 0.55,
                "profit_factor": 1.2,
            },
            {
                "label": "Run B",
                "net_pnl": 200.0,
                "sharpe": 1.0,
                "max_drawdown": 0.15,
                "hit_rate": 0.55,
                "profit_factor": 1.2,
            },
        ]
        fig = chart_radar(data)
        assert isinstance(fig, go.Figure)
        for trace in fig.data:
            # 6 values: 5 axes + closing point, all should be 0.5
            for v in trace.r:
                assert v == pytest.approx(0.5)

    def test_empty_runs(self):
        """Empty runs_data should return a valid figure with no traces."""
        from scripts.dashboard.charts import chart_radar

        fig = chart_radar([])
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0


# ---------------------------------------------------------------------------
# Tests — chart_scatter_predictions (§8.3)
# ---------------------------------------------------------------------------


class TestChartScatterPredictions:
    """#077 — Scatter predictions chart (§8.3)."""

    def test_returns_figure(self, preds_df):
        from scripts.dashboard.charts import chart_scatter_predictions

        fig = chart_scatter_predictions(preds_df, theta=0.005, threshold_method="quantile")
        assert isinstance(fig, go.Figure)

    def test_has_scatter_traces(self, preds_df):
        """Should have at least one scatter trace for Go/No-Go."""
        from scripts.dashboard.charts import chart_scatter_predictions

        fig = chart_scatter_predictions(preds_df, theta=0.005, threshold_method="quantile")
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) >= 1

    def test_diagonal_line(self, preds_df):
        """Diagonal perfect-prediction line should be present."""
        from scripts.dashboard.charts import chart_scatter_predictions

        fig = chart_scatter_predictions(preds_df, theta=0.005, threshold_method="quantile")
        shapes = fig.layout.shapes
        assert shapes is not None
        diag = [s for s in shapes if s.type == "line"]
        assert len(diag) >= 1

    def test_signal_method_returns_annotation(self, preds_df):
        """threshold_method='none' should return a figure with an annotation."""
        from scripts.dashboard.charts import chart_scatter_predictions

        fig = chart_scatter_predictions(preds_df, theta=0.0, threshold_method="none")
        assert isinstance(fig, go.Figure)
        annotations = fig.layout.annotations
        assert annotations is not None
        assert len(annotations) >= 1

    def test_signal_method_no_scatter(self, preds_df):
        """threshold_method='none' should have no scatter traces."""
        from scripts.dashboard.charts import chart_scatter_predictions

        fig = chart_scatter_predictions(preds_df, theta=0.0, threshold_method="none")
        scatter_traces = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter_traces) == 0

    def test_axes_labels_per_spec(self, preds_df):
        """§8.3: ŷ on X-axis, y_true on Y-axis."""
        from scripts.dashboard.charts import chart_scatter_predictions

        fig = chart_scatter_predictions(preds_df, theta=0.005, threshold_method="quantile")
        assert fig.layout.xaxis.title.text == "ŷ"
        assert fig.layout.yaxis.title.text == "y_true"

    def test_go_mask_unilateral(self):
        """Go/No-Go coloring must be unilateral (y_hat > theta), not bilateral.

        Negative y_hat values should never be colored as 'Go' (green),
        consistent with apply_threshold in ai_trading/calibration/threshold.py.
        """
        from scripts.dashboard.charts import chart_scatter_predictions
        from scripts.dashboard.utils import COLOR_FOLD_BORDER, COLOR_PROFIT

        # y_hat with values on both sides of theta=0.01:
        #   +0.02 → Go (above theta)
        #   -0.02 → No-Go (below theta, even though abs(-0.02) >= 0.01)
        #   +0.005 → No-Go (below theta)
        df = pd.DataFrame({
            "y_true": [0.01, -0.01, 0.005],
            "y_hat": [0.02, -0.02, 0.005],
        })
        fig = chart_scatter_predictions(df, theta=0.01, threshold_method="quantile")
        scatter = [t for t in fig.data if isinstance(t, go.Scatter)]
        assert len(scatter) == 1
        colors = list(scatter[0].marker.color)
        # Only first point (y_hat=0.02 > 0.01) should be Go (green)
        assert colors[0] == COLOR_PROFIT
        assert colors[1] == COLOR_FOLD_BORDER  # -0.02 is NOT > 0.01
        assert colors[2] == COLOR_FOLD_BORDER  # 0.005 is NOT > 0.01


# ---------------------------------------------------------------------------
# Tests — chart_fold_equity (§8.2)
# ---------------------------------------------------------------------------


class TestChartFoldEquity:
    """#077 — Fold equity with trade markers (§8.2)."""

    def test_returns_figure(self, equity_df, trades_df):
        from scripts.dashboard.charts import chart_fold_equity

        fig = chart_fold_equity(equity_df, trades_df)
        assert isinstance(fig, go.Figure)

    def test_has_equity_line(self, equity_df, trades_df):
        from scripts.dashboard.charts import chart_fold_equity

        fig = chart_fold_equity(equity_df, trades_df)
        line_traces = [
            t for t in fig.data
            if isinstance(t, go.Scatter) and getattr(t, "mode", "") in ("lines", "lines+markers")
        ]
        assert len(line_traces) >= 1

    def test_entry_markers(self, equity_df, trades_df):
        """Entry markers should be ▲ green."""
        from scripts.dashboard.charts import chart_fold_equity
        from scripts.dashboard.utils import COLOR_PROFIT

        fig = chart_fold_equity(equity_df, trades_df)
        entry_traces = [
            t for t in fig.data
            if isinstance(t, go.Scatter)
            and getattr(t.marker, "symbol", None) == "triangle-up"
        ]
        assert len(entry_traces) >= 1
        assert entry_traces[0].marker.color == COLOR_PROFIT

    def test_exit_markers(self, equity_df, trades_df):
        """Exit markers should be ▼ red."""
        from scripts.dashboard.charts import chart_fold_equity
        from scripts.dashboard.utils import COLOR_LOSS

        fig = chart_fold_equity(equity_df, trades_df)
        exit_traces = [
            t for t in fig.data
            if isinstance(t, go.Scatter)
            and getattr(t.marker, "symbol", None) == "triangle-down"
        ]
        assert len(exit_traces) >= 1
        assert exit_traces[0].marker.color == COLOR_LOSS

    def test_empty_trades(self, equity_df):
        """Empty trades df should still produce a figure (just the equity line)."""
        from scripts.dashboard.charts import chart_fold_equity

        empty_trades = pd.DataFrame(
            {
                "entry_time_utc": pd.Series([], dtype="datetime64[ns]"),
                "exit_time_utc": pd.Series([], dtype="datetime64[ns]"),
                "net_return": pd.Series([], dtype=float),
                "fold": pd.Series([], dtype=int),
            }
        )
        fig = chart_fold_equity(equity_df, empty_trades)
        assert isinstance(fig, go.Figure)
        # Still has the equity line
        assert len(fig.data) >= 1
