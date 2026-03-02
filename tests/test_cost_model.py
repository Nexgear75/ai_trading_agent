"""Tests for the transaction cost model — apply_cost_model.

Task #027 — WS-8.
Spec §12.3: per-side multiplicative cost model.
"""

from __future__ import annotations

import pytest

from ai_trading.backtest.costs import apply_cost_model

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trade(entry_price: float, exit_price: float) -> dict:
    """Return a minimal trade dict with required keys."""
    return {
        "signal_time": "2024-01-01T00:00:00",
        "entry_time": "2024-01-01T01:00:00",
        "exit_time": "2024-01-01T05:00:00",
        "entry_price": entry_price,
        "exit_price": exit_price,
    }


# ---------------------------------------------------------------------------
# Nominal — formula correctness
# ---------------------------------------------------------------------------

class TestFormulaCorrectness:
    """Verify §12.3 formulas are implemented exactly."""

    def test_entry_price_eff(self):
        """AC2: p_entry_eff = p_entry × (1 + s)."""
        trades = [_make_trade(100.0, 102.0)]
        s = 0.0003
        result = apply_cost_model(trades, fee_rate_per_side=0.001, slippage_rate_per_side=s)
        expected_entry_eff = 100.0 * (1 + s)
        assert result[0]["entry_price_eff"] == pytest.approx(expected_entry_eff, rel=1e-12)

    def test_exit_price_eff(self):
        """AC2: p_exit_eff = p_exit × (1 - s)."""
        trades = [_make_trade(100.0, 102.0)]
        s = 0.0003
        result = apply_cost_model(trades, fee_rate_per_side=0.001, slippage_rate_per_side=s)
        expected_exit_eff = 102.0 * (1 - s)
        assert result[0]["exit_price_eff"] == pytest.approx(expected_exit_eff, rel=1e-12)

    def test_m_net_formula(self):
        """AC1: M_net = (1 - f)² × (p_exit_eff / p_entry_eff)."""
        f = 0.001
        s = 0.0003
        trades = [_make_trade(100.0, 102.0)]
        result = apply_cost_model(trades, fee_rate_per_side=f, slippage_rate_per_side=s)
        p_entry_eff = 100.0 * (1 + s)
        p_exit_eff = 102.0 * (1 - s)
        expected_m_net = (1 - f) ** 2 * (p_exit_eff / p_entry_eff)
        assert result[0]["m_net"] == pytest.approx(expected_m_net, rel=1e-12)

    def test_r_net_formula(self):
        """AC3: r_net = M_net - 1."""
        f = 0.001
        s = 0.0003
        trades = [_make_trade(100.0, 102.0)]
        result = apply_cost_model(trades, fee_rate_per_side=f, slippage_rate_per_side=s)
        assert result[0]["r_net"] == pytest.approx(result[0]["m_net"] - 1, rel=1e-12)

    def test_numerical_hand_calculation(self):
        """AC4: f=0.001, s=0.0003, Open=100, Close=102 → r_net ≈ 0.0174.

        Hand calculation:
        p_entry_eff = 100 × 1.0003 = 100.03
        p_exit_eff  = 102 × 0.9997 = 101.9694
        M_net = (1 - 0.001)² × (101.9694 / 100.03)
              = 0.999001 × 1.019381...
              = ≈ 1.01838...
        r_net = M_net - 1 ≈ 0.01838...
        """
        f = 0.001
        s = 0.0003
        trades = [_make_trade(100.0, 102.0)]
        result = apply_cost_model(trades, fee_rate_per_side=f, slippage_rate_per_side=s)

        # Exact hand calculation
        p_entry_eff = 100.0 * (1 + 0.0003)
        p_exit_eff = 102.0 * (1 - 0.0003)
        m_net = (1 - 0.001) ** 2 * (p_exit_eff / p_entry_eff)
        r_net = m_net - 1

        assert result[0]["r_net"] == pytest.approx(r_net, rel=1e-10)
        # Sanity: r_net should be roughly ~0.017–0.019
        assert 0.017 < result[0]["r_net"] < 0.020

    def test_symmetric_slippage(self):
        """AC5: slippage applied on both buy and sell side."""
        s = 0.01  # Large slippage to make effect visible
        trades = [_make_trade(100.0, 100.0)]
        result = apply_cost_model(trades, fee_rate_per_side=0.0, slippage_rate_per_side=s)
        # Entry costs more, exit yields less → both hurt
        assert result[0]["entry_price_eff"] > 100.0
        assert result[0]["exit_price_eff"] < 100.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases from acceptance criteria."""

    def test_equal_entry_exit_negative_r_net(self):
        """AC7: p_entry == p_exit → r_net negative (costs only)."""
        f = 0.001
        s = 0.0003
        trades = [_make_trade(100.0, 100.0)]
        result = apply_cost_model(trades, fee_rate_per_side=f, slippage_rate_per_side=s)
        assert result[0]["r_net"] < 0

    def test_zero_costs_raw_return(self):
        """AC8: f=0, s=0 → r_net = (p_exit / p_entry) - 1."""
        trades = [_make_trade(100.0, 105.0)]
        result = apply_cost_model(trades, fee_rate_per_side=0.0, slippage_rate_per_side=0.0)
        expected = (105.0 / 100.0) - 1
        assert result[0]["r_net"] == pytest.approx(expected, rel=1e-12)
        assert result[0]["m_net"] == pytest.approx(105.0 / 100.0, rel=1e-12)
        assert result[0]["entry_price_eff"] == pytest.approx(100.0, rel=1e-12)
        assert result[0]["exit_price_eff"] == pytest.approx(105.0, rel=1e-12)

    def test_empty_trade_list(self):
        """Empty input → empty output."""
        result = apply_cost_model([], fee_rate_per_side=0.001, slippage_rate_per_side=0.0003)
        assert result == []

    def test_multiple_trades(self):
        """Multiple trades are all processed correctly."""
        trades = [
            _make_trade(100.0, 105.0),
            _make_trade(200.0, 210.0),
            _make_trade(50.0, 48.0),
        ]
        f = 0.0005
        s = 0.00025
        result = apply_cost_model(trades, fee_rate_per_side=f, slippage_rate_per_side=s)
        assert len(result) == 3
        for r in result:
            assert "entry_price_eff" in r
            assert "exit_price_eff" in r
            assert "m_net" in r
            assert "r_net" in r

    def test_original_keys_preserved(self):
        """Output trades preserve all original keys."""
        trade = _make_trade(100.0, 102.0)
        result = apply_cost_model([trade], fee_rate_per_side=0.001, slippage_rate_per_side=0.0003)
        for key in ("signal_time", "entry_time", "exit_time", "entry_price", "exit_price"):
            assert key in result[0]
            assert result[0][key] == trade[key]

    def test_losing_trade_with_costs(self):
        """Losing trade (exit < entry) yields large negative r_net."""
        f = 0.001
        s = 0.0003
        trades = [_make_trade(100.0, 95.0)]
        result = apply_cost_model(trades, fee_rate_per_side=f, slippage_rate_per_side=s)
        assert result[0]["r_net"] < -0.05  # ~5% loss + costs


# ---------------------------------------------------------------------------
# Validation / error cases
# ---------------------------------------------------------------------------

class TestValidation:
    """Input validation — strict code, no fallbacks."""

    def test_negative_fee_rate_raises(self):
        """Negative fee_rate_per_side raises ValueError."""
        trades = [_make_trade(100.0, 102.0)]
        with pytest.raises(ValueError, match="fee_rate_per_side"):
            apply_cost_model(trades, fee_rate_per_side=-0.001, slippage_rate_per_side=0.0)

    def test_fee_rate_ge_one_raises(self):
        """fee_rate_per_side >= 1 raises ValueError (nonsensical fee)."""
        trades = [_make_trade(100.0, 102.0)]
        with pytest.raises(ValueError, match="fee_rate_per_side"):
            apply_cost_model(trades, fee_rate_per_side=1.0, slippage_rate_per_side=0.0)

    def test_fee_rate_above_one_raises(self):
        """fee_rate_per_side > 1 raises ValueError."""
        trades = [_make_trade(100.0, 102.0)]
        with pytest.raises(ValueError, match="fee_rate_per_side"):
            apply_cost_model(trades, fee_rate_per_side=2.0, slippage_rate_per_side=0.0)

    def test_negative_slippage_rate_raises(self):
        """Negative slippage_rate_per_side raises ValueError."""
        trades = [_make_trade(100.0, 102.0)]
        with pytest.raises(ValueError, match="slippage_rate_per_side"):
            apply_cost_model(trades, fee_rate_per_side=0.0, slippage_rate_per_side=-0.001)

    def test_slippage_rate_ge_one_raises(self):
        """slippage_rate_per_side >= 1 raises ValueError (nonsensical slippage)."""
        trades = [_make_trade(100.0, 102.0)]
        with pytest.raises(ValueError, match="slippage_rate_per_side"):
            apply_cost_model(trades, fee_rate_per_side=0.0, slippage_rate_per_side=1.0)

    def test_slippage_rate_above_one_raises(self):
        """slippage_rate_per_side > 1 raises ValueError."""
        trades = [_make_trade(100.0, 102.0)]
        with pytest.raises(ValueError, match="slippage_rate_per_side"):
            apply_cost_model(trades, fee_rate_per_side=0.0, slippage_rate_per_side=1.5)

    def test_missing_entry_price_key_raises(self):
        """Trade missing 'entry_price' key raises ValueError."""
        trade = {"exit_price": 102.0, "signal_time": "x", "entry_time": "x", "exit_time": "x"}
        with pytest.raises(ValueError, match="entry_price"):
            apply_cost_model([trade], fee_rate_per_side=0.001, slippage_rate_per_side=0.0003)

    def test_missing_exit_price_key_raises(self):
        """Trade missing 'exit_price' key raises ValueError."""
        trade = {"entry_price": 100.0, "signal_time": "x", "entry_time": "x", "exit_time": "x"}
        with pytest.raises(ValueError, match="exit_price"):
            apply_cost_model([trade], fee_rate_per_side=0.001, slippage_rate_per_side=0.0003)

    def test_zero_entry_price_raises(self):
        """entry_price == 0 raises ValueError (division by zero)."""
        trades = [_make_trade(0.0, 102.0)]
        with pytest.raises(ValueError, match="entry_price"):
            apply_cost_model(trades, fee_rate_per_side=0.001, slippage_rate_per_side=0.0003)

    def test_negative_entry_price_raises(self):
        """Negative entry_price raises ValueError."""
        trades = [_make_trade(-100.0, 102.0)]
        with pytest.raises(ValueError, match="entry_price"):
            apply_cost_model(trades, fee_rate_per_side=0.001, slippage_rate_per_side=0.0003)
