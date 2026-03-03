"""Metrics builder — construct and serialize ``metrics.json`` and per-fold files.

Builds the global ``metrics.json`` from per-fold metrics and aggregate data,
and writes individual ``metrics_fold.json`` files into each ``folds/fold_XX/``
directory.  The JSON output conforms to
``docs/specifications/metrics.schema.json`` (Draft 2020-12).

Task #046 — WS-11.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required keys per fold (schema-enforced)
# ---------------------------------------------------------------------------

_REQUIRED_FOLD_KEYS = frozenset({
    "fold_id",
    "period_test",
    "threshold",
    "prediction",
    "n_samples_train",
    "n_samples_val",
    "n_samples_test",
    "trading",
})

_PREDICTION_FLOAT_KEYS = ("mae", "rmse", "directional_accuracy", "spearman_ic")

_TRADING_FLOAT_KEYS = (
    "net_pnl",
    "net_return",
    "max_drawdown",
    "sharpe",
    "profit_factor",
    "hit_rate",
    "avg_trade_return",
    "median_trade_return",
    "exposure_time_frac",
    "sharpe_per_trade",
)

_TRADING_INT_KEYS = ("n_trades",)

_REQUIRED_PREDICTION_KEYS = frozenset({"mae", "rmse", "directional_accuracy"})

_REQUIRED_TRADING_KEYS = frozenset(
    {"net_pnl", "net_return", "max_drawdown", "profit_factor", "n_trades"}
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_float(value: float | int | None) -> float | None:
    """Convert a numeric value to Python float, preserving None."""
    if value is None:
        return None
    return float(value)


def _ensure_int(value: int) -> int:
    """Convert a value to Python int."""
    return int(value)


def _normalize_prediction(prediction: dict) -> dict:
    """Normalize prediction metrics to float64."""
    for key in _REQUIRED_PREDICTION_KEYS:
        if key not in prediction:
            raise KeyError(f"Missing required prediction key: '{key}'")
    result: dict = {}
    for key in _PREDICTION_FLOAT_KEYS:
        if key in prediction:
            result[key] = _ensure_float(prediction[key])
    return result


def _normalize_trading(trading: dict) -> dict:
    """Normalize trading metrics: floats for metrics, int for n_trades."""
    for key in _REQUIRED_TRADING_KEYS:
        if key not in trading:
            raise KeyError(f"Missing required trading key: '{key}'")
    result: dict = {}
    for key in _TRADING_FLOAT_KEYS:
        if key in trading:
            result[key] = _ensure_float(trading[key])
    for key in _TRADING_INT_KEYS:
        if key in trading:
            result[key] = _ensure_int(trading[key])
    return result


def _normalize_aggregate_block(block: dict) -> dict:
    """Normalize an aggregate block (mean/std) to float64."""
    result: dict = {}
    for stat_key in ("mean", "std"):
        stat_dict = block[stat_key]
        result[stat_key] = {
            k: _ensure_float(v) for k, v in stat_dict.items()
        }
    return result


def _normalize_fold(fold_data: dict) -> dict:
    """Build a schema-conforming fold dict from raw fold data."""
    for key in _REQUIRED_FOLD_KEYS:
        if key not in fold_data:
            raise KeyError(
                f"Missing required fold field: '{key}'"
            )

    return {
        "fold_id": _ensure_int(fold_data["fold_id"]),
        "period_test": fold_data["period_test"],
        "threshold": fold_data["threshold"],
        "prediction": _normalize_prediction(fold_data["prediction"]),
        "n_samples_train": _ensure_int(fold_data["n_samples_train"]),
        "n_samples_val": _ensure_int(fold_data["n_samples_val"]),
        "n_samples_test": _ensure_int(fold_data["n_samples_test"]),
        "trading": _normalize_trading(fold_data["trading"]),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_metrics(
    *,
    run_id: str,
    strategy_info: dict,
    folds_data: list[dict],
    aggregate_data: dict,
) -> dict:
    """Build a metrics dict conforming to ``metrics.schema.json``.

    All parameters are **required** (keyword-only, no defaults).

    Parameters
    ----------
    run_id:
        Unique run identifier (e.g. ``YYYYMMDD_HHMMSS_<strategy>``).
    strategy_info:
        Strategy metadata with keys ``strategy_type`` and ``name``.
    folds_data:
        Per-fold metrics, one dict per fold with keys: ``fold_id``,
        ``period_test``, ``threshold``, ``prediction``,
        ``n_samples_train``, ``n_samples_val``, ``n_samples_test``,
        ``trading``.
    aggregate_data:
        Aggregate metrics with ``prediction`` and ``trading`` sub-dicts,
        each containing ``mean`` and ``std`` sub-dicts.

    Returns
    -------
    dict
        Metrics dict ready for JSON serialization.

    Raises
    ------
    ValueError
        If ``run_id`` is empty or ``folds_data`` is empty,
        or if duplicate ``fold_id`` values are found.
    KeyError
        If required keys are missing from ``strategy_info``,
        ``folds_data`` entries, or ``aggregate_data``.
    """
    if not run_id:
        raise ValueError("run_id must be a non-empty string")

    if len(folds_data) == 0:
        raise ValueError("folds_data must not be empty")

    # Validate strategy_info required keys
    _ = strategy_info["strategy_type"]
    _ = strategy_info["name"]

    # Validate aggregate_data required keys
    _ = aggregate_data["prediction"]
    _ = aggregate_data["trading"]

    # Check for duplicate fold_ids
    fold_ids: list[int] = []
    for fold in folds_data:
        fid = fold["fold_id"]
        if fid in fold_ids:
            raise ValueError(
                f"Duplicate fold_id found: {fid}. "
                "Each fold must have a unique fold_id."
            )
        fold_ids.append(fid)

    # Build normalized folds
    normalized_folds = [_normalize_fold(f) for f in folds_data]

    # Build normalized aggregate
    aggregate: dict = {
        "prediction": _normalize_aggregate_block(aggregate_data["prediction"]),
        "trading": _normalize_aggregate_block(aggregate_data["trading"]),
    }
    # Pass through optional aggregate fields
    if "notes" in aggregate_data:
        aggregate["notes"] = aggregate_data["notes"]
    if "comparison_type" in aggregate_data:
        aggregate["comparison_type"] = aggregate_data["comparison_type"]

    return {
        "run_id": run_id,
        "strategy": {
            "strategy_type": strategy_info["strategy_type"],
            "name": strategy_info["name"],
        },
        "folds": normalized_folds,
        "aggregate": aggregate,
    }


def write_metrics(metrics_data: dict, run_dir: Path) -> None:
    """Write a metrics dict as ``metrics.json`` into *run_dir*.

    Parameters
    ----------
    metrics_data:
        Metrics dict (as returned by :func:`build_metrics`).
    run_dir:
        Target directory. Created (with parents) if it does not exist.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "metrics.json"
    output_path.write_text(
        json.dumps(metrics_data, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_fold_metrics(fold_data: dict, fold_dir: Path) -> None:
    """Write per-fold metrics as ``metrics_fold.json`` into *fold_dir*.

    Parameters
    ----------
    fold_data:
        Single fold metrics dict (same structure as a fold entry
        in the global ``metrics.json``).
    fold_dir:
        Target fold directory (e.g. ``run_dir/folds/fold_00/``).
        Created (with parents) if it does not exist.
    """
    fold_dir.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_fold(fold_data)
    output_path = fold_dir / "metrics_fold.json"
    output_path.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
