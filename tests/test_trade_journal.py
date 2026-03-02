"""Tests for trade journal CSV export — Task #035.

Task #035 — WS-8: Export du journal de trades en CSV avec les colonnes
normatives §12.6. Vérifie la décomposition des coûts, les formules de
return, la cohérence avec l'équité finale, et les cas limites.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ai_trading.backtest.journal import export_trade_journal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = [
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

F = 0.001  # fee_rate_per_side
S = 0.0005  # slippage_rate_per_side

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_enriched_trade(
    entry_price: float = 100.0,
    exit_price: float = 110.0,
    y_true: float = 0.09531,
    y_hat: float = 0.10,
    entry_time: str = "2024-01-01 02:00",
    exit_time: str = "2024-01-01 06:00",
    f: float = F,
    s: float = S,
) -> dict:
    """Build an enriched trade dict (as produced by apply_cost_model + caller)."""
    p_entry_eff = entry_price * (1 + s)
    p_exit_eff = exit_price * (1 - s)
    m_net = (1 - f) ** 2 * (p_exit_eff / p_entry_eff)
    r_net = m_net - 1
    return {
        "signal_time": pd.Timestamp("2024-01-01 01:00"),
        "entry_time": pd.Timestamp(entry_time),
        "exit_time": pd.Timestamp(exit_time),
        "entry_price": entry_price,
        "exit_price": exit_price,
        "entry_price_eff": p_entry_eff,
        "exit_price_eff": p_exit_eff,
        "m_net": m_net,
        "r_net": r_net,
        "y_true": y_true,
        "y_hat": y_hat,
    }


# ---------------------------------------------------------------------------
# Nominal — column order §12.6
# ---------------------------------------------------------------------------


class TestColumnOrder:
    """CSV columns must match §12.6 in exact order."""

    def test_columns_match_spec_order(self, tmp_path: Path) -> None:
        """AC1: CSV colonnes conformes à §12.6 dans l'ordre spécifié."""
        trades = [_make_enriched_trade()]
        df = export_trade_journal(trades, tmp_path / "trades.csv", F, S)
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_returns_dataframe(self, tmp_path: Path) -> None:
        """Function returns a pandas DataFrame."""
        trades = [_make_enriched_trade()]
        result = export_trade_journal(trades, tmp_path / "trades.csv", F, S)
        assert isinstance(result, pd.DataFrame)


# ---------------------------------------------------------------------------
# Nominal — fees_paid formula
# ---------------------------------------------------------------------------


class TestFeesPaid:
    """AC2: fees_paid = f * (entry_price + exit_price) for each trade."""

    def test_fees_paid_single_trade(self, tmp_path: Path) -> None:
        entry_price, exit_price = 100.0, 110.0
        trades = [_make_enriched_trade(entry_price=entry_price, exit_price=exit_price)]
        df = export_trade_journal(trades, tmp_path / "trades.csv", F, S)
        expected = F * (entry_price + exit_price)
        assert df["fees_paid"].iloc[0] == pytest.approx(expected, rel=1e-12)

    def test_fees_paid_multiple_trades(self, tmp_path: Path) -> None:
        trade1 = _make_enriched_trade(entry_price=100.0, exit_price=105.0)
        trade2 = _make_enriched_trade(
            entry_price=200.0,
            exit_price=210.0,
            entry_time="2024-01-02 02:00",
            exit_time="2024-01-02 06:00",
        )
        df = export_trade_journal([trade1, trade2], tmp_path / "trades.csv", F, S)
        assert df["fees_paid"].iloc[0] == pytest.approx(F * (100.0 + 105.0), rel=1e-12)
        assert df["fees_paid"].iloc[1] == pytest.approx(F * (200.0 + 210.0), rel=1e-12)

    def test_fees_paid_zero_fee_rate(self, tmp_path: Path) -> None:
        """With f=0, fees_paid must be 0."""
        trades = [_make_enriched_trade(f=0.0, s=S)]
        df = export_trade_journal(trades, tmp_path / "trades.csv", 0.0, S)
        assert df["fees_paid"].iloc[0] == 0.0


# ---------------------------------------------------------------------------
# Nominal — slippage_paid formula
# ---------------------------------------------------------------------------


