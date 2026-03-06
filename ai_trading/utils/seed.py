"""Seed manager — centralised reproducibility seeding.

Sets global seeds for random, numpy, and optionally PyTorch at the start
of a pipeline run. Called once by the orchestrator.

Reference: Specification §16.1, Task #048.
"""

import logging
import os
import random

import numpy as np

logger = logging.getLogger(__name__)


def set_global_seed(seed: int, deterministic_torch: bool) -> None:
    """Fix global seeds for reproducibility.

    Sets seeds for ``random``, ``numpy``, ``os.environ['PYTHONHASHSEED']``,
    and optionally PyTorch (if installed).

    Args:
        seed: Strictly positive integer used as the global seed.
        deterministic_torch: If True *and* PyTorch is available, activate
            ``torch.use_deterministic_algorithms(True)``.  When that call
            raises ``RuntimeError`` (e.g. CUDA ops without deterministic
            implementation), falls back to ``warn_only=True`` and logs a
            WARNING.  This fallback is a **documented exception** to the
            strict-no-fallback rule.

    Raises:
        TypeError: If *seed* is not an ``int`` (bool excluded).
        ValueError: If *seed* is not strictly positive (< 1).
    """
    # --- Validate seed -------------------------------------------------------
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(
            f"seed must be an int, got {type(seed).__name__}"
        )
    if seed < 1:
        raise ValueError(
            f"seed must be strictly positive (>= 1), got {seed}"
        )

    # --- Core seeds ----------------------------------------------------------
    random.seed(seed)
    np.random.seed(seed)  # noqa: NPY002 — legacy API required for global seed
    os.environ["PYTHONHASHSEED"] = str(seed)

    logger.info("Global seeds set: random, numpy, PYTHONHASHSEED = %d", seed)

    # --- Optional PyTorch seeding --------------------------------------------
    try:
        import torch  # type: ignore[import-not-found]
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
            "falling back to warn_only=True (documented exception to strict-no-fallback)"
        )
