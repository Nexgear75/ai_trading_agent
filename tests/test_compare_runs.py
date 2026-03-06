"""Tests for scripts/compare_runs.py — inter-strategy comparison script.

Task #052 — WS-12.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers — synthetic metrics.json builders
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _make_metrics(
    *,
    run_id: str,
    strategy_type: str,
    name: str,
    net_pnl_mean: float,
    max_drawdown_mean: float,
    sharpe_mean: float = 1.0,
    comparison_type: str | None = None,
) -> dict:
    """Build a minimal valid metrics.json dict for testing."""
    aggregate: dict = {
        "prediction": {
            "mean": {"mae": 0.01, "rmse": 0.02, "directional_accuracy": 0.55},
            "std": {"mae": 0.001, "rmse": 0.002, "directional_accuracy": 0.03},
        },
        "trading": {
            "mean": {
                "net_pnl": net_pnl_mean,
                "net_return": 0.05,
                "max_drawdown": max_drawdown_mean,
                "sharpe": sharpe_mean,
                "profit_factor": 1.5,
                "n_trades": 10,
            },
            "std": {
                "net_pnl": 10.0,
                "net_return": 0.01,
                "max_drawdown": 0.02,
                "sharpe": 0.3,
                "profit_factor": 0.2,
                "n_trades": 2,
            },
        },
    }
    if comparison_type is not None:
        aggregate["comparison_type"] = comparison_type

    return {
        "run_id": run_id,
        "strategy": {
            "strategy_type": strategy_type,
            "name": name,
        },
        "folds": [
            {
                "fold_id": 0,
                "period_test": {
                    "start_utc": "2024-01-01T00:00:00Z",
                    "end_utc": "2024-02-01T00:00:00Z",
                },
                "threshold": {"method": "quantile_grid", "theta": 0.5},
                "prediction": {"mae": 0.01, "rmse": 0.02, "directional_accuracy": 0.55},
                "n_samples_train": 500,
                "n_samples_val": 100,
                "n_samples_test": 100,
                "trading": {
                    "net_pnl": net_pnl_mean,
                    "net_return": 0.05,
                    "max_drawdown": max_drawdown_mean,
                    "sharpe": sharpe_mean,
                    "profit_factor": 1.5,
                    "n_trades": 10,
                },
            }
        ],
        "aggregate": aggregate,
    }


def _write_metrics(path: Path, metrics: dict) -> Path:
    """Write metrics dict to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def run_dirs(tmp_path: Path) -> dict[str, Path]:
    """Create synthetic run directories with metrics.json files.

    Returns a dict mapping strategy name to the metrics.json path.
    """
    strategies = {
        "lstm": _make_metrics(
            run_id="run_lstm",
            strategy_type="model",
            name="lstm",
            net_pnl_mean=150.0,
            max_drawdown_mean=0.10,
            sharpe_mean=1.8,
            comparison_type="go_nogo",
        ),
        "xgboost": _make_metrics(
            run_id="run_xgboost",
            strategy_type="model",
            name="xgboost",
            net_pnl_mean=80.0,
            max_drawdown_mean=0.15,
            sharpe_mean=1.2,
            comparison_type="go_nogo",
        ),
        "sma_rule": _make_metrics(
            run_id="run_sma",
            strategy_type="baseline",
            name="sma_rule",
            net_pnl_mean=50.0,
            max_drawdown_mean=0.12,
            sharpe_mean=0.9,
            comparison_type="go_nogo",
        ),
        "no_trade": _make_metrics(
            run_id="run_notrade",
            strategy_type="baseline",
            name="no_trade",
            net_pnl_mean=0.0,
            max_drawdown_mean=0.0,
            sharpe_mean=0.0,
            comparison_type="go_nogo",
        ),
        "buy_hold": _make_metrics(
            run_id="run_buyhold",
            strategy_type="baseline",
            name="buy_hold",
            net_pnl_mean=200.0,
            max_drawdown_mean=0.20,
            sharpe_mean=1.0,
            comparison_type="contextual",
        ),
    }
    paths: dict[str, Path] = {}
    for name, metrics in strategies.items():
        p = tmp_path / f"run_{name}" / "metrics.json"
        _write_metrics(p, metrics)
        paths[name] = p
    return paths


# ---------------------------------------------------------------------------
# Tests — load_metrics
# ---------------------------------------------------------------------------


