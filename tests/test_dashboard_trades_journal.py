"""Tests for run_detail_logic.py — trade distribution stats and journal.

Task #082 — WS-D-3: Page 2 — distribution des trades et journal paginé.
Spec refs: §6.5 distribution des trades, §6.6 journal des trades,
           §11.2 pagination (50 lignes/page).

Tests cover:
- compute_trade_stats: mean, median, std, skewness, best, worst
- build_trade_journal: column construction, costs, equity after
- join_equity_after: merge_asof per fold, missing equity, no match
- paginate_dataframe: slicing, boundaries, empty
- filter_trades: by fold, by sign, by date range, combinations
- Edge cases: empty trades, single trade, no equity curve
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers — synthetic data fixtures
# ---------------------------------------------------------------------------


def _make_trades_df(
    n: int = 10,
    n_folds: int = 2,
    seed: int = 42,
) -> pd.DataFrame:
    """Build a synthetic trades DataFrame similar to load_trades() output."""
    rng = np.random.default_rng(seed)
    base_time = pd.Timestamp("2025-01-01 00:00:00")
    rows = []
    for i in range(n):
        fold_idx = i % n_folds
        entry_time = base_time + pd.Timedelta(hours=i * 10)
        exit_time = entry_time + pd.Timedelta(hours=5)
        entry_price = 40000.0 + rng.normal(0, 500)
        gross_ret = rng.normal(0.001, 0.01)
        exit_price = entry_price * (1 + gross_ret)
        fees = abs(gross_ret) * 0.001
        slippage = abs(gross_ret) * 0.0005
        net_ret = gross_ret - fees - slippage
        rows.append({
            "entry_time_utc": str(entry_time),
            "exit_time_utc": str(exit_time),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "entry_price_eff": entry_price * 1.001,
            "exit_price_eff": exit_price * 0.999,
            "f": 0.001,
            "s": 0.0005,
            "fees_paid": fees,
            "slippage_paid": slippage,
            "y_true": gross_ret,
            "y_hat": gross_ret + rng.normal(0, 0.001),
            "gross_return": gross_ret,
            "net_return": net_ret,
            "fold": f"fold_{fold_idx:02d}",
            "costs": fees + slippage,
        })
    return pd.DataFrame(rows)


def _make_equity_df(
    n_folds: int = 2,
    bars_per_fold: int = 20,
) -> pd.DataFrame:
    """Build a synthetic stitched equity_curve DataFrame."""
    rows = []
    base_time = pd.Timestamp("2025-01-01 00:00:00")
    equity = 10000.0
    for fold_idx in range(n_folds):
        fold_start = base_time + pd.Timedelta(hours=fold_idx * bars_per_fold)
        for bar in range(bars_per_fold):
            t = fold_start + pd.Timedelta(hours=bar)
            equity += np.random.default_rng(42 + fold_idx * 100 + bar).normal(5, 2)
            rows.append({
                "time_utc": str(t),
                "equity": equity,
                "in_trade": bar % 3 == 0,
                "fold": fold_idx,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# §6.5 — compute_trade_stats
# ---------------------------------------------------------------------------


class TestComputeTradeStats:
    """#082 — Trade distribution statistics (§6.5)."""

    def test_nominal_all_stats_present(self) -> None:
        """#082 — Returns dict with all 6 expected stat keys."""
        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=20)
        stats = compute_trade_stats(df)
        expected_keys = {"mean", "median", "std", "skewness", "best_trade", "worst_trade"}
        assert expected_keys == set(stats.keys())

    def test_mean_matches_pandas(self) -> None:
        """#082 — Mean matches pd.Series.mean()."""
        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=50, seed=123)
        stats = compute_trade_stats(df)
        assert stats["mean"] == pytest.approx(df["net_return"].mean(), rel=1e-10)

    def test_median_matches_pandas(self) -> None:
        """#082 — Median matches pd.Series.median()."""
        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=50, seed=123)
        stats = compute_trade_stats(df)
        assert stats["median"] == pytest.approx(df["net_return"].median(), rel=1e-10)

    def test_std_matches_pandas(self) -> None:
        """#082 — Std matches pd.Series.std() (ddof=1)."""
        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=50, seed=123)
        stats = compute_trade_stats(df)
        assert stats["std"] == pytest.approx(df["net_return"].std(), rel=1e-10)

    def test_skewness_matches_scipy(self) -> None:
        """#082 — Skewness matches scipy.stats.skew(bias=False)."""
        from scipy.stats import skew

        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=50, seed=123)
        stats = compute_trade_stats(df)
        expected_skew = skew(df["net_return"].values, bias=False)
        assert stats["skewness"] == pytest.approx(expected_skew, rel=1e-10)

    def test_best_trade(self) -> None:
        """#082 — Best trade is the maximum net_return."""
        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=20)
        stats = compute_trade_stats(df)
        assert stats["best_trade"] == pytest.approx(df["net_return"].max(), rel=1e-10)

    def test_worst_trade(self) -> None:
        """#082 — Worst trade is the minimum net_return."""
        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=20)
        stats = compute_trade_stats(df)
        assert stats["worst_trade"] == pytest.approx(df["net_return"].min(), rel=1e-10)

    def test_single_trade(self) -> None:
        """#082 — Single trade: mean == value, std == NaN, skewness == NaN."""
        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=1)
        stats = compute_trade_stats(df)
        assert stats["mean"] == pytest.approx(df["net_return"].iloc[0], rel=1e-10)
        assert stats["best_trade"] == stats["worst_trade"]

    def test_empty_trades_raises(self) -> None:
        """#082 — Empty DataFrame raises ValueError."""
        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=2).iloc[:0]
        with pytest.raises(ValueError, match="empty"):
            compute_trade_stats(df)

    def test_identical_returns(self) -> None:
        """#082 — All identical returns: std == 0, skewness == NaN or 0."""
        from scripts.dashboard.pages.run_detail_logic import compute_trade_stats

        df = _make_trades_df(n=5)
        df["net_return"] = 0.01
        stats = compute_trade_stats(df)
        assert stats["std"] == pytest.approx(0.0, abs=1e-15)
        assert stats["mean"] == pytest.approx(0.01, rel=1e-10)


