"""Feature registry and BaseFeature abstract class.

Provides a pluggable architecture for feature engineering:
- ``FEATURE_REGISTRY``: global dict mapping feature name → class.
- ``@register_feature(name)``: decorator to register a feature class.
- ``BaseFeature``: abstract base class defining the feature contract.

Each feature's ``compute()`` method must be **strictly causal**: it must only
use data at or before time *t* to produce the value at *t*. No future data
(look-ahead) is permitted.
"""

from abc import ABC, abstractmethod

import pandas as pd

# Global registry: feature name → feature class.
# Empty at import time; populated when feature modules are imported.
FEATURE_REGISTRY: dict[str, type["BaseFeature"]] = {}


def register_feature(name: str):
    """Decorator that registers a BaseFeature subclass under *name*.

    Parameters
    ----------
    name : str
        Unique identifier for the feature (e.g. ``"logret_1"``).

    Returns
    -------
    Callable
        Class decorator that registers and returns the class unchanged.

    Raises
    ------
    ValueError
        If *name* is already present in ``FEATURE_REGISTRY``.
    TypeError
        If *cls* is not a subclass of ``BaseFeature``.
    """

    def decorator(cls: type["BaseFeature"]) -> type["BaseFeature"]:
        if not (isinstance(cls, type) and issubclass(cls, BaseFeature)):
            raise TypeError(
                f"@register_feature('{name}'): {cls!r} is not a BaseFeature subclass."
            )
        if name in FEATURE_REGISTRY:
            raise ValueError(
                f"Feature '{name}' is already registered in FEATURE_REGISTRY."
            )
        FEATURE_REGISTRY[name] = cls
        return cls

    return decorator


class BaseFeature(ABC):
    """Abstract base class for all pipeline features.

    Subclasses **must** implement:
    - ``compute(ohlcv, params) -> pd.Series``
    - ``min_periods(params) -> int``

    Subclasses **must** explicitly declare the class attribute
    ``required_params: list[str]`` (even if empty ``[]``). Omitting it
    raises ``TypeError`` at class creation time (enforced by
    ``__init_subclass__``).

    Contract
    --------
    ``compute()`` must be **strictly causal**: the value at index *t* must
    depend only on OHLCV data at indices ``<= t``. Any violation is a
    look-ahead bug.
    """

    required_params: list[str] = []

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if "required_params" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must explicitly declare 'required_params' "
                f"(e.g. required_params: list[str] = []). "
                f"Inheriting the base default silently is not allowed."
            )

    @abstractmethod
    def min_periods(self, params: dict) -> int:
        """Number of leading NaN values in the output of ``compute()``.

        Equivalently, the 0-based index of the first non-NaN value.

        Example: if ``compute()`` returns ``[NaN, NaN, 0.5, ...]``,
        then ``min_periods = 2``.

        This value can be used by the pipeline and configuration to
        determine the minimum warmup period (i.e. how many leading rows
        must be excluded because they contain NaN).

        Parameters
        ----------
        params : dict
            Full ``config.features.params`` dict. The feature reads only
            the keys it needs to compute its warmup length.
        """

    @abstractmethod
    def compute(self, ohlcv: pd.DataFrame, params: dict) -> pd.Series:
        """Compute the feature from OHLCV data.

        Parameters
        ----------
        ohlcv : pd.DataFrame
            DataFrame with at least columns ``open``, ``high``, ``low``,
            ``close``, ``volume``, indexed by timestamp.
        params : dict
            Full ``config.features.params`` dict. The feature reads only
            the keys declared in ``required_params``.

        Returns
        -------
        pd.Series
            Feature values indexed by the same timestamps as *ohlcv*.
        """