class TestLoadMetrics:
    """Tests for load_metrics function."""

    def test_load_single_file(self, run_dirs: dict[str, Path]) -> None:
        """#052 — load_metrics loads a single metrics.json correctly."""
        from scripts.compare_runs import load_metrics

        result = load_metrics([run_dirs["lstm"]])
        assert len(result) == 1
        assert result[0]["run_id"] == "run_lstm"
        assert result[0]["strategy"]["name"] == "lstm"

    def test_load_multiple_files(self, run_dirs: dict[str, Path]) -> None:
        """#052 — load_metrics loads multiple metrics.json files."""
        from scripts.compare_runs import load_metrics

        paths = [run_dirs["lstm"], run_dirs["xgboost"], run_dirs["sma_rule"]]
        result = load_metrics(paths)
        assert len(result) == 3
        names = {m["strategy"]["name"] for m in result}
        assert names == {"lstm", "xgboost", "sma_rule"}

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        """#052 — load_metrics raises FileNotFoundError for missing file."""
        from scripts.compare_runs import load_metrics

        missing = tmp_path / "nonexistent" / "metrics.json"
        with pytest.raises(FileNotFoundError):
            load_metrics([missing])

    def test_load_invalid_json_raises(self, tmp_path: Path) -> None:
        """#052 — load_metrics raises ValueError for invalid JSON."""
        from scripts.compare_runs import load_metrics

        bad_file = tmp_path / "bad_run" / "metrics.json"
        bad_file.parent.mkdir(parents=True)
        bad_file.write_text("not valid json {{{", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            load_metrics([bad_file])

    def test_load_missing_required_keys_raises(self, tmp_path: Path) -> None:
        """#052 — load_metrics raises ValueError if metrics.json misses required keys."""
        from scripts.compare_runs import load_metrics

        incomplete = tmp_path / "incomplete" / "metrics.json"
        incomplete.parent.mkdir(parents=True)
        incomplete.write_text(
            json.dumps({"run_id": "x"}), encoding="utf-8"
        )
        with pytest.raises(ValueError, match="required"):
            load_metrics([incomplete])

    def test_load_empty_list_raises(self) -> None:
        """#052 — load_metrics raises ValueError for empty paths list."""
        from scripts.compare_runs import load_metrics

        with pytest.raises(ValueError, match="at least one"):
            load_metrics([])

    def test_load_missing_aggregate_trading_mean_raises(self, tmp_path: Path) -> None:
        """#052 — load_metrics raises ValueError when aggregate.trading.mean is missing."""
        from scripts.compare_runs import load_metrics

        # Missing 'trading' in aggregate
        bad = {
            "run_id": "x",
            "strategy": {"strategy_type": "model", "name": "lstm"},
            "aggregate": {},
        }
        p = tmp_path / "bad" / "metrics.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError, match="trading"):
            load_metrics([p])

    def test_load_missing_trading_mean_raises(self, tmp_path: Path) -> None:
        """#052 — load_metrics raises ValueError when aggregate.trading has no 'mean'."""
        from scripts.compare_runs import load_metrics

        bad = {
            "run_id": "x",
            "strategy": {"strategy_type": "model", "name": "lstm"},
            "aggregate": {"trading": {}},
        }
        p = tmp_path / "bad2" / "metrics.json"
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(ValueError, match="mean"):
            load_metrics([p])


# ---------------------------------------------------------------------------
# Tests — compare_strategies
# ---------------------------------------------------------------------------


class TestCompareStrategies:
    """Tests for compare_strategies function."""

    def test_comparison_returns_dataframe(self, run_dirs: dict[str, Path]) -> None:
        """#052 — compare_strategies returns a DataFrame with expected columns."""
        from scripts.compare_runs import compare_strategies, load_metrics

        metrics_list = load_metrics(list(run_dirs.values()))
        df = compare_strategies(metrics_list)
        assert isinstance(df, pd.DataFrame)
        assert "strategy_name" in df.columns
        assert "strategy_type" in df.columns
        assert "net_pnl_mean" in df.columns
        assert "max_drawdown_mean" in df.columns
        assert "sharpe_mean" in df.columns

    def test_go_nogo_and_contextual_separated(self, run_dirs: dict[str, Path]) -> None:
        """#052 — comparison separates go_nogo and contextual strategies."""
        from scripts.compare_runs import compare_strategies, load_metrics

        metrics_list = load_metrics(list(run_dirs.values()))
        df = compare_strategies(metrics_list)
        assert "comparison_type" in df.columns
        types = set(df["comparison_type"].unique())
        assert "go_nogo" in types
        assert "contextual" in types

    def test_identifies_best_strategy(self, run_dirs: dict[str, Path]) -> None:
        """#052 — Within go_nogo, identifies best strategy by net_pnl_mean."""
        from scripts.compare_runs import compare_strategies, load_metrics

        metrics_list = load_metrics(list(run_dirs.values()))
        df = compare_strategies(metrics_list)
        go_nogo = df[df["comparison_type"] == "go_nogo"]
        best = go_nogo.loc[go_nogo["net_pnl_mean"].idxmax()]
        assert str(best["strategy_name"]) == "lstm"

    def test_all_strategies_present(self, run_dirs: dict[str, Path]) -> None:
        """#052 — All loaded strategies appear in the comparison table."""
        from scripts.compare_runs import compare_strategies, load_metrics

        metrics_list = load_metrics(list(run_dirs.values()))
        df = compare_strategies(metrics_list)
        assert len(df) == 5
        expected_names = {"lstm", "xgboost", "sma_rule", "no_trade", "buy_hold"}
        assert set(df["strategy_name"]) == expected_names

    def test_comparison_with_only_go_nogo(self, tmp_path: Path) -> None:
        """#052 — Works when only go_nogo strategies are provided (no buy_hold)."""
        from scripts.compare_runs import compare_strategies, load_metrics

        m1 = _make_metrics(
            run_id="r1", strategy_type="model", name="lstm",
            net_pnl_mean=100.0, max_drawdown_mean=0.10,
            comparison_type="go_nogo",
        )
        m2 = _make_metrics(
            run_id="r2", strategy_type="baseline", name="no_trade",
            net_pnl_mean=0.0, max_drawdown_mean=0.0,
            comparison_type="go_nogo",
        )
        p1 = _write_metrics(tmp_path / "r1" / "metrics.json", m1)
        p2 = _write_metrics(tmp_path / "r2" / "metrics.json", m2)
        metrics_list = load_metrics([p1, p2])
        df = compare_strategies(metrics_list)
        assert len(df) == 2
        assert set(df["comparison_type"].unique()) == {"go_nogo"}

    def test_comparison_type_derived_from_name(self, tmp_path: Path) -> None:
        """#052 — When comparison_type is absent, it is derived from strategy name."""
        from scripts.compare_runs import compare_strategies, load_metrics

        m1 = _make_metrics(
            run_id="r1", strategy_type="model", name="gru",
            net_pnl_mean=100.0, max_drawdown_mean=0.10,
        )
        m2 = _make_metrics(
            run_id="r2", strategy_type="baseline", name="buy_hold",
            net_pnl_mean=200.0, max_drawdown_mean=0.20,
        )
        p1 = _write_metrics(tmp_path / "r1" / "metrics.json", m1)
        p2 = _write_metrics(tmp_path / "r2" / "metrics.json", m2)
        metrics_list = load_metrics([p1, p2])
        df = compare_strategies(metrics_list)
        gru_row = df[df["strategy_name"] == "gru"].iloc[0]
        bh_row = df[df["strategy_name"] == "buy_hold"].iloc[0]
        assert gru_row["comparison_type"] == "go_nogo"
        assert bh_row["comparison_type"] == "contextual"


# ---------------------------------------------------------------------------
# Tests — check_criterion_14_4
# ---------------------------------------------------------------------------


class TestCheckCriterion144:
    """Tests for check_criterion_14_4 function (§14.4 spec)."""

    def test_model_beats_baseline_returns_true(self, run_dirs: dict[str, Path]) -> None:
        """#052 — Returns True when best model beats at least one baseline."""
        from scripts.compare_runs import (
            check_criterion_14_4,
            compare_strategies,
            load_metrics,
        )

        metrics_list = load_metrics(list(run_dirs.values()))
        df = compare_strategies(metrics_list)
        assert check_criterion_14_4(df) is True

    def test_model_worse_than_all_baselines_returns_false(self, tmp_path: Path) -> None:
        """#052 — Returns False when no model beats any baseline."""
        from scripts.compare_runs import (
            check_criterion_14_4,
            compare_strategies,
            load_metrics,
        )

        m_model = _make_metrics(
            run_id="r1", strategy_type="model", name="bad_model",
            net_pnl_mean=-50.0, max_drawdown_mean=0.30,
            comparison_type="go_nogo",
        )
        m_baseline = _make_metrics(
            run_id="r2", strategy_type="baseline", name="sma_rule",
            net_pnl_mean=50.0, max_drawdown_mean=0.05,
            comparison_type="go_nogo",
        )
        p1 = _write_metrics(tmp_path / "r1" / "metrics.json", m_model)
        p2 = _write_metrics(tmp_path / "r2" / "metrics.json", m_baseline)
        metrics_list = load_metrics([p1, p2])
        df = compare_strategies(metrics_list)
        assert check_criterion_14_4(df) is False

    def test_model_beats_by_mdd(self, tmp_path: Path) -> None:
        """#052 — Model beats baseline via lower MDD even with lower PnL."""
        from scripts.compare_runs import (
            check_criterion_14_4,
            compare_strategies,
            load_metrics,
        )

        m_model = _make_metrics(
            run_id="r1", strategy_type="model", name="low_risk_model",
            net_pnl_mean=40.0, max_drawdown_mean=0.05,
            comparison_type="go_nogo",
        )
        m_baseline = _make_metrics(
            run_id="r2", strategy_type="baseline", name="sma_rule",
            net_pnl_mean=50.0, max_drawdown_mean=0.20,
            comparison_type="go_nogo",
        )
        p1 = _write_metrics(tmp_path / "r1" / "metrics.json", m_model)
        p2 = _write_metrics(tmp_path / "r2" / "metrics.json", m_baseline)
        metrics_list = load_metrics([p1, p2])
        df = compare_strategies(metrics_list)
        # Model has lower MDD → beats baseline in MDD
        assert check_criterion_14_4(df) is True

    def test_no_model_raises(self, tmp_path: Path) -> None:
        """#052 — Raises ValueError when no model strategy is present."""
        from scripts.compare_runs import (
            check_criterion_14_4,
            compare_strategies,
            load_metrics,
        )

        m1 = _make_metrics(
            run_id="r1", strategy_type="baseline", name="sma_rule",
            net_pnl_mean=50.0, max_drawdown_mean=0.10,
            comparison_type="go_nogo",
        )
        m2 = _make_metrics(
            run_id="r2", strategy_type="baseline", name="no_trade",
            net_pnl_mean=0.0, max_drawdown_mean=0.0,
            comparison_type="go_nogo",
        )
        p1 = _write_metrics(tmp_path / "r1" / "metrics.json", m1)
        p2 = _write_metrics(tmp_path / "r2" / "metrics.json", m2)
        metrics_list = load_metrics([p1, p2])
        df = compare_strategies(metrics_list)
        with pytest.raises(ValueError, match="model"):
            check_criterion_14_4(df)

    def test_no_baseline_raises(self, tmp_path: Path) -> None:
        """#052 — Raises ValueError when no baseline strategy is present."""
        from scripts.compare_runs import (
            check_criterion_14_4,
            compare_strategies,
            load_metrics,
        )

        m1 = _make_metrics(
            run_id="r1", strategy_type="model", name="lstm",
            net_pnl_mean=100.0, max_drawdown_mean=0.10,
            comparison_type="go_nogo",
        )
        p1 = _write_metrics(tmp_path / "r1" / "metrics.json", m1)
        metrics_list = load_metrics([p1])
        df = compare_strategies(metrics_list)
        with pytest.raises(ValueError, match="baseline"):
            check_criterion_14_4(df)

    def test_buy_hold_included_in_criterion(self, tmp_path: Path) -> None:
        """#052 — buy_hold (contextual) IS included in §14.4 per spec."""
        from scripts.compare_runs import (
            check_criterion_14_4,
            compare_strategies,
            load_metrics,
        )

        # Model worse than buy_hold but better than no_trade
        m_model = _make_metrics(
            run_id="r1", strategy_type="model", name="lstm",
            net_pnl_mean=10.0, max_drawdown_mean=0.15,
            comparison_type="go_nogo",
        )
        m_no_trade = _make_metrics(
            run_id="r2", strategy_type="baseline", name="no_trade",
            net_pnl_mean=0.0, max_drawdown_mean=0.0,
            comparison_type="go_nogo",
        )
        m_bh = _make_metrics(
            run_id="r3", strategy_type="baseline", name="buy_hold",
            net_pnl_mean=500.0, max_drawdown_mean=0.05,
            comparison_type="contextual",
        )
        p1 = _write_metrics(tmp_path / "r1" / "metrics.json", m_model)
        p2 = _write_metrics(tmp_path / "r2" / "metrics.json", m_no_trade)
        p3 = _write_metrics(tmp_path / "r3" / "metrics.json", m_bh)
        metrics_list = load_metrics([p1, p2, p3])
        df = compare_strategies(metrics_list)
        # Model beats no_trade in net_pnl → True
        # buy_hold is also checked now (model doesn't beat it, but beats no_trade)
        assert check_criterion_14_4(df) is True

    def test_model_beats_only_buy_hold_returns_true(self, tmp_path: Path) -> None:
        """#052 — §14.4 passes if model beats buy_hold even when losing to go_nogo baselines."""
        from scripts.compare_runs import (
            check_criterion_14_4,
            compare_strategies,
            load_metrics,
        )

        # Model loses to sma_rule (go_nogo) but beats buy_hold (contextual)
        m_model = _make_metrics(
            run_id="r1", strategy_type="model", name="lstm",
            net_pnl_mean=30.0, max_drawdown_mean=0.25,
            comparison_type="go_nogo",
        )
        m_sma = _make_metrics(
            run_id="r2", strategy_type="baseline", name="sma_rule",
            net_pnl_mean=50.0, max_drawdown_mean=0.10,
            comparison_type="go_nogo",
        )
        m_bh = _make_metrics(
            run_id="r3", strategy_type="baseline", name="buy_hold",
            net_pnl_mean=20.0, max_drawdown_mean=0.30,
            comparison_type="contextual",
        )
        p1 = _write_metrics(tmp_path / "r1" / "metrics.json", m_model)
        p2 = _write_metrics(tmp_path / "r2" / "metrics.json", m_sma)
        p3 = _write_metrics(tmp_path / "r3" / "metrics.json", m_bh)
        metrics_list = load_metrics([p1, p2, p3])
        df = compare_strategies(metrics_list)
        # Model (pnl=30) < sma_rule (pnl=50), mdd 0.25 > 0.10 → loses to sma
        # Model (pnl=30) > buy_hold (pnl=20) → beats buy_hold
        assert check_criterion_14_4(df) is True


# ---------------------------------------------------------------------------
# Tests — CSV/Markdown output
# ---------------------------------------------------------------------------


class TestOutputFiles:
    """Tests for CSV and Markdown table output."""

    def test_write_csv(self, run_dirs: dict[str, Path], tmp_path: Path) -> None:
        """#052 — CSV output is written and readable."""
        from scripts.compare_runs import compare_strategies, load_metrics, write_csv

        metrics_list = load_metrics(list(run_dirs.values()))
        df = compare_strategies(metrics_list)
        csv_path = tmp_path / "comparison.csv"
        write_csv(df, csv_path)
        assert csv_path.exists()
        loaded = pd.read_csv(csv_path)
        assert len(loaded) == len(df)
        assert "strategy_name" in loaded.columns

    def test_write_markdown(self, run_dirs: dict[str, Path], tmp_path: Path) -> None:
        """#052 — Markdown output is written and readable."""
        from scripts.compare_runs import compare_strategies, load_metrics, write_markdown

        metrics_list = load_metrics(list(run_dirs.values()))
        df = compare_strategies(metrics_list)
        md_path = tmp_path / "comparison.md"
        write_markdown(df, md_path)
        assert md_path.exists()
        content = md_path.read_text(encoding="utf-8")
        # Markdown table starts with header separator
        assert "|" in content
        # All strategy names appear
        for name in ("lstm", "xgboost", "sma_rule", "no_trade", "buy_hold"):
            assert name in content


# ---------------------------------------------------------------------------
# Tests — CLI integration
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for the CLI entry point."""

    def test_cli_runs_successfully(self, run_dirs: dict[str, Path], tmp_path: Path) -> None:
        """#052 — CLI script runs end-to-end with valid inputs."""
        script = str(PROJECT_ROOT / "scripts" / "compare_runs.py")
        paths = [str(run_dirs[k]) for k in ("lstm", "sma_rule", "buy_hold")]
        out_dir = tmp_path / "output"
        result = subprocess.run(
            [sys.executable, script, "--runs", *paths, "--output-dir", str(out_dir)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert (out_dir / "comparison.csv").exists()
        assert (out_dir / "comparison.md").exists()

    def test_cli_missing_file_exits_nonzero(self, tmp_path: Path) -> None:
        """#052 — CLI exits with non-zero code when a file is missing."""
        script = str(PROJECT_ROOT / "scripts" / "compare_runs.py")
        missing = str(tmp_path / "nonexistent" / "metrics.json")
        result = subprocess.run(
            [sys.executable, script, "--runs", missing, "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0

    def test_cli_no_runs_exits_nonzero(self) -> None:
        """#052 — CLI exits with non-zero code when --runs is empty."""
        script = str(PROJECT_ROOT / "scripts" / "compare_runs.py")
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0
