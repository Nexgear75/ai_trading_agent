"""BaseModel abstract class and MODEL_REGISTRY for the AI Trading Pipeline.

Provides:
- ``BaseModel(ABC)``: abstract interface that all models and baselines must implement.
- ``MODEL_REGISTRY``: global dict mapping model name → class.
- ``@register_model(name)``: decorator to register a BaseModel subclass.
- ``get_model_class(name)``: resolve a registered name to its class.

Contract
--------
All models receive and return arrays with these conventions:

- **X_train / X_val / X** : ``np.ndarray`` of shape ``(N, L, F)`` and dtype ``float32``.
  N = number of samples, L = sequence length, F = number of features.
- **y_train / y_val** : ``np.ndarray`` of shape ``(N,)`` and dtype ``float32``.
  Target labels (e.g. forward returns or binary signals).
- **y_hat** (return of ``predict``) : ``np.ndarray`` of shape ``(N,)`` and dtype ``float32``.
  For ``output_type="regression"``: raw predicted values → passed through threshold θ.
  For ``output_type="signal"``: binary 0/1 signals → bypass θ calibration.

Class attributes
~~~~~~~~~~~~~~~~
- ``output_type``: ``Literal["regression", "signal"]`` — **mandatory** in each subclass.
  ``"regression"`` for supervised models (XGBoost, CNN, GRU, LSTM, PatchTST).
  ``"signal"`` for RL agents and baselines (no-trade, buy & hold, SMA).
- ``execution_mode``: ``Literal["standard", "single_trade"]`` — default ``"standard"``.
  ``"single_trade"`` is reserved for BuyHoldBaseline (one entry, one exit).

Anti-fuite
~~~~~~~~~~
- ``fit()`` must only use ``X_train / y_train`` for fitting.
  ``X_val / y_val`` are for early-stopping or validation metrics only.
- Scalers must be fit on train data only (already handled upstream).
- No future data may leak through ``meta_train``, ``meta_val``, ``ohlcv``, or ``meta``.

Spec reference: §10.1, §10.2, §10.4.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

import numpy as np

# Global registry: model name → model class.
# Empty at import time; populated when model modules are imported.
MODEL_REGISTRY: dict[str, type[BaseModel]] = {}

_VALID_OUTPUT_TYPES = frozenset({"regression", "signal"})
_VALID_EXECUTION_MODES = frozenset({"standard", "single_trade"})


def register_model(name: str):
    """Decorator that registers a BaseModel subclass under *name*.

    Parameters
    ----------
    name : str
        Unique identifier for the model (e.g. ``"xgboost_reg"``).

    Returns
    -------
    Callable
        Class decorator that registers and returns the class unchanged.

    Raises
    ------
    ValueError
        If *name* is already present in ``MODEL_REGISTRY``.
    TypeError
        If *cls* is not a subclass of ``BaseModel``.
    """

    def decorator(cls: type[BaseModel]) -> type[BaseModel]:
        if not (isinstance(cls, type) and issubclass(cls, BaseModel)):
            raise TypeError(
                f"@register_model('{name}'): {cls!r} is not a BaseModel subclass."
            )
        if name in MODEL_REGISTRY:
            raise ValueError(
                f"Model '{name}' is already registered in MODEL_REGISTRY."
            )
        MODEL_REGISTRY[name] = cls
        return cls

    return decorator


def get_model_class(name: str) -> type[BaseModel]:
    """Resolve a registered model name to its class.

    Parameters
    ----------
    name : str
        The name under which the model was registered via ``@register_model``.

    Returns
    -------
    type[BaseModel]
        The model class.

    Raises
    ------
    ValueError
        If *name* is not found in ``MODEL_REGISTRY``.
    """
    if name not in MODEL_REGISTRY:
        if MODEL_REGISTRY:
            available = ", ".join(sorted(MODEL_REGISTRY))
            msg = f"Model '{name}' is not registered in MODEL_REGISTRY. Available: {available}."
        else:
            msg = f"Model '{name}' is not registered in MODEL_REGISTRY (registry is empty)."
        raise ValueError(msg)
    return MODEL_REGISTRY[name]


class BaseModel(ABC):
    """Abstract base class for all pipeline models and baselines.

    Subclasses **must**:
    1. Declare ``output_type`` in their own ``__dict__`` (class body).
       Valid values: ``"regression"`` or ``"signal"``.
    2. Implement all abstract methods: ``fit``, ``predict``, ``save``, ``load``.

    Subclasses **may** override ``execution_mode`` (default ``"standard"``).
    Valid values: ``"standard"`` or ``"single_trade"``.

    Shapes and dtypes
    -----------------
    - X : ``(N, L, F)`` float32
    - y : ``(N,)`` float32
    - y_hat : ``(N,)`` float32
    - artifacts (return of fit) : dict of serializable objects

    Anti-fuite
    ----------
    - fit() must use X_val/y_val only for validation/early-stopping, never for fitting.
    - No future data may leak through meta or ohlcv parameters.
    """

    execution_mode: Literal["standard", "single_trade"] = "standard"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)

        # --- output_type: must be explicitly declared in the subclass ---
        if "output_type" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must declare 'output_type' with a value "
                f"(e.g. output_type = 'regression'), not just a type annotation."
            )

        # --- output_type: validate type and value ---
        ot = cls.__dict__["output_type"]
        if not isinstance(ot, str):
            raise TypeError(
                f"{cls.__name__}: output_type must be a string, "
                f"got {type(ot).__name__}."
            )
        if ot not in _VALID_OUTPUT_TYPES:
            raise ValueError(
                f"{cls.__name__}: output_type must be one of {sorted(_VALID_OUTPUT_TYPES)}, "
                f"got '{ot}'."
            )

        # --- execution_mode: validate type and value if overridden ---
        if "execution_mode" in cls.__dict__:
            em = cls.__dict__["execution_mode"]
            if not isinstance(em, str):
                raise TypeError(
                    f"{cls.__name__}: execution_mode must be a string, "
                    f"got {type(em).__name__}."
                )
            if em not in _VALID_EXECUTION_MODES:
                raise ValueError(
                    f"{cls.__name__}: execution_mode must be one of "
                    f"{sorted(_VALID_EXECUTION_MODES)}, got '{em}'."
                )

    @abstractmethod
    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        config: Any,
        run_dir: Path,
        meta_train: Any = None,
        meta_val: Any = None,
        ohlcv: Any = None,
    ) -> dict:
        """Train the model on (X_train, y_train) with optional validation data.

        Parameters
        ----------
        X_train : np.ndarray
            Training features, shape ``(N, L, F)``, dtype float32.
        y_train : np.ndarray
            Training labels, shape ``(N,)``, dtype float32.
        X_val : np.ndarray
            Validation features, shape ``(N_val, L, F)``, dtype float32.
        y_val : np.ndarray
            Validation labels, shape ``(N_val,)``, dtype float32.
        config : Any
            Full pipeline configuration (Pydantic model).
        run_dir : Path
            Directory for run artifacts (checkpoints, logs).
        meta_train : Any, optional
            Additional metadata for training samples. Default ``None``.
        meta_val : Any, optional
            Additional metadata for validation samples. Default ``None``.
        ohlcv : Any, optional
            Raw OHLCV data (for models that need price context). Default ``None``.

        Returns
        -------
        dict
            Artifacts produced during training (e.g. loss curves, best epoch).
        """

    @abstractmethod
    def predict(
        self,
        X: np.ndarray,
        meta: Any = None,
        ohlcv: Any = None,
    ) -> np.ndarray:
        """Generate predictions for input features.

        Parameters
        ----------
        X : np.ndarray
            Input features, shape ``(N, L, F)``, dtype float32.
        meta : Any, optional
            Additional metadata for the samples. Default ``None``.
        ohlcv : Any, optional
            Raw OHLCV data (for models that need price context). Default ``None``.

        Returns
        -------
        np.ndarray
            Predictions, shape ``(N,)``, dtype float32.
            For ``output_type="regression"``: continuous values.
            For ``output_type="signal"``: binary 0/1 signals.
        """

    @abstractmethod
    def save(self, path: Path) -> None:
        """Persist model state to disk.

        Parameters
        ----------
        path : Path
            Directory or file path for saving model artifacts.
        """

    @abstractmethod
    def load(self, path: Path) -> None:
        """Restore model state from disk.

        Parameters
        ----------
        path : Path
            Directory or file path from which to load model artifacts.
        """
