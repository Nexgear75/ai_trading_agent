"""Tests pour le module XGBoost : data_preparator, training, evaluation."""

import os

import joblib
import numpy as np
import pandas as pd
import pytest
import xgboost as xgb

from config import get_timeframe_config, get_xgboost_config
from data.features.pipeline import get_feature_columns, FEATURE_COLUMNS


# ----- Fixtures ----- #

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
    monkeypatch.setattr("models.xgboost.data_preparator.get_timeframe_config", patched)
    monkeypatch.setattr("models.xgboost.evaluation.get_timeframe_config", patched)
    monkeypatch.setattr("utils.dataset_loader.get_timeframe_config", patched)


# ----- Tests data_preparator ----- #

class TestDataPreparator:
    """Tests pour prepare_data."""

    @pytest.mark.usefixtures("_patch_output")
    def test_shapes_2d(self):
        """X_train et X_val doivent être 2D [n, window × n_features]."""
        from models.xgboost.data_preparator import prepare_data

        X_train, X_val, y_train, y_val, _, _, _, _, close_val = prepare_data(
            symbol="BTC", timeframe="1d", train_ratio=0.8
        )
        tf_config = get_timeframe_config("1d")
        window_size = tf_config["window_size"]
        n_features = len(get_feature_columns("1d"))
        expected_flat = window_size * n_features

        assert X_train.ndim == 2
        assert X_val.ndim == 2
        assert X_train.shape[1] == expected_flat
        assert X_val.shape[1] == expected_flat

    @pytest.mark.usefixtures("_patch_output")
    def test_no_nan(self):
        """Aucun NaN dans les arrays de sortie."""
        from models.xgboost.data_preparator import prepare_data

        X_train, X_val, y_train, y_val, _, _, _, _, _ = prepare_data(
            symbol="BTC", timeframe="1d"
        )
        assert not np.isnan(X_train).any()
        assert not np.isnan(X_val).any()
        assert not np.isnan(y_train).any()
        assert not np.isnan(y_val).any()

    @pytest.mark.usefixtures("_patch_output")
    def test_split_ratio(self):
        """Le split train/val respecte approximativement le ratio demandé."""
        from models.xgboost.data_preparator import prepare_data

        X_train, X_val, _, _, _, _, _, _, _ = prepare_data(
            symbol="BTC", timeframe="1d", train_ratio=0.8
        )
        total = len(X_train) + len(X_val)
        actual_ratio = len(X_train) / total
        assert 0.75 <= actual_ratio <= 0.85

    @pytest.mark.usefixtures("_patch_output")
    def test_scalers_fit_on_train(self):
        """Les scalers retournés sont fitté (ont des attributs center_ / mean_)."""
        from models.xgboost.data_preparator import prepare_data

        _, _, _, _, feature_scaler, target_scaler, _, _, _ = prepare_data(
            symbol="BTC", timeframe="1d"
        )
        assert hasattr(feature_scaler, "center_")  # RobustScaler
        assert hasattr(target_scaler, "mean_")      # StandardScaler

    @pytest.mark.usefixtures("_patch_output")
    def test_clip_bounds_shape(self):
        """clip_bounds a la bonne shape [n_flat_features, 2]."""
        from models.xgboost.data_preparator import prepare_data

        X_train, _, _, _, _, _, clip_bounds, _, _ = prepare_data(
            symbol="BTC", timeframe="1d"
        )
        assert clip_bounds.shape == (X_train.shape[1], 2)


# ----- Tests training ----- #

