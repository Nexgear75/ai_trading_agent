"""Tests for ai_trading.utils.seed — Seed manager (#048).

Covers:
- AC1: Module exists and is importable.
- AC2: set_global_seed(42, False) fixes random, numpy, PYTHONHASHSEED.
- AC3: set_global_seed(42, True) activates torch.use_deterministic_algorithms.
- AC4: Graceful handling when PyTorch is not installed (optional import, INFO log).
- AC5: Fallback warn_only=True logged at WARNING when deterministic fails.
- AC6: Two successive calls with same seed produce identical sequences.
- AC7: Explicit error if seed is non-integer or non-positive.
- AC8: Edge cases and boundary conditions.
"""

import logging
import os
import random
import sys
from unittest import mock

import numpy as np
import pytest


class TestSeedManagerImport:
    """AC1: Module exists and is importable."""

    def test_module_importable(self):
        """The module ai_trading.utils.seed can be imported."""
        from ai_trading.utils import seed  # noqa: F401

    def test_set_global_seed_callable(self):
        """set_global_seed is a callable function."""
        from ai_trading.utils.seed import set_global_seed

        assert callable(set_global_seed)


class TestSetGlobalSeedBasic:
    """AC2: set_global_seed(42, False) fixes seeds for random, numpy, PYTHONHASHSEED."""

    def test_random_seed_fixed(self):
        """random.random() produces deterministic sequence after set_global_seed."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(42, deterministic_torch=False)
        seq1 = [random.random() for _ in range(10)]

        set_global_seed(42, deterministic_torch=False)
        seq2 = [random.random() for _ in range(10)]

        assert seq1 == seq2

    def test_numpy_seed_fixed(self):
        """numpy.random.rand() produces deterministic sequence after set_global_seed."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(42, deterministic_torch=False)
        arr1 = np.random.rand(10)

        set_global_seed(42, deterministic_torch=False)
        arr2 = np.random.rand(10)

        np.testing.assert_array_equal(arr1, arr2)

    def test_pythonhashseed_set(self):
        """os.environ['PYTHONHASHSEED'] is set to str(seed)."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(42, deterministic_torch=False)
        assert os.environ["PYTHONHASHSEED"] == "42"

    def test_pythonhashseed_different_seed(self):
        """PYTHONHASHSEED updates when seed changes."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(99, deterministic_torch=False)
        assert os.environ["PYTHONHASHSEED"] == "99"


class TestReproducibility:
    """AC6: Two successive calls with same seed produce identical sequences."""

    def test_numpy_reproducibility(self):
        """numpy.random.rand(10) identical after two calls with same seed."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(123, deterministic_torch=False)
        a = np.random.rand(10)

        set_global_seed(123, deterministic_torch=False)
        b = np.random.rand(10)

        np.testing.assert_array_equal(a, b)

    def test_random_reproducibility(self):
        """random.random() identical after two calls with same seed."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(123, deterministic_torch=False)
        v1 = random.random()

        set_global_seed(123, deterministic_torch=False)
        v2 = random.random()

        assert v1 == v2

    def test_different_seeds_produce_different_sequences(self):
        """Different seeds produce different numpy sequences."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(42, deterministic_torch=False)
        a = np.random.rand(10)

        set_global_seed(99, deterministic_torch=False)
        b = np.random.rand(10)

        assert not np.array_equal(a, b)


class TestValidation:
    """AC7: Explicit error if seed is non-integer or non-positive."""

    def test_negative_seed_raises(self):
        """Negative seed raises ValueError."""
        from ai_trading.utils.seed import set_global_seed

        with pytest.raises(ValueError, match="seed"):
            set_global_seed(-1, deterministic_torch=False)

    def test_zero_seed_raises(self):
        """Zero seed raises ValueError (strictly positive required)."""
        from ai_trading.utils.seed import set_global_seed

        with pytest.raises(ValueError, match="seed"):
            set_global_seed(0, deterministic_torch=False)

    def test_float_seed_raises(self):
        """Float seed raises TypeError."""
        from ai_trading.utils.seed import set_global_seed

        with pytest.raises(TypeError, match="seed"):
            set_global_seed(42.5, deterministic_torch=False)  # type: ignore[arg-type]

    def test_none_seed_raises(self):
        """None seed raises TypeError."""
        from ai_trading.utils.seed import set_global_seed

        with pytest.raises(TypeError, match="seed"):
            set_global_seed(None, deterministic_torch=False)  # type: ignore[arg-type]

    def test_string_seed_raises(self):
        """String seed raises TypeError."""
        from ai_trading.utils.seed import set_global_seed

        with pytest.raises(TypeError, match="seed"):
            set_global_seed("42", deterministic_torch=False)  # type: ignore[arg-type]

    def test_bool_seed_raises(self):
        """Boolean seed raises TypeError (bool is subclass of int)."""
        from ai_trading.utils.seed import set_global_seed

        with pytest.raises(TypeError, match="seed"):
            set_global_seed(True, deterministic_torch=False)  # type: ignore[arg-type]

    def test_large_seed_accepted(self):
        """Large seed (2**31 - 1) is accepted without error."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(2**31 - 1, deterministic_torch=False)
        assert os.environ["PYTHONHASHSEED"] == str(2**31 - 1)