class TestSlippagePaid:
    """AC3: slippage_paid = s * (entry_price + exit_price) for each trade."""

    def test_slippage_paid_single_trade(self, tmp_path: Path) -> None:
        entry_price, exit_price = 100.0, 110.0
        trades = [_make_enriched_trade(entry_price=entry_price, exit_price=exit_price)]
        df = export_trade_journal(trades, tmp_path / "trades.csv", F, S)
        expected = S * (entry_price + exit_price)
        assert df["slippage_paid"].iloc[0] == pytest.approx(expected, rel=1e-12)

    def test_slippage_paid_multiple_trades(self, tmp_path: Path) -> None:
        trade1 = _make_enriched_trade(entry_price=100.0, exit_price=105.0)
        trade2 = _make_enriched_trade(
            entry_price=200.0,
            exit_price=210.0,
            entry_time="2024-01-02 02:00",
            exit_time="2024-01-02 06:00",
        )
        df = export_trade_journal([trade1, trade2], tmp_path / "trades.csv", F, S)
        assert df["slippage_paid"].iloc[0] == pytest.approx(S * (100.0 + 105.0), rel=1e-12)
        assert df["slippage_paid"].iloc[1] == pytest.approx(S * (200.0 + 210.0), rel=1e-12)

    def test_slippage_paid_zero_rate(self, tmp_path: Path) -> None:
        """With s=0, slippage_paid must be 0."""
        trades = [_make_enriched_trade(f=F, s=0.0)]
        df = export_trade_journal(trades, tmp_path / "trades.csv", F, 0.0)
        assert df["slippage_paid"].iloc[0] == 0.0


# ---------------------------------------------------------------------------
# Nominal — gross_return formula
# ---------------------------------------------------------------------------


class TestGrossReturn:
    """AC4: gross_return = (exit_price / entry_price) - 1 for each trade."""

    def test_gross_return_profit(self, tmp_path: Path) -> None:
        trades = [_make_enriched_trade(entry_price=100.0, exit_price=110.0)]
        df = export_trade_journal(trades, tmp_path / "trades.csv", F, S)
        expected = (110.0 / 100.0) - 1.0
        assert df["gross_return"].iloc[0] == pytest.approx(expected, rel=1e-12)

    def test_gross_return_loss(self, tmp_path: Path) -> None:
        trades = [_make_enriched_trade(entry_price=100.0, exit_price=90.0)]
        df = export_trade_journal(trades, tmp_path / "trades.csv", F, S)
        expected = (90.0 / 100.0) - 1.0
        assert df["gross_return"].iloc[0] == pytest.approx(expected, rel=1e-12)

    def test_gross_return_zero(self, tmp_path: Path) -> None:
        """Entry == exit → gross_return = 0."""
        trades = [_make_enriched_trade(entry_price=100.0, exit_price=100.0)]
        df = export_trade_journal(trades, tmp_path / "trades.csv", F, S)
        assert df["gross_return"].iloc[0] == pytest.approx(0.0, abs=1e-14)


# ---------------------------------------------------------------------------
# Nominal — net_return
# ---------------------------------------------------------------------------


class TestNetReturn:
    """AC5: net_return == r_net from the enriched trade dict."""

    def test_net_return_matches_r_net(self, tmp_path: Path) -> None:
        trade = _make_enriched_trade(entry_price=100.0, exit_price=110.0)
        df = export_trade_journal([trade], tmp_path / "trades.csv", F, S)
        assert df["net_return"].iloc[0] == pytest.approx(trade["r_net"], rel=1e-12)

    def test_net_return_less_than_gross_when_costs(self, tmp_path: Path) -> None:
        """With positive f and s, net_return < gross_return."""
        trades = [_make_enriched_trade(entry_price=100.0, exit_price=110.0)]
        df = export_trade_journal(trades, tmp_path / "trades.csv", F, S)
        assert df["net_return"].iloc[0] < df["gross_return"].iloc[0]


# ---------------------------------------------------------------------------
# Nominal — equity coherence
# ---------------------------------------------------------------------------


