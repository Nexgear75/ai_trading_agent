"""Walk-forward splitter for rolling cross-validation (WS-4.5, WS-4.6).

Computes fold boundaries in UTC dates and returns index-based splits
for train / val / test partitions with embargo gap and purge.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import timedelta

import numpy as np
import pandas as pd

from ai_trading.config import SplitsConfig
from ai_trading.data.timeframes import parse_timeframe

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FoldInfo:
    """Immutable descriptor for a single walk-forward fold."""

    train_indices: np.ndarray
    val_indices: np.ndarray
    test_indices: np.ndarray

    # UTC bounds (inclusive)
    train_start: pd.Timestamp
    train_only_end: pd.Timestamp
    val_start: pd.Timestamp
    train_val_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp

    # Sample counters
    n_train: int
    n_val: int
    n_test: int

    # Purge cutoff (set by apply_purge, None before purge)
    purge_cutoff: pd.Timestamp | None = field(default=None)


def apply_purge(
    fold: FoldInfo,
    timestamps: pd.DatetimeIndex,
    horizon_H_bars: int,  # noqa: N803
    embargo_bars: int,
    delta: timedelta,
) -> FoldInfo:
    """Apply purge to a fold, removing samples whose labels leak into test zone.

    Implements the purge rule from spec §8.2:
    ``purge_cutoff = test_start - embargo_bars * Δ``
    A sample *t* is kept in train/val iff ``t + H * Δ <= purge_cutoff``.

    Parameters
    ----------
    fold
        Unpurged fold from :class:`WalkForwardSplitter`.
    timestamps
        Full DatetimeIndex of the dataset.
    horizon_H_bars
        Label look-ahead horizon in bars (``label.horizon_H_bars``).
    embargo_bars
        Embargo gap in bars (``splits.embargo_bars``).
    delta
        Candle duration (e.g. ``timedelta(hours=1)``).

    Returns
    -------
    FoldInfo
        New fold with filtered train/val indices and ``purge_cutoff`` set.
    """
    purge_cutoff = fold.test_start - embargo_bars * delta
    max_allowed = purge_cutoff - horizon_H_bars * delta

    # Filter train indices
    train_ts = timestamps[fold.train_indices]
    train_keep = train_ts <= max_allowed
    new_train_indices = fold.train_indices[train_keep]

    # Filter val indices
    val_ts = timestamps[fold.val_indices]
    val_keep = val_ts <= max_allowed
    new_val_indices = fold.val_indices[val_keep]

    return FoldInfo(
        train_indices=new_train_indices,
        val_indices=new_val_indices,
        test_indices=fold.test_indices,
        train_start=fold.train_start,
        train_only_end=fold.train_only_end,
        val_start=fold.val_start,
        train_val_end=fold.train_val_end,
        test_start=fold.test_start,
        test_end=fold.test_end,
        n_train=len(new_train_indices),
        n_val=len(new_val_indices),
        n_test=fold.n_test,
        purge_cutoff=purge_cutoff,
    )


class WalkForwardSplitter:
    """Rolling walk-forward splitter with date-based boundaries.

    Parameters
    ----------
    splits_config
        Configuration object with attributes: ``train_days``, ``test_days``,
        ``step_days``, ``val_frac_in_train``, ``embargo_bars``,
        ``min_samples_train``, ``min_samples_test``.
    timeframe
        Candle timeframe string (e.g. ``"1h"``).
    """

    def __init__(self, splits_config: SplitsConfig, timeframe: str) -> None:
        self._cfg = splits_config
        self._delta = parse_timeframe(timeframe)

    def split(self, timestamps: pd.DatetimeIndex) -> list[FoldInfo]:
        """Compute walk-forward folds over *timestamps*.

        Returns
        -------
        list[FoldInfo]
            Valid folds after truncation and min-samples filtering.

        Raises
        ------
        ValueError
            If no valid folds remain after filtering.
        """
        cfg = self._cfg
        delta = self._delta

        if len(timestamps) == 0:
            raise ValueError("timestamps must not be empty")

        dataset_start = timestamps[0]
        dataset_end = timestamps[-1]

        val_days = math.floor(cfg.train_days * cfg.val_frac_in_train)
        if val_days < 1:
            raise ValueError(
                f"val_days={val_days} (floor({cfg.train_days} * "
                f"{cfg.val_frac_in_train})): validation window is empty. "
                f"Increase train_days or val_frac_in_train."
            )

        # Theoretical upper bound on fold count
        total_days = (dataset_end - dataset_start).days + 1
        n_folds_theoretical = max(
            math.floor((total_days - cfg.train_days) / cfg.step_days), 0
        )

        folds: list[FoldInfo] = []
        n_excluded = 0

        for k in range(n_folds_theoretical):
            train_start = dataset_start + timedelta(days=k * cfg.step_days)
            train_val_end = train_start + timedelta(days=cfg.train_days) - delta
            val_start = train_start + timedelta(days=cfg.train_days - val_days)
            train_only_end = val_start - delta
            test_start = (
                train_start
                + timedelta(days=cfg.train_days)
                + cfg.embargo_bars * delta
            )
            test_end = test_start + timedelta(days=cfg.test_days) - delta

            # Truncation: test_end must fit within dataset
            if test_end > dataset_end:
                n_excluded += 1
                continue

            # Select indices by date bounds (inclusive)
            train_mask = (timestamps >= train_start) & (timestamps <= train_only_end)
            val_mask = (timestamps >= val_start) & (timestamps <= train_val_end)
            test_mask = (timestamps >= test_start) & (timestamps <= test_end)

            train_idx = np.where(train_mask)[0]
            val_idx = np.where(val_mask)[0]
            test_idx = np.where(test_mask)[0]

            n_train = len(train_idx)
            n_val = len(val_idx)
            n_test = len(test_idx)

            # Min-samples filtering
            if n_train < cfg.min_samples_train:
                logger.warning(
                    "Fold k=%d excluded: n_train=%d < min_samples_train=%d",
                    k, n_train, cfg.min_samples_train,
                )
                n_excluded += 1
                continue

            if n_test < cfg.min_samples_test:
                logger.warning(
                    "Fold k=%d excluded: n_test=%d < min_samples_test=%d",
                    k, n_test, cfg.min_samples_test,
                )
                n_excluded += 1
                continue

            folds.append(
                FoldInfo(
                    train_indices=train_idx,
                    val_indices=val_idx,
                    test_indices=test_idx,
                    train_start=train_start,
                    train_only_end=train_only_end,
                    val_start=val_start,
                    train_val_end=train_val_end,
                    test_start=test_start,
                    test_end=test_end,
                    n_train=n_train,
                    n_val=n_val,
                    n_test=n_test,
                )
            )

        n_valid = len(folds)

        logger.info(
            "Walk-forward split: n_folds_theoretical=%d, n_folds_valid=%d, "
            "n_folds_excluded=%d",
            n_folds_theoretical, n_valid, n_excluded,
        )

        if n_valid == 0:
            if n_folds_theoretical == 0:
                raise ValueError(
                    "No valid folds: dataset too short for the given "
                    "split parameters"
                )
            raise ValueError(
                f"No valid folds: {n_excluded} fold(s) excluded "
                f"(truncation or min_samples filtering)"
            )

        return folds
