"""Artifacts: manifest, metrics files, run directory, JSON schema validation."""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from lib.config import PipelineConfig

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

STRATEGY_FRAMEWORK_MAP: dict[str, str] = {
    "dummy": "internal",
    "xgboost_reg": "xgboost",
    "cnn1d_reg": "pytorch",
    "gru_reg": "pytorch",
    "lstm_reg": "pytorch",
    "patchtst_reg": "pytorch",
    "rl_ppo": "pytorch",
    "no_trade": "baseline",
    "buy_hold": "baseline",
    "sma_rule": "baseline",
}


def get_git_commit(working_dir: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, cwd=working_dir,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Could not determine git commit hash. Using 'unknown'.")
        return "unknown"


def build_manifest(
    *,
    run_id: str, config_snapshot: dict, dataset_info: dict,
    label_info: dict, window_info: dict, features_info: dict,
    splits_info: dict, strategy_info: dict, costs_info: dict,
    environment_info: dict, artifacts_info: dict,
    git_commit: str, pipeline_version: str,
) -> dict:
    if not run_id:
        raise ValueError("run_id must be a non-empty string")
    if not git_commit:
        raise ValueError("git_commit must be a non-empty string")
    if not pipeline_version:
        raise ValueError("pipeline_version must be a non-empty string")
    strategy_name = strategy_info["name"]
    if strategy_name not in STRATEGY_FRAMEWORK_MAP:
        raise ValueError(f"Unknown strategy name '{strategy_name}'.")
    framework = STRATEGY_FRAMEWORK_MAP[strategy_name]
    strategy_section: dict = {
        "strategy_type": strategy_info["strategy_type"],
        "name": strategy_name,
        "framework": framework,
        "output_type": strategy_info["output_type"],
    }
    if "hyperparams" in strategy_info:
        strategy_section["hyperparams"] = strategy_info["hyperparams"]
    if "thresholding" in strategy_info:
        strategy_section["thresholding"] = strategy_info["thresholding"]
    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "run_id": run_id, "created_at_utc": created_at,
        "pipeline_version": pipeline_version, "git_commit": git_commit,
        "config_snapshot": config_snapshot, "dataset": dataset_info,
        "label": label_info, "window": window_info, "features": features_info,
        "splits": splits_info, "strategy": strategy_section,
        "costs": costs_info, "environment": environment_info,
        "artifacts": artifacts_info,
    }