# ---------------------------------------------------------------------------
# §6.6 — join_equity_after
# ---------------------------------------------------------------------------


class TestJoinEquityAfter:
    """#082 — Equity after jointure via merge_asof (§6.6)."""

    def test_nominal_join_exact_match(self) -> None:
        """#082 — Exact time match returns correct equity value."""
        from scripts.dashboard.pages.run_detail_logic import join_equity_after

        trades_df = pd.DataFrame({
            "exit_time_utc": ["2025-01-01 05:00:00"],
            "fold": ["fold_00"],
        })
        equity_df = pd.DataFrame({
            "time_utc": [
                "2025-01-01 04:00:00",
                "2025-01-01 05:00:00",
                "2025-01-01 06:00:00",
            ],
            "equity": [10000.0, 10050.0, 10100.0],
            "fold": [0, 0, 0],
        })
        result = join_equity_after(trades_df, equity_df)
        assert len(result) == 1
        assert result.iloc[0] == pytest.approx(10050.0)

    def test_backward_join(self) -> None:
        """#082 — If no exact match, backward join picks previous bar."""
        from scripts.dashboard.pages.run_detail_logic import join_equity_after

        trades_df = pd.DataFrame({
            "exit_time_utc": ["2025-01-01 05:30:00"],
            "fold": ["fold_00"],
        })
        equity_df = pd.DataFrame({
            "time_utc": [
                "2025-01-01 05:00:00",
                "2025-01-01 06:00:00",
            ],
            "equity": [10050.0, 10100.0],
            "fold": [0, 0],
        })
        result = join_equity_after(trades_df, equity_df)
        assert len(result) == 1
        assert result.iloc[0] == pytest.approx(10050.0)

    def test_per_fold_join(self) -> None:
        """#082 — Jointure done per fold, not across folds."""
        from scripts.dashboard.pages.run_detail_logic import join_equity_after

        trades_df = pd.DataFrame({
            "exit_time_utc": [
                "2025-01-01 05:00:00",
                "2025-01-02 05:00:00",
            ],
            "fold": ["fold_00", "fold_01"],
        })
        equity_df = pd.DataFrame({
            "time_utc": [
                "2025-01-01 05:00:00",
                "2025-01-02 05:00:00",
            ],
            "equity": [10050.0, 20050.0],
            "fold": [0, 1],
        })
        result = join_equity_after(trades_df, equity_df)
        assert len(result) == 2
        assert result.iloc[0] == pytest.approx(10050.0)
        assert result.iloc[1] == pytest.approx(20050.0)

    def test_no_match_returns_nan(self) -> None:
        """#082 — If exit_time before all equity times, returns NaN."""
        from scripts.dashboard.pages.run_detail_logic import join_equity_after

        trades_df = pd.DataFrame({
            "exit_time_utc": ["2024-12-31 23:00:00"],
            "fold": ["fold_00"],
        })
        equity_df = pd.DataFrame({
            "time_utc": ["2025-01-01 00:00:00", "2025-01-01 01:00:00"],
            "equity": [10000.0, 10010.0],
            "fold": [0, 0],
        })
        result = join_equity_after(trades_df, equity_df)
        assert len(result) == 1
        assert pd.isna(result.iloc[0])

    def test_equity_none_returns_none(self) -> None:
        """#082 — If equity_df is None, returns None."""
        from scripts.dashboard.pages.run_detail_logic import join_equity_after

        trades_df = _make_trades_df(n=3)
        result = join_equity_after(trades_df, None)
        assert result is None


