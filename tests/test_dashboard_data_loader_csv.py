"""Tests for scripts/dashboard/data_loader.py — CSV loading functions.

Task #075 — WS-D-1: Data loader CSV (equity curves, trades, predictions, fold metrics).

Verifies:
- load_equity_curve: stitched equity curve loading with required columns
- load_fold_equity_curve: per-fold equity curve loading
- load_trades: multi-fold concatenation with fold column and costs column
- load_fold_trades: single fold trades loading
- load_predictions: preds_val.csv / preds_test.csv loading
- load_fold_metrics: metrics_fold.json loading
- Graceful degradation: None when file absent, ValueError when columns missing
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers — synthetic CSV builders
# ---------------------------------------------------------------------------

EQUITY_COLS = ["time_utc", "equity", "in_trade", "fold"]
FOLD_EQUITY_COLS = ["time_utc", "equity", "in_trade"]
TRADES_COLS = [
    "entry_time_utc",
    "exit_time_utc",
    "entry_price",
    "exit_price",
    "entry_price_eff",
    "exit_price_eff",
    "f",
    "s",
    "fees_paid",
    "slippage_paid",
    "y_true",
    "y_hat",
    "gross_return",
    "net_return",
]
PREDS_COLS = ["timestamp", "y_true", "y_hat"]


def _make_equity_csv(path: Path, *, n_rows: int = 3, cols: list[str] | None = None) -> None:
    """Write a synthetic equity_curve.csv."""
    cols = cols if cols is not None else EQUITY_COLS
    rows = []
    for i in range(n_rows):
        row = {}
        if "time_utc" in cols:
            row["time_utc"] = f"2025-01-0{i + 1}T00:00:00Z"
        if "equity" in cols:
            row["equity"] = 1000.0 + i * 10
        if "in_trade" in cols:
            row["in_trade"] = i % 2 == 0
        if "fold" in cols:
            row["fold"] = f"fold_0{i}"
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)


def _make_fold_equity_csv(
    path: Path, *, n_rows: int = 3, cols: list[str] | None = None
) -> None:
    """Write a synthetic fold equity_curve.csv (no fold column)."""
    cols = cols if cols is not None else FOLD_EQUITY_COLS
    rows = []
    for i in range(n_rows):
        row = {}
        if "time_utc" in cols:
            row["time_utc"] = f"2025-01-0{i + 1}T00:00:00Z"
        if "equity" in cols:
            row["equity"] = 1000.0 + i * 10
        if "in_trade" in cols:
            row["in_trade"] = i % 2 == 0
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)


def _make_trades_csv(
    path: Path, *, n_rows: int = 2, cols: list[str] | None = None
) -> None:
    """Write a synthetic trades.csv."""
    cols = cols if cols is not None else TRADES_COLS
    rows = []
    for i in range(n_rows):
        row = {}
        if "entry_time_utc" in cols:
            row["entry_time_utc"] = f"2025-01-0{i + 1}T00:00:00Z"
        if "exit_time_utc" in cols:
            row["exit_time_utc"] = f"2025-01-0{i + 1}T01:00:00Z"
        if "entry_price" in cols:
            row["entry_price"] = 100.0 + i
        if "exit_price" in cols:
            row["exit_price"] = 101.0 + i
        if "entry_price_eff" in cols:
            row["entry_price_eff"] = 100.1 + i
        if "exit_price_eff" in cols:
            row["exit_price_eff"] = 100.9 + i
        if "f" in cols:
            row["f"] = 1.0
        if "s" in cols:
            row["s"] = 1.0
        if "fees_paid" in cols:
            row["fees_paid"] = 0.5 + i * 0.1
        if "slippage_paid" in cols:
            row["slippage_paid"] = 0.2 + i * 0.1
        if "y_true" in cols:
            row["y_true"] = 0.01
        if "y_hat" in cols:
            row["y_hat"] = 0.009
        if "gross_return" in cols:
            row["gross_return"] = 0.01
        if "net_return" in cols:
            row["net_return"] = 0.005
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)


def _make_preds_csv(
    path: Path, *, n_rows: int = 3, cols: list[str] | None = None
) -> None:
    """Write a synthetic preds_val.csv or preds_test.csv."""
    cols = cols if cols is not None else PREDS_COLS
    rows = []
    for i in range(n_rows):
        row = {}
        if "timestamp" in cols:
            row["timestamp"] = f"2025-01-0{i + 1}T00:00:00Z"
        if "y_true" in cols:
            row["y_true"] = 0.01 * (i + 1)
        if "y_hat" in cols:
            row["y_hat"] = 0.009 * (i + 1)
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)


def _make_run_with_folds(
    run_dir: Path, *, n_folds: int = 2, trades_per_fold: int = 2
) -> Path:
    """Create a run dir with fold subdirectories containing trades.csv."""
    folds_dir = run_dir / "folds"
    for i in range(n_folds):
        fold_dir = folds_dir / f"fold_{i:02d}"
        fold_dir.mkdir(parents=True)
        _make_trades_csv(fold_dir / "trades.csv", n_rows=trades_per_fold)
    return run_dir


# ---------------------------------------------------------------------------
# Tests — load_equity_curve
# ---------------------------------------------------------------------------


class TestLoadEquityCurve:
    """Tests for load_equity_curve(run_dir)."""

    def test_valid_file(self, tmp_path: Path) -> None:
        """#075 — Valid equity_curve.csv returns DataFrame with correct columns."""
        from scripts.dashboard.data_loader import load_equity_curve

        _make_equity_csv(tmp_path / "equity_curve.csv", n_rows=3)
        result = load_equity_curve(tmp_path)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        for col in ["time_utc", "equity", "in_trade", "fold"]:
            assert col in result.columns
        assert len(result) == 3

    def test_absent_file_returns_none(self, tmp_path: Path) -> None:
        """#075 — Missing equity_curve.csv returns None."""
        from scripts.dashboard.data_loader import load_equity_curve

        result = load_equity_curve(tmp_path)
        assert result is None

    def test_missing_columns_raises(self, tmp_path: Path) -> None:
        """#075 — Existing file with missing required columns raises ValueError."""
        from scripts.dashboard.data_loader import load_equity_curve

        # Write a CSV with only time_utc and equity (missing in_trade, fold)
        _make_equity_csv(
            tmp_path / "equity_curve.csv", cols=["time_utc", "equity"]
        )
        with pytest.raises(ValueError, match="missing required columns"):
            load_equity_curve(tmp_path)


