"""Tests for scripts/dashboard/pages/run_detail_logic.py — header and KPI cards.

Task #080 — WS-D-3: Page 2 — en-tête du run et KPI cards.
Spec refs: §6.1 en-tête du run, §6.2 métriques agrégées, §9.3 conventions.

Tests cover:
- build_header_info: construction from manifest, config_snapshot, metrics
- build_kpi_cards: construction from metrics + folds + config
- Sharpe label conditional on sharpe_annualized config
- n_contributing calculation per metric
- Null handling (all nulls → "—")
- Missing/no run selected scenario
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers — synthetic data fixtures
# ---------------------------------------------------------------------------


def _make_manifest(
    *,
    run_id: str = "20260301_120000_xgboost",
    created_at_utc: str = "2026-03-01T12:00:00Z",
    strategy_name: str = "xgboost_reg",
    strategy_type: str = "model",
    framework: str = "xgboost",
    symbols: list[str] | None = None,
    timeframe: str = "1h",
    start: str = "2017-08-17",
    end: str = "2026-01-01",
    global_seed: int = 42,
) -> dict:
    """Build a minimal valid manifest dict."""
    if symbols is None:
        symbols = ["BTCUSDT"]
    return {
        "run_id": run_id,
        "created_at_utc": created_at_utc,
        "config_snapshot": {
            "dataset": {
                "symbols": symbols,
                "timeframe": timeframe,
                "start": start,
                "end": end,
            },
            "reproducibility": {
                "global_seed": global_seed,
            },
        },
        "strategy": {
            "strategy_type": strategy_type,
            "name": strategy_name,
            "framework": framework,
        },
        "dataset": {
            "symbols": symbols,
            "timeframe": timeframe,
            "start": start,
            "end": end,
        },
    }


def _make_config_snapshot(
    *,
    sharpe_annualized: bool = False,
) -> dict:
    """Build a minimal config_snapshot dict."""
    return {
        "metrics": {
            "sharpe_annualized": sharpe_annualized,
        },
    }


def _make_metrics(
    *,
    n_folds: int = 3,
    net_pnl: list[float | None] | None = None,
    sharpe: list[float | None] | None = None,
    max_drawdown: list[float | None] | None = None,
    hit_rate: list[float | None] | None = None,
    profit_factor: list[float | None] | None = None,
    n_trades: list[int | None] | None = None,
) -> dict:
    """Build a minimal valid metrics dict with per-fold trading data."""
    if net_pnl is None:
        net_pnl = [0.05, -0.02, 0.03]
    if sharpe is None:
        sharpe = [1.5, 0.8, 1.2]
    if max_drawdown is None:
        max_drawdown = [0.05, 0.12, 0.08]
    if hit_rate is None:
        hit_rate = [0.56, 0.48, 0.52]
    if profit_factor is None:
        profit_factor = [1.3, 0.9, 1.1]
    if n_trades is None:
        n_trades = [20, 15, 25]

    folds = []
    for i in range(n_folds):
        fold = {
            "fold_id": i,
            "trading": {
                "net_pnl": net_pnl[i] if i < len(net_pnl) else None,
                "sharpe": sharpe[i] if i < len(sharpe) else None,
                "max_drawdown": max_drawdown[i] if i < len(max_drawdown) else None,
                "hit_rate": hit_rate[i] if i < len(hit_rate) else None,
                "profit_factor": profit_factor[i] if i < len(profit_factor) else None,
                "n_trades": n_trades[i] if i < len(n_trades) else None,
            },
        }
        folds.append(fold)

    return {
        "run_id": "20260301_120000_xgboost",
        "strategy": {"name": "xgboost_reg", "strategy_type": "model"},
        "folds": folds,
        "aggregate": {
            "trading": {
                "mean": {
                    "net_pnl": 0.02,
                    "sharpe": 1.17,
                    "max_drawdown": 0.083,
                    "hit_rate": 0.52,
                    "profit_factor": 1.1,
                    "n_trades": 20.0,
                },
                "std": {
                    "net_pnl": 0.036,
                    "sharpe": 0.35,
                    "max_drawdown": 0.035,
                    "hit_rate": 0.04,
                    "profit_factor": 0.2,
                    "n_trades": 5.0,
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# §6.1 — build_header_info
# ---------------------------------------------------------------------------


class TestBuildHeaderInfo:
    """#080 — Build header info dict from manifest (§6.1)."""

    def test_nominal_all_fields(self) -> None:
        """#080 — Header contains all expected fields from §6.1."""
        from scripts.dashboard.pages.run_detail_logic import build_header_info

        manifest = _make_manifest()
        n_folds = 3
        header = build_header_info(manifest, n_folds)

        assert header["run_id"] == "20260301_120000_xgboost"
        assert header["date"] == "2026-03-01 12:00 UTC"
        assert header["strategy"] == "xgboost_reg"
        assert header["framework"] == "xgboost"
        assert header["symbol"] == "BTCUSDT"
        assert header["timeframe"] == "1h"
        assert header["period"] == "2017-08-17 — 2026-01-01 (excl.)"
        assert header["seed"] == 42
        assert header["n_folds"] == 3

    def test_multiple_symbols_joined(self) -> None:
        """#080 — Multiple symbols are joined with ', '."""
        from scripts.dashboard.pages.run_detail_logic import build_header_info

        manifest = _make_manifest(symbols=["BTCUSDT", "ETHUSDT"])
        header = build_header_info(manifest, n_folds=2)
        assert header["symbol"] == "BTCUSDT, ETHUSDT"

    def test_date_format_utc_suffix(self) -> None:
        """#080 — Date formatted as 'YYYY-MM-DD HH:MM UTC'."""
        from scripts.dashboard.pages.run_detail_logic import build_header_info

        manifest = _make_manifest(created_at_utc="2026-01-15T09:30:45Z")
        header = build_header_info(manifest, n_folds=1)
        assert header["date"] == "2026-01-15 09:30 UTC"

    def test_period_excl_suffix(self) -> None:
        """#080 — Period end has '(excl.)' suffix (§6.1)."""
        from scripts.dashboard.pages.run_detail_logic import build_header_info

        manifest = _make_manifest(start="2020-01-01", end="2025-12-31")
        header = build_header_info(manifest, n_folds=1)
        assert "(excl.)" in header["period"]
        assert header["period"] == "2020-01-01 — 2025-12-31 (excl.)"

    def test_framework_missing_key(self) -> None:
        """#080 — Framework is None if key absent from manifest."""
        from scripts.dashboard.pages.run_detail_logic import build_header_info

        manifest = _make_manifest()
        del manifest["strategy"]["framework"]
        header = build_header_info(manifest, n_folds=1)
        assert header["framework"] is None

    def test_seed_from_config_snapshot(self) -> None:
        """#080 — Seed is read from manifest.config_snapshot.reproducibility."""
        from scripts.dashboard.pages.run_detail_logic import build_header_info

        manifest = _make_manifest(global_seed=123)
        header = build_header_info(manifest, n_folds=1)
        assert header["seed"] == 123