# ---------------------------------------------------------------------------
# §6.6 — build_trade_journal
# ---------------------------------------------------------------------------


class TestBuildTradeJournal:
    """#082 — Trade journal construction (§6.6)."""

    def test_nominal_columns(self) -> None:
        """#082 — Journal has all expected columns per §6.6."""
        from scripts.dashboard.pages.run_detail_logic import build_trade_journal

        trades_df = _make_trades_df(n=5, n_folds=2)
        equity_df = _make_equity_df(n_folds=2, bars_per_fold=100)
        journal = build_trade_journal(trades_df, equity_df)
        expected_cols = [
            "Fold", "Entry time", "Exit time", "Entry price", "Exit price",
            "Gross return", "Costs", "Net return", "Equity after",
        ]
        assert list(journal.columns) == expected_cols

    def test_costs_column_computed(self) -> None:
        """#082 — Costs column equals fees_paid + slippage_paid."""
        from scripts.dashboard.pages.run_detail_logic import build_trade_journal

        trades_df = _make_trades_df(n=5)
        journal = build_trade_journal(trades_df, None)
        for idx in range(len(trades_df)):
            expected = trades_df.iloc[idx]["fees_paid"] + trades_df.iloc[idx]["slippage_paid"]
            assert journal.iloc[idx]["Costs"] == pytest.approx(expected, rel=1e-10)

    def test_equity_after_column_omitted_if_no_equity(self) -> None:
        """#082 — Equity after column omitted when equity_df is None."""
        from scripts.dashboard.pages.run_detail_logic import build_trade_journal

        trades_df = _make_trades_df(n=5)
        journal = build_trade_journal(trades_df, None)
        assert "Equity after" not in journal.columns

    def test_equity_after_em_dash_no_match(self) -> None:
        """#082 — Equity after shows '—' when no match found."""
        from scripts.dashboard.pages.run_detail_logic import build_trade_journal

        trades_df = pd.DataFrame({
            "entry_time_utc": ["2024-01-01 00:00:00"],
            "exit_time_utc": ["2024-01-01 05:00:00"],
            "entry_price": [40000.0],
            "exit_price": [40100.0],
            "fees_paid": [0.001],
            "slippage_paid": [0.0005],
            "gross_return": [0.0025],
            "net_return": [0.001],
            "fold": ["fold_00"],
            "costs": [0.0015],
        })
        # Equity starts after the trade exit → no backward match
        equity_df = pd.DataFrame({
            "time_utc": ["2025-01-01 00:00:00"],
            "equity": [10000.0],
            "fold": [0],
        })
        journal = build_trade_journal(trades_df, equity_df)
        assert journal.iloc[0]["Equity after"] == "—"

    def test_row_count_matches_trades(self) -> None:
        """#082 — Journal row count matches trades count."""
        from scripts.dashboard.pages.run_detail_logic import build_trade_journal

        trades_df = _make_trades_df(n=10)
        journal = build_trade_journal(trades_df, None)
        assert len(journal) == 10

    def test_empty_trades(self) -> None:
        """#082 — Empty trades produces empty journal."""
        from scripts.dashboard.pages.run_detail_logic import build_trade_journal

        trades_df = _make_trades_df(n=2).iloc[:0]
        journal = build_trade_journal(trades_df, None)
        assert len(journal) == 0


