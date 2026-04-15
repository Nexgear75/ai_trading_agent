"""Tests pour le module PatchTST : architecture, data_preparator, training, evaluation."""

import os

import numpy as np
import pandas as pd
import pytest
import torch

from config import get_timeframe_config, get_patchtst_config
from data.features.pipeline import get_feature_columns, FEATURE_COLUMNS


# ----- Fixtures ----- #

@pytest.fixture(autouse=True)
def _force_cpu(monkeypatch):
    """Force le device CPU pour éviter les crashs MPS dans les tests."""
    monkeypatch.setattr("torch.mps.is_available", lambda: False)
    torch.manual_seed(42)


@pytest.fixture
def synthetic_csv(tmp_path):
    """Génère un CSV synthétique imitant la sortie de data/main.py (1d)."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    feature_cols = FEATURE_COLUMNS
    data = {"symbol": ["BTC_USDT"] * n, "close": 30000 + np.cumsum(np.random.randn(n) * 100)}
    for col in feature_cols:
        data[col] = np.random.randn(n) * 0.01
    data["label"] = np.random.choice([-1, 0, 1], size=n)
    df = pd.DataFrame(data, index=dates)
    df.index.name = "timestamp"

    out_dir = tmp_path / "output" / "1d"
    out_dir.mkdir(parents=True)
    csv_path = out_dir / "BTC_USDT.csv"
    df.to_csv(csv_path)
    full_path = out_dir / "full_dataset.csv"
    df.to_csv(full_path)
    return tmp_path


@pytest.fixture
def _patch_output(synthetic_csv, monkeypatch):
    """Patch get_timeframe_config pour pointer output_path vers le CSV synthétique."""
    original = get_timeframe_config

    def patched(timeframe="1d"):
        cfg = original(timeframe)
        cfg["output_path"] = str(synthetic_csv / "output" / timeframe)
        return cfg

    monkeypatch.setattr("config.get_timeframe_config", patched)
    monkeypatch.setattr("models.patch_tst.data_preparator.get_timeframe_config", patched)
    monkeypatch.setattr("models.patch_tst.evaluation.get_timeframe_config", patched)
    monkeypatch.setattr("utils.dataset_loader.get_timeframe_config", patched)


# ----- Tests architecture ----- #

class TestPatchTSTModel:
    """Tests pour l'architecture PatchTST."""

    def test_forward_shape(self):
        """Le forward pass produit un tenseur de shape (batch,)."""
        from models.patch_tst.PatchTST import PatchTST

        model = PatchTST(
            window_size=30, n_features=16,
            patch_len=6, stride=3, d_model=32, n_heads=4,
            n_layers=1, d_ff=64, dropout=0.0, dropout_fc=0.0,
        )
        x = torch.randn(4, 30, 16)
        out = model(x)
        assert out.shape == (4,)

    def test_num_patches_calculation(self):
        """num_patches est correctement calculé."""
        from models.patch_tst.PatchTST import PatchTST

        model = PatchTST(window_size=30, n_features=16, patch_len=6, stride=3)
        # (30 - 6) // 3 + 1 = 9
        assert model.num_patches == 9

    def test_gradient_flows(self):
        """Les gradients se propagent jusqu'à la couche de projection."""
        from models.patch_tst.PatchTST import PatchTST

        model = PatchTST(
            window_size=30, n_features=16,
            patch_len=6, stride=3, d_model=32, n_heads=4,
            n_layers=1, d_ff=64,
        )
        x = torch.randn(2, 30, 16)
        out = model(x)
        loss = out.sum()
        loss.backward()
        assert model.patch_proj.weight.grad is not None
        assert model.patch_proj.weight.grad.abs().sum() > 0

    def test_different_batch_sizes(self):
        """Le modèle fonctionne avec différentes tailles de batch."""
        from models.patch_tst.PatchTST import PatchTST

        model = PatchTST(
            window_size=30, n_features=16,
            patch_len=6, stride=3, d_model=32, n_heads=4,
            n_layers=1, d_ff=64,
        )
        model.eval()
        for bs in [1, 8, 32]:
            x = torch.randn(bs, 30, 16)
            out = model(x)
            assert out.shape == (bs,)

    def test_1h_config_shape(self):
        """Le modèle fonctionne avec la config 1h (window=72)."""
        from models.patch_tst.PatchTST import PatchTST

        model = PatchTST(
            window_size=72, n_features=24,
            patch_len=12, stride=6, d_model=64, n_heads=4,
            n_layers=2, d_ff=128,
        )
        x = torch.randn(2, 72, 24)
        out = model(x)
        assert out.shape == (2,)
        # (72 - 12) // 6 + 1 = 11
        assert model.num_patches == 11


