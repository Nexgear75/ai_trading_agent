"""Feature pipeline — assemblage et orchestration.

Provides :func:`compute_features` to iterate over the configured feature
list, resolve each feature from ``FEATURE_REGISTRY``, validate required
params, compute all features, and assemble the result DataFrame.

Also provides :func:`resolve_features` to expose the resolved
``BaseFeature`` instances (needed by task #014 for warmup validation).

Task #013 — WS-3.
"""

import logging

import pandas as pd

from ai_trading.features.registry import FEATURE_REGISTRY, BaseFeature

logger = logging.getLogger(__name__)


def _to_params_dict(params_obj: object) -> dict:
    """Convert a params object (Pydantic, SimpleNamespace, or dict) to a plain dict."""
    if isinstance(params_obj, dict):
        return params_obj
    if hasattr(params_obj, "model_dump"):
        return params_obj.model_dump()
    return vars(params_obj)


def resolve_features(config: object) -> list[BaseFeature]:
    """Resolve feature instances from the registry based on config.

    Parameters
    ----------
    config
        Pipeline config with ``config.features.feature_list`` (list[str])
        and ``config.features.params`` (object or dict with feature params).

    Returns
    -------
    list[BaseFeature]
        Ordered list of instantiated features matching ``feature_list``.

    Raises
    ------
    ValueError
        If the registry is empty, a feature is unknown, the feature list
        is empty, contains duplicates, or a required param is missing.
    """
    feature_list: list[str] = config.features.feature_list

    if not feature_list:
        raise ValueError("features.feature_list is empty — at least one feature required.")

    if len(feature_list) != len(set(feature_list)):
        seen: set[str] = set()
        for name in feature_list:
            if name in seen:
                raise ValueError(
                    f"Duplicate feature in feature_list: '{name}'."
                )
            seen.add(name)

    if not FEATURE_REGISTRY:
        raise ValueError(
            "FEATURE_REGISTRY is empty — feature modules have not been imported. "
            "Ensure 'import ai_trading.features' is called before compute_features."
        )

    params_dict = _to_params_dict(config.features.params)

    instances: list[BaseFeature] = []
    for name in feature_list:
        if name not in FEATURE_REGISTRY:
            raise ValueError(
                f"Feature '{name}' not found in FEATURE_REGISTRY. "
                f"Available: {sorted(FEATURE_REGISTRY.keys())}."
            )

        cls = FEATURE_REGISTRY[name]
        instance = cls()

        # Validate required params
        for param_name in instance.required_params:
            if param_name not in params_dict:
                raise ValueError(
                    f"Feature '{name}' requires param '{param_name}' but it is "
                    f"missing from config.features.params."
                )

        instances.append(instance)

    return instances


def compute_features(ohlcv: pd.DataFrame, config: object) -> pd.DataFrame:
    """Compute all configured features and assemble into a DataFrame.

    Parameters
    ----------
    ohlcv : pd.DataFrame
        OHLCV data with columns ``open``, ``high``, ``low``, ``close``,
        ``volume``, indexed by timestamp.
    config
        Pipeline config with ``config.features.feature_list``,
        ``config.features.params``, and ``config.features.feature_version``.

    Returns
    -------
    pd.DataFrame
        DataFrame with one column per feature, ordered as in
        ``config.features.feature_list``, and indexed by ohlcv timestamps.

    Raises
    ------
    ValueError
        If the registry is empty, a feature is unknown, the feature list
        is empty, contains duplicates, or a required param is missing.
    """
    feature_version: str = config.features.feature_version
    logger.info("Computing features (version=%s)", feature_version)

    instances = resolve_features(config)

    feature_list: list[str] = config.features.feature_list
    params_dict = _to_params_dict(config.features.params)

    columns: list[pd.Series] = []
    for name, instance in zip(feature_list, instances, strict=True):
        series = instance.compute(ohlcv, params_dict)
        if len(series) != len(ohlcv):
            raise ValueError(
                f"Feature '{name}' returned {len(series)} rows, "
                f"expected {len(ohlcv)} (same as OHLCV input)."
            )
        series = series.rename(name)
        columns.append(series)

    result = pd.DataFrame({s.name: s for s in columns}, index=ohlcv.index)
    return result