class TestEquityCoherence:
    """AC6: E_final == E_0 * prod(1 + w * r_net_i) at atol=1e-8."""

    def test_product_of_net_returns_equals_equity_ratio(self, tmp_path: Path) -> None:
        """Three trades → cumulative product matches final equity."""
        trades = [
            _make_enriched_trade(
                entry_price=100.0,
                exit_price=105.0,
                entry_time="2024-01-01 02:00",
                exit_time="2024-01-01 06:00",
            ),
            _make_enriched_trade(
                entry_price=105.0,
                exit_price=108.0,
                entry_time="2024-01-02 02:00",
                exit_time="2024-01-02 06:00",
            ),
            _make_enriched_trade(
                entry_price=108.0,
                exit_price=103.0,
                entry_time="2024-01-03 02:00",
                exit_time="2024-01-03 06:00",
            ),
        ]
        w = 1.0  # position_fraction
        initial_equity = 1.0

        df = export_trade_journal(trades, tmp_path / "trades.csv", F, S)

        # Reconstruct equity from journal net_return
        equity_final = initial_equity
        for r_net in df["net_return"]:
            equity_final *= 1 + w * r_net

        # Also compute from trade dicts directly
        expected_final = initial_equity
        for t in trades:
            expected_final *= 1 + w * t["r_net"]

        assert equity_final == pytest.approx(expected_final, abs=1e-8)


# ---------------------------------------------------------------------------
# Nominal — y_hat modes
# ---------------------------------------------------------------------------


class TestYHat:
    """AC7: y_hat = 1 for signal output_type, float for regression."""

    def test_y_hat_signal_mode_is_one(self, tmp_path: Path) -> None:
        """For signal-mode trades, caller sets y_hat=1; journal preserves it."""
        trade = _make_enriched_trade(y_hat=1.0)
        df = export_trade_journal([trade], tmp_path / "trades.csv", F, S)
        assert df["y_hat"].iloc[0] == 1.0

    def test_y_hat_regression_mode_is_float(self, tmp_path: Path) -> None:
        """For regression-mode trades, y_hat is a float log-return."""
        trade = _make_enriched_trade(y_hat=0.04879)
        df = export_trade_journal([trade], tmp_path / "trades.csv", F, S)
        assert df["y_hat"].iloc[0] == pytest.approx(0.04879, rel=1e-12)

    def test_y_true_preserved(self, tmp_path: Path) -> None:
        """y_true from trade dict must appear unchanged in the journal."""
        trade = _make_enriched_trade(y_true=0.09531)
        df = export_trade_journal([trade], tmp_path / "trades.csv", F, S)
        assert df["y_true"].iloc[0] == pytest.approx(0.09531, rel=1e-12)


# ---------------------------------------------------------------------------
# Edge — empty trades
# ---------------------------------------------------------------------------


class TestEmptyTrades:
    """AC8: 0 trades → CSV header only, no data rows."""

    def test_empty_list_produces_header_only(self, tmp_path: Path) -> None:
        path = tmp_path / "trades.csv"
        df = export_trade_journal([], path, F, S)
        assert len(df) == 0
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_empty_csv_file_is_parseable(self, tmp_path: Path) -> None:
        path = tmp_path / "trades.csv"
        export_trade_journal([], path, F, S)
        df_read = pd.read_csv(path)
        assert len(df_read) == 0
        assert list(df_read.columns) == EXPECTED_COLUMNS


# ---------------------------------------------------------------------------
# Nominal — multiple trades, CSV parseable
# ---------------------------------------------------------------------------