# ---------------------------------------------------------------------------
# §6.2 — build_kpi_cards
# ---------------------------------------------------------------------------


class TestBuildKpiCards:
    """#080 — Build KPI card data from metrics and config (§6.2)."""

    def test_nominal_six_cards(self) -> None:
        """#080 — Returns exactly 6 KPI card dicts."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics()
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        assert len(cards) == 6

    def test_card_keys(self) -> None:
        """#080 — Each card has label, value, color keys."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics()
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        for card in cards:
            assert "label" in card
            assert "value" in card
            assert "color" in card

    def test_card_labels_order(self) -> None:
        """#080 — Cards are in spec order: PnL, Sharpe, MDD, Hit, PF, Trades."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics()
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        labels = [c["label"] for c in cards]
        assert labels[0] == "Net PnL"
        assert "Sharpe" in labels[1]
        assert labels[2] == "Max Drawdown"
        assert labels[3] == "Hit Rate"
        assert labels[4] == "Profit Factor"
        assert labels[5] == "Nombre de trades"

    def test_sharpe_label_not_annualized(self) -> None:
        """#080 — Sharpe label is 'Sharpe Ratio' when not annualized."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics()
        config = _make_config_snapshot(sharpe_annualized=False)
        cards = build_kpi_cards(metrics, config)
        assert cards[1]["label"] == "Sharpe Ratio"

    def test_sharpe_label_annualized(self) -> None:
        """#080 — Sharpe label is 'Sharpe Ratio (annualisé)' when annualized."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics()
        config = _make_config_snapshot(sharpe_annualized=True)
        cards = build_kpi_cards(metrics, config)
        assert cards[1]["label"] == "Sharpe Ratio (annualisé)"

    def test_pnl_color_positive(self) -> None:
        """#080 — PnL card uses profit color when mean > 0."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards
        from scripts.dashboard.utils import COLOR_PROFIT

        metrics = _make_metrics(net_pnl=[0.05, 0.02, 0.03])
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        assert cards[0]["color"] == COLOR_PROFIT

    def test_pnl_color_negative(self) -> None:
        """#080 — PnL card uses loss color when mean <= 0."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards
        from scripts.dashboard.utils import COLOR_LOSS

        metrics = _make_metrics(net_pnl=[-0.05, -0.02, -0.03])
        config = _make_config_snapshot()
        # Override aggregate mean to match
        metrics["aggregate"]["trading"]["mean"]["net_pnl"] = -0.033
        cards = build_kpi_cards(metrics, config)
        assert cards[0]["color"] == COLOR_LOSS

    def test_n_contributing_all_folds(self) -> None:
        """#080 — No fold count shown when all folds contribute."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics(
            n_folds=3,
            sharpe=[1.5, 0.8, 1.2],
        )
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        # Sharpe card should not have "(X/Y folds)"
        assert "folds" not in cards[1]["value"]

    def test_n_contributing_partial_folds(self) -> None:
        """#080 — Fold count shown when some folds have null (§6.2)."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics(
            n_folds=3,
            profit_factor=[1.3, None, 1.1],
        )
        # Recalculate aggregate for profit_factor (2 non-null folds)
        metrics["aggregate"]["trading"]["mean"]["profit_factor"] = 1.2
        metrics["aggregate"]["trading"]["std"]["profit_factor"] = 0.1
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        # Profit Factor card should show (2/3 folds)
        pf_card = cards[4]
        assert "(2/3 folds)" in pf_card["value"]

    def test_all_null_displays_em_dash(self) -> None:
        """#080 — All folds null for a metric → '—' (§6.2, §9.3)."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics(
            n_folds=3,
            sharpe=[None, None, None],
        )
        metrics["aggregate"]["trading"]["mean"]["sharpe"] = None
        metrics["aggregate"]["trading"]["std"]["sharpe"] = None
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        assert cards[1]["value"] == "—"

    def test_n_trades_format_integer(self) -> None:
        """#080 — Nombre de trades uses integer format."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics(n_trades=[20, 15, 25])
        metrics["aggregate"]["trading"]["mean"]["n_trades"] = 20.0
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        trades_card = cards[5]
        # Should format as integer (no decimals, no ± std)
        assert "20" in trades_card["value"]

    def test_hit_rate_one_decimal(self) -> None:
        """#080 — Hit Rate format uses 1 decimal (§9.3)."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics(hit_rate=[0.556, 0.521, 0.544])
        metrics["aggregate"]["trading"]["mean"]["hit_rate"] = 0.5403
        metrics["aggregate"]["trading"]["std"]["hit_rate"] = 0.0175
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        hr_card = cards[3]
        # Check 1-decimal pct format (54.0%)
        assert "54.0%" in hr_card["value"]

    def test_std_none_with_mean_raises(self) -> None:
        """#080 — ValueError if mean is not None but std is None (§R1)."""
        import pytest

        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics()
        metrics["aggregate"]["trading"]["mean"]["net_pnl"] = 0.05
        metrics["aggregate"]["trading"]["std"]["net_pnl"] = None
        config = _make_config_snapshot()
        with pytest.raises(ValueError, match="mean is not None but std is None"):
            build_kpi_cards(metrics, config)

    def test_config_missing_metrics_key_raises(self) -> None:
        """#080 — KeyError if config_snapshot lacks 'metrics' key (§R1)."""
        import pytest

        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics()
        config_bad: dict = {}
        with pytest.raises(KeyError):
            build_kpi_cards(metrics, config_bad)

    def test_config_missing_sharpe_annualized_raises(self) -> None:
        """#080 — KeyError if config_snapshot['metrics'] lacks 'sharpe_annualized' (§R1)."""
        import pytest

        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics()
        config_bad = {"metrics": {}}
        with pytest.raises(KeyError):
            build_kpi_cards(metrics, config_bad)