# ----- Tests data_preparator ----- #

class TestDataPreparator:
    """Tests pour prepare_data (inlined)."""

    @pytest.mark.usefixtures("_patch_output")
    def test_shapes_3d(self):
        """Les DataLoaders contiennent des tenseurs 3D [batch, window, features]."""
        from models.patch_tst.data_preparator import prepare_data

        train_loader, val_loader, _, _, _, _, _ = prepare_data(
            symbol="BTC", timeframe="1d", batch_size=16
        )
        X_batch, y_batch = next(iter(train_loader))
        tf_config = get_timeframe_config("1d")
        n_features = len(get_feature_columns("1d"))

        assert X_batch.ndim == 3
        assert X_batch.shape[1] == tf_config["window_size"]
        assert X_batch.shape[2] == n_features
        assert y_batch.ndim == 1

    @pytest.mark.usefixtures("_patch_output")
    def test_no_nan(self):
        """Aucun NaN dans les tenseurs."""
        from models.patch_tst.data_preparator import prepare_data

        train_loader, val_loader, _, _, _, _, _ = prepare_data(
            symbol="BTC", timeframe="1d", batch_size=256
        )
        for X_batch, y_batch in train_loader:
            assert not torch.isnan(X_batch).any()
            assert not torch.isnan(y_batch).any()

    def test_minimal_history_raises(self, tmp_path, monkeypatch):
        """Un historique produisant une seule fenêtre lève ValueError."""
        np.random.seed(42)
        # 1d: window=30, horizon=3 → 34 lignes = 1 fenêtre après dropna
        n = 34
        dates = pd.date_range("2022-01-01", periods=n, freq="D")
        data = {"symbol": ["BTC_USDT"] * n,
                "close": 30000 + np.arange(n, dtype=float)}
        for col in FEATURE_COLUMNS:
            data[col] = np.linspace(0.0, 1.0, n)
        data["label"] = np.random.choice([-1, 0, 1], size=n)
        df = pd.DataFrame(data, index=dates)
        df.index.name = "timestamp"
        out_dir = tmp_path / "output" / "1d"
        out_dir.mkdir(parents=True)
        df.to_csv(out_dir / "BTC_USDT.csv")
        df.to_csv(out_dir / "full_dataset.csv")

        original = get_timeframe_config

        def patched(timeframe="1d"):
            cfg = original(timeframe)
            cfg["output_path"] = str(tmp_path / "output" / timeframe)
            return cfg

        monkeypatch.setattr("config.get_timeframe_config", patched)
        monkeypatch.setattr("models.patch_tst.data_preparator.get_timeframe_config", patched)
        monkeypatch.setattr("utils.dataset_loader.get_timeframe_config", patched)

        from models.patch_tst.data_preparator import prepare_data

        with pytest.raises(ValueError, match="No training samples"):
            prepare_data(symbol="BTC", timeframe="1d")


# ----- Tests training ----- #