class TestMultipleTradesCsv:
    """AC9, AC10: multiple trades → parseable CSV with correct values."""

    def test_csv_parseable_with_correct_row_count(self, tmp_path: Path) -> None:
        trades = [
            _make_enriched_trade(
                entry_price=100.0,
                exit_price=105.0,
                entry_time="2024-01-01 02:00",
                exit_time="2024-01-01 06:00",
            ),
            _make_enriched_trade(
                entry_price=200.0,
                exit_price=195.0,
                entry_time="2024-01-02 02:00",
                exit_time="2024-01-02 06:00",
            ),
        ]
        path = tmp_path / "trades.csv"
        export_trade_journal(trades, path, F, S)
        df_read = pd.read_csv(path)
        assert len(df_read) == 2
        assert list(df_read.columns) == EXPECTED_COLUMNS

    def test_entry_exit_times_in_csv(self, tmp_path: Path) -> None:
        """Timestamps must be present and parseable in the CSV."""
        trade = _make_enriched_trade()
        path = tmp_path / "trades.csv"
        export_trade_journal([trade], path, F, S)
        df_read = pd.read_csv(path, parse_dates=["entry_time_utc", "exit_time_utc"])
        assert pd.api.types.is_datetime64_any_dtype(df_read["entry_time_utc"])
        assert pd.api.types.is_datetime64_any_dtype(df_read["exit_time_utc"])

    def test_f_and_s_columns_constant(self, tmp_path: Path) -> None:
        """f and s columns must be constant across all rows."""
        trades = [
            _make_enriched_trade(
                entry_time="2024-01-01 02:00",
                exit_time="2024-01-01 06:00",
            ),
            _make_enriched_trade(
                entry_time="2024-01-02 02:00",
                exit_time="2024-01-02 06:00",
            ),
        ]
        df = export_trade_journal(trades, tmp_path / "trades.csv", F, S)
        assert all(df["f"] == F)
        assert all(df["s"] == S)


# ---------------------------------------------------------------------------
# Error — missing required keys
# ---------------------------------------------------------------------------


class TestMissingKeys:
    """Missing required keys in trade dict must raise ValueError."""

    _REQUIRED_KEYS = [
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "entry_price_eff",
        "exit_price_eff",
        "r_net",
        "y_true",
        "y_hat",
    ]

    @pytest.mark.parametrize("missing_key", _REQUIRED_KEYS)
    def test_missing_key_raises(self, tmp_path: Path, missing_key: str) -> None:
        trade = _make_enriched_trade()
        del trade[missing_key]
        with pytest.raises(ValueError, match=missing_key):
            export_trade_journal([trade], tmp_path / "trades.csv", F, S)


# ---------------------------------------------------------------------------
# Error — invalid fee/slippage rates
# ---------------------------------------------------------------------------


class TestInvalidRates:
    """Fee and slippage rates must be in [0, 1)."""

    def test_negative_fee_rate_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="fee_rate_per_side"):
            export_trade_journal([], tmp_path / "t.csv", -0.001, S)

    def test_fee_rate_gte_one_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="fee_rate_per_side"):
            export_trade_journal([], tmp_path / "t.csv", 1.0, S)

    def test_negative_slippage_rate_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="slippage_rate_per_side"):
            export_trade_journal([], tmp_path / "t.csv", F, -0.001)

    def test_slippage_rate_gte_one_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="slippage_rate_per_side"):
            export_trade_journal([], tmp_path / "t.csv", F, 1.0)

    def test_nan_fee_rate_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="fee_rate_per_side"):
            export_trade_journal([], tmp_path / "t.csv", float("nan"), S)

    def test_nan_slippage_rate_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="slippage_rate_per_side"):
            export_trade_journal([], tmp_path / "t.csv", F, float("nan"))

    def test_inf_fee_rate_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="fee_rate_per_side"):
            export_trade_journal([], tmp_path / "t.csv", float("inf"), S)

    def test_inf_slippage_rate_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="slippage_rate_per_side"):
            export_trade_journal([], tmp_path / "t.csv", F, float("inf"))


# ---------------------------------------------------------------------------
# Error — entry_price <= 0
# ---------------------------------------------------------------------------


class TestEntryPriceValidation:
    """entry_price must be > 0 (gross_return computation requires it)."""

    def test_zero_entry_price_raises(self, tmp_path: Path) -> None:
        trade = _make_enriched_trade(entry_price=0.0, exit_price=100.0)
        # Force entry_price to 0 (helper computes derived fields with s)
        trade["entry_price"] = 0.0
        with pytest.raises(ValueError, match="entry_price"):
            export_trade_journal([trade], tmp_path / "t.csv", F, S)

    def test_negative_entry_price_raises(self, tmp_path: Path) -> None:
        trade = _make_enriched_trade()
        trade["entry_price"] = -10.0
        with pytest.raises(ValueError, match="entry_price"):
            export_trade_journal([trade], tmp_path / "t.csv", F, S)