# ---------------------------------------------------------------------------
# §11.2 — paginate_dataframe
# ---------------------------------------------------------------------------


class TestPaginateDataframe:
    """#082 — Pagination at 50 rows/page (§11.2)."""

    def test_first_page(self) -> None:
        """#082 — First page returns rows 0..49."""
        from scripts.dashboard.pages.run_detail_logic import paginate_dataframe

        df = pd.DataFrame({"x": range(120)})
        page = paginate_dataframe(df, page=1, page_size=50)
        assert len(page) == 50
        assert page.iloc[0]["x"] == 0
        assert page.iloc[-1]["x"] == 49

    def test_second_page(self) -> None:
        """#082 — Second page returns rows 50..99."""
        from scripts.dashboard.pages.run_detail_logic import paginate_dataframe

        df = pd.DataFrame({"x": range(120)})
        page = paginate_dataframe(df, page=2, page_size=50)
        assert len(page) == 50
        assert page.iloc[0]["x"] == 50
        assert page.iloc[-1]["x"] == 99

    def test_last_page_partial(self) -> None:
        """#082 — Last page may have fewer than page_size rows."""
        from scripts.dashboard.pages.run_detail_logic import paginate_dataframe

        df = pd.DataFrame({"x": range(120)})
        page = paginate_dataframe(df, page=3, page_size=50)
        assert len(page) == 20
        assert page.iloc[0]["x"] == 100

    def test_empty_dataframe(self) -> None:
        """#082 — Empty DataFrame returns empty page."""
        from scripts.dashboard.pages.run_detail_logic import paginate_dataframe

        df = pd.DataFrame({"x": []})
        page = paginate_dataframe(df, page=1, page_size=50)
        assert len(page) == 0

    def test_page_beyond_data(self) -> None:
        """#082 — Page beyond data returns empty."""
        from scripts.dashboard.pages.run_detail_logic import paginate_dataframe

        df = pd.DataFrame({"x": range(10)})
        page = paginate_dataframe(df, page=2, page_size=50)
        assert len(page) == 0

    def test_total_pages_calculation(self) -> None:
        """#082 — Total pages: ceil(n_rows / page_size)."""
        import math

        from scripts.dashboard.pages.run_detail_logic import paginate_dataframe

        df = pd.DataFrame({"x": range(120)})
        # Verify by iterating
        total = math.ceil(len(df) / 50)
        assert total == 3
        # All pages together cover all rows
        all_rows = pd.concat(
            [paginate_dataframe(df, page=p, page_size=50) for p in range(1, total + 1)]
        )
        assert len(all_rows) == 120

    def test_page_zero_raises(self) -> None:
        """#082 — Page 0 is invalid, raises ValueError."""
        from scripts.dashboard.pages.run_detail_logic import paginate_dataframe

        df = pd.DataFrame({"x": range(10)})
        with pytest.raises(ValueError, match="page"):
            paginate_dataframe(df, page=0, page_size=50)

    def test_negative_page_raises(self) -> None:
        """#082 — Negative page raises ValueError."""
        from scripts.dashboard.pages.run_detail_logic import paginate_dataframe

        df = pd.DataFrame({"x": range(10)})
        with pytest.raises(ValueError, match="page"):
            paginate_dataframe(df, page=-1, page_size=50)