class TestTraining:
    """Tests pour train."""

    @pytest.mark.usefixtures("_patch_output")
    def test_train_saves_checkpoint(self, tmp_path, monkeypatch):
        """train() produit un modèle .json et un scalers .joblib."""
        checkpoint_dir = str(tmp_path / "ckpt" / "1d")
        paths = {
            "dir": checkpoint_dir,
            "model": os.path.join(checkpoint_dir, "best_model.json"),
            "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
        }
        monkeypatch.setattr(
            "models.xgboost.training._get_checkpoint_paths",
            lambda tf: paths,
        )
        # Réduire le nombre d'arbres pour la vitesse
        monkeypatch.setattr(
            "models.xgboost.training.get_xgboost_config",
            lambda tf: {
                "n_estimators": 5,
                "max_depth": 3,
                "learning_rate": 0.1,
                "early_stopping_rounds": 3,
            },
        )

        from models.xgboost.training import train

        model, feat_scaler, tgt_scaler = train(symbol="BTC", timeframe="1d")

        assert os.path.isfile(paths["model"])
        assert os.path.isfile(paths["scalers"])
        assert isinstance(model, xgb.XGBRegressor)

    @pytest.mark.usefixtures("_patch_output")
    def test_scalers_metadata(self, tmp_path, monkeypatch):
        """Le fichier scalers.joblib contient les métadonnées attendues."""
        checkpoint_dir = str(tmp_path / "ckpt2" / "1d")
        paths = {
            "dir": checkpoint_dir,
            "model": os.path.join(checkpoint_dir, "best_model.json"),
            "scalers": os.path.join(checkpoint_dir, "scalers.joblib"),
        }
        monkeypatch.setattr(
            "models.xgboost.training._get_checkpoint_paths",
            lambda tf: paths,
        )
        monkeypatch.setattr(
            "models.xgboost.training.get_xgboost_config",
            lambda tf: {
                "n_estimators": 5,
                "max_depth": 3,
                "learning_rate": 0.1,
                "early_stopping_rounds": 3,
            },
        )

        from models.xgboost.training import train

        train(symbol="BTC", timeframe="1d")

        scalers = joblib.load(paths["scalers"])
        assert "feature_scaler" in scalers
        assert "target_scaler" in scalers
        assert "clip_bounds" in scalers
        assert "target_clip_bounds" in scalers
        assert "timeframe" in scalers
        assert "xgb_cfg" in scalers
        assert scalers["timeframe"] == "1d"


# ----- Tests evaluation ----- #

