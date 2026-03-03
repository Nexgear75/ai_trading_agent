"""Compare multiple AI Trading pipeline runs and produce a comparison table.

Standalone CLI script (post-MVP). Loads ``metrics.json`` files from multiple
runs, builds a comparison DataFrame, checks criterion §14.4, and writes
CSV + Markdown output.

Task #052 — WS-12.

Usage::

    python scripts/compare_runs.py \\
        --runs runs/run_lstm/metrics.json runs/run_sma/metrics.json \\
        --output-dir outputs/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Required keys in metrics.json (from metrics.schema.json)
# ---------------------------------------------------------------------------

_REQUIRED_TOP_KEYS = frozenset({"run_id", "strategy", "aggregate"})
_REQUIRED_STRATEGY_KEYS = frozenset({"strategy_type", "name"})

# Strategies classified as "contextual" rather than "go_nogo"
_CONTEXTUAL_STRATEGY_NAMES = frozenset({"buy_hold"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_metrics(paths: list[Path]) -> list[dict]:
    """Load and validate ``metrics.json`` files from *paths*.

    Parameters
    ----------
    paths:
        List of paths to ``metrics.json`` files. Must contain at least one.

    Returns
    -------
    list[dict]
        Parsed and validated metrics dicts.

    Raises
    ------
    ValueError
        If *paths* is empty, a file contains invalid JSON, or required
        keys are missing.
    FileNotFoundError
        If a path does not exist.
    """
    if len(paths) == 0:
        raise ValueError("paths must contain at least one metrics.json path")

    results: list[dict] = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            raise FileNotFoundError(f"Metrics file not found: {p}")

        raw = p.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"File {p} contains invalid JSON: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"File {p}: expected a JSON object, got {type(data).__name__}"
            )

        missing = _REQUIRED_TOP_KEYS - data.keys()
        if missing:
            raise ValueError(
                f"File {p}: missing required top-level keys: {sorted(missing)}"
            )

        strategy = data["strategy"]
        if not isinstance(strategy, dict):
            raise ValueError(
                f"File {p}: 'strategy' must be an object, got {type(strategy).__name__}"
            )
        missing_strat = _REQUIRED_STRATEGY_KEYS - strategy.keys()
        if missing_strat:
            raise ValueError(
                f"File {p}: missing required strategy keys: {sorted(missing_strat)}"
            )

        # Validate nested aggregate structure required by compare_strategies
        aggregate = data["aggregate"]
        if not isinstance(aggregate, dict):
            raise ValueError(
                f"File {p}: 'aggregate' must be an object, got {type(aggregate).__name__}"
            )
        if "trading" not in aggregate:
            raise ValueError(
                f"File {p}: 'aggregate' missing required key 'trading'"
            )
        trading = aggregate["trading"]
        if not isinstance(trading, dict):
            raise ValueError(
                f"File {p}: 'aggregate.trading' must be an object, "
                f"got {type(trading).__name__}"
            )
        if "mean" not in trading:
            raise ValueError(
                f"File {p}: 'aggregate.trading' missing required key 'mean'"
            )
        if not isinstance(trading["mean"], dict):
            raise ValueError(
                f"File {p}: 'aggregate.trading.mean' must be an object, "
                f"got {type(trading['mean']).__name__}"
            )

        results.append(data)

    return results


def compare_strategies(metrics_list: list[dict]) -> pd.DataFrame:
    """Build a comparison DataFrame from loaded metrics dicts.

    Extracts aggregate trading metrics and strategy metadata.
    Assigns ``comparison_type`` as ``"contextual"`` for buy & hold
    and ``"go_nogo"`` for all other strategies.

    Parameters
    ----------
    metrics_list:
        List of validated metrics dicts (from :func:`load_metrics`).

    Returns
    -------
    pd.DataFrame
        Comparison table with columns: ``run_id``, ``strategy_name``,
        ``strategy_type``, ``comparison_type``, ``net_pnl_mean``,
        ``max_drawdown_mean``, ``sharpe_mean``, and other aggregate
        trading metrics available.
    """
    rows: list[dict] = []
    for m in metrics_list:
        strategy = m["strategy"]
        aggregate = m["aggregate"]
        trading_mean = aggregate["trading"]["mean"]

        # Derive comparison_type: explicit in aggregate, or infer from name
        if "comparison_type" in aggregate:
            comp_type = aggregate["comparison_type"]
        elif strategy["name"] in _CONTEXTUAL_STRATEGY_NAMES:
            comp_type = "contextual"
        else:
            comp_type = "go_nogo"

        row = {
            "run_id": m["run_id"],
            "strategy_name": strategy["name"],
            "strategy_type": strategy["strategy_type"],
            "comparison_type": comp_type,
            "net_pnl_mean": trading_mean["net_pnl"],
            "net_return_mean": trading_mean["net_return"],
            "max_drawdown_mean": trading_mean["max_drawdown"],
            "sharpe_mean": trading_mean["sharpe"],
            "profit_factor_mean": trading_mean["profit_factor"],
            "n_trades_mean": trading_mean["n_trades"],
        }
        rows.append(row)

    return pd.DataFrame(rows)


def check_criterion_14_4(comparison: pd.DataFrame) -> bool:
    """Check §14.4: best model beats at least one baseline.

    Per §14.4, the best model must beat at least one baseline
    (no-trade **and/or** buy & hold) in P&L net or MDD.
    Both go_nogo and contextual baselines are included.

    A model "beats" a baseline if it has **higher** ``net_pnl_mean`` **or**
    **lower** ``max_drawdown_mean``.

    Parameters
    ----------
    comparison:
        DataFrame from :func:`compare_strategies`.

    Returns
    -------
    bool
        True if at least one model beats at least one baseline.

    Raises
    ------
    ValueError
        If no model or no baseline is present in the comparison.
    """
    go_nogo = comparison[comparison["comparison_type"] == "go_nogo"]
    models = go_nogo[go_nogo["strategy_type"] == "model"]
    # §14.4 includes ALL baselines (go_nogo + contextual like buy_hold)
    baselines = comparison[comparison["strategy_type"] == "baseline"]

    if len(models) == 0:
        raise ValueError(
            "No model strategy found in go_nogo comparison. "
            "Cannot evaluate criterion §14.4."
        )
    if len(baselines) == 0:
        raise ValueError(
            "No baseline strategy found in comparison. "
            "Cannot evaluate criterion §14.4."
        )

    # Best model = highest net_pnl_mean among models
    best_model = models.loc[models["net_pnl_mean"].idxmax()]
    best_pnl = best_model["net_pnl_mean"]
    best_mdd = best_model["max_drawdown_mean"]

    for _, baseline in baselines.iterrows():
        # Model beats baseline if better PnL OR better (lower) MDD
        if best_pnl > baseline["net_pnl_mean"]:
            return True
        if best_mdd < baseline["max_drawdown_mean"]:
            return True

    return False


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write comparison DataFrame to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_markdown(df: pd.DataFrame, path: Path) -> None:
    """Write comparison DataFrame as a Markdown table.

    Produces two sections: Go/No-Go comparison and Contextual comparison.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Strategy Comparison Report\n")

    go_nogo = df[df["comparison_type"] == "go_nogo"]
    contextual = df[df["comparison_type"] == "contextual"]

    if len(go_nogo) > 0:
        lines.append("## Go/No-Go Comparison (§13.4)\n")
        lines.append(_df_to_md_table(go_nogo))
        lines.append("")

    if len(contextual) > 0:
        lines.append("## Contextual Comparison — Buy & Hold (§13.4)\n")
        lines.append(_df_to_md_table(contextual))
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _df_to_md_table(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a Markdown table string."""
    cols = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows_lines = []
    for _, row in df.iterrows():
        vals = [str(row[c]) for c in cols]
        rows_lines.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep, *rows_lines])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for compare_runs."""
    parser = argparse.ArgumentParser(
        description="Compare AI Trading pipeline runs from metrics.json files."
    )
    parser.add_argument(
        "--runs",
        nargs="+",
        type=Path,
        required=True,
        help="Paths to metrics.json files to compare.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where comparison.csv and comparison.md will be written.",
    )

    args = parser.parse_args(argv)

    try:
        metrics_list = load_metrics(args.runs)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    df = compare_strategies(metrics_list)

    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    write_csv(df, out_dir / "comparison.csv")
    write_markdown(df, out_dir / "comparison.md")

    # Check §14.4
    try:
        result = check_criterion_14_4(df)
        if result:
            print("§14.4 PASS: Best model beats at least one baseline.")
        else:
            print("§14.4 FAIL: No model beats any baseline in net PnL or MDD.")
    except ValueError as exc:
        print(f"§14.4 SKIP: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