class TestPyTorchOptional:
    """AC4: Graceful handling when PyTorch is not installed."""

    def test_no_pytorch_does_not_raise(self):
        """set_global_seed works when torch is not importable."""
        from ai_trading.utils.seed import set_global_seed

        with mock.patch.dict(sys.modules, {"torch": None}):
            # Should not raise
            set_global_seed(42, deterministic_torch=False)

    def test_no_pytorch_logs_info(self, caplog):
        """When PyTorch is unavailable, an INFO log is emitted."""
        from ai_trading.utils.seed import set_global_seed

        with mock.patch.dict(sys.modules, {"torch": None}):
            with caplog.at_level(logging.INFO, logger="ai_trading.utils.seed"):
                set_global_seed(42, deterministic_torch=True)

        assert any("torch" in r.message.lower() or "pytorch" in r.message.lower()
                    for r in caplog.records if r.levelno == logging.INFO)

    def test_no_pytorch_deterministic_true_no_crash(self):
        """deterministic_torch=True with no PyTorch doesn't crash."""
        from ai_trading.utils.seed import set_global_seed

        with mock.patch.dict(sys.modules, {"torch": None}):
            set_global_seed(42, deterministic_torch=True)


class TestPyTorchDeterministic:
    """AC3 & AC5: PyTorch deterministic algorithms activation and fallback."""

    def test_deterministic_torch_calls_use_deterministic(self):
        """deterministic_torch=True calls torch.use_deterministic_algorithms(True)."""
        from ai_trading.utils.seed import set_global_seed

        mock_torch = mock.MagicMock()
        mock_torch.use_deterministic_algorithms = mock.MagicMock()
        mock_torch.cuda = mock.MagicMock()

        with mock.patch.dict(sys.modules, {"torch": mock_torch}):
            set_global_seed(42, deterministic_torch=True)

        mock_torch.manual_seed.assert_called_once_with(42)
        mock_torch.cuda.manual_seed_all.assert_called_once_with(42)
        mock_torch.use_deterministic_algorithms.assert_called_with(True)

    def test_deterministic_false_skips_deterministic_algorithms(self):
        """deterministic_torch=False does not call use_deterministic_algorithms."""
        from ai_trading.utils.seed import set_global_seed

        mock_torch = mock.MagicMock()

        with mock.patch.dict(sys.modules, {"torch": mock_torch}):
            set_global_seed(42, deterministic_torch=False)

        mock_torch.manual_seed.assert_called_once_with(42)
        mock_torch.cuda.manual_seed_all.assert_called_once_with(42)
        mock_torch.use_deterministic_algorithms.assert_not_called()

    def test_deterministic_fallback_warn_only(self, caplog):
        """AC5: RuntimeError triggers warn_only=True fallback with WARNING log."""
        from ai_trading.utils.seed import set_global_seed

        mock_torch = mock.MagicMock()
        # First call raises RuntimeError, second call (with warn_only) succeeds
        mock_torch.use_deterministic_algorithms = mock.MagicMock(
            side_effect=[RuntimeError("CUDA op not deterministic"), None]
        )
        mock_torch.cuda = mock.MagicMock()

        with mock.patch.dict(sys.modules, {"torch": mock_torch}):
            with caplog.at_level(logging.WARNING, logger="ai_trading.utils.seed"):
                set_global_seed(42, deterministic_torch=True)

        # Verify warn_only=True was called
        calls = mock_torch.use_deterministic_algorithms.call_args_list
        assert len(calls) == 2
        assert calls[0] == mock.call(True)
        assert calls[1] == mock.call(True, warn_only=True)

        # Verify WARNING was logged
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1
        assert any("warn_only" in r.message.lower() or "deterministic" in r.message.lower()
                    for r in warning_records)


class TestEdgeCases:
    """AC8: Edge and boundary conditions."""

    def test_seed_one_accepted(self):
        """Minimum valid seed (1) is accepted."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(1, deterministic_torch=False)
        assert os.environ["PYTHONHASHSEED"] == "1"

    def test_consecutive_calls_reset_state(self):
        """Calling set_global_seed twice resets all generators."""
        from ai_trading.utils.seed import set_global_seed

        set_global_seed(42, deterministic_torch=False)
        _ = np.random.rand(5)
        _ = random.random()

        # Reset with same seed
        set_global_seed(42, deterministic_torch=False)
        a = np.random.rand(10)

        # Reset again
        set_global_seed(42, deterministic_torch=False)
        b = np.random.rand(10)

        np.testing.assert_array_equal(a, b)
