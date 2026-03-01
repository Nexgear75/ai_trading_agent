"""Warmup validation — mask computation and NaN checks.

Applies the warmup zone (``min_warmup`` leading bars) and verifies the
absence of residual NaN values in the valid zone. Combines the warmup mask
with the gap-based ``valid_mask`` from WS-2.3 (task #006) to produce the
final validity mask.

Reference: spec §6.6, plan WS-3.7.
Task #014 — WS-3.
"""

import numpy as np
import pandas as pd


def apply_warmup(
    features_df: pd.DataFrame,
    valid_mask: np.ndarray,
    min_warmup: int,
    feature_instances: list,
    params: dict | None = None,
) -> np.ndarray:
    """Apply warmup masking and validate absence of NaN in valid zone.

    Parameters
    ----------
    features_df : pd.DataFrame
        Feature DataFrame of shape ``(N, F)`` produced by the pipeline.
    valid_mask : np.ndarray
        Boolean array of shape ``(N,)`` from gap/missing candle detection
        (WS-2.3, task #006). ``True`` = bar is structurally valid.
    min_warmup : int
        Number of leading bars to invalidate (from ``config.window.min_warmup``).
    feature_instances : list[BaseFeature]
        Resolved feature instances (with ``min_periods(params)`` method).
    params : dict | None
        Feature params dict (from ``config.features.params``), passed to
        ``min_periods()``. If ``None``, an empty dict is used.

    Returns
    -------
    np.ndarray
        Boolean array of shape ``(N,)``. ``True`` = bar is valid for use.

    Raises
    ------
    ValueError
        If ``feature_instances`` is empty, if ``min_warmup < max(min_periods)``,
        if ``valid_mask`` length doesn't match ``features_df``, or if NaN
        values are found in the valid zone.
    """
    n = len(features_df)

    if len(feature_instances) == 0:
        raise ValueError(
            "feature_instances is empty — at least one feature required "
            "to compute warmup validation."
        )

    if len(valid_mask) != n:
        raise ValueError(
            f"valid_mask length ({len(valid_mask)}) does not match "
            f"features_df length ({n})."
        )

    # Resolve params for min_periods calls
    params_dict = params if params is not None else {}

    # Runtime assertion: min_warmup >= max(min_periods)
    max_min_periods = max(
        inst.min_periods(params_dict) for inst in feature_instances
    )
    if min_warmup < max_min_periods:
        raise ValueError(
            f"min_warmup ({min_warmup}) must be >= max(min_periods) "
            f"({max_min_periods}). The warmup zone does not cover all "
            f"feature NaN prefixes."
        )

    # Build warmup mask: False for the first min_warmup rows, True after
    warmup_mask = np.zeros(n, dtype=bool)
    if min_warmup < n:
        warmup_mask[min_warmup:] = True

    # Combine: final_mask = warmup_mask AND valid_mask
    final_mask = warmup_mask & valid_mask

    # Check for residual NaN in the valid zone
    valid_zone = features_df.values[final_mask]
    if np.any(np.isnan(valid_zone)):
        nan_count = int(np.sum(np.isnan(valid_zone)))
        raise ValueError(
            f"NaN values detected in the valid zone (post-warmup, post-gap mask): "
            f"{nan_count} NaN(s) found. This indicates a feature computation bug "
            f"or insufficient warmup."
        )

    return final_mask
