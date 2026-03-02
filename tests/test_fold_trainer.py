"""Tests for FoldTrainer — orchestration scale → fit → predict → save.

Task #028 (WS-6).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from ai_trading.config import load_config
from ai_trading.data.scaler import create_scaler
from ai_trading.models.dummy import DummyModel
from ai_trading.training.trainer import FoldTrainer

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def config():
    """Load default pipeline config."""
    return load_config(str(PROJECT_ROOT / "configs" / "default.yaml"))


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def make_fold_data(rng):
    """Factory for synthetic train/val/test 3D arrays and labels."""

    def _make(
        n_train: int = 50,
        n_val: int = 20,
        n_test: int = 10,
        seq_len: int = 24,
        n_features: int = 9,
    ):
        X_train = rng.standard_normal((n_train, seq_len, n_features)).astype(np.float32)
        y_train = rng.standard_normal(n_train).astype(np.float32)
        X_val = rng.standard_normal((n_val, seq_len, n_features)).astype(np.float32)
        y_val = rng.standard_normal(n_val).astype(np.float32)
        X_test = rng.standard_normal((n_test, seq_len, n_features)).astype(np.float32)
        return X_train, y_train, X_val, y_val, X_test

    return _make


# ---------------------------------------------------------------------------
# Nominal: full workflow scale → fit → predict → save
# ---------------------------------------------------------------------------


class TestFoldTrainerNominal:
    """Nominal workflow: scale → fit → predict → save with DummyModel."""

    def test_full_workflow_no_crash(self, config, make_fold_data, tmp_path):
        """#028 — Full workflow runs without crash using DummyModel."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        result = trainer.train_fold(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            run_dir=tmp_path,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        assert "y_hat_val" in result
        assert "y_hat_test" in result
        assert "artifacts" in result
        assert "scaler" in result

    def test_y_hat_val_shape(self, config, make_fold_data, tmp_path):
        """#028 — y_hat_val has shape (N_val,)."""
        n_val = 20
        X_train, y_train, X_val, y_val, X_test = make_fold_data(n_val=n_val)
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        result = trainer.train_fold(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            run_dir=tmp_path,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        assert result["y_hat_val"].shape == (n_val,)
        assert result["y_hat_val"].dtype == np.float32

    def test_y_hat_test_shape(self, config, make_fold_data, tmp_path):
        """#028 — y_hat_test has shape (N_test,)."""
        n_test = 15
        X_train, y_train, X_val, y_val, X_test = make_fold_data(n_test=n_test)
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        result = trainer.train_fold(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            run_dir=tmp_path,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        assert result["y_hat_test"].shape == (n_test,)
        assert result["y_hat_test"].dtype == np.float32

    def test_model_save_called(self, config, make_fold_data, tmp_path):
        """#028 — model.save() is called with run_dir / 'model'."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with patch.object(model, "save", wraps=model.save) as mock_save:
            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=None,
                meta_val=None,
                ohlcv=None,
            )
            mock_save.assert_called_once_with(tmp_path / "model")

    def test_model_save_creates_artifact(self, config, make_fold_data, tmp_path):
        """#028 — After train_fold, model artifact exists on disk."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        trainer.train_fold(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            run_dir=tmp_path,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        model_dir = tmp_path / "model"
        assert model_dir.exists()

    def test_scaler_returned_in_result(self, config, make_fold_data, tmp_path):
        """#028 — Result contains the fitted scaler for traceability."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        result = trainer.train_fold(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            run_dir=tmp_path,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        scaler = result["scaler"]
        # Scaler must be fitted (has mean_ and std_ for StandardScaler)
        assert scaler.mean_ is not None


# ---------------------------------------------------------------------------
# Scaling: anti-leak checks
# ---------------------------------------------------------------------------


class TestFoldTrainerScaling:
    """Verify scaler is fit on X_train only (anti-leak)."""

    def test_scaler_fit_called_on_train_only(self, config, make_fold_data, tmp_path):
        """#028 — scaler.fit() must be called with X_train only."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with patch(
            "ai_trading.training.trainer.create_scaler"
        ) as mock_factory:
            mock_scaler = MagicMock()
            mock_scaler.fit.return_value = mock_scaler
            mock_scaler.transform.side_effect = lambda x: x
            mock_factory.return_value = mock_scaler

            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=None,
                meta_val=None,
                ohlcv=None,
            )

            # fit called exactly once with X_train
            mock_scaler.fit.assert_called_once()
            fit_arg = mock_scaler.fit.call_args[0][0]
            np.testing.assert_array_equal(fit_arg, X_train)

    def test_scaler_transform_called_on_all_splits(
        self, config, make_fold_data, tmp_path
    ):
        """#028 — scaler.transform() called on train, val, and test."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with patch(
            "ai_trading.training.trainer.create_scaler"
        ) as mock_factory:
            mock_scaler = MagicMock()
            mock_scaler.fit.return_value = mock_scaler
            mock_scaler.transform.side_effect = lambda x: x
            mock_factory.return_value = mock_scaler

            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=None,
                meta_val=None,
                ohlcv=None,
            )

            assert mock_scaler.transform.call_count == 3
            calls = mock_scaler.transform.call_args_list
            np.testing.assert_array_equal(calls[0][0][0], X_train)
            np.testing.assert_array_equal(calls[1][0][0], X_val)
            np.testing.assert_array_equal(calls[2][0][0], X_test)

    def test_anti_leak_perturbation(self, config, tmp_path):
        """#028 — Perturbing test data does not affect val predictions.

        Anti-leak: scaler fit on train → val predictions must not change
        when test data is modified.
        """
        rng1 = np.random.default_rng(99)
        n_train, n_val, n_test, L, F = 40, 15, 10, 24, 9
        X_train = rng1.standard_normal((n_train, L, F)).astype(np.float32)
        y_train = rng1.standard_normal(n_train).astype(np.float32)
        X_val = rng1.standard_normal((n_val, L, F)).astype(np.float32)
        y_val = rng1.standard_normal(n_val).astype(np.float32)
        X_test_a = rng1.standard_normal((n_test, L, F)).astype(np.float32)
        X_test_b = rng1.standard_normal((n_test, L, F)).astype(np.float32) * 100

        model_a = DummyModel(seed=7)
        model_b = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        dir_a = tmp_path / "a"
        dir_a.mkdir()
        result_a = trainer.train_fold(
            model=model_a,
            X_train=X_train.copy(),
            y_train=y_train.copy(),
            X_val=X_val.copy(),
            y_val=y_val.copy(),
            X_test=X_test_a,
            run_dir=dir_a,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        dir_b = tmp_path / "b"
        dir_b.mkdir()
        result_b = trainer.train_fold(
            model=model_b,
            X_train=X_train.copy(),
            y_train=y_train.copy(),
            X_val=X_val.copy(),
            y_val=y_val.copy(),
            X_test=X_test_b,
            run_dir=dir_b,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        np.testing.assert_array_equal(
            result_a["y_hat_val"],
            result_b["y_hat_val"],
        )


# ---------------------------------------------------------------------------
# model.fit() arguments
# ---------------------------------------------------------------------------


class TestFoldTrainerModelFit:
    """Verify model.fit() receives correct arguments."""

    def test_fit_receives_scaled_data(self, config, make_fold_data, tmp_path):
        """#028 — model.fit() receives scaled X_train and X_val, not raw."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with patch.object(model, "fit", wraps=model.fit) as mock_fit:
            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=None,
                meta_val=None,
                ohlcv=None,
            )

            mock_fit.assert_called_once()
            call_kwargs = mock_fit.call_args
            kw = call_kwargs[1] or {}
            fit_X_train = kw["X_train"] if "X_train" in kw else call_kwargs[0][0]

            # Scaled data should differ from raw (unless degenerate)
            # We check that scaler was applied — mean should be closer to 0
            # than original data
            scaler = create_scaler(config.scaling)
            scaler.fit(X_train)
            expected_X_train = scaler.transform(X_train)
            np.testing.assert_allclose(fit_X_train, expected_X_train, rtol=1e-5)

    def test_fit_receives_meta_train_meta_val_ohlcv(
        self, config, make_fold_data, tmp_path
    ):
        """#028 — model.fit() receives meta_train, meta_val, and ohlcv."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        meta_train = {"foo": "bar"}
        meta_val = {"baz": 42}
        ohlcv = "ohlcv_placeholder"

        with patch.object(model, "fit", wraps=model.fit) as mock_fit:
            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=meta_train,
                meta_val=meta_val,
                ohlcv=ohlcv,
            )

            mock_fit.assert_called_once()
            _, kwargs = mock_fit.call_args
            assert kwargs["meta_train"] is meta_train
            assert kwargs["meta_val"] is meta_val
            assert kwargs["ohlcv"] is ohlcv

    def test_fit_receives_config_and_run_dir(
        self, config, make_fold_data, tmp_path
    ):
        """#028 — model.fit() receives config and run_dir."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with patch.object(model, "fit", wraps=model.fit) as mock_fit:
            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=None,
                meta_val=None,
                ohlcv=None,
            )

            _, kwargs = mock_fit.call_args
            assert kwargs["config"] is config
            assert kwargs["run_dir"] == tmp_path