class TestEvaluation:
    """Tests pour load_model et evaluate."""

    def test_load_model(self, tmp_path):
        """load_model charge correctement un modèle sauvegardé."""
        model = xgb.XGBRegressor(n_estimators=3, max_depth=2, random_state=42)
        np.random.seed(42)
        X = np.random.randn(50, 10)
        y = np.random.randn(50)
        model.fit(X, y)

        model_path = str(tmp_path / "test_model.json")
        model.save_model(model_path)

        from models.xgboost.evaluation import load_model

        loaded = load_model(model_path)
        preds_original = model.predict(X)
        preds_loaded = loaded.predict(X)
        np.testing.assert_array_almost_equal(preds_original, preds_loaded)

    @pytest.mark.usefixtures("_patch_output")
    def test_evaluate_returns_metrics(self, tmp_path, monkeypatch):
        """evaluate() retourne un dict de métriques avec les clés attendues."""
        # Préparer un faux modèle entraîné sur les données synthétiques
        from models.xgboost.data_preparator import prepare_data

        X_train, X_val, y_train, y_val, feat_scaler, tgt_scaler, clip_bounds, target_clip_bounds, close_val = (
            prepare_data(symbol="BTC", timeframe="1d")
        )

        model = xgb.XGBRegressor(n_estimators=5, max_depth=2, random_state=42)
        model.fit(X_train, y_train)

        # Sauvegarder model + scalers
        checkpoint_dir = str(tmp_path / "eval_ckpt" / "1d")
        os.makedirs(checkpoint_dir, exist_ok=True)
        model_path = os.path.join(checkpoint_dir, "best_model.json")
        scalers_path = os.path.join(checkpoint_dir, "scalers.joblib")
        results_dir = str(tmp_path / "eval_results" / "1d")

        model.save_model(model_path)
        joblib.dump({
            "feature_scaler": feat_scaler,
            "target_scaler": tgt_scaler,
            "clip_bounds": clip_bounds,
            "target_clip_bounds": target_clip_bounds,
            "timeframe": "1d",
            "window_size": 30,
            "train_ratio": 0.8,
        }, scalers_path)

        paths = {
            "dir": checkpoint_dir,
            "model": model_path,
            "scalers": scalers_path,
            "results": results_dir,
        }
        monkeypatch.setattr(
            "models.xgboost.evaluation._get_checkpoint_paths",
            lambda tf: paths,
        )

        from models.xgboost.evaluation import evaluate

        metrics = evaluate(symbol="BTC", timeframe="1d", model_path=model_path)

        assert isinstance(metrics, dict)
        expected_keys = {"MSE", "RMSE", "MAE", "R²", "Direction Accuracy"}
        assert expected_keys == set(metrics.keys())
        for v in metrics.values():
            assert np.isfinite(v)

    @pytest.mark.usefixtures("_patch_output")
    def test_evaluate_generates_plots(self, tmp_path, monkeypatch):
        """evaluate() génère les fichiers PNG attendus."""
        from models.xgboost.data_preparator import prepare_data

        X_train, X_val, y_train, y_val, feat_scaler, tgt_scaler, clip_bounds, target_clip_bounds, close_val = (
            prepare_data(symbol="BTC", timeframe="1d")
        )

        model = xgb.XGBRegressor(n_estimators=5, max_depth=2, random_state=42)
        model.fit(X_train, y_train)

        checkpoint_dir = str(tmp_path / "plot_ckpt" / "1d")
        os.makedirs(checkpoint_dir, exist_ok=True)
        model_path = os.path.join(checkpoint_dir, "best_model.json")
        scalers_path = os.path.join(checkpoint_dir, "scalers.joblib")
        results_dir = str(tmp_path / "plot_results" / "1d")

        model.save_model(model_path)
        joblib.dump({
            "feature_scaler": feat_scaler,
            "target_scaler": tgt_scaler,
            "clip_bounds": clip_bounds,
            "target_clip_bounds": target_clip_bounds,
            "timeframe": "1d",
            "window_size": 30,
            "train_ratio": 0.8,
        }, scalers_path)

        paths = {
            "dir": checkpoint_dir,
            "model": model_path,
            "scalers": scalers_path,
            "results": results_dir,
        }
        monkeypatch.setattr(
            "models.xgboost.evaluation._get_checkpoint_paths",
            lambda tf: paths,
        )

        from models.xgboost.evaluation import evaluate

        evaluate(symbol="BTC", timeframe="1d", model_path=model_path)

        expected_plots = [
            "predictions_vs_actual.png",
            "scatter.png",
            "residuals.png",
            "direction_accuracy.png",
            "price_vs_predicted.png",
        ]
        for plot in expected_plots:
            assert os.path.isfile(os.path.join(results_dir, plot)), f"Missing: {plot}"


# ----- Tests config ----- #

class TestConfig:
    """Tests pour get_xgboost_config."""

    def test_known_timeframe(self):
        """1d retourne la config explicite."""
        cfg = get_xgboost_config("1d")
        assert cfg["n_estimators"] == 1000
        assert cfg["max_depth"] == 6
        assert cfg["learning_rate"] == 0.05
        assert cfg["early_stopping_rounds"] == 50

    def test_1h_timeframe(self):
        """1h retourne la config optimisée."""
        cfg = get_xgboost_config("1h")
        assert cfg["n_estimators"] == 1500
        assert cfg["max_depth"] == 8

    def test_fallback_timeframe(self):
        """Un timeframe non listé retourne le fallback."""
        cfg = get_xgboost_config("4h")
        assert "n_estimators" in cfg
        assert "max_depth" in cfg
        assert "learning_rate" in cfg
        assert "early_stopping_rounds" in cfg
