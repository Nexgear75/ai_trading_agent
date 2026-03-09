"""Model registry, base class, and model implementations."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

import numpy as np

from lib.data import flatten_seq_to_tab
from lib.features import VALID_OUTPUT_TYPES

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# MODEL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

MODEL_REGISTRY: dict[str, type[BaseModelABC]] = {}
_VALID_EXECUTION_MODES = frozenset({"standard", "single_trade"})


class BaseModelABC(ABC):
    execution_mode: Literal["standard", "single_trade"] = "standard"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "output_type" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must declare 'output_type' with a value."
            )
        ot = cls.__dict__["output_type"]
        if not isinstance(ot, str):
            raise TypeError(f"{cls.__name__}: output_type must be a string.")
        if ot not in VALID_OUTPUT_TYPES:
            raise ValueError(
                f"{cls.__name__}: output_type must be one of {sorted(VALID_OUTPUT_TYPES)}, got '{ot}'."
            )
        if "execution_mode" in cls.__dict__:
            em = cls.__dict__["execution_mode"]
            if not isinstance(em, str):
                raise TypeError(f"{cls.__name__}: execution_mode must be a string.")
            if em not in _VALID_EXECUTION_MODES:
                raise ValueError(
                    f"{cls.__name__}: execution_mode must be one of "
                    f"{sorted(_VALID_EXECUTION_MODES)}, got '{em}'."
                )

    @abstractmethod
    def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
            meta_train=None, meta_val=None, ohlcv=None) -> dict: ...

    @abstractmethod
    def predict(self, X, meta=None, ohlcv=None) -> np.ndarray: ...

    @abstractmethod
    def save(self, path: Path) -> None: ...

    @abstractmethod
    def load(self, path: Path) -> None: ...


def register_model(name: str):
    def decorator(cls: type[BaseModelABC]) -> type[BaseModelABC]:
        if not (isinstance(cls, type) and issubclass(cls, BaseModelABC)):
            raise TypeError(
                f"@register_model('{name}'): {cls!r} is not a BaseModelABC subclass."
            )
        if name in MODEL_REGISTRY:
            raise ValueError(f"Model '{name}' is already registered in MODEL_REGISTRY.")
        MODEL_REGISTRY[name] = cls
        return cls
    return decorator


def get_model_class(name: str) -> type[BaseModelABC]:
    if name not in MODEL_REGISTRY:
        if MODEL_REGISTRY:
            available = ", ".join(sorted(MODEL_REGISTRY))
            msg = f"Model '{name}' is not registered. Available: {available}."
        else:
            msg = f"Model '{name}' is not registered (registry is empty)."
        raise ValueError(msg)
    return MODEL_REGISTRY[name]


# ═══════════════════════════════════════════════════════════════════════════
# MODEL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════

# --- DummyModel ---

@register_model("dummy")
class DummyModel(BaseModelABC):
    output_type = "regression"

    def __init__(self, seed: int) -> None:
        self._seed = seed

    def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
            meta_train=None, meta_val=None, ohlcv=None) -> dict:
        return {}

    def predict(self, X, meta=None, ohlcv=None) -> np.ndarray:
        n = X.shape[0]
        rng = np.random.default_rng(self._seed)
        return rng.standard_normal(n).astype(np.float32)

    @staticmethod
    def _resolve_path(path: Path) -> Path:
        path = Path(path)
        if path.suffix != ".json":
            return path / "dummy_model.json"
        return path

    def save(self, path: Path) -> None:
        resolved = self._resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(json.dumps({"seed": self._seed}))

    def load(self, path: Path) -> None:
        resolved = self._resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Model file not found: {resolved}")
        data = json.loads(resolved.read_text())
        self._seed = data["seed"]


# --- XGBoostRegModel ---

@register_model("xgboost_reg")
class XGBoostRegModel(BaseModelABC):
    output_type = "regression"

    def __init__(self) -> None:
        self._model = None
        self._feature_names: list[str] | None = None

    def fit(self, X_train, y_train, X_val, y_val, config, run_dir,
            meta_train=None, meta_val=None, ohlcv=None) -> dict:
        import xgboost as xgb

        if X_train.ndim != 3:
            raise ValueError(f"X_train must be 3D, got {X_train.ndim}D.")
        if X_val.ndim != 3:
            raise ValueError(f"X_val must be 3D, got {X_val.ndim}D.")
        if y_train.ndim != 1:
            raise ValueError(f"y_train must be 1D, got {y_train.ndim}D.")
        if y_val.ndim != 1:
            raise ValueError(f"y_val must be 1D, got {y_val.ndim}D.")
        if X_train.shape[0] == 0:
            raise ValueError("X_train must have at least 1 sample.")
        if X_val.shape[0] == 0:
            raise ValueError("X_val must have at least 1 sample.")
        if X_train.shape[0] != y_train.shape[0]:
            raise ValueError("X_train and y_train sample count mismatch.")
        if X_val.shape[0] != y_val.shape[0]:
            raise ValueError("X_val and y_val sample count mismatch.")
        if X_train.dtype != np.float32:
            raise TypeError(f"X_train must be float32, got {X_train.dtype}.")
        if X_val.dtype != np.float32:
            raise TypeError(f"X_val must be float32, got {X_val.dtype}.")
        if y_train.dtype != np.float32:
            raise TypeError(f"y_train must be float32, got {y_train.dtype}.")
        if y_val.dtype != np.float32:
            raise TypeError(f"y_val must be float32, got {y_val.dtype}.")

        n_features = X_train.shape[2]
        feature_names = [f"f{i}" for i in range(n_features)]
        self._feature_names = feature_names
        x_tab_train, _ = flatten_seq_to_tab(X_train, feature_names)
        x_tab_val, _ = flatten_seq_to_tab(X_val, feature_names)

        xgb_cfg = config.models.xgboost
        self._model = xgb.XGBRegressor(
            max_depth=xgb_cfg.max_depth,
            n_estimators=xgb_cfg.n_estimators,
            learning_rate=xgb_cfg.learning_rate,
            subsample=xgb_cfg.subsample,
            colsample_bytree=xgb_cfg.colsample_bytree,
            reg_alpha=xgb_cfg.reg_alpha,
            reg_lambda=xgb_cfg.reg_lambda,
            objective="reg:squarederror",
            tree_method="hist",
            booster="gbtree",
            random_state=config.reproducibility.global_seed,
            early_stopping_rounds=config.training.early_stopping_patience,
            verbosity=0,
        )

        self._model.fit(
            x_tab_train, y_train,
            eval_set=[(x_tab_val, y_val)],
            verbose=False,
        )
        return {
            "best_iteration": self._model.best_iteration,
            "best_score": self._model.best_score,
            "n_features_in": x_tab_train.shape[1],
        }

    def predict(self, X, meta=None, ohlcv=None) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Model not fitted.")
        if X.ndim != 3:
            raise ValueError(f"X must be 3D, got {X.ndim}D.")
        if X.dtype != np.float32:
            raise TypeError(f"X.dtype must be float32, got {X.dtype}.")
        if X.shape[0] == 0:
            return np.empty((0,), dtype=np.float32)
        if self._feature_names is None:
            raise RuntimeError("Feature names not set.")
        x_tab, _ = flatten_seq_to_tab(X, self._feature_names)
        y_hat = self._model.predict(x_tab)
        return y_hat.astype(np.float32)

    @staticmethod
    def _resolve_path(path: Path) -> Path:
        path = Path(path)
        if path.suffix not in (".json", ".ubj"):
            return path / "xgboost_model.json"
        return path

    def save(self, path: Path) -> None:
        if self._model is None:
            raise RuntimeError("Model not fitted.")
        resolved = self._resolve_path(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._model.save_model(str(resolved))

    def load(self, path: Path) -> None:
        import xgboost as xgb
        resolved = self._resolve_path(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Model file not found: {resolved}")
        self._model = xgb.XGBRegressor()
        self._model.load_model(str(resolved))