def write_manifest(manifest_data: dict, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "manifest.json"
    output_path.write_text(
        json.dumps(manifest_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


# ═══════════════════════════════════════════════════════════════════════════
# METRICS BUILDER
# ═══════════════════════════════════════════════════════════════════════════

_REQUIRED_FOLD_KEYS = frozenset({
    "fold_id", "period_test", "threshold", "prediction",
    "n_samples_train", "n_samples_val", "n_samples_test", "trading",
})
_PREDICTION_FLOAT_KEYS = ("mae", "rmse", "directional_accuracy", "spearman_ic")
_TRADING_FLOAT_KEYS = (
    "net_pnl", "net_return", "max_drawdown", "sharpe", "profit_factor",
    "hit_rate", "avg_trade_return", "median_trade_return",
    "exposure_time_frac", "sharpe_per_trade",
)
_TRADING_INT_KEYS = ("n_trades",)
_REQUIRED_PREDICTION_KEYS = frozenset({"mae", "rmse", "directional_accuracy"})
_REQUIRED_TRADING_KEYS = frozenset(
    {"net_pnl", "net_return", "max_drawdown", "profit_factor", "n_trades"}
)


def _ensure_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _ensure_int(value: int) -> int:
    return int(value)


def _normalize_prediction(prediction: dict) -> dict:
    for key in _REQUIRED_PREDICTION_KEYS:
        if key not in prediction:
            raise KeyError(f"Missing required prediction key: '{key}'")
    result: dict = {}
    for key in _PREDICTION_FLOAT_KEYS:
        if key in prediction:
            result[key] = _ensure_float(prediction[key])
    return result


def _normalize_trading(trading: dict) -> dict:
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
    result: dict = {}
    for stat_key in ("mean", "std"):
        stat_dict = block[stat_key]
        result[stat_key] = {k: _ensure_float(v) for k, v in stat_dict.items()}
    return result


def _normalize_fold(fold_data: dict) -> dict:
    for key in _REQUIRED_FOLD_KEYS:
        if key not in fold_data:
            raise KeyError(f"Missing required fold field: '{key}'")
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


def build_metrics(
    *, run_id: str, strategy_info: dict,
    folds_data: list[dict], aggregate_data: dict,
) -> dict:
    if not run_id:
        raise ValueError("run_id must be a non-empty string")
    if len(folds_data) == 0:
        raise ValueError("folds_data must not be empty")
    _ = strategy_info["strategy_type"]
    _ = strategy_info["name"]
    _ = strategy_info["output_type"]
    _ = aggregate_data["prediction"]
    _ = aggregate_data["trading"]
    fold_ids: list[int] = []
    for fold in folds_data:
        fid = fold["fold_id"]
        if fid in fold_ids:
            raise ValueError(f"Duplicate fold_id found: {fid}.")
        fold_ids.append(fid)
    normalized_folds = [_normalize_fold(f) for f in folds_data]
    aggregate: dict = {
        "prediction": _normalize_aggregate_block(aggregate_data["prediction"]),
        "trading": _normalize_aggregate_block(aggregate_data["trading"]),
    }
    if "notes" in aggregate_data:
        aggregate["notes"] = aggregate_data["notes"]
    if "comparison_type" in aggregate_data:
        aggregate["comparison_type"] = aggregate_data["comparison_type"]
    return {
        "run_id": run_id,
        "strategy": {
            "strategy_type": strategy_info["strategy_type"],
            "name": strategy_info["name"],
            "output_type": strategy_info["output_type"],
        },
        "folds": normalized_folds,
        "aggregate": aggregate,
    }


def write_metrics(metrics_data: dict, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    output_path = run_dir / "metrics.json"
    output_path.write_text(
        json.dumps(metrics_data, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_fold_metrics(fold_data: dict, fold_dir: Path) -> None:
    fold_dir.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_fold(fold_data)
    output_path = fold_dir / "metrics_fold.json"
    output_path.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


# ═══════════════════════════════════════════════════════════════════════════
# RUN DIRECTORY
# ═══════════════════════════════════════════════════════════════════════════

def generate_run_id(strategy_name: str) -> str:
    if not strategy_name:
        raise ValueError("strategy_name must be a non-empty string")
    utc_now = datetime.now(UTC)
    timestamp = utc_now.strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{strategy_name}"


def save_config_snapshot(run_dir: Path, config: PipelineConfig) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = run_dir / "config_snapshot.yaml"
    data = config.model_dump()
    snapshot_path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def create_run_dir(
    config: PipelineConfig, strategy_name: str, n_folds: int,
) -> Path:
    if n_folds < 1:
        raise ValueError(f"n_folds must be >= 1, got {n_folds}")
    output_dir = Path(config.artifacts.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = generate_run_id(strategy_name)
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    folds_dir = run_dir / "folds"
    for i in range(n_folds):
        fold_dir = folds_dir / f"fold_{i:02d}" / "model_artifacts"
        fold_dir.mkdir(parents=True, exist_ok=True)
    save_config_snapshot(run_dir, config)
    return run_dir


# ═══════════════════════════════════════════════════════════════════════════
# JSON SCHEMA VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SCHEMAS_DIR = _PROJECT_ROOT


def _load_schema(schema_name: str) -> dict:
    schema_path = _SCHEMAS_DIR / schema_name
    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def _validate_json(data: dict, schema_name: str) -> None:
    schema = _load_schema(schema_name)
    validator = Draft202012Validator(schema)
    validator.validate(data)


def validate_manifest(data: dict) -> None:
    _validate_json(data, "manifest.schema.json")


def validate_metrics(data: dict) -> None:
    _validate_json(data, "metrics.schema.json")