# ---------------------------------------------------------------------------
# Tests — load_fold_equity_curve
# ---------------------------------------------------------------------------


class TestLoadFoldEquityCurve:
    """Tests for load_fold_equity_curve(fold_dir)."""

    def test_valid_file(self, tmp_path: Path) -> None:
        """#075 — Valid fold equity_curve.csv returns DataFrame."""
        from scripts.dashboard.data_loader import load_fold_equity_curve

        _make_fold_equity_csv(tmp_path / "equity_curve.csv", n_rows=4)
        result = load_fold_equity_curve(tmp_path)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        for col in FOLD_EQUITY_COLS:
            assert col in result.columns
        assert len(result) == 4

    def test_absent_file_returns_none(self, tmp_path: Path) -> None:
        """#075 — Missing fold equity_curve.csv returns None."""
        from scripts.dashboard.data_loader import load_fold_equity_curve

        result = load_fold_equity_curve(tmp_path)
        assert result is None

    def test_missing_columns_raises(self, tmp_path: Path) -> None:
        """#075 — Existing fold equity file with missing columns raises ValueError."""
        from scripts.dashboard.data_loader import load_fold_equity_curve

        _make_fold_equity_csv(
            tmp_path / "equity_curve.csv", cols=["time_utc"]
        )
        with pytest.raises(ValueError, match="missing required columns"):
            load_fold_equity_curve(tmp_path)