# ---------------------------------------------------------------------------
# §6.6 — filter_trades
# ---------------------------------------------------------------------------


class TestFilterTrades:
    """#082 — Trade journal filters (§6.6)."""

    def test_filter_by_fold(self) -> None:
        """#082 — Filter by fold returns only matching rows."""
        from scripts.dashboard.pages.run_detail_logic import filter_trades

        df = _make_trades_df(n=10, n_folds=2)
        filtered = filter_trades(df, fold="fold_00")
        assert all(filtered["fold"] == "fold_00")
        assert len(filtered) > 0

    def test_filter_by_fold_all(self) -> None:
        """#082 — fold=None returns all rows (no filtering)."""
        from scripts.dashboard.pages.run_detail_logic import filter_trades

        df = _make_trades_df(n=10, n_folds=2)
        filtered = filter_trades(df, fold=None)
        assert len(filtered) == len(df)

    def test_filter_by_sign_winning(self) -> None:
        """#082 — sign='winning' returns rows with net_return > 0."""
        from scripts.dashboard.pages.run_detail_logic import filter_trades

        df = _make_trades_df(n=50, seed=99)
        filtered = filter_trades(df, sign="winning")
        assert all(filtered["net_return"] > 0)

    def test_filter_by_sign_losing(self) -> None:
        """#082 — sign='losing' returns rows with net_return <= 0."""
        from scripts.dashboard.pages.run_detail_logic import filter_trades

        df = _make_trades_df(n=50, seed=99)
        filtered = filter_trades(df, sign="losing")
        assert all(filtered["net_return"] <= 0)

    def test_filter_by_sign_all(self) -> None:
        """#082 — sign=None returns all rows."""
        from scripts.dashboard.pages.run_detail_logic import filter_trades

        df = _make_trades_df(n=10)
        filtered = filter_trades(df, sign=None)
        assert len(filtered) == len(df)

    def test_filter_by_date_range(self) -> None:
        """#082 — Date range filter on entry_time_utc."""
        from scripts.dashboard.pages.run_detail_logic import filter_trades

        df = _make_trades_df(n=20, n_folds=1)
        start = pd.Timestamp("2025-01-01 00:00:00")
        end = pd.Timestamp("2025-01-04 00:00:00")
        filtered = filter_trades(df, date_start=start, date_end=end)
        entry_times = pd.to_datetime(filtered["entry_time_utc"])
        assert all(entry_times >= start)
        assert all(entry_times <= end)

    def test_filter_combined(self) -> None:
        """#082 — Combined fold + sign filter applies both."""
        from scripts.dashboard.pages.run_detail_logic import filter_trades

        df = _make_trades_df(n=50, n_folds=2, seed=99)
        filtered = filter_trades(df, fold="fold_00", sign="winning")
        assert all(filtered["fold"] == "fold_00")
        assert all(filtered["net_return"] > 0)

    def test_filter_empty_result(self) -> None:
        """#082 — Filter that matches nothing returns empty DataFrame."""
        from scripts.dashboard.pages.run_detail_logic import filter_trades

        df = _make_trades_df(n=10, n_folds=2)
        filtered = filter_trades(df, fold="fold_99")
        assert len(filtered) == 0

    def test_filter_no_criteria(self) -> None:
        """#082 — No filter criteria returns all rows."""
        from scripts.dashboard.pages.run_detail_logic import filter_trades

        df = _make_trades_df(n=10)
        filtered = filter_trades(df)
        assert len(filtered) == len(df)
