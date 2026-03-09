"""Global seed management for reproducibility."""

from __future__ import annotations

import logging
import os
import random

import numpy as np

logger = logging.getLogger(__name__)


def set_global_seed(seed: int, deterministic_torch: bool) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"seed must be an int, got {type(seed).__name__}")
    if seed < 1:
        raise ValueError(f"seed must be strictly positive (>= 1), got {seed}")
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    logger.info("Global seeds set: random, numpy, PYTHONHASHSEED = %d", seed)
    try:
        import torch
    except ImportError:
        logger.info("PyTorch is not available — skipping torch seed setup")
        return
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    logger.info("PyTorch seeds set: manual_seed, cuda.manual_seed_all = %d", seed)
    if not deterministic_torch:
        return
    try:
        torch.use_deterministic_algorithms(True)
        logger.info("torch.use_deterministic_algorithms(True) activated")
    except RuntimeError:
        torch.use_deterministic_algorithms(True, warn_only=True)
        logger.warning(
            "torch.use_deterministic_algorithms(True) raised RuntimeError; "
            "falling back to warn_only=True"
        )