# ---------------------------------------------------------------------------
# Tests — load_trades (multi-fold concatenation)
# ---------------------------------------------------------------------------


class TestLoadTrades:
    """Tests for load_trades(run_dir)."""

    def test_valid_multi_fold(self, tmp_path: Path) -> None:
        """#075 — Concatenates trades from multiple folds with fold and costs columns."""
        from scripts.dashboard.data_loader import load_trades

        _make_run_with_folds(tmp_path, n_folds=2, trades_per_fold=3)
        result = load_trades(tmp_path)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 6  # 2 folds * 3 trades
        # fold column exists and contains correct fold names
        assert "fold" in result.columns
        assert set(result["fold"].unique()) == {"fold_00", "fold_01"}
        # costs column exists and is fees_paid + slippage_paid
        assert "costs" in result.columns
        for _, row in result.iterrows():
            assert row["costs"] == pytest.approx(
                row["fees_paid"] + row["slippage_paid"]
            )

    def test_no_folds_dir_returns_none(self, tmp_path: Path) -> None:
        """#075 — No folds directory → None."""
        from scripts.dashboard.data_loader import load_trades

        result = load_trades(tmp_path)
        assert result is None

    def test_folds_without_trades_returns_none(self, tmp_path: Path) -> None:
        """#075 — Fold directories exist but without trades.csv → None."""
        from scripts.dashboard.data_loader import load_trades

        (tmp_path / "folds" / "fold_00").mkdir(parents=True)
        (tmp_path / "folds" / "fold_01").mkdir(parents=True)
        result = load_trades(tmp_path)
        assert result is None

    def test_missing_columns_in_trades_raises(self, tmp_path: Path) -> None:
        """#075 — trades.csv with missing required columns raises ValueError."""
        from scripts.dashboard.data_loader import load_trades

        fold_dir = tmp_path / "folds" / "fold_00"
        fold_dir.mkdir(parents=True)
        # Write CSV with only a subset of required columns
        _make_trades_csv(
            fold_dir / "trades.csv",
            cols=["entry_time_utc", "exit_time_utc"],
        )
        with pytest.raises(ValueError, match="missing required columns"):
            load_trades(tmp_path)

    def test_single_fold(self, tmp_path: Path) -> None:
        """#075 — Single fold still works and has fold column."""
        from scripts.dashboard.data_loader import load_trades

        _make_run_with_folds(tmp_path, n_folds=1, trades_per_fold=2)
        result = load_trades(tmp_path)
        assert result is not None
        assert len(result) == 2
        assert set(result["fold"].unique()) == {"fold_00"}


# ---------------------------------------------------------------------------
# Tests — load_fold_trades
# ---------------------------------------------------------------------------


class TestLoadFoldTrades:
    """Tests for load_fold_trades(fold_dir)."""

    def test_valid_file(self, tmp_path: Path) -> None:
        """#075 — Valid trades.csv returns DataFrame."""
        from scripts.dashboard.data_loader import load_fold_trades

        _make_trades_csv(tmp_path / "trades.csv", n_rows=3)
        result = load_fold_trades(tmp_path)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        for col in TRADES_COLS:
            assert col in result.columns
        assert len(result) == 3

    def test_absent_file_returns_none(self, tmp_path: Path) -> None:
        """#075 — Missing trades.csv returns None."""
        from scripts.dashboard.data_loader import load_fold_trades

        result = load_fold_trades(tmp_path)
        assert result is None

    def test_missing_columns_raises(self, tmp_path: Path) -> None:
        """#075 — Existing trades.csv with missing columns raises ValueError."""
        from scripts.dashboard.data_loader import load_fold_trades

        _make_trades_csv(
            tmp_path / "trades.csv",
            cols=["entry_time_utc"],
        )
        with pytest.raises(ValueError, match="missing required columns"):
            load_fold_trades(tmp_path)