# ---------------------------------------------------------------------------
# Patience / config-driven
# ---------------------------------------------------------------------------


class TestFoldTrainerPatience:
    """Verify patience is configurable via config."""

    def test_patience_from_config(self, config):
        """#028 — FoldTrainer reads early_stopping_patience from config."""
        trainer = FoldTrainer(config=config)
        # Trainer stores the config, which contains early_stopping_patience
        assert trainer._config.training.early_stopping_patience == 10

    def test_patience_transmitted_to_model(
        self, config, make_fold_data, tmp_path
    ):
        """#028 — Patience value in config is passed to model.fit() via config object."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with patch.object(model, "fit", wraps=model.fit) as mock_fit:
            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=None,
                meta_val=None,
                ohlcv=None,
            )

            _, kwargs = mock_fit.call_args
            passed_config = kwargs["config"]
            assert passed_config.training.early_stopping_patience == 10


# ---------------------------------------------------------------------------
# Predict uses scaled data
# ---------------------------------------------------------------------------


class TestFoldTrainerPredict:
    """Verify model.predict() receives scaled data."""

    def test_predict_receives_scaled_val(self, config, make_fold_data, tmp_path):
        """#028 — model.predict() for val receives scaler.transform(X_val)."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with patch.object(model, "predict", wraps=model.predict) as mock_predict:
            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=None,
                meta_val=None,
                ohlcv=None,
            )

            assert mock_predict.call_count == 2
            # First call: val prediction
            kw0 = mock_predict.call_args_list[0][1] or {}
            val_call_X = kw0["X"] if "X" in kw0 else mock_predict.call_args_list[0][0][0]

            scaler = create_scaler(config.scaling)
            scaler.fit(X_train)
            expected_X_val = scaler.transform(X_val)
            np.testing.assert_allclose(val_call_X, expected_X_val, rtol=1e-5)

    def test_predict_receives_scaled_test(self, config, make_fold_data, tmp_path):
        """#028 — model.predict() for test receives scaler.transform(X_test)."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with patch.object(model, "predict", wraps=model.predict) as mock_predict:
            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=None,
                meta_val=None,
                ohlcv=None,
            )

            # Second call: test prediction
            kw1 = mock_predict.call_args_list[1][1] or {}
            test_call_X = kw1["X"] if "X" in kw1 else mock_predict.call_args_list[1][0][0]

            scaler = create_scaler(config.scaling)
            scaler.fit(X_train)
            expected_X_test = scaler.transform(X_test)
            np.testing.assert_allclose(test_call_X, expected_X_test, rtol=1e-5)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestFoldTrainerEdgeCases:
    """Edge cases and error scenarios."""

    def test_single_sample_per_split(self, config, tmp_path):
        """#028 — Minimum viable: 1 sample each for train/val/test."""
        rng = np.random.default_rng(99)
        L, F = 24, 9
        X_train = rng.standard_normal((1, L, F)).astype(np.float32)
        y_train = rng.standard_normal(1).astype(np.float32)
        X_val = rng.standard_normal((1, L, F)).astype(np.float32)
        y_val = rng.standard_normal(1).astype(np.float32)
        X_test = rng.standard_normal((1, L, F)).astype(np.float32)

        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        result = trainer.train_fold(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            run_dir=tmp_path,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        assert result["y_hat_val"].shape == (1,)
        assert result["y_hat_test"].shape == (1,)

    def test_artifacts_from_model_returned(self, config, make_fold_data, tmp_path):
        """#028 — Artifacts dict from model.fit() is returned as-is."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        # DummyModel.fit() returns {}
        result = trainer.train_fold(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            run_dir=tmp_path,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        assert result["artifacts"] == {}

    def test_model_fit_error_propagates(self, config, make_fold_data, tmp_path):
        """#028 — If model.fit() raises, the error propagates (no fallback)."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with (
            patch.object(model, "fit", side_effect=RuntimeError("boom")),
            pytest.raises(RuntimeError, match="boom"),
        ):
            trainer.train_fold(
                model=model,
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                X_test=X_test,
                run_dir=tmp_path,
                meta_train=None,
                meta_val=None,
                ohlcv=None,
            )

    def test_scaler_error_propagates(self, config, make_fold_data, tmp_path):
        """#028 — If scaler.fit() raises, the error propagates (no fallback)."""
        X_train, y_train, X_val, y_val, X_test = make_fold_data()
        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        with patch(
            "ai_trading.training.trainer.create_scaler"
        ) as mock_factory:
            mock_scaler = MagicMock()
            mock_scaler.fit.side_effect = ValueError("NaN in X_train before scaling")
            mock_factory.return_value = mock_scaler

            with pytest.raises(ValueError, match="NaN in X_train"):
                trainer.train_fold(
                    model=model,
                    X_train=X_train,
                    y_train=y_train,
                    X_val=X_val,
                    y_val=y_val,
                    X_test=X_test,
                    run_dir=tmp_path,
                    meta_train=None,
                    meta_val=None,
                    ohlcv=None,
                )

    def test_different_n_features_preserved(self, config, tmp_path):
        """#028 — Works with different feature counts."""
        rng = np.random.default_rng(55)
        n_features = 3
        L = 24
        X_train = rng.standard_normal((30, L, n_features)).astype(np.float32)
        y_train = rng.standard_normal(30).astype(np.float32)
        X_val = rng.standard_normal((10, L, n_features)).astype(np.float32)
        y_val = rng.standard_normal(10).astype(np.float32)
        X_test = rng.standard_normal((5, L, n_features)).astype(np.float32)

        model = DummyModel(seed=7)
        trainer = FoldTrainer(config=config)

        result = trainer.train_fold(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            run_dir=tmp_path,
            meta_train=None,
            meta_val=None,
            ohlcv=None,
        )

        assert result["y_hat_val"].shape == (10,)
        assert result["y_hat_test"].shape == (5,)