# ---------------------------------------------------------------------------
# §6.2 — count_non_null_folds
# ---------------------------------------------------------------------------


class TestCountNonNullFolds:
    """#080 — count_non_null_folds utility."""

    def test_all_non_null(self) -> None:
        """#080 — All folds have value → count == n_folds."""
        from scripts.dashboard.pages.run_detail_logic import count_non_null_folds

        folds = [
            {"trading": {"sharpe": 1.0}},
            {"trading": {"sharpe": 0.5}},
        ]
        assert count_non_null_folds(folds, "sharpe") == 2

    def test_some_null(self) -> None:
        """#080 — Null folds not counted."""
        from scripts.dashboard.pages.run_detail_logic import count_non_null_folds

        folds = [
            {"trading": {"profit_factor": 1.3}},
            {"trading": {"profit_factor": None}},
            {"trading": {"profit_factor": 1.1}},
        ]
        assert count_non_null_folds(folds, "profit_factor") == 2

    def test_all_null(self) -> None:
        """#080 — All null → count == 0."""
        from scripts.dashboard.pages.run_detail_logic import count_non_null_folds

        folds = [
            {"trading": {"sharpe": None}},
            {"trading": {"sharpe": None}},
        ]
        assert count_non_null_folds(folds, "sharpe") == 0

    def test_empty_folds(self) -> None:
        """#080 — Empty folds list → count == 0."""
        from scripts.dashboard.pages.run_detail_logic import count_non_null_folds

        assert count_non_null_folds([], "sharpe") == 0

    def test_missing_trading_key(self) -> None:
        """#080 — Fold without 'trading' key → treated as null."""
        from scripts.dashboard.pages.run_detail_logic import count_non_null_folds

        folds = [
            {"trading": {"sharpe": 1.0}},
            {"prediction": {"mae": 0.01}},
        ]
        assert count_non_null_folds(folds, "sharpe") == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """#080 — Edge cases and error handling."""

    def test_single_fold(self) -> None:
        """#080 — Single fold produces valid cards."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics(
            n_folds=1,
            net_pnl=[0.05],
            sharpe=[1.5],
            max_drawdown=[0.03],
            hit_rate=[0.55],
            profit_factor=[1.2],
            n_trades=[10],
        )
        metrics["aggregate"]["trading"]["mean"]["n_trades"] = 10.0
        metrics["aggregate"]["trading"]["std"]["n_trades"] = 0.0
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        assert len(cards) == 6

    def test_zero_trades_fold(self) -> None:
        """#080 — Fold with 0 trades and null metrics handled."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards

        metrics = _make_metrics(
            n_folds=2,
            net_pnl=[0.0, 0.05],
            sharpe=[None, 1.2],
            max_drawdown=[0.0, 0.05],
            hit_rate=[None, 0.55],
            profit_factor=[None, 1.3],
            n_trades=[0, 20],
        )
        metrics["aggregate"]["trading"]["mean"]["sharpe"] = 1.2
        metrics["aggregate"]["trading"]["std"]["sharpe"] = 0.0
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        # Sharpe should show (1/2 folds)
        assert "(1/2 folds)" in cards[1]["value"]

    def test_mdd_color_thresholds(self) -> None:
        """#080 — MDD color follows spec thresholds."""
        from scripts.dashboard.pages.run_detail_logic import build_kpi_cards
        from scripts.dashboard.utils import COLOR_LOSS, COLOR_PROFIT, COLOR_WARNING

        # MDD < 10% → green
        metrics = _make_metrics()
        metrics["aggregate"]["trading"]["mean"]["max_drawdown"] = 0.05
        config = _make_config_snapshot()
        cards = build_kpi_cards(metrics, config)
        assert cards[2]["color"] == COLOR_PROFIT

        # MDD 10-25% → orange
        metrics["aggregate"]["trading"]["mean"]["max_drawdown"] = 0.15
        cards = build_kpi_cards(metrics, config)
        assert cards[2]["color"] == COLOR_WARNING

        # MDD >= 25% → red
        metrics["aggregate"]["trading"]["mean"]["max_drawdown"] = 0.30
        cards = build_kpi_cards(metrics, config)
        assert cards[2]["color"] == COLOR_LOSS

    def test_single_symbol_no_comma(self) -> None:
        """#080 — Single symbol has no trailing comma."""
        from scripts.dashboard.pages.run_detail_logic import build_header_info

        manifest = _make_manifest(symbols=["BTCUSDT"])
        header = build_header_info(manifest, n_folds=1)
        assert "," not in header["symbol"]