# ---------------------------------------------------------------------------
# Tests — load_predictions
# ---------------------------------------------------------------------------


class TestLoadPredictions:
    """Tests for load_predictions(fold_dir, split)."""

    def test_load_preds_val(self, tmp_path: Path) -> None:
        """#075 — Loads preds_val.csv correctly."""
        from scripts.dashboard.data_loader import load_predictions

        _make_preds_csv(tmp_path / "preds_val.csv", n_rows=5)
        result = load_predictions(tmp_path, "val")
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        for col in PREDS_COLS:
            assert col in result.columns
        assert len(result) == 5

    def test_load_preds_test(self, tmp_path: Path) -> None:
        """#075 — Loads preds_test.csv correctly."""
        from scripts.dashboard.data_loader import load_predictions

        _make_preds_csv(tmp_path / "preds_test.csv", n_rows=4)
        result = load_predictions(tmp_path, "test")
        assert result is not None
        assert len(result) == 4

    def test_absent_file_returns_none(self, tmp_path: Path) -> None:
        """#075 — Missing predictions file returns None."""
        from scripts.dashboard.data_loader import load_predictions

        result = load_predictions(tmp_path, "val")
        assert result is None

    def test_missing_columns_raises(self, tmp_path: Path) -> None:
        """#075 — Existing preds file with missing columns raises ValueError."""
        from scripts.dashboard.data_loader import load_predictions

        _make_preds_csv(
            tmp_path / "preds_val.csv", cols=["timestamp"]
        )
        with pytest.raises(ValueError, match="missing required columns"):
            load_predictions(tmp_path, "val")

    def test_invalid_split_raises(self, tmp_path: Path) -> None:
        """#075 — Invalid split parameter raises ValueError."""
        from scripts.dashboard.data_loader import load_predictions

        with pytest.raises(ValueError, match="split must be 'val' or 'test'"):
            load_predictions(tmp_path, "train")


# ---------------------------------------------------------------------------
# Tests — load_fold_metrics
# ---------------------------------------------------------------------------


class TestLoadFoldMetrics:
    """Tests for load_fold_metrics(fold_dir)."""

    def test_valid_file(self, tmp_path: Path) -> None:
        """#075 — Valid metrics_fold.json returns dict."""
        from scripts.dashboard.data_loader import load_fold_metrics

        metrics = {"mae": 0.01, "sharpe": 1.5}
        (tmp_path / "metrics_fold.json").write_text(
            json.dumps(metrics), encoding="utf-8"
        )
        result = load_fold_metrics(tmp_path)
        assert result is not None
        assert isinstance(result, dict)
        assert result["mae"] == pytest.approx(0.01)
        assert result["sharpe"] == pytest.approx(1.5)

    def test_absent_file_returns_none(self, tmp_path: Path) -> None:
        """#075 — Missing metrics_fold.json returns None."""
        from scripts.dashboard.data_loader import load_fold_metrics

        result = load_fold_metrics(tmp_path)
        assert result is None

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        """#075 — Invalid JSON in metrics_fold.json raises ValueError."""
        from scripts.dashboard.data_loader import load_fold_metrics

        (tmp_path / "metrics_fold.json").write_text(
            "{not valid json", encoding="utf-8"
        )
        with pytest.raises(ValueError, match="invalid JSON"):
            load_fold_metrics(tmp_path)

    def test_non_dict_raises(self, tmp_path: Path) -> None:
        """#075 — metrics_fold.json containing non-dict raises ValueError."""
        from scripts.dashboard.data_loader import load_fold_metrics

        (tmp_path / "metrics_fold.json").write_text(
            json.dumps([1, 2, 3]), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="expected a JSON object"):
            load_fold_metrics(tmp_path)