class TestTraining:
    """Tests pour train."""

    @pytest.mark.usefixtures("_patch_output")
    def test_train_saves_checkpoint(self, tmp_path, monkeypatch):
        """train() produit un modèle .pth et un scalers .joblib."""
        checkpoint_dir = str(tmp_path / "ckpt" / "1d")
        paths = {
            "dir": checkpoint_dir,
            "model": os.path.join(checkpoint_dir, "best_model.pth"),
            "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
        }
        monkeypatch.setattr(
            "models.patch_tst.training._get_checkpoint_paths",
            lambda tf: paths,
        )
        # Config minimale pour la vitesse
        monkeypatch.setattr(
            "models.patch_tst.training.get_patchtst_config",
            lambda tf: {
                "patch_len": 6, "stride": 3, "d_model": 16, "n_heads": 4,
                "n_layers": 1, "d_ff": 32, "dropout": 0.0, "dropout_fc": 0.0,
            },
        )

        from models.patch_tst.training import train

        model, feat_scaler, tgt_scaler = train(
            symbol="BTC", timeframe="1d", epochs=2, batch_size=32, patience=5
        )

        assert os.path.isfile(paths["model"])
        assert os.path.isfile(paths["scalers"])

    @pytest.mark.usefixtures("_patch_output")
    def test_checkpoint_metadata(self, tmp_path, monkeypatch):
        """Le checkpoint contient les métadonnées PatchTST."""
        import joblib as jl

        checkpoint_dir = str(tmp_path / "ckpt2" / "1d")
        paths = {
            "dir": checkpoint_dir,
            "model": os.path.join(checkpoint_dir, "best_model.pth"),
            "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
        }
        monkeypatch.setattr(
            "models.patch_tst.training._get_checkpoint_paths",
            lambda tf: paths,
        )
        monkeypatch.setattr(
            "models.patch_tst.training.get_patchtst_config",
            lambda tf: {
                "patch_len": 6, "stride": 3, "d_model": 16, "n_heads": 4,
                "n_layers": 1, "d_ff": 32, "dropout": 0.0, "dropout_fc": 0.0,
            },
        )

        from models.patch_tst.training import train

        train(symbol="BTC", timeframe="1d", epochs=2, batch_size=32, patience=5)

        checkpoint = torch.load(paths["model"], weights_only=False)
        assert "patchtst_cfg" in checkpoint
        assert "model_state" in checkpoint
        assert "history" in checkpoint
        assert checkpoint["timeframe"] == "1d"

        scalers = jl.load(paths["scalers"])
        assert "feature_scaler" in scalers
        assert "target_scaler" in scalers
        assert "clip_bounds" in scalers
        assert "target_clip_bounds" in scalers


# ----- Tests evaluation ----- #

class TestEvaluation:
    """Tests pour load_model et evaluate."""

    def test_load_model(self, tmp_path):
        """load_model reconstruit correctement un PatchTST sauvegardé."""
        from models.patch_tst.PatchTST import PatchTST as PatchTSTClass

        cfg = {
            "patch_len": 6, "stride": 3, "d_model": 16, "n_heads": 4,
            "n_layers": 1, "d_ff": 32, "dropout": 0.0, "dropout_fc": 0.0,
        }
        model = PatchTSTClass(window_size=30, n_features=16, **cfg)
        x = torch.randn(2, 30, 16)
        preds_original = model(x).detach()

        model_path = str(tmp_path / "test_model.pth")
        torch.save({
            "model_state": model.state_dict(),
            "history": {"train_loss": [0.1], "val_loss": [0.2]},
            "timeframe": "1d",
            "window_size": 30,
            "n_features": 16,
            "patchtst_cfg": cfg,
        }, model_path)

        from models.patch_tst.evaluation import load_model

        device = torch.device("cpu")
        loaded, history = load_model(model_path, device)
        preds_loaded = loaded(x).detach()

        np.testing.assert_array_almost_equal(
            preds_original.numpy(), preds_loaded.numpy(), decimal=5
        )
        assert "train_loss" in history

    @pytest.mark.usefixtures("_patch_output")
    def test_evaluate_returns_metrics(self, tmp_path, monkeypatch):
        """evaluate() via run_evaluation produit des graphiques."""
        from models.patch_tst.PatchTST import PatchTST as PatchTSTClass
        from models.patch_tst.data_preparator import prepare_data
        import joblib as jl

        cfg = {
            "patch_len": 6, "stride": 3, "d_model": 16, "n_heads": 4,
            "n_layers": 1, "d_ff": 32, "dropout": 0.0, "dropout_fc": 0.0,
        }
        # Préparer données et model
        train_loader, val_loader, feat_scaler, tgt_scaler, clip_bounds, target_clip_bounds, close_val = (
            prepare_data(symbol="BTC", timeframe="1d", batch_size=32)
        )

        model = PatchTSTClass(window_size=30, n_features=len(get_feature_columns("1d")), **cfg)
        # Entraîner un mini-batch pour avoir des poids non-nuls
        opt = torch.optim.Adam(model.parameters(), lr=0.01)
        X_batch, y_batch = next(iter(train_loader))
        model.train()
        opt.zero_grad()
        loss = torch.nn.HuberLoss()(model(X_batch), y_batch)
        loss.backward()
        opt.step()

        # Sauvegarder checkpoint
        checkpoint_dir = str(tmp_path / "eval_ckpt" / "1d")
        os.makedirs(checkpoint_dir, exist_ok=True)
        model_path = os.path.join(checkpoint_dir, "best_model.pth")
        scalers_path = os.path.join(checkpoint_dir, "scalers.joblib")
        results_dir = str(tmp_path / "eval_results" / "1d")

        tf_config = get_timeframe_config("1d")
        torch.save({
            "model_state": model.state_dict(),
            "history": {"train_loss": [0.5], "val_loss": [0.6]},
            "timeframe": "1d",
            "window_size": tf_config["window_size"],
            "n_features": len(get_feature_columns("1d")),
            "patchtst_cfg": cfg,
        }, model_path)
        jl.dump({
            "feature_scaler": feat_scaler,
            "target_scaler": tgt_scaler,
            "clip_bounds": clip_bounds,
            "target_clip_bounds": target_clip_bounds,
            "timeframe": "1d",
            "window_size": tf_config["window_size"],
            "train_ratio": 0.8,
            "prediction_horizon": tf_config["prediction_horizon"],
        }, scalers_path)

        paths = {
            "dir": checkpoint_dir,
            "model": model_path,
            "scalers": scalers_path,
            "results": results_dir,
        }
        monkeypatch.setattr(
            "models.patch_tst.evaluation._get_checkpoint_paths",
            lambda tf: paths,
        )

        from models.patch_tst.evaluation import evaluate

        evaluate(symbol="BTC", timeframe="1d", model_path=model_path)

        expected_plots = [
            "predictions_vs_actual.png",
            "scatter.png",
            "residuals.png",
            "direction_accuracy.png",
            "price_vs_predicted.png",
            "training_curves.png",
        ]
        for plot in expected_plots:
            assert os.path.isfile(os.path.join(results_dir, plot)), f"Missing: {plot}"


# ----- Tests config ----- #

class TestConfig:
    """Tests pour get_patchtst_config."""

    def test_1d_config(self):
        """1d retourne la config explicite."""
        cfg = get_patchtst_config("1d")
        assert cfg["patch_len"] == 6
        assert cfg["stride"] == 3
        assert cfg["d_model"] == 64
        assert cfg["n_heads"] == 4
        assert cfg["d_model"] % cfg["n_heads"] == 0

    def test_1h_config(self):
        """1h retourne la config optimisée."""
        cfg = get_patchtst_config("1h")
        assert cfg["patch_len"] == 12
        assert cfg["stride"] == 6
        assert cfg["d_model"] % cfg["n_heads"] == 0

    def test_fallback_config(self):
        """Un timeframe sans config explicite lève ValueError."""
        with pytest.raises(ValueError, match="No PatchTST config"):
            get_patchtst_config("4h")

    def test_num_patches_1d(self):
        """Vérifier num_patches=9 pour la config 1d (window=30)."""
        cfg = get_patchtst_config("1d")
        num_patches = (30 - cfg["patch_len"]) // cfg["stride"] + 1
        assert num_patches == 9

    def test_num_patches_1h(self):
        """Vérifier num_patches=11 pour la config 1h (window=72)."""
        cfg = get_patchtst_config("1h")
        num_patches = (72 - cfg["patch_len"]) // cfg["stride"] + 1
        assert num_patches == 11
