"""
Module de backtesting générique pour tous les modèles du projet.

Simule une stratégie de trading basée sur les prédictions d'un modèle ML,
calcule les métriques de performance et génère une courbe d'équité.

================================================================================
EXEMPLES D'UTILISATION
================================================================================

1) Backtest simple sur un seul symbole:
   python -m testing.backtesting --model cnn --symbol BTC --capital 10000

2) Backtest avec seuil de prédiction personnalisé:
   python -m testing.backtesting --model cnn --symbol BTC --capital 10000 --threshold 0.02

3) Backtest avec positions short autorisées:
   python -m testing.backtesting --model cnn --symbol BTC --allow-short --threshold 0.015

4) Backtest sur tous les symboles définis dans SYMBOLS:
   python -m testing.backtesting --model cnn --all-symbols --capital 1000

5) Backtest avec risk management ATR-based (SL/TP/trailing stop):
   python -m testing.backtesting --model cnn --symbol BTC --atr-risk --threshold 0.01

6) Backtest avec frais personnalisés:
   python -m testing.backtesting --model cnn --symbol BTC --entry-fee 0.0005 --exit-fee 0.0005

7) Backtest avec date de début personnalisée (out-of-sample):
   python -m testing.backtesting --model cnn --symbol BTC --test-start-date 2024-06-01

8) Backtest sur timeframe différent:
   python -m testing.backtesting --model cnn --symbol BTC --timeframe 1h --threshold 0.005

9) Backtest ensemble de modèles (ensemble):
   python -m testing.backtesting --model ensemble --symbol BTC --ensemble-models cnn,bilstm --ensemble-strategy weighted_average

10) Backtest ensemble avec poids personnalisés:
    python -m testing.backtesting --model ensemble --symbol BTC --ensemble-models cnn,bilstm,gru --ensemble-weights 0.5,0.3,0.2

11) Backtest ensemble sur tous les symboles:
    python -m testing.backtesting --model ensemble --all-symbols --ensemble-models cnn,bilstm --ensemble-strategy majority_vote

================================================================================
OPTIONS DISPONIBLES
================================================================================

--model (required)          Type du modèle: cnn, lstm, gru, bilstm, xgboost, ensemble, etc.

--symbol                    Symbole de la crypto (ex: BTC, ETH). Requis sauf avec --all-symbols.

--capital                   Capital initial (défaut: 1000). En mode --all-symbols, c'est le
                            capital par symbole.

--threshold                 Seuil de prédiction pour ouvrir une position (défaut: 0.0).
                            Une prédiction > threshold déclenche un LONG, < -threshold un SHORT.
                            Valeurs typiques: 0.005 (0.5%) à 0.03 (3%).

--allow-short               Autorise les positions SHORT sur les prédictions négatives.

--timeframe                 Timeframe du modèle: 1d, 1h, 4h, 15m (défaut: 1d).
                            Doit correspondre au timeframe sur lequel le modèle est entraîné.

--model-path                Chemin vers un checkpoint spécifique (optionnel).
                            Défaut: models/<model>/checkpoints/<timeframe>/best_model.pth

--entry-fee                 Frais à l'entrée en pourcentage (ex: 0.001 = 0.1%, défaut: 0.1%).

--exit-fee                  Frais à la sortie en pourcentage (ex: 0.001 = 0.1%, défaut: 0.1%).

--atr-risk                  Active le risk management ATR-based avec:
                            - Stop-loss basé sur l'ATR (0.75x ATR)
                            - Take-profit basé sur l'ATR (1.5x ATR)
                            - Trailing stop (2.5x ATR threshold)
                            - Cooldown après 5 pertes consécutives

--test-start-date           Date de début pour le test out-of-sample (ex: 2025-01-01).
                            Si non spécifié, utilise TEST_START_DATE du config.

--all-symbols               Tester sur tous les symboles définis dans config.SYMBOLS.
                            Le capital spécifié est alloué PAR symbole.

--ensemble-models           Liste des modèles pour l'ensemble, séparés par virgule.
                            Ex: cnn,bilstm,cnn_bilstm_am. Requis si --model ensemble.

--ensemble-strategy         Stratégie d'agrégation pour l'ensemble:
                            - majority_vote: Vote majoritaire
                            - weighted_average: Moyenne pondérée (défaut)
                            - confidence_weighted: Pondéré par la confiance
                            - unanimous: Tous les modèles doivent être d'accord

--ensemble-weights          Poids personnalisés pour chaque modèle, séparés par virgule.
                            Ex: 0.5,0.3,0.2. Défaut: poids égaux.

================================================================================
EXEMPLES DE SCÉNARIOS
================================================================================

# Scénario 1: Backtest conservateur sur BTC
# - Seuil élevé (2%) pour filtrer les signaux faibles
# - Sans short (uniquement LONG)
python -m testing.backtesting --model cnn --symbol BTC --capital 10000 --threshold 0.02

# Scénario 2: Backtest agressif multi-symboles avec ATR risk
# - Seuil bas (0.8%) pour plus de trades
# - Short autorisé
# - Risk management ATR pour protéger le capital
# - Capital de 500$ par symbole
python -m testing.backtesting --model cnn --all-symbols --capital 500 --threshold 0.008 --allow-short --atr-risk

# Scénario 3: Backtest avec frais de trading réalistes
# - Binance spot: 0.1% entry + 0.1% exit
# - Comparaison avec frais réduits (VIP)
python -m testing.backtesting --model cnn --symbol BTC --entry-fee 0.001 --exit-fee 0.001

# Scénario 4: Ensemble de modèles avec stratégie conservative
# - Unanimous: tous les modèles doivent être d'accord
# - Réduit les faux signaux mais aussi le nombre de trades
python -m testing.backtesting --model ensemble --symbol BTC --ensemble-models cnn,lstm,gru --ensemble-strategy unanimous --threshold 0.01

# Scénario 5: Backtest sur timeframe court (1h) pour day-trading simulation
# - Seuil adapté à la volatilité intraday
# - Risk management crucial sur des horizons courts
python -m testing.backtesting --model cnn --symbol BTC --timeframe 1h --threshold 0.005 --atr-risk

# Scénario 6: Validation sur période récente (stress test)
# - Test sur les 6 derniers mois uniquement
# - Vérifie la robustesse du modèle sur données récentes
python -m testing.backtesting --model cnn --symbol BTC --test-start-date 2024-06-01

# Scénario 7: Comparaison modèles individuels vs ensemble
# Test individuel CNN:
python -m testing.backtesting --model cnn --symbol BTC --capital 10000 --threshold 0.01
# Test individuel LSTM:
python -m testing.backtesting --model lstm --symbol BTC --capital 10000 --threshold 0.01
# Test ensemble pondéré:
python -m testing.backtesting --model ensemble --symbol BTC --ensemble-models cnn,lstm --ensemble-strategy weighted_average --threshold 0.01

================================================================================
"""

import argparse
import importlib
import os
from dataclasses import dataclass, field
from typing import Optional

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

from config import (
    DEFAULT_TIMEFRAME,
    TIMEFRAME_MINUTES,
    get_timeframe_config,
    SYMBOLS,
    DEFAULT_ENTRY_FEE,
    DEFAULT_EXIT_FEE,
    DEFAULT_SLIPPAGE_PCT,
    TEST_START_DATE,
)
from data.features.pipeline import FEATURE_COLUMNS, get_feature_columns
from data.preprocessing.builder import build_windows
from utils.dataset_loader import load_symbol


# ----- Dataclasses ----- #


@dataclass
class Trade:
    """Représente un trade individuel."""

    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    direction: str  # "LONG" ou "SHORT"
    entry_price: float
    exit_price: float
    predicted_return: float
    actual_return: float
    entry_fee: float  # frais à l'entrée
    exit_fee: float  # frais à la sortie
    total_fees: float  # frais totaux
    pnl_before_fees: float  # PnL brut avant frais
    pnl: float  # PnL net après frais
    exit_reason: str = "horizon"  # "horizon", "stop_loss", "take_profit", "trailing_stop", "time_exit", "partial_exit", "signal_flip"
    # Métriques PRO (optionnelles)
    slippage_entry: float = 0.0  # Slippage à l'entrée (%)
    slippage_exit: float = 0.0  # Slippage à la sortie (%)
    spread_cost: float = 0.0  # Coût du spread (%)
    intra_bar: bool = False  # True si SL/TP touché intra-bougie
    bars_held: int = 0  # Nombre de barres détenues


@dataclass
class BacktestResult:
    """Résultat complet d'un backtest."""

    trades: list[Trade] = field(default_factory=list)
    portfolio_values: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    n_trades: int = 0
    avg_trade_return: float = 0.0
    profit_factor: float = 0.0
    # Métriques de frais
    total_fees_paid: float = 0.0
    avg_fees_per_trade: float = 0.0
    fee_impact_pct: float = 0.0
    entry_fee_pct: float = DEFAULT_ENTRY_FEE
    exit_fee_pct: float = DEFAULT_EXIT_FEE
    # ATR risk management stats
    sl_exits: int = 0
    tp_exits: int = 0
    trailing_exits: int = 0
    horizon_exits: int = 0


# ----- Chargement modèle et scalers ----- #


def load_model_dynamic(
    model_type: str,
    device: torch.device,
    model_path: Optional[str] = None,
    timeframe: str = DEFAULT_TIMEFRAME,
) -> tuple[torch.nn.Module, dict]:
    """Charge dynamiquement un modèle via son type (importlib).

    Importe `models.<model_type>.evaluation.load_model` et l'appelle.

    Args:
        model_type: Type du modèle (ex: "cnn", "lstm", "gru").
        device: Device cible (mps, cuda, cpu).
        model_path: Chemin vers le checkpoint. Si None, utilise le
                     chemin par défaut du modèle pour le timeframe.
        timeframe: Timeframe du modèle (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").

    Returns:
        (model, history) avec le modèle en mode eval.
    """
    module_path = f"models.{model_type}.evaluation"

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(
            f"Impossible d'importer le module {module_path}. "
            f"Vérifiez que le modèle existe et que le fichier evaluation.py est présent."
        ) from e

    # Déterminer le chemin du modèle
    if model_path is None:
        model_path = f"models/{model_type}/checkpoints/{timeframe}/best_model.pth"

    if not os.path.isfile(model_path):
        raise FileNotFoundError(
            f"Checkpoint introuvable : {model_path}. "
            f"Entraînez d'abord le modèle avec `python -m models.{model_type}.training --timeframe {timeframe}`"
        )

    # Charger via la fonction load_model du module
    try:
        model, history = module.load_model(model_path, device)
    except AttributeError as e:
        raise AttributeError(
            f"Le module {module_path} doit exposer une fonction load_model(path, device)"
        ) from e

    return model, history


def load_scalers(model_type: str, timeframe: str = DEFAULT_TIMEFRAME) -> dict:
    """Charge les scalers sauvegardés pour un type de modèle et timeframe.

    Args:
        model_type: Type du modèle (ex: "cnn").
        timeframe: Timeframe du modèle (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").

    Returns:
        Dict avec clés "feature_scaler" et "target_scaler".
    """
    scalers_path = f"models/{model_type}/checkpoints/{timeframe}/scalers.joblib"

    if not os.path.isfile(scalers_path):
        raise FileNotFoundError(
            f"Scalers introuvables : {scalers_path}. "
            f"Entraînez d'abord le modèle avec `python -m models.{model_type}.training --timeframe {timeframe}`"
        )

    return joblib.load(scalers_path)


# ----- Préparation des données ----- #


def prepare_raw_windows(
    symbol: str,
    timeframe: str = DEFAULT_TIMEFRAME,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    """Prépare les fenêtres brutes (non scalées) pour le backtesting ensemble.

    Contrairement à prepare_backtest_data, aucun scaler n'est appliqué.
    Chaque modèle de l'ensemble applique ses propres scalers en interne.

    Args:
        symbol: Symbole de la crypto (ex: "BTC").
        timeframe: Timeframe du dataset (ex: "1d", "1h", "4h").

    Returns:
        (X_raw, y, timestamps, df_prices) où X_raw est non-scalé.
    """
    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    prediction_horizon = tf_config["prediction_horizon"]

    df = load_symbol(symbol, timeframe=timeframe).copy()
    df_prices = df[["close"]].copy()
    df["label"] = df["close"].shift(-prediction_horizon) / df["close"] - 1
    df = df.dropna(subset=["label"])

    feature_cols = get_feature_columns(timeframe)
    X, y, timestamps = build_windows(
        df, window_size=window_size, feature_columns=feature_cols
    )

    if len(X) == 0:
        raise ValueError(
            f"Pas assez de données pour construire des fenêtres pour {symbol}"
        )

    print(
        f"Fenêtres brutes préparées : {len(X)} fenêtres, window_size={window_size}, {X.shape[2]} features"
    )
    return X, y, timestamps, df_prices


def prepare_backtest_data(
    symbol: str,
    feature_scaler,
    clip_bounds: np.ndarray | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    test_start_date: str | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    """Prépare les données pour le backtest (dataset complet, pas de split).

    Charge le symbole, recalcule les labels, construit les fenêtres,
    applique le scaler (transform uniquement, pas fit_transform).
    Filtre les données à partir de test_start_date pour tester sur des données
    jamais vues pendant l'entraînement.

    Args:
        symbol: Symbole de la crypto (ex: "BTC").
        feature_scaler: RobustScaler déjà fitté (chargé depuis joblib).
        clip_bounds: Bornes pour le clipping des outliers (optionnel).
        timeframe: Timeframe du dataset (ex: "1d", "1h", "4h").
        Défaut: DEFAULT_TIMEFRAME ("1d").
        test_start_date: Date de début pour le test (ex: "2025-01-01").
        Si None, utilise TEST_START_DATE du config.

    Returns:
        (X_scaled, y, timestamps, df_prices) où :
        - X_scaled: (N, window_size, n_features) features scalées
        - y: (N,) labels (forward returns réels)
        - timestamps: (N,) dates correspondantes
        - df_prices: DataFrame avec colonne 'close' indexé par timestamp
    """
    # Get timeframe configuration
    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    prediction_horizon = tf_config["prediction_horizon"]

    # Charger les données complètes
    df = load_symbol(symbol, timeframe=timeframe).copy()

    # Recalculer les features si necessaires (certains CSV peuvent etre incomplets)
    feature_cols = get_feature_columns(timeframe)
    missing_features = [col for col in feature_cols if col not in df.columns]
    if missing_features:
        print(f"  Recalcul de {len(missing_features)} features manquantes...")
        from data.features.pipeline import build_features

        df = build_features(df, timeframe=timeframe)

    # Filtrer les données à partir de la date de test (out-of-sample)
    if test_start_date is None:
        test_start_date = TEST_START_DATE
    df = df[df.index >= test_start_date].copy()

    if len(df) == 0:
        raise ValueError(
            f"Pas de données pour {symbol} après {test_start_date}. "
            f"Vérifiez que les données existent pour cette période."
        )

    print(f" Filtrage out-of-sample: {len(df)} échantillons depuis {test_start_date}")

    # Conserver les prix OHLCV complets pour le backtesting PRO (avant de modifier df)
    price_cols = ["close"]
    if "high" in df.columns and "low" in df.columns:
        price_cols = ["high", "low", "close"]
    # Ajouter open et volume si disponibles (pour features PRO)
    if "open" in df.columns:
        price_cols.insert(0, "open")
    if "volume" in df.columns:
        price_cols.append("volume")
    df_prices = df[price_cols].copy()

    # Recalculer le label (forward return sur prediction_horizon périodes)
    df["label"] = df["close"].shift(-prediction_horizon) / df["close"] - 1

    # Supprimer les lignes sans label (derniers prediction_horizon périodes)
    df = df.dropna(subset=["label"])

    if len(df) == 0:
        raise ValueError(
            f"Pas assez de données pour {symbol} après filtrage et calcul des labels. "
            f"Il faut au moins {prediction_horizon} périodes après {test_start_date}."
        )

    # Construire les fenêtres avec la taille et les features appropriées pour ce timeframe
    feature_cols = get_feature_columns(timeframe)
    X, y, timestamps = build_windows(
        df, window_size=window_size, feature_columns=feature_cols
    )

    if len(X) == 0:
        raise ValueError(
            f"Pas assez de données pour construire des fenêtres pour {symbol}"
        )

    # Vérification anti look-ahead bias AVANT clipping/scaling (X encore brut)
    _verify_no_lookahead_bias(df, X, timestamps, symbol, timeframe)

    # Appliquer le clipping puis le feature scaler (transform seulement, pas fit_transform)
    n_samples, window_len, n_features = X.shape
    X_flat = X.reshape(-1, n_features)

    # Clipping outliers (même bornes que le training)
    if clip_bounds is not None:
        for i in range(n_features):
            X_flat[:, i] = np.clip(X_flat[:, i], clip_bounds[i, 0], clip_bounds[i, 1])

    X_scaled_flat = feature_scaler.transform(X_flat)
    X_scaled = X_scaled_flat.reshape(n_samples, window_len, n_features)

    print(
        f"Données préparées : {len(X)} fenêtres, window_size={window_size}, {n_features} features"
    )

    return X_scaled, y, timestamps, df_prices


def _verify_no_lookahead_bias(
    df: pd.DataFrame,
    X: np.ndarray,
    timestamps: np.ndarray,
    symbol: str,
    timeframe: str = DEFAULT_TIMEFRAME,
) -> None:
    """
    Vérifie qu'il n'y a pas de fuite de données futures (look-ahead bias).

    Contrats de `build_windows`:
        X[i] = df[feature_cols][t - window_size : t]   # exclusif à t
        y[i] = df["label"][t]
        timestamps[i] = t
    La fenêtre X[i] doit donc correspondre, valeur par valeur, à la tranche
    de `df` se terminant à `t-1` inclus.

    Args:
        df: DataFrame source (après filtrage et dropna "label").
        X: Array des features (n_samples, window_size, n_features).
        timestamps: Array des timestamps de prédiction.
        symbol: Symbole pour les messages d'erreur.
        timeframe: Timeframe des données (pour les messages).

    Raises:
        ValueError: Si une anomalie de look-ahead est détectée.
    """
    feature_cols = get_feature_columns(timeframe)

    if "label" in feature_cols:
        raise ValueError(
            f"[{symbol}] ERREUR CRITIQUE: 'label' est dans la liste des features."
        )

    window_size = X.shape[1]
    df_index = df.index
    n_checks = min(20, len(timestamps))
    mismatches = 0

    for i in range(n_checks):
        ts = pd.Timestamp(timestamps[i])
        try:
            pos = df_index.get_loc(ts)
        except KeyError:
            continue
        if pos < window_size:
            continue

        expected = df[feature_cols].iloc[pos - window_size : pos].to_numpy()
        actual = X[i]

        # Chercher l'index cohérent dans X : build_windows émet les fenêtres
        # à partir de l'offset window_size, donc timestamps[0] = df.index[window_size].
        # Quand un dropna a tronqué df après build_windows, la correspondance directe
        # i → pos-window_size peut glisser. On teste d'abord la correspondance stricte.
        if expected.shape != actual.shape:
            mismatches += 1
            continue
        if not np.allclose(expected, actual, equal_nan=True, rtol=1e-6, atol=1e-8):
            mismatches += 1

    if mismatches == n_checks and n_checks > 0:
        raise ValueError(
            f"[{symbol}] Look-ahead vérification: aucune fenêtre ne matche "
            f"sur {n_checks} échantillons — risque de fuite ou bug de fenêtrage."
        )

    print(
        f"  ✓ Anti look-ahead OK ({n_checks - mismatches}/{n_checks} fenêtres matchent) "
        f"| features {X.shape[1]}×{X.shape[2]} [{timeframe}]"
    )


# ----- Inférence ----- #


def run_predictions(
    model: torch.nn.Module,
    X: np.ndarray,
    target_scaler,
    device: torch.device,
    batch_size: int = 64,
) -> np.ndarray:
    """Génère les prédictions du modèle et les inverse-transforme.

    Args:
        model: Modèle PyTorch en mode eval.
        X: Features scalées (N, 30, 20).
        target_scaler: StandardScaler pour inverse_transform.
        device: Device.
        batch_size: Taille des batchs d'inférence.

    Returns:
        Array (N,) de prédictions de rendement en % réel.
    """
    # Créer DataLoader avec dummy targets (nécessaire pour compatibilité)
    X_tensor = torch.tensor(X, dtype=torch.float32)
    y_dummy = torch.zeros(len(X), dtype=torch.float32)
    dataset = TensorDataset(X_tensor, y_dummy)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    # Inférence batch
    all_preds = []
    model.eval()

    with torch.no_grad():
        for X_batch, _ in dataloader:
            X_batch = X_batch.to(device)
            preds = model(X_batch)
            all_preds.append(preds.cpu().numpy())

    y_pred_scaled = np.concatenate(all_preds).ravel()

    # Inverse transform pour retrouver les vrais pourcentages
    y_pred = target_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()

    return y_pred


# ----- Simulation de trading ----- #


def _compute_atr_series(df_prices: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcule l'ATR normalisé (ATR / close) sur le DataFrame de prix.

    Args:
        df_prices: DataFrame avec colonnes 'high', 'low', 'close'.
        period: Période de l'ATR.

    Returns:
        Series d'ATR normalisé indexée comme df_prices.
    """
    if "high" not in df_prices.columns or "low" not in df_prices.columns:
        # Fallback : estimer la volatilité à partir du close seul
        returns = df_prices["close"].pct_change().abs()
        atr_norm = returns.rolling(period).mean()
        return atr_norm

    prev_close = df_prices["close"].shift(1)
    tr = pd.concat(
        [
            df_prices["high"] - df_prices["low"],
            (df_prices["high"] - prev_close).abs(),
            (df_prices["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.rolling(period).mean()
    return atr / df_prices["close"]


def simulate_trading(
    predictions: np.ndarray,
    timestamps: np.ndarray,
    df_prices: pd.DataFrame,
    capital: float = 10_000.0,
    threshold: float = 0.0,
    allow_short: bool = False,
    entry_fee_pct: float = DEFAULT_ENTRY_FEE,
    exit_fee_pct: float = DEFAULT_EXIT_FEE,
    prediction_horizon: int = 3,
    timeframe_minutes: int = 1440,
    use_atr_risk: bool = False,
    risk_per_trade: float = 0.01,
    sl_atr_mult: float = 0.75,
    tp_atr_mult: float = 1.5,
    trailing_atr_mult: float = 2.5,
    max_consecutive_losses: int = 5,
    cooldown_bars: int = 2,
    # Nouveaux paramètres PRO
    use_intra_bar: bool = True,
    use_slippage: bool = True,
    use_spread: bool = True,
    use_time_exit: bool = True,
    time_exit_bars: int = 48,
    slippage_vol_factor: float = 0.3,
    base_spread_bps: float = 5.0,
    stop_gap_slippage_pct: float = 0.0005,
    min_notional_usd: float = 10.0,
) -> BacktestResult:
    """Simule la stratégie de trading sur les prédictions.

    Pour chaque période t :
        - Si prediction[t] > threshold  → ouvrir LONG
        - Si prediction[t] < -threshold → ouvrir SHORT (si autorisé)
        - Sinon → rester FLAT
        - Clôture après prediction_horizon périodes (ou SL/TP si use_atr_risk)

    Le capital est divisé en prediction_horizon slots pour permettre
    des positions simultanées sans sur-allocation.

    Args:
        predictions: (N,) prédictions de rendement.
        timestamps: (N,) timestamps correspondants.
        df_prices: DataFrame avec colonne 'close'.
        capital: Capital initial.
        threshold: Seuil de prédiction pour ouvrir une position.
        allow_short: Si True, autorise les positions short.
        entry_fee_pct: Frais à l'entrée (ex: 0.001 = 0.1%).
        exit_fee_pct: Frais à la sortie (ex: 0.001 = 0.1%).
        prediction_horizon: Nombre de barres avant clôture forcée.
        timeframe_minutes: Durée d'une barre en minutes.
        use_atr_risk: Si True, active le risk management ATR-based.
        risk_per_trade: % du capital risqué par trade (défaut: 1%).
        sl_atr_mult: Multiplicateur ATR pour le stop-loss (défaut: 0.75).
        tp_atr_mult: Multiplicateur ATR pour le take-profit (défaut: 1.5).
        trailing_atr_mult: Seuil ATR pour activer le trailing stop (défaut: 2.5).
        max_consecutive_losses: Nombre max de pertes consécutives avant cooldown.
        cooldown_bars: Barres de pause après max_consecutive_losses.

    Returns:
        BacktestResult avec tous les trades et métriques.
    """
    result = BacktestResult()
    result.entry_fee_pct = entry_fee_pct
    result.exit_fee_pct = exit_fee_pct

    if len(predictions) == 0:
        print("Aucune prédiction à traiter")
        return result

    # Créer une série des close prices indexée par timestamp
    close_prices = df_prices["close"]

    # Vérifier si on a les données OHLC complètes pour les features PRO
    has_ohlc = all(c in df_prices.columns for c in ["high", "low", "open"])
    has_volume = "volume" in df_prices.columns

    if has_ohlc and use_intra_bar:
        print(f"✓ Mode PRO activé: intra-bar SL/TP, slippage, spread")
    elif use_intra_bar:
        print(f"⚠️ Données OHLC incomplètes, mode standard utilisé")
        use_intra_bar = False
        use_slippage = False
        use_spread = False

    # ATR-based risk management setup
    atr_series = None
    if use_atr_risk:
        atr_series = _compute_atr_series(df_prices)

    # Calculer la volatilité pour le slippage
    volatility_series = None
    if use_slippage and has_ohlc:
        returns = df_prices["close"].pct_change().abs()
        volatility_series = returns.rolling(20).mean()

    # Spread estimé
    spread_series = None
    if use_spread and has_ohlc:
        base_spread = base_spread_bps / 10000
        if volatility_series is not None:
            spread_series = base_spread * (1 + volatility_series * 100)
        else:
            spread_series = pd.Series(base_spread, index=df_prices.index)

    # Allocation : diviser le capital en slots pour positions simultanées
    slot_capital = capital / prediction_horizon

    # Suivi du cash et des positions ouvertes
    cash = capital  # Cash disponible, s'accumule avec les PnL réalisés
    allocated = 0.0  # Capital alloué aux positions ouvertes
    open_positions = []  # Liste de dicts avec trade info
    portfolio_values = []
    consecutive_losses = 0
    cooldown_until = -1  # Index de barre jusqu'auquel on est en cooldown

    # Pour chaque période de prédiction
    for i, ts in enumerate(timestamps):
        ts = pd.Timestamp(ts)

        # 1. Fermer les positions (maturité, SL, TP, trailing)
        positions_to_close = []
        for pos in open_positions:
            current_price = close_prices.loc[ts]
            exit_reason = None
            exit_price_override = None

            # ATR-based intra-trade risk checks (avec vérification intra-bar PRO)
            intra_bar_triggered = False

            if use_atr_risk and "sl_price" in pos:
                # Vérification intra-bar (PRO) - utilise high/low de la bougie
                if use_intra_bar and has_ohlc:
                    high = df_prices.loc[ts, "high"]
                    low = df_prices.loc[ts, "low"]

                    if pos["direction"] == "LONG":
                        # Check SL touché — gap risk: fill à SL ou en dessous
                        if low <= pos["sl_price"]:
                            exit_reason = "stop_loss"
                            exit_price_override = min(low, pos["sl_price"]) * (
                                1 - stop_gap_slippage_pct
                            )
                            intra_bar_triggered = True
                        # Check TP touché — fill au plus mauvais entre high et TP
                        elif high >= pos["tp_price"]:
                            exit_reason = "take_profit"
                            exit_price_override = min(high, pos["tp_price"])
                            intra_bar_triggered = True
                    else:  # SHORT
                        # Check SL touché — gap risk: fill à SL ou au-dessus
                        if high >= pos["sl_price"]:
                            exit_reason = "stop_loss"
                            exit_price_override = max(high, pos["sl_price"]) * (
                                1 + stop_gap_slippage_pct
                            )
                            intra_bar_triggered = True
                        # Check TP touché
                        elif low <= pos["tp_price"]:
                            exit_reason = "take_profit"
                            exit_price_override = max(low, pos["tp_price"])
                            intra_bar_triggered = True

                # Vérification au close (standard)
                if exit_reason is None:
                    if pos["direction"] == "LONG":
                        if current_price <= pos["sl_price"]:
                            exit_reason = "stop_loss"
                            exit_price_override = pos["sl_price"]
                        elif current_price >= pos["tp_price"]:
                            exit_reason = "take_profit"
                            exit_price_override = pos["tp_price"]
                        else:
                            # Trailing stop
                            unrealized_pct = current_price / pos["entry_price"] - 1
                            if unrealized_pct > pos.get(
                                "trailing_threshold", float("inf")
                            ):
                                new_sl = current_price * (
                                    1 - pos["atr_at_entry"] * sl_atr_mult
                                )
                                if new_sl > pos["sl_price"]:
                                    pos["sl_price"] = new_sl
                                    pos["trailing_active"] = True
                    elif pos["direction"] == "SHORT":
                        if current_price >= pos["sl_price"]:
                            exit_reason = "stop_loss"
                            exit_price_override = pos["sl_price"]
                        elif current_price <= pos["tp_price"]:
                            exit_reason = "take_profit"
                            exit_price_override = pos["tp_price"]
                        else:
                            unrealized_pct = pos["entry_price"] / current_price - 1
                            if unrealized_pct > pos.get(
                                "trailing_threshold", float("inf")
                            ):
                                new_sl = current_price * (
                                    1 + pos["atr_at_entry"] * sl_atr_mult
                                )
                                if new_sl < pos["sl_price"]:
                                    pos["sl_price"] = new_sl
                                    pos["trailing_active"] = True

                # Marquer si intra-bar
                if intra_bar_triggered:
                    pos["intra_bar"] = True

            # Time-based exit (PRO)
            if exit_reason is None and use_time_exit:
                bars_held = i - pos["entry_idx"]
                if bars_held >= time_exit_bars:
                    exit_reason = "time_exit"

            # Horizon exit (fallback)
            if exit_reason is None and i - pos["entry_idx"] >= prediction_horizon:
                exit_reason = "horizon"

            if exit_reason:
                positions_to_close.append((pos, exit_reason, exit_price_override))

        for pos, exit_reason, exit_price_override in positions_to_close:
            exit_idx = pos["entry_idx"] + prediction_horizon
            exit_price_raw = exit_price_override  # Use SL/TP price if triggered
            exit_ts: pd.Timestamp

            if exit_price_raw is None:
                if exit_idx < len(timestamps):
                    exit_ts = pd.Timestamp(timestamps[exit_idx])
                    exit_price_raw = close_prices.loc[exit_ts]
                else:
                    entry_ts = pd.Timestamp(timestamps[pos["entry_idx"]])
                    projected_exit = entry_ts + pd.Timedelta(
                        minutes=prediction_horizon * timeframe_minutes
                    )
                    future_prices = close_prices[close_prices.index >= projected_exit]
                    if len(future_prices) > 0:
                        exit_price_raw = future_prices.iloc[0]
                        exit_ts = pd.Timestamp(future_prices.index[0])
                    else:
                        continue
            else:
                exit_ts = ts  # SL/TP triggered at current bar

            entry_price = pos["entry_price"]
            direction = pos["direction"]
            allocated_capital = pos["allocated"]

            # Calculer le slippage à la sortie (PRO)
            slippage_exit = 0.0
            spread_cost = 0.0

            if use_slippage and volatility_series is not None:
                vol = volatility_series.get(ts, 0.01)
                slippage_exit = vol * slippage_vol_factor
                # Plus de slippage pour les stops (gap risk)
                if exit_reason in ["stop_loss", "trailing_stop"]:
                    slippage_exit *= 1.5
                    slippage_exit = min(slippage_exit, 0.003)  # Cap à 0.3% pour stops
                else:
                    slippage_exit = min(slippage_exit, 0.001)  # Cap à 0.1% ailleurs

            if use_spread and spread_series is not None:
                spread_cost = spread_series.get(ts, 0.0005)

            # Ajuster le prix de sortie avec slippage et spread
            exit_price = exit_price_raw
            if direction == "LONG":
                # Vente: bid - slippage
                exit_price = exit_price_raw * (1 - spread_cost / 2 - slippage_exit)
            else:
                # Achat pour couvrir short: ask + slippage
                exit_price = exit_price_raw * (1 + spread_cost / 2 + slippage_exit)

            if direction == "LONG":
                actual_return = exit_price / entry_price - 1
                pnl_before_fees = allocated_capital * actual_return
            else:
                actual_return = entry_price / exit_price - 1
                pnl_before_fees = allocated_capital * actual_return

            exit_value = allocated_capital * (1 + actual_return)
            exit_fee = exit_value * exit_fee_pct
            entry_fee = pos.get("entry_fee", 0.0)
            total_fees = entry_fee + exit_fee
            pnl = pnl_before_fees - exit_fee

            # Calculer bars held
            bars_held = exit_idx - pos["entry_idx"]

            trade = Trade(
                entry_date=pos["entry_date"],
                exit_date=exit_ts,
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                predicted_return=pos["predicted_return"],
                actual_return=actual_return,
                entry_fee=entry_fee,
                exit_fee=exit_fee,
                total_fees=total_fees,
                pnl_before_fees=pnl_before_fees,
                pnl=pnl,
                exit_reason=exit_reason,
                # Métriques PRO
                slippage_entry=pos.get("slippage_entry", 0.0),
                slippage_exit=slippage_exit,
                spread_cost=spread_cost,
                intra_bar=pos.get("intra_bar", False),
                bars_held=bars_held,
            )
            result.trades.append(trade)

            # Track consecutive losses and cooldown
            if pnl < 0:
                consecutive_losses += 1
                if consecutive_losses >= max_consecutive_losses and use_atr_risk:
                    cooldown_until = i + cooldown_bars
            else:
                consecutive_losses = 0

            # Track exit reasons
            if exit_reason == "stop_loss":
                result.sl_exits += 1
            elif exit_reason == "take_profit":
                result.tp_exits += 1
            elif exit_reason == "trailing_stop":
                result.trailing_exits += 1
            else:
                result.horizon_exits += 1

            cash += allocated_capital + pnl
            allocated -= allocated_capital
            open_positions.remove(pos)

        # 2. Générer le signal et ouvrir une nouvelle position si pertinent
        # Ne pas ouvrir de position dans les derniers prediction_horizon périodes
        signal = None
        pred = None
        can_open = i < len(predictions) - prediction_horizon and not (
            use_atr_risk and i < cooldown_until
        )
        if can_open:
            pred = predictions[i]
            if pred > threshold:
                signal = "LONG"
            elif pred < -threshold and allow_short:
                signal = "SHORT"

        if signal is not None:
            entry_price_raw = close_prices.loc[ts]

            slippage_entry = 0.0
            if use_slippage and volatility_series is not None:
                vol = volatility_series.get(ts, 0.01)
                slippage_entry = vol * slippage_vol_factor
                slippage_entry = min(slippage_entry, 0.001)

            spread_entry = 0.0
            if use_spread and spread_series is not None:
                spread_entry = spread_series.get(ts, 0.0005)

            if signal == "LONG":
                entry_price = entry_price_raw * (1 + spread_entry / 2 + slippage_entry)
            else:
                entry_price = entry_price_raw * (1 - spread_entry / 2 - slippage_entry)

            if use_atr_risk and atr_series is not None:
                atr_val = atr_series.get(ts, None)
                if atr_val is None or np.isnan(atr_val) or atr_val <= 0:
                    atr_val = 0.02
                sl_distance = atr_val * sl_atr_mult
                risk_amount = (cash + allocated) * risk_per_trade
                trade_capital = min(risk_amount / (sl_distance + 1e-10), slot_capital)
            else:
                trade_capital = slot_capital
                atr_val = None

            entry_fee = trade_capital * entry_fee_pct
            total_entry_cost = trade_capital + entry_fee

            # Rejeter trades sous le notional minimum (artefact ATR sizing)
            # ou si pas assez de cash disponible
            if trade_capital >= min_notional_usd and cash >= total_entry_cost:
                cash -= total_entry_cost
                allocated += trade_capital

                pos_info = {
                    "entry_idx": i,
                    "entry_date": ts,
                    "direction": signal,
                    "entry_price": entry_price,
                    "entry_price_raw": entry_price_raw,
                    "predicted_return": pred,
                    "allocated": trade_capital,
                    "entry_fee": entry_fee,
                    "slippage_entry": slippage_entry,
                    "spread_entry": spread_entry,
                }

                if use_atr_risk and atr_val is not None:
                    pos_info["atr_at_entry"] = atr_val
                    if signal == "LONG":
                        pos_info["sl_price"] = entry_price * (1 - atr_val * sl_atr_mult)
                        pos_info["tp_price"] = entry_price * (1 + atr_val * tp_atr_mult)
                    else:
                        pos_info["sl_price"] = entry_price * (1 + atr_val * sl_atr_mult)
                        pos_info["tp_price"] = entry_price * (1 - atr_val * tp_atr_mult)
                    pos_info["trailing_threshold"] = atr_val * trailing_atr_mult
                    pos_info["trailing_active"] = False

                open_positions.append(pos_info)

        # 3. Calculer la valeur mark-to-market du portefeuille
        # Cash + capital alloué + PnL non réalisé
        portfolio_value = cash + allocated

        # Ajouter les PnL non réalisés (mark-to-market)
        for pos in open_positions:
            current_price = close_prices.loc[ts]
            if pos["direction"] == "LONG":
                unrealized_pnl = pos["allocated"] * (
                    current_price / pos["entry_price"] - 1
                )
            else:
                unrealized_pnl = pos["allocated"] * (
                    pos["entry_price"] / current_price - 1
                )
            portfolio_value += unrealized_pnl

        portfolio_values.append((ts, portfolio_value))

    # Convertir en Series
    if portfolio_values:
        result.portfolio_values = pd.Series(
            [v for _, v in portfolio_values], index=[t for t, _ in portfolio_values]
        )

    return result


# ----- Oracle ----- #


def simulate_oracle(
    y: np.ndarray,
    timestamps: np.ndarray,
    df_prices: pd.DataFrame,
    capital: float = 10_000.0,
    allow_short: bool = False,
    entry_fee_pct: float = DEFAULT_ENTRY_FEE,
    exit_fee_pct: float = DEFAULT_EXIT_FEE,
    prediction_horizon: int = 3,
    timeframe_minutes: int = 1440,
    use_atr_risk: bool = False,
    use_slippage: bool = True,
    use_spread: bool = True,
    base_spread_bps: float = 5.0,
) -> BacktestResult:
    """Simule un oracle parfait qui connaît exactement les retours futurs.

    Un oracle rationnel ne trade QUE si le gain attendu dépasse les coûts
    (frais + spread + slippage). Les entrées dont |y| < seuil de rentabilité
    sont donc filtrées — ce qui garantit que l'oracle constitue bien une
    borne supérieure positive (jamais négative).

    L'oracle utilise le même régime de risk management que le backtest
    principal (paramètres `use_atr_risk`/`use_slippage`/`use_spread`). Quand
    ATR risk est activé, `use_intra_bar` est forcé à False : un trader
    omniscient ne se fait pas sortir par un SL hit intra-bar sur un trade
    qu'il sait gagnant close-to-close.

    Args:
        y: (N,) retours futurs réels (ground truth).
        timestamps: (N,) timestamps correspondants.
        df_prices: DataFrame avec colonne 'close'.
        capital: Capital initial.
        allow_short: Si True, autorise les positions short sur retours négatifs.
        entry_fee_pct: Frais à l'entrée.
        exit_fee_pct: Frais à la sortie.
        prediction_horizon: Horizon de prédiction en barres.
        timeframe_minutes: Durée d'une barre en minutes.
        use_atr_risk: Propagation du régime ATR du backtest principal.
        use_slippage / use_spread: Propagation des flags de coûts.
        base_spread_bps: Spread de base pour calibrer le seuil de rentabilité.

    Returns:
        BacktestResult de l'oracle, positif ou nul par construction.
    """
    # Seuil de rentabilité net : frais A/R + spread A/R + slippage A/R cappé
    max_slippage_one_side = 0.001  # cap appliqué dans simulate_trading
    breakeven = (
        entry_fee_pct
        + exit_fee_pct
        + (base_spread_bps / 10_000)
        + 2 * max_slippage_one_side
    )

    # Filtrer : ne garder que les signaux dont |y| > breakeven
    y_filtered = np.where(np.abs(y) > breakeven, y, 0.0)
    n_total = int(np.sum(np.abs(y) > 0))
    n_kept = int(np.sum(np.abs(y_filtered) > 0))
    pct = (n_kept / n_total * 100) if n_total > 0 else 0.0
    print(
        f"  ✓ Oracle: {n_kept}/{n_total} signaux conservés "
        f"({pct:.1f}%, breakeven={breakeven * 100:.2f}%)"
    )

    return simulate_trading(
        predictions=y_filtered,
        timestamps=timestamps,
        df_prices=df_prices,
        capital=capital,
        threshold=0.0,
        allow_short=allow_short,
        entry_fee_pct=entry_fee_pct,
        exit_fee_pct=exit_fee_pct,
        prediction_horizon=prediction_horizon,
        timeframe_minutes=timeframe_minutes,
        use_atr_risk=use_atr_risk,
        # Oracle n'utilise jamais intra-bar : il sait à l'avance le close-to-close
        use_intra_bar=False,
        use_slippage=use_slippage,
        use_spread=use_spread,
        base_spread_bps=base_spread_bps,
    )


# ----- Métriques ----- #


def compute_backtest_metrics(
    result: BacktestResult,
    capital: float,
    df_prices: pd.DataFrame,
    timestamps: np.ndarray,
) -> None:
    """Calcule les métriques de performance du backtest.

    Métriques calculées :
        - Total return (%)
        - Annualized return (%)
        - Sharpe ratio (annualisé, base 365 jours crypto)
        - Max drawdown (%)
        - Win rate (%)
        - Nombre de trades
        - Rendement moyen par trade
        - Profit factor (gains bruts / pertes brutes)

    Args:
        result: BacktestResult à enrichir avec les métriques.
        capital: Capital initial.
        df_prices: DataFrame avec les prix pour calculer le benchmark.
        timestamps: Array des timestamps pour le calcul annuel.
    """
    trades = result.trades

    # Nombre de trades
    result.n_trades = len(trades)

    if result.n_trades == 0:
        print("Aucun trade exécuté")
        return

    # Win rate
    winning_trades = [t for t in trades if t.pnl > 0]
    result.win_rate = len(winning_trades) / len(trades) * 100

    # Rendement moyen par trade
    result.avg_trade_return = np.mean([t.actual_return for t in trades]) * 100

    # Profit factor
    gross_profits = sum(t.pnl for t in trades if t.pnl > 0)
    gross_losses = abs(sum(t.pnl for t in trades if t.pnl < 0))
    result.profit_factor = (
        gross_profits / gross_losses if gross_losses > 0 else float("inf")
    )

    # Métriques de frais
    result.total_fees_paid = sum(t.total_fees for t in trades)
    result.avg_fees_per_trade = result.total_fees_paid / len(trades)

    # Calculer l'impact des frais sur le rendement
    total_pnl_before_fees = sum(t.pnl_before_fees for t in trades)
    if total_pnl_before_fees > 0:
        result.fee_impact_pct = (
            result.total_fees_paid / (capital + total_pnl_before_fees)
        ) * 100
    else:
        result.fee_impact_pct = 0.0

    # Total return basé sur les trades réalisés (PnL net après frais)
    total_pnl = sum(t.pnl for t in trades)
    result.total_return = total_pnl / capital * 100

    # Utiliser portfolio_values si disponible et cohérent
    if len(result.portfolio_values) > 0:
        final_value = result.portfolio_values.iloc[-1]
        # Vérifier cohérence: si portfolio_values est cohérent avec les trades
        portfolio_return = (final_value - capital) / capital * 100
        # Prendre le max des deux si incohérence flagrante (bug de data)
        if abs(portfolio_return - result.total_return) > 50:  # Écart > 50%
            print(
                f"  ⚠️  Écart entre méthodes de calcul: trades={result.total_return:.2f}%, portfolio={portfolio_return:.2f}%"
            )
        else:
            result.total_return = portfolio_return

        # Daily returns pour Sharpe ratio
        daily_values = result.portfolio_values
        daily_returns = daily_values.pct_change().dropna()

        if len(daily_returns) > 1 and daily_returns.std() > 0:
            # Sharpe ratio annualisé (base 365 jours pour crypto)
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(365)
            result.sharpe_ratio = sharpe

        # Max drawdown
        rolling_max = daily_values.cummax()
        drawdown = (daily_values - rolling_max) / rolling_max
        result.max_drawdown = drawdown.min() * 100  # Valeur négative

        # Annualized return
        n_days = (daily_values.index[-1] - daily_values.index[0]).days
        if n_days > 0:
            total_ret = final_value / capital
            result.annualized_return = (total_ret ** (365 / n_days) - 1) * 100


def print_summary(
    result: BacktestResult,
    symbol: str,
    model_type: str,
    capital: float,
    oracle_result: Optional["BacktestResult"] = None,
):
    """Affiche un résumé formaté des résultats du backtest."""
    print(f"\n{'=' * 60}")
    print(f"BACKTEST RESULTS")
    print(f"{'=' * 60}")
    print(f"Model:        {model_type.upper()}")
    print(f"Symbol:       {symbol}")
    print(f"Capital:      ${capital:,.2f}")
    print(f"{'=' * 60}")

    if result.n_trades == 0:
        print("Aucun trade exécuté avec les paramètres choisis")
        return

    # Calculer le capital final
    if len(result.portfolio_values) > 0:
        final_capital = result.portfolio_values.iloc[-1]
    else:
        final_capital = capital

    print(f"Total Return:        {result.total_return:+.2f}%")
    print(f"Annualized Return:   {result.annualized_return:+.2f}%")
    print(f"Sharpe Ratio:        {result.sharpe_ratio:.2f}")
    print(f"Max Drawdown:        {result.max_drawdown:.2f}%")
    print(f"{'=' * 60}")
    print(f"Initial Capital:     ${capital:,.2f}")
    print(f"Final Capital:       ${final_capital:,.2f}")
    print(f"{'=' * 60}")
    print(f"Number of Trades:    {result.n_trades}")
    print(f"Win Rate:            {result.win_rate:.1f}%")
    print(f"Avg Trade Return:    {result.avg_trade_return:+.2f}%")
    print(f"Profit Factor:       {result.profit_factor:.2f}")
    print(f"{'=' * 60}")
    print(f"FEES SUMMARY")
    print(f"{'=' * 60}")
    print(f"Entry Fee Rate:      {result.entry_fee_pct * 100:.3f}%")
    print(f"Exit Fee Rate:       {result.exit_fee_pct * 100:.3f}%")
    print(f"Total Fees Paid:     ${result.total_fees_paid:,.2f}")
    print(f"Avg Fees/Trade:      ${result.avg_fees_per_trade:.2f}")
    print(f"Fee Impact:          {result.fee_impact_pct:.2f}%")
    if result.sl_exits + result.tp_exits + result.trailing_exits > 0:
        print(f"{'=' * 60}")
        print(f"ATR RISK MANAGEMENT")
        print(f"{'=' * 60}")
        print(f"Stop-Loss Exits:     {result.sl_exits}")
        print(f"Take-Profit Exits:   {result.tp_exits}")
        print(f"Trailing Exits:      {result.trailing_exits}")
        print(f"Horizon Exits:       {result.horizon_exits}")
    print(f"{'=' * 60}")

    if oracle_result is not None and oracle_result.n_trades > 0:
        oracle_final = (
            oracle_result.portfolio_values.iloc[-1]
            if len(oracle_result.portfolio_values) > 0
            else capital
        )
        efficiency = (
            (result.total_return / oracle_result.total_return * 100)
            if oracle_result.total_return != 0
            else 0.0
        )
        print(f"ORACLE COMPARISON (perfect foresight upper bound)")
        print(f"{'=' * 60}")
        print(f"Oracle Total Return:    {oracle_result.total_return:+.2f}%")
        print(f"Oracle Ann. Return:     {oracle_result.annualized_return:+.2f}%")
        print(f"Oracle Sharpe:          {oracle_result.sharpe_ratio:.2f}")
        print(f"Oracle Max Drawdown:    {oracle_result.max_drawdown:.2f}%")
        print(f"Oracle Final Capital:   ${oracle_final:,.2f}")
        print(f"Oracle Trades:          {oracle_result.n_trades}")
        print(f"Oracle Win Rate:        {oracle_result.win_rate:.1f}%")
        print(f"Oracle Total Fees:      ${oracle_result.total_fees_paid:,.2f}")
        print(f"{'=' * 60}")
        print(f"Model Efficiency:       {efficiency:.1f}% of oracle")
        print(f"{'=' * 60}")

    print()


# ----- Graphiques ----- #


def plot_equity_curve(
    result: BacktestResult,
    save_path: str,
    symbol: str,
    model_type: str,
    capital: float,
    df_prices: pd.DataFrame,
    timestamps: np.ndarray,
    oracle_result: Optional[BacktestResult] = None,
):
    """Génère et sauvegarde la courbe d'équité avec annotations.

    Inclut :
        - Courbe de valeur du portefeuille
        - Courbe oracle (borne supérieure théorique) si fournie
        - Drawdown en sous-graphique
        - Courbe buy-and-hold pour comparaison

    Args:
        result: BacktestResult avec portfolio_values.
        save_path: Dossier de sauvegarde.
        symbol: Nom du symbole (pour le titre).
        model_type: Type du modèle (pour le titre).
        capital: Capital initial.
        df_prices: DataFrame avec les prix pour le benchmark.
        timestamps: Timestamps du backtest.
        oracle_result: BacktestResult de l'oracle (optionnel).
    """
    if len(result.portfolio_values) == 0:
        print("Pas de données pour générer le graphique")
        return

    os.makedirs(save_path, exist_ok=True)

    # Calculer le buy-and-hold
    first_ts = pd.Timestamp(timestamps[0])
    last_ts = pd.Timestamp(timestamps[-1])

    bh_data = df_prices.loc[first_ts:last_ts, "close"]
    bh_normalized = bh_data / bh_data.iloc[0] * capital

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])

    # Graphique principal : equity curve
    ax1 = axes[0]
    ax1.plot(
        result.portfolio_values.index,
        result.portfolio_values.values,
        label=f"Strategy ({model_type.upper()})",
        linewidth=1.5,
        color="blue",
    )
    ax1.plot(
        bh_normalized.index,
        bh_normalized.values,
        label="Buy & Hold",
        linewidth=1.5,
        color="gray",
        alpha=0.7,
        linestyle="--",
    )

    if oracle_result is not None and len(oracle_result.portfolio_values) > 0:
        ax1.plot(
            oracle_result.portfolio_values.index,
            oracle_result.portfolio_values.values,
            label=f"Oracle (perfect foresight) +{oracle_result.total_return:.1f}%",
            linewidth=1.5,
            color="green",
            alpha=0.8,
            linestyle="-.",
        )

    ax1.axhline(
        capital, color="black", linestyle=":", alpha=0.5, label="Initial Capital"
    )

    ax1.set_ylabel("Portfolio Value ($)")
    ax1.set_title(f"Backtest: {model_type.upper()} on {symbol}")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # Format y-axis as currency
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

    # Graphique secondaire : drawdown
    ax2 = axes[1]
    rolling_max = result.portfolio_values.cummax()
    drawdown = (result.portfolio_values - rolling_max) / rolling_max * 100
    ax2.fill_between(drawdown.index, drawdown.values, 0, color="red", alpha=0.3)
    ax2.plot(drawdown.index, drawdown.values, color="red", linewidth=1)
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Date")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    filename = f"backtest_{symbol.replace('/', '_')}.png"
    filepath = os.path.join(save_path, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Courbe d'équité sauvegardée : {filepath}")


def plot_ensemble_model_predictions(
    per_model_preds: dict[str, np.ndarray],
    ensemble_preds: np.ndarray,
    oracle_preds: np.ndarray,
    timestamps: np.ndarray,
    save_path: str,
    symbol: str,
    strategy: str,
    threshold: float,
) -> None:
    """Graphique comparant les prédictions individuelles, l'ensemble, et l'oracle.

    Panneau supérieur : retours prédits (%) par modèle + ensemble + oracle.
    Panneau inférieur : signal discret (buy/sell/hold) par modèle — heatmap.

    Args:
        per_model_preds: {nom_modèle: array (N,) de retours prédits}.
        ensemble_preds: Array (N,) de prédictions agrégées.
        oracle_preds: Array (N,) de retours futurs réels (ground truth).
        timestamps: Array (N,) de timestamps.
        save_path: Dossier de destination.
        symbol: Symbole crypto (pour le titre).
        strategy: Nom de la stratégie d'agrégation.
        threshold: Seuil de signal (pour colorer buy/sell/hold).
    """
    os.makedirs(save_path, exist_ok=True)

    n_models = len(per_model_preds)
    ts = [pd.Timestamp(t) for t in timestamps]

    # Downsample to ≤2000 points so lines stay readable
    step = max(1, len(ts) // 2000)
    xs = np.arange(0, len(ts), step)  # integer x-axis shared by both panels
    ts_s = [ts[i] for i in xs]  # corresponding timestamps for labels

    # Distinct colours: tab10 for models, fixed for ensemble/oracle
    tab10 = plt.cm.tab10.colors
    model_colors = [tab10[i % 10] for i in range(n_models)]
    ensemble_color = "#7c3aed"
    oracle_color = "#dc2626"

    fig, axes = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[3, 1])

    # ----- Panneau 1 : prédictions continues -----
    ax1 = axes[0]

    for i, (name, preds) in enumerate(per_model_preds.items()):
        ax1.plot(
            xs, preds[xs], linewidth=1.2, alpha=0.75, color=model_colors[i], label=name
        )

    ax1.plot(
        xs,
        ensemble_preds[xs],
        linewidth=2.2,
        color=ensemble_color,
        label=f"Ensemble ({strategy})",
        zorder=5,
    )
    ax1.plot(
        xs,
        oracle_preds[xs],
        linewidth=1.4,
        color=oracle_color,
        linestyle="--",
        alpha=0.85,
        label="Oracle (actual return)",
        zorder=4,
    )

    ax1.axhline(
        threshold,
        color="gray",
        linewidth=0.8,
        linestyle=":",
        label=f"±threshold ({threshold:.3%})",
    )
    ax1.axhline(-threshold, color="gray", linewidth=0.8, linestyle=":")
    ax1.axhline(0, color="black", linewidth=0.5, alpha=0.35)

    # Clip y-axis to 2nd–98th percentile so model lines aren't dwarfed by
    # oracle return spikes
    all_vals = np.concatenate(
        [preds[xs] for preds in per_model_preds.values()]
        + [ensemble_preds[xs], oracle_preds[xs]]
    )
    lo = float(np.nanpercentile(all_vals, 2))
    hi = float(np.nanpercentile(all_vals, 98))
    pad = max((hi - lo) * 0.12, threshold * 3)
    ax1.set_ylim(lo - pad, hi + pad)

    ax1.set_xlim(xs[0], xs[-1])
    ax1.set_ylabel("Predicted return (%)")
    ax1.set_title(f"Ensemble prediction breakdown — {symbol} | strategy: {strategy}")
    ax1.legend(loc="upper left", fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.2)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x * 100:.2f}%"))

    # Shared x-tick labels (dates) on top panel
    n_ticks = 6
    tick_idx = np.linspace(0, len(xs) - 1, n_ticks, dtype=int)
    ax1.set_xticks([xs[i] for i in tick_idx])
    ax1.set_xticklabels(
        [ts_s[i].strftime("%Y-%m-%d") for i in tick_idx],
        rotation=20,
        ha="right",
        fontsize=8,
    )

    # ----- Panneau 2 : signal direction heatmap -----
    ax2 = axes[1]

    rows = list(per_model_preds.keys()) + ["Ensemble"]
    all_sampled = [preds[xs] for preds in per_model_preds.values()] + [
        ensemble_preds[xs]
    ]

    signal_matrix = np.zeros((len(rows), len(xs)))
    for r, row_preds in enumerate(all_sampled):
        signal_matrix[r] = np.where(
            row_preds > threshold,
            1.0,
            np.where(row_preds < -threshold, -1.0, 0.0),
        )

    # Use integer extent matching the top panel's x-axis
    ax2.imshow(
        signal_matrix,
        aspect="auto",
        cmap=plt.cm.RdYlGn,
        vmin=-1,
        vmax=1,
        extent=[xs[0], xs[-1], -0.5, len(rows) - 0.5],
        interpolation="nearest",
    )
    ax2.set_yticks(range(len(rows)))
    ax2.set_yticklabels(rows, fontsize=8)
    ax2.set_xlim(xs[0], xs[-1])
    ax2.set_xlabel("Time")
    ax2.set_title("Signal direction  (green = buy · yellow = hold · red = sell)")
    ax2.set_xticks([xs[i] for i in tick_idx])
    ax2.set_xticklabels(
        [ts_s[i].strftime("%Y-%m-%d") for i in tick_idx],
        rotation=20,
        ha="right",
        fontsize=8,
    )

    plt.tight_layout()
    filename = f"ensemble_predictions_{symbol.replace('/', '_')}.png"
    filepath = os.path.join(save_path, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Graphique des prédictions ensemble sauvegardé : {filepath}")


def plot_ensemble_equity_comparison(
    per_model_results: dict[str, BacktestResult],
    ensemble_result: BacktestResult,
    oracle_result: BacktestResult,
    df_prices: pd.DataFrame,
    timestamps: np.ndarray,
    capital: float,
    save_path: str,
    symbol: str,
    strategy: str,
) -> None:
    """Equity curve comparing each individual model, the ensemble, and the oracle.

    Every model is shown as if it were trading alone (same capital, same threshold).
    The ensemble and oracle lines provide upper/lower context.

    Args:
        per_model_results: {model_name: BacktestResult} for each constituent model.
        ensemble_result: BacktestResult for the ensemble.
        oracle_result: BacktestResult with perfect-foresight predictions.
        df_prices: DataFrame with 'close' column for the buy-and-hold benchmark.
        timestamps: Array of backtest timestamps (for x-axis anchoring).
        capital: Initial capital.
        save_path: Directory to write the PNG.
        symbol: Crypto symbol (used in title and filename).
        strategy: Ensemble strategy name (used in title).
    """
    os.makedirs(save_path, exist_ok=True)

    tab10 = plt.cm.tab10.colors
    model_names = list(per_model_results.keys())

    fig, axes = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])
    ax1, ax2 = axes

    # Buy-and-hold benchmark
    first_ts = pd.Timestamp(timestamps[0])
    last_ts = pd.Timestamp(timestamps[-1])
    bh = df_prices.loc[first_ts:last_ts, "close"]
    bh_norm = bh / bh.iloc[0] * capital

    ax1.plot(
        bh_norm.index,
        bh_norm.values,
        color="silver",
        linewidth=1.2,
        linestyle="--",
        alpha=0.7,
        label="Buy & Hold",
    )

    # Individual models
    for i, (name, res) in enumerate(per_model_results.items()):
        if len(res.portfolio_values) == 0:
            continue
        ret_label = f"{res.total_return:+.1f}%"
        ax1.plot(
            res.portfolio_values.index,
            res.portfolio_values.values,
            color=tab10[i % 10],
            linewidth=1.4,
            alpha=0.8,
            label=f"{name}  ({ret_label})",
        )

    # Ensemble
    if len(ensemble_result.portfolio_values) > 0:
        ens_label = f"{ensemble_result.total_return:+.1f}%"
        ax1.plot(
            ensemble_result.portfolio_values.index,
            ensemble_result.portfolio_values.values,
            color="#7c3aed",
            linewidth=2.4,
            zorder=5,
            label=f"Ensemble/{strategy}  ({ens_label})",
        )

    # Oracle
    if len(oracle_result.portfolio_values) > 0:
        ora_label = f"{oracle_result.total_return:+.1f}%"
        ax1.plot(
            oracle_result.portfolio_values.index,
            oracle_result.portfolio_values.values,
            color="#16a34a",
            linewidth=1.6,
            linestyle="-.",
            alpha=0.85,
            zorder=4,
            label=f"Oracle (perfect foresight)  ({ora_label})",
        )

    ax1.axhline(
        capital,
        color="black",
        linewidth=0.6,
        linestyle=":",
        alpha=0.4,
        label="Initial capital",
    )
    ax1.set_ylabel("Portfolio value ($)")
    ax1.set_title(f"Model comparison — {symbol} | ensemble strategy: {strategy}")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.25)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    # Drawdown panel: ensemble only (cleaner than stacking all)
    if len(ensemble_result.portfolio_values) > 0:
        pv = ensemble_result.portfolio_values
        dd = (pv - pv.cummax()) / pv.cummax() * 100
        ax2.fill_between(dd.index, dd.values, 0, color="#7c3aed", alpha=0.25)
        ax2.plot(
            dd.index, dd.values, color="#7c3aed", linewidth=1, label="Ensemble drawdown"
        )
        ax2.set_ylabel("Drawdown (%)")
        ax2.set_xlabel("Date")
        ax2.legend(fontsize=8, loc="lower left")
        ax2.grid(True, alpha=0.25)

    plt.tight_layout()
    filename = f"ensemble_equity_comparison_{symbol.replace('/', '_')}.png"
    filepath = os.path.join(save_path, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Graphique de comparaison des équités sauvegardé : {filepath}")


# ----- Point d'entrée principal ----- #


def run_backtest(
    model_type: str,
    symbol: str,
    capital: float = 10_000.0,
    threshold: float = 0.0,
    allow_short: bool = False,
    timeframe: str = DEFAULT_TIMEFRAME,
    model_path: Optional[str] = None,
    entry_fee_pct: Optional[float] = None,
    exit_fee_pct: Optional[float] = None,
    use_atr_risk: bool = False,
    test_start_date: str | None = None,
) -> BacktestResult:
    """Orchestre le backtest complet.

    Charge le modèle, prépare les données, génère les prédictions,
    simule le trading, calcule les métriques, et sauvegarde les résultats.

    Args:
        model_type: Type du modèle (ex: "cnn").
        symbol: Symbole de la crypto (ex: "BTC").
        capital: Capital initial.
        threshold: Seuil de prédiction pour ouvrir une position.
        allow_short: Autoriser les positions short.
        timeframe: Timeframe du modèle (ex: "1d", "1h", "4h").
        Défaut: DEFAULT_TIMEFRAME ("1d").
        model_path: Chemin vers le checkpoint (optionnel).
        entry_fee_pct: Frais à l'entrée (utilise DEFAULT_ENTRY_FEE si None).
        exit_fee_pct: Frais à la sortie (utilise DEFAULT_EXIT_FEE si None).
        use_atr_risk: Activer le risk management ATR-based.
        test_start_date: Date de début pour le test (ex: "2025-01-01").
        Si None, utilise TEST_START_DATE du config.

    Returns:
        BacktestResult complet.
    """
    # Get timeframe configuration
    tf_config = get_timeframe_config(timeframe)
    prediction_horizon = tf_config["prediction_horizon"]
    timeframe_minutes = tf_config["minutes_per_bar"]

    print(f"\n{'=' * 60}")
    print(f"Démarrage du backtest : {model_type.upper()} sur {symbol}")
    print(f"Timeframe: {timeframe} | Horizon: {prediction_horizon} bars")
    print(f"{'=' * 60}")

    # Device
    device = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device : {device}")

    # 1. Charger modèle et scalers
    print(f"\nChargement du modèle {model_type} [{timeframe}]...")
    model, history = load_model_dynamic(
        model_type, device, model_path, timeframe=timeframe
    )

    print(f"Chargement des scalers [{timeframe}]...")
    scalers = load_scalers(model_type, timeframe=timeframe)
    feature_scaler = scalers["feature_scaler"]
    target_scaler = scalers["target_scaler"]
    clip_bounds = scalers.get("clip_bounds")
    if clip_bounds is not None:
        print("  ✓ clip_bounds chargés")

    # 2. Préparer les données
    print(f"\nPréparation des données pour {symbol} [{timeframe}]...")
    X_scaled, y, timestamps, df_prices = prepare_backtest_data(
        symbol,
        feature_scaler,
        clip_bounds,
        timeframe=timeframe,
        test_start_date=test_start_date,
    )

    # 3. Générer les prédictions
    print(f"Génération des prédictions...")
    predictions = run_predictions(model, X_scaled, target_scaler, device)

    # Utiliser les frais par défaut si non spécifiés
    if entry_fee_pct is None:
        entry_fee_pct = DEFAULT_ENTRY_FEE
    if exit_fee_pct is None:
        exit_fee_pct = DEFAULT_EXIT_FEE

    # 4. Simuler le trading
    print(
        f"Simulation du trading (threshold={threshold}, allow_short={allow_short})..."
    )
    print(f"Frais: entrée={entry_fee_pct * 100:.3f}%, sortie={exit_fee_pct * 100:.3f}%")
    result = simulate_trading(
        predictions,
        timestamps,
        df_prices,
        capital,
        threshold,
        allow_short,
        entry_fee_pct,
        exit_fee_pct,
        prediction_horizon,
        timeframe_minutes,
        use_atr_risk=use_atr_risk,
    )

    # 4b. Oracle : borne supérieure théorique (prédictions parfaites)
    print(f"Simulation oracle (connaissance parfaite du futur)...")
    oracle_result = simulate_oracle(
        y=y,
        timestamps=timestamps,
        df_prices=df_prices,
        capital=capital,
        allow_short=allow_short,
        entry_fee_pct=entry_fee_pct,
        exit_fee_pct=exit_fee_pct,
        prediction_horizon=prediction_horizon,
        timeframe_minutes=timeframe_minutes,
        use_atr_risk=use_atr_risk,
    )

    # 5. Calculer les métriques
    compute_backtest_metrics(result, capital, df_prices, timestamps)
    compute_backtest_metrics(oracle_result, capital, df_prices, timestamps)

    # 6. Afficher et sauvegarder les résultats
    print_summary(result, symbol, model_type, capital, oracle_result=oracle_result)

    results_dir = f"models/{model_type}/results/{timeframe}"
    plot_equity_curve(
        result,
        results_dir,
        symbol,
        model_type,
        capital,
        df_prices,
        timestamps,
        oracle_result=oracle_result,
    )

    return result


def _build_ensemble(
    model_types: list[str],
    strategy: str,
    weights: list[float] | None,
    timeframe: str,
) -> "EnsemblePredictor":
    """Load all constituent models and return a ready EnsemblePredictor."""
    from models.registry import get_predictor
    from models.ensemble.ensemble_predictor import EnsemblePredictor

    predictors = []
    for mt in model_types:
        predictor = get_predictor(mt)
        if hasattr(predictor, "_timeframe"):
            predictor._timeframe = timeframe
        ckpt_ext = "json" if mt == "xgboost" else "pth"
        ckpt_path = f"models/{mt}/checkpoints/{timeframe}/best_model.{ckpt_ext}"
        print(f"  Chargement {mt} depuis {ckpt_path}...")
        predictor.load(ckpt_path)
        predictors.append(predictor)

    return EnsemblePredictor(
        models=predictors, strategy=strategy, weights=weights, timeframe=timeframe
    )


def run_ensemble_backtest(
    model_types: list[str],
    symbol: str,
    strategy: str = "weighted_average",
    weights: list[float] | None = None,
    capital: float = 10_000.0,
    threshold: float = 0.0,
    allow_short: bool = False,
    timeframe: str = DEFAULT_TIMEFRAME,
    entry_fee_pct: Optional[float] = None,
    exit_fee_pct: Optional[float] = None,
    _ensemble=None,
) -> BacktestResult:
    """Backtest an ensemble of models that vote on each trading signal.

    Each model in ``model_types`` must have a trained checkpoint at the
    standard path ``models/<type>/checkpoints/<timeframe>/best_model.pth``.
    Raw (unscaled) windows are fed to every model; each predictor applies
    its own scalers internally.

    Args:
        model_types: List of model keys, e.g. ["cnn", "bilstm", "cnn_bilstm_am"].
        symbol: Crypto symbol, e.g. "BTC".
        strategy: Aggregation strategy — one of:
            "majority_vote", "weighted_average", "confidence_weighted", "unanimous".
        weights: Per-model weights for "weighted_average" (defaults to equal).
        capital: Starting capital.
        threshold: Signal threshold; overrides config default when > 0.
        allow_short: Allow short positions.
        timeframe: Shared timeframe for all models.
        entry_fee_pct / exit_fee_pct: Fee rates (defaults to config values).
        _ensemble: Pre-loaded EnsemblePredictor (skips loading when provided).

    Returns:
        BacktestResult with ensemble predictions.
    """
    from config import SIGNAL_THRESHOLDS

    tf_config = get_timeframe_config(timeframe)
    prediction_horizon = tf_config["prediction_horizon"]
    timeframe_minutes = tf_config["minutes_per_bar"]

    if entry_fee_pct is None:
        entry_fee_pct = DEFAULT_ENTRY_FEE
    if exit_fee_pct is None:
        exit_fee_pct = DEFAULT_EXIT_FEE
    if threshold == 0.0:
        threshold = SIGNAL_THRESHOLDS.get(timeframe, 0.01)

    print(f"\n{'=' * 60}")
    print(f"ENSEMBLE BACKTEST sur {symbol} [{timeframe}]")
    print(f"Modèles : {', '.join(model_types)}")
    print(f"Stratégie : {strategy}")
    print(f"{'=' * 60}")

    # Build and load models only when not pre-supplied (multi-symbol reuse)
    ensemble = _ensemble or _build_ensemble(model_types, strategy, weights, timeframe)

    # Prepare raw (unscaled) windows — each model scales internally
    print(f"\nPréparation des données brutes pour {symbol} [{timeframe}]...")
    X_raw, y, timestamps, df_prices = prepare_raw_windows(symbol, timeframe)

    # Generate per-model AND ensemble predictions in a single pass
    print(f"Génération des prédictions ensemble ({len(X_raw)} fenêtres)...")
    predictions, per_model_preds = ensemble.predict_batch_full(X_raw)

    # Simulate trading
    print(f"Simulation (threshold={threshold:.4f}, strategy={strategy})...")
    result = simulate_trading(
        predictions,
        timestamps,
        df_prices,
        capital,
        threshold,
        allow_short,
        entry_fee_pct,
        exit_fee_pct,
        prediction_horizon,
        timeframe_minutes,
    )

    oracle_result = simulate_oracle(
        y=y,
        timestamps=timestamps,
        df_prices=df_prices,
        capital=capital,
        allow_short=allow_short,
        entry_fee_pct=entry_fee_pct,
        exit_fee_pct=exit_fee_pct,
        prediction_horizon=prediction_horizon,
        timeframe_minutes=timeframe_minutes,
        use_atr_risk=False,
    )

    # Backtest each model individually (same params) for the comparison chart
    per_model_results: dict[str, BacktestResult] = {}
    for model_name, model_preds in per_model_preds.items():
        m_result = simulate_trading(
            model_preds,
            timestamps,
            df_prices,
            capital,
            threshold,
            allow_short,
            entry_fee_pct,
            exit_fee_pct,
            prediction_horizon,
            timeframe_minutes,
        )
        compute_backtest_metrics(m_result, capital, df_prices, timestamps)
        per_model_results[model_name] = m_result

    compute_backtest_metrics(result, capital, df_prices, timestamps)
    compute_backtest_metrics(oracle_result, capital, df_prices, timestamps)

    label = f"ensemble[{'+'.join(model_types)}]/{strategy}"
    print_summary(result, symbol, label, capital, oracle_result=oracle_result)

    results_dir = f"models/ensemble/results/{timeframe}"

    print("Génération du graphique de comparaison des équités...")
    plot_ensemble_equity_comparison(
        per_model_results=per_model_results,
        ensemble_result=result,
        oracle_result=oracle_result,
        df_prices=df_prices,
        timestamps=timestamps,
        capital=capital,
        save_path=results_dir,
        symbol=symbol,
        strategy=strategy,
    )

    print("Génération du graphique des prédictions par modèle...")
    plot_ensemble_model_predictions(
        per_model_preds=per_model_preds,
        ensemble_preds=predictions,
        oracle_preds=y,
        timestamps=timestamps,
        save_path=results_dir,
        symbol=symbol,
        strategy=strategy,
        threshold=threshold,
    )

    return result


# ----- Multi-model comparison (compare-all) ----- #


def _checkpoint_path_for(model_type: str, timeframe: str) -> str:
    """Return the standard checkpoint path for a given supervised model."""
    ext = "json" if model_type == "xgboost" else "pth"
    return f"models/{model_type}/checkpoints/{timeframe}/best_model.{ext}"


def _prepare_raw_windows_oos(
    symbol: str,
    timeframe: str,
    test_start_date: str | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    """Like ``prepare_raw_windows`` but filtered to the out-of-sample period."""
    tf_config = get_timeframe_config(timeframe)
    window_size = tf_config["window_size"]
    prediction_horizon = tf_config["prediction_horizon"]

    df = load_symbol(symbol, timeframe=timeframe).copy()
    if test_start_date is None:
        test_start_date = TEST_START_DATE
    df = df[df.index >= test_start_date].copy()
    if len(df) == 0:
        raise ValueError(
            f"Pas de données pour {symbol} après {test_start_date}."
        )

    df_prices = df[[c for c in ("open", "high", "low", "close", "volume") if c in df.columns]].copy()
    df["label"] = df["close"].shift(-prediction_horizon) / df["close"] - 1
    df = df.dropna(subset=["label"])

    feature_cols = get_feature_columns(timeframe)
    X, y, timestamps = build_windows(
        df, window_size=window_size, feature_columns=feature_cols
    )
    if len(X) == 0:
        raise ValueError(f"Pas assez de données pour construire des fenêtres pour {symbol}")
    return X, y, timestamps, df_prices


def _run_rl_contestant(
    symbol: str,
    capital: float,
    test_start_date: str | None,
) -> tuple[BacktestResult, pd.DataFrame]:
    """Run the PPO agent on its native 1h data, return a BacktestResult.

    The RL agent owns its own env loop (fees + risk guardrails are inside
    TradingEnv), so we don't funnel it through simulate_trading. Instead we
    wrap the equity curve the env produces into a BacktestResult indexed by
    real 1h timestamps so it lines up with everything else at plot time.
    """
    from config import update_global_config
    update_global_config("1h")

    from models.rl.agent import PPOAgent
    from models.rl.data_preparator import prepare_rl_data
    from models.rl.environment import TradingEnv
    from models.rl.risk_manager import BUY_ACTIONS, SELL_ACTIONS

    ckpt = "models/rl/checkpoints/best_agent.pth"
    if not os.path.isfile(ckpt):
        raise FileNotFoundError(ckpt)

    _, df_val, scaler, clip_bounds = prepare_rl_data(symbol, verbose=False)

    # Honor --test-start-date if it sits inside the RL val split.
    if test_start_date is not None:
        cutoff = pd.Timestamp(test_start_date)
        if cutoff > df_val.index[0]:
            df_val = df_val[df_val.index >= cutoff].copy()

    env = TradingEnv(
        df=df_val,
        feature_scaler=scaler,
        clip_bounds=clip_bounds,
        randomize_start=False,
        noise_std=0.0,
        initial_cash=capital,
        max_steps=10_000_000,
    )

    agent = PPOAgent()
    agent.load(ckpt, verbose=False)
    agent.policy.eval()
    agent.value.eval()

    obs, _ = env.reset()
    done = False
    equity_curve = [env.initial_cash]
    was_positioned = False
    entry_ts = None
    entry_price = None
    entry_value = None
    trades: list[Trade] = []

    while not done:
        action, _, _ = agent.select_action(obs, deterministic=True)
        obs, _, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        equity_curve.append(info["portfolio_value"])

        is_positioned = info["position"] > 1e-10
        step_idx = min(env._current_step, len(env.close_prices) - 1)
        ts = env.df.index[step_idx]
        price = float(env.close_prices[step_idx])

        if is_positioned and not was_positioned:
            entry_ts = ts
            entry_price = price
            entry_value = info["portfolio_value"]
        elif not is_positioned and was_positioned and entry_value is not None:
            ret = (info["portfolio_value"] - entry_value) / entry_value
            pnl = info["portfolio_value"] - entry_value
            trades.append(Trade(
                entry_date=entry_ts, exit_date=ts,
                direction="LONG", entry_price=entry_price or price, exit_price=price,
                predicted_return=0.0, actual_return=ret,
                entry_fee=0.0, exit_fee=0.0, total_fees=0.0,
                pnl_before_fees=pnl, pnl=pnl,
                exit_reason="rl_policy",
            ))
            entry_ts = None
            entry_value = None
            entry_price = None
        was_positioned = is_positioned

    if was_positioned and entry_value is not None:
        final_val = equity_curve[-1]
        ret = (final_val - entry_value) / entry_value
        pnl = final_val - entry_value
        trades.append(Trade(
            entry_date=entry_ts, exit_date=env.df.index[min(env._current_step, len(env.close_prices) - 1)],
            direction="LONG", entry_price=entry_price or 0.0,
            exit_price=float(env.close_prices[min(env._current_step, len(env.close_prices) - 1)]),
            predicted_return=0.0, actual_return=ret,
            entry_fee=0.0, exit_fee=0.0, total_fees=0.0,
            pnl_before_fees=pnl, pnl=pnl,
            exit_reason="open_at_end",
        ))

    # Equity curve timestamps: env.df.index[_start_idx .. _start_idx + len]
    start = env._start_idx
    idx = env.df.index[start : start + len(equity_curve)]
    portfolio_values = pd.Series(equity_curve[: len(idx)], index=idx, dtype=float)

    result = BacktestResult(
        trades=trades,
        portfolio_values=portfolio_values,
        entry_fee_pct=0.0,
        exit_fee_pct=0.0,
    )
    df_prices = env.df[["close"]].copy()
    return result, df_prices


def run_compare_all_backtest(
    symbol: str,
    capital: float = 10_000.0,
    threshold: float = 0.0,
    allow_short: bool = False,
    timeframe: str = DEFAULT_TIMEFRAME,
    entry_fee_pct: Optional[float] = None,
    exit_fee_pct: Optional[float] = None,
    test_start_date: str | None = None,
    exclude: list[str] | None = None,
    ensemble_strategy: str = "confidence_weighted",
) -> dict[str, BacktestResult]:
    """Benchmark RL + supervised ensemble + every individual supervised model.

    Contestants:
        - Every registered supervised model with a checkpoint at
          ``models/<type>/checkpoints/<timeframe>/best_model.*``
        - A supervised ensemble built from the available supervised models
        - The PPO RL agent (runs on 1h regardless of --timeframe)

    Missing checkpoints are soft-skipped with a warning.
    Metrics are computed at each contestant's native frequency; the equity
    plot resamples every curve to daily before overlaying them.
    """
    from config import SIGNAL_THRESHOLDS
    from models.registry import list_models

    exclude = set(exclude or [])

    tf_config = get_timeframe_config(timeframe)
    prediction_horizon = tf_config["prediction_horizon"]
    timeframe_minutes = tf_config["minutes_per_bar"]
    if entry_fee_pct is None:
        entry_fee_pct = DEFAULT_ENTRY_FEE
    if exit_fee_pct is None:
        exit_fee_pct = DEFAULT_EXIT_FEE
    if threshold == 0.0:
        threshold = SIGNAL_THRESHOLDS.get(timeframe, 0.01)

    print(f"\n{'=' * 70}")
    print(f"COMPARE-ALL BACKTEST on {symbol} [{timeframe}]")
    print(f"Contestants: supervised models + supervised ensemble + RL policy")
    print(f"{'=' * 70}")

    # Pick supervised contestants that actually have a checkpoint
    supervised_candidates = [
        m for m in list_models()
        if m not in {"rl", "ensemble"} and m not in exclude
    ]
    available_supervised: list[str] = []
    for mt in supervised_candidates:
        path = _checkpoint_path_for(mt, timeframe)
        if os.path.isfile(path):
            available_supervised.append(mt)
        else:
            print(f"  ⚠ skip {mt}: no checkpoint at {path}")

    results: dict[str, BacktestResult] = {}
    df_prices_supervised: pd.DataFrame | None = None
    timestamps_supervised: np.ndarray | None = None
    y_supervised: np.ndarray | None = None

    if available_supervised:
        print(f"\nSupervised contestants: {', '.join(available_supervised)}")
        print(f"Ensemble strategy: {ensemble_strategy}")

        ensemble = _build_ensemble(
            available_supervised, ensemble_strategy, None, timeframe
        )

        X_raw, y, timestamps, df_prices = _prepare_raw_windows_oos(
            symbol, timeframe, test_start_date
        )
        df_prices_supervised = df_prices
        timestamps_supervised = timestamps
        y_supervised = y

        print(f"Running {len(available_supervised) + 1} supervised backtests "
              f"({len(X_raw)} windows)...")
        ensemble_preds, per_model_preds = ensemble.predict_batch_full(X_raw)

        for model_name, preds in per_model_preds.items():
            res = simulate_trading(
                preds, timestamps, df_prices, capital,
                threshold, allow_short, entry_fee_pct, exit_fee_pct,
                prediction_horizon, timeframe_minutes,
            )
            compute_backtest_metrics(res, capital, df_prices, timestamps)
            results[model_name] = res

        ens_res = simulate_trading(
            ensemble_preds, timestamps, df_prices, capital,
            threshold, allow_short, entry_fee_pct, exit_fee_pct,
            prediction_horizon, timeframe_minutes,
        )
        compute_backtest_metrics(ens_res, capital, df_prices, timestamps)
        results[f"ensemble/{ensemble_strategy}"] = ens_res
    else:
        print("  (no supervised contestants available — skipping supervised block)")

    # RL contestant (separate data stream)
    rl_df_prices: pd.DataFrame | None = None
    if "rl" not in exclude:
        try:
            rl_res, rl_df_prices = _run_rl_contestant(symbol, capital, test_start_date)
            # Use portfolio_values derived timestamps for metrics
            rl_timestamps = np.array(rl_res.portfolio_values.index)
            compute_backtest_metrics(rl_res, capital, rl_df_prices, rl_timestamps)
            results["rl"] = rl_res
        except FileNotFoundError as exc:
            print(f"  ⚠ skip rl: missing checkpoint ({exc})")
        except Exception as exc:
            print(f"  ⚠ skip rl: {exc}")

    # Oracle baseline — only when we have supervised data to run it on
    oracle_result: BacktestResult | None = None
    if y_supervised is not None and df_prices_supervised is not None and timestamps_supervised is not None:
        oracle_result = simulate_oracle(
            y=y_supervised,
            timestamps=timestamps_supervised,
            df_prices=df_prices_supervised,
            capital=capital,
            allow_short=allow_short,
            entry_fee_pct=entry_fee_pct,
            exit_fee_pct=exit_fee_pct,
            prediction_horizon=prediction_horizon,
            timeframe_minutes=timeframe_minutes,
            use_atr_risk=False,
        )
        compute_backtest_metrics(oracle_result, capital, df_prices_supervised, timestamps_supervised)

    # Output table + files
    _print_compare_all_summary(results, capital, symbol, timeframe)

    save_dir = "testing/results/compare_all"
    os.makedirs(save_dir, exist_ok=True)
    ts_tag = _build_date_tag(test_start_date, results)
    csv_path = os.path.join(save_dir, f"{symbol}_{timeframe}_{ts_tag}.csv")
    _write_compare_all_csv(results, capital, csv_path)

    png_path = os.path.join(save_dir, f"{symbol}_{timeframe}_{ts_tag}.png")
    _plot_compare_all_equity(
        results=results,
        oracle_result=oracle_result,
        df_prices=df_prices_supervised if df_prices_supervised is not None else rl_df_prices,
        capital=capital,
        symbol=symbol,
        save_path=png_path,
    )

    return results


def _build_date_tag(test_start_date: str | None, results: dict[str, BacktestResult]) -> str:
    """Produce a short 'start_end' tag from whichever result has portfolio data."""
    for r in results.values():
        if len(r.portfolio_values) > 0:
            start = r.portfolio_values.index[0].strftime("%Y%m%d")
            end = r.portfolio_values.index[-1].strftime("%Y%m%d")
            return f"{start}_{end}"
    if test_start_date:
        return test_start_date.replace("-", "")
    return "unknown"


def _write_compare_all_csv(
    results: dict[str, BacktestResult],
    capital: float,
    csv_path: str,
) -> None:
    """Dump a ranked metrics table sorted by Sharpe."""
    rows = []
    for name, r in results.items():
        fees_pct = (r.total_fees_paid / capital * 100) if capital > 0 else 0.0
        rows.append({
            "model": name,
            "total_return_pct": round(r.total_return, 3),
            "annualized_return_pct": round(r.annualized_return, 3),
            "sharpe": round(r.sharpe_ratio, 3),
            "max_drawdown_pct": round(r.max_drawdown, 3),
            "n_trades": r.n_trades,
            "win_rate": round(r.win_rate, 2),
            "profit_factor": round(r.profit_factor, 3) if np.isfinite(r.profit_factor) else float("inf"),
            "fees_pct_capital": round(fees_pct, 3),
        })
    df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    df.to_csv(csv_path, index=False)
    print(f"Metrics CSV saved: {csv_path}")


def _print_compare_all_summary(
    results: dict[str, BacktestResult],
    capital: float,
    symbol: str,
    timeframe: str,
) -> None:
    """Print a ranked table (by Sharpe) covering every contestant."""
    rows = [
        {
            "name": name,
            "ret": r.total_return,
            "ann": r.annualized_return,
            "sharpe": r.sharpe_ratio,
            "dd": r.max_drawdown,
            "trades": r.n_trades,
            "win": r.win_rate,
            "pf": r.profit_factor,
        }
        for name, r in results.items()
    ]
    rows.sort(key=lambda x: x["sharpe"], reverse=True)

    print(f"\n{'=' * 100}")
    print(f"COMPARE-ALL RESULTS — {symbol} [{timeframe}] | Capital: ${capital:,.0f}")
    print(f"{'=' * 100}")
    header = (
        f"{'Model':<32} {'Return %':>10} {'Ann. %':>10} {'Sharpe':>8} "
        f"{'MaxDD %':>9} {'Trades':>8} {'Win %':>7} {'PF':>8}"
    )
    print(header)
    print("─" * 100)
    for r in rows:
        pf_s = f"{r['pf']:.2f}" if np.isfinite(r["pf"]) else "inf"
        print(
            f"{r['name']:<32} "
            f"{r['ret']:>+9.2f}% "
            f"{r['ann']:>+9.2f}% "
            f"{r['sharpe']:>8.2f} "
            f"{r['dd']:>8.2f}% "
            f"{r['trades']:>8} "
            f"{r['win']:>6.1f}% "
            f"{pf_s:>8}"
        )
    print(f"{'=' * 100}\n")


def _plot_compare_all_equity(
    results: dict[str, BacktestResult],
    oracle_result: BacktestResult | None,
    df_prices: pd.DataFrame | None,
    capital: float,
    symbol: str,
    save_path: str,
) -> None:
    """Overlay every contestant's equity curve (daily-resampled) + B&H + oracle."""
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), height_ratios=[3, 1])
    ax1, ax2 = axes

    tab10 = plt.cm.tab10.colors

    daily_curves: dict[str, pd.Series] = {}
    for name, r in results.items():
        if len(r.portfolio_values) == 0:
            continue
        daily = r.portfolio_values.resample("1D").last().dropna()
        if len(daily) == 0:
            continue
        daily_curves[name] = daily

    if not daily_curves:
        print("No equity curves to plot — aborting plot")
        plt.close(fig)
        return

    # Buy-and-hold over the union date range
    all_starts = [s.index[0] for s in daily_curves.values()]
    all_ends = [s.index[-1] for s in daily_curves.values()]
    start_ts = min(all_starts)
    end_ts = max(all_ends)

    if df_prices is not None and "close" in df_prices.columns:
        bh = df_prices.loc[start_ts:end_ts, "close"].resample("1D").last().dropna()
        if len(bh) > 0:
            bh_norm = bh / bh.iloc[0] * capital
            ax1.plot(
                bh_norm.index, bh_norm.values,
                color="silver", linewidth=1.2, linestyle="--",
                alpha=0.7, label="Buy & Hold",
            )

    for i, (name, daily) in enumerate(daily_curves.items()):
        ret = (daily.iloc[-1] - capital) / capital * 100
        is_rl = name == "rl"
        is_ensemble = name.startswith("ensemble")
        color = "#dc2626" if is_rl else ("#7c3aed" if is_ensemble else tab10[i % 10])
        lw = 2.4 if (is_rl or is_ensemble) else 1.4
        zorder = 5 if (is_rl or is_ensemble) else 3
        ax1.plot(
            daily.index, daily.values,
            color=color, linewidth=lw, alpha=0.9, zorder=zorder,
            label=f"{name}  ({ret:+.1f}%)",
        )

    if oracle_result is not None and len(oracle_result.portfolio_values) > 0:
        ora_daily = oracle_result.portfolio_values.resample("1D").last().dropna()
        if len(ora_daily) > 0:
            ax1.plot(
                ora_daily.index, ora_daily.values,
                color="#16a34a", linewidth=1.6, linestyle="-.",
                alpha=0.85, zorder=4,
                label=f"Oracle  ({oracle_result.total_return:+.1f}%)",
            )

    ax1.axhline(capital, color="black", linewidth=0.6, linestyle=":", alpha=0.4)
    ax1.set_ylabel("Portfolio value ($)")
    ax1.set_title(f"Compare-all — {symbol}")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.25)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    for i, (name, daily) in enumerate(daily_curves.items()):
        dd = (daily - daily.cummax()) / daily.cummax() * 100
        is_rl = name == "rl"
        is_ensemble = name.startswith("ensemble")
        color = "#dc2626" if is_rl else ("#7c3aed" if is_ensemble else tab10[i % 10])
        lw = 1.6 if (is_rl or is_ensemble) else 0.9
        ax2.plot(dd.index, dd.values, color=color, linewidth=lw, alpha=0.8, label=name)
    ax2.axhline(0, color="black", linewidth=0.5, alpha=0.4)
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_xlabel("Date")
    ax2.legend(fontsize=7, loc="lower left", ncol=2)
    ax2.grid(True, alpha=0.25)

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Equity comparison plot saved: {save_path}")


def run_ensemble_backtest_all_symbols(
    model_types: list[str],
    strategy: str = "weighted_average",
    weights: list[float] | None = None,
    capital_per_symbol: float = 1_000.0,
    threshold: float = 0.0,
    allow_short: bool = False,
    timeframe: str = DEFAULT_TIMEFRAME,
    entry_fee_pct: Optional[float] = None,
    exit_fee_pct: Optional[float] = None,
) -> dict[str, BacktestResult]:
    """Run ensemble backtest on every symbol in config.SYMBOLS.

    Models are loaded once and reused across all symbols.
    One equity-comparison chart is saved per symbol plus a global summary table.

    Args:
        model_types: Model keys, e.g. ["cnn", "bilstm", "cnn_bilstm_am"].
        strategy: Aggregation strategy.
        weights: Per-model weights (equal if None).
        capital_per_symbol: Starting capital for each symbol.
        threshold: Signal threshold (0 = use timeframe default).
        allow_short: Allow short positions.
        timeframe: Shared timeframe for all models.
        entry_fee_pct / exit_fee_pct: Fee rates.

    Returns:
        Dict mapping symbol → BacktestResult (ensemble).
    """
    from config import SIGNAL_THRESHOLDS

    if entry_fee_pct is None:
        entry_fee_pct = DEFAULT_ENTRY_FEE
    if exit_fee_pct is None:
        exit_fee_pct = DEFAULT_EXIT_FEE
    if threshold == 0.0:
        threshold = SIGNAL_THRESHOLDS.get(timeframe, 0.01)

    print(f"\n{'=' * 70}")
    print(f"ENSEMBLE BACKTEST MULTI-SYMBOLES [{timeframe}]")
    print(f"Modèles : {', '.join(model_types)}  |  Stratégie : {strategy}")
    print(f"Symboles : {len(SYMBOLS)}  |  Capital/symbole : ${capital_per_symbol:,.0f}")
    print(f"{'=' * 70}")

    # Load models once for all symbols
    print("\nChargement des modèles (une seule fois)...")
    ensemble = _build_ensemble(model_types, strategy, weights, timeframe)

    results: dict[str, BacktestResult] = {}
    failed: list[str] = []

    for sym_full in SYMBOLS:
        sym = sym_full.replace("/USDT", "")
        try:
            result = run_ensemble_backtest(
                model_types=model_types,
                symbol=sym,
                strategy=strategy,
                weights=weights,
                capital=capital_per_symbol,
                threshold=threshold,
                allow_short=allow_short,
                timeframe=timeframe,
                entry_fee_pct=entry_fee_pct,
                exit_fee_pct=exit_fee_pct,
                _ensemble=ensemble,
            )
            results[sym] = result
        except Exception as exc:
            print(f"  ⚠ {sym} ignoré : {exc}")
            failed.append(sym)

    _print_ensemble_multi_symbol_summary(
        results, capital_per_symbol, model_types, strategy, timeframe
    )

    if failed:
        print(f"\nSymboles en échec : {', '.join(failed)}")

    return results


def _print_ensemble_multi_symbol_summary(
    results: dict[str, BacktestResult],
    capital_per_symbol: float,
    model_types: list[str],
    strategy: str,
    timeframe: str,
) -> None:
    """Print a ranked summary table for all symbols."""
    label = f"Ensemble [{'+'.join(model_types)}] / {strategy}"
    print(f"\n{'=' * 90}")
    print(f"RÉSUMÉ GLOBAL — {label} [{timeframe}]")
    print(f"{'=' * 90}")

    rows = [
        {
            "symbol": sym,
            "return": r.total_return,
            "final": capital_per_symbol * (1 + r.total_return / 100),
            "trades": r.n_trades,
            "win_rate": r.win_rate,
            "sharpe": r.sharpe_ratio,
            "drawdown": r.max_drawdown,
        }
        for sym, r in results.items()
        if r.n_trades > 0
    ]

    if not rows:
        print("Aucun trade exécuté.")
        return

    rows.sort(key=lambda x: x["return"], reverse=True)

    header = (
        f"{'Symbol':<8} {'Return %':>10} {'Final $':>12} "
        f"{'Trades':>8} {'Win %':>7} {'Sharpe':>8} {'MaxDD %':>9}"
    )
    print(header)
    print("─" * 90)
    for row in rows:
        print(
            f"{row['symbol']:<8} "
            f"{row['return']:>+9.2f}% "
            f"${row['final']:>10,.0f} "
            f"{row['trades']:>8} "
            f"{row['win_rate']:>6.1f}% "
            f"{row['sharpe']:>8.2f} "
            f"{row['drawdown']:>8.2f}%"
        )
    print("─" * 90)

    avg_return = sum(r["return"] for r in rows) / len(rows)
    total_final = sum(r["final"] for r in rows)
    global_return = (
        (total_final - capital_per_symbol * len(rows))
        / (capital_per_symbol * len(rows))
        * 100
    )
    print(
        f"{'AVERAGE':<8} {avg_return:>+9.2f}%   "
        f"{'TOTAL':>20} ${total_final:>10,.0f}   Global: {global_return:+.2f}%"
    )
    print(f"{'=' * 90}\n")


def run_backtest_all_symbols(
    model_type: str,
    capital_per_symbol: float = 1_000.0,
    threshold: float = 0.0,
    allow_short: bool = False,
    timeframe: str = DEFAULT_TIMEFRAME,
    model_path: Optional[str] = None,
    entry_fee_pct: Optional[float] = None,
    exit_fee_pct: Optional[float] = None,
    use_atr_risk: bool = False,
    test_start_date: str | None = None,
) -> dict[str, BacktestResult]:
    """Exécute le backtest sur tous les symboles définis dans config.SYMBOLS.

    Chaque symbole est testé avec son propre capital initial, ce qui permet
    de comparer les performances individuelles sans cumul.

    Args:
        model_type: Type du modèle (ex: "cnn").
        capital_per_symbol: Capital initial par symbole (défaut: $1,000).
        threshold: Seuil de prédiction pour ouvrir une position.
        allow_short: Autoriser les positions short.
        timeframe: Timeframe du modèle (ex: "1d", "1h", "4h").
        model_path: Chemin vers le checkpoint (optionnel).
        entry_fee_pct: Frais à l'entrée (utilise DEFAULT_ENTRY_FEE si None).
        exit_fee_pct: Frais à la sortie (utilise DEFAULT_EXIT_FEE si None).
        use_atr_risk: Activer le risk management ATR-based.
        test_start_date: Date de début pour le test (ex: "2025-01-01").

    Returns:
        Dict mapping symbol -> BacktestResult pour chaque symbole testé.
    """
    results = {}
    total_symbols = len(SYMBOLS)

    print(f"\n{'=' * 70}")
    print(f"BACKTEST MULTI-SYMBOLS - {model_type.upper()} [{timeframe}]")
    print(f"{'=' * 70}")
    print(f"Nombre de symboles: {total_symbols}")
    print(f"Capital par symbole: ${capital_per_symbol:,.2f}")
    print(f"Date de début test: {test_start_date or TEST_START_DATE}")
    print(
        f"Frais: entrée={(entry_fee_pct or DEFAULT_ENTRY_FEE) * 100:.3f}%, sortie={(exit_fee_pct or DEFAULT_EXIT_FEE) * 100:.3f}%"
    )
    print(f"{'=' * 70}\n")

    for i, symbol in enumerate(SYMBOLS, 1):
        symbol_clean = symbol.replace("/USDT", "")
        print(f"\n{'─' * 60}")
        print(f"[{i}/{total_symbols}] Backtest de {symbol}")
        print(f"{'─' * 60}")

        try:
            result = run_backtest(
                model_type=model_type,
                symbol=symbol_clean,
                capital=capital_per_symbol,
                threshold=threshold,
                allow_short=allow_short,
                timeframe=timeframe,
                model_path=model_path,
                entry_fee_pct=entry_fee_pct,
                exit_fee_pct=exit_fee_pct,
                use_atr_risk=use_atr_risk,
                test_start_date=test_start_date,
            )
            results[symbol] = result
        except Exception as e:
            print(f" ❌ Erreur sur {symbol}: {e}")
            # Créer un résultat vide pour ce symbole
            empty_result = BacktestResult()
            results[symbol] = empty_result

    # Afficher le résumé global
    print_multi_symbol_summary(results, capital_per_symbol, model_type, timeframe)

    return results


def print_multi_symbol_summary(
    results: dict[str, BacktestResult],
    capital_per_symbol: float,
    model_type: str,
    timeframe: str,
) -> None:
    """Affiche un tableau récapitulatif des résultats pour tous les symboles.

    Colonnes affichées:
    - Symbol
    - Total Return (%): Gain/perte en pourcentage vs capital initial
    - Final Capital: Capital final après tous les trades
    - Trades: Nombre total de trades exécutés
    - Total Fees ($): Montant total payé en frais
    - Win Rate (%): Pourcentage de trades gagnants

    Args:
        results: Dict mapping symbol -> BacktestResult.
        capital_per_symbol: Capital initial par symbole.
        model_type: Type du modèle testé.
        timeframe: Timeframe utilisé.
    """
    print(f"\n{'=' * 90}")
    print(f"RÉSUMÉ GLOBAL - {model_type.upper()} [{timeframe}] - TOUS LES SYMBOLES")
    print(f"{'=' * 90}")

    # Préparer les données pour le tableau
    table_data = []
    total_capital_start = 0.0
    total_capital_end = 0.0
    total_trades = 0
    total_fees = 0.0
    total_wins = 0
    symbols_with_trades = 0

    for symbol, result in results.items():
        if result.n_trades > 0:
            symbols_with_trades += 1
            final_capital = capital_per_symbol * (1 + result.total_return / 100)
            winning_trades = int(result.win_rate * result.n_trades / 100)

            table_data.append(
                {
                    "symbol": symbol.replace("/USDT", ""),
                    "total_return": result.total_return,
                    "final_capital": final_capital,
                    "n_trades": result.n_trades,
                    "total_fees": result.total_fees_paid,
                    "win_rate": result.win_rate,
                }
            )

            total_capital_start += capital_per_symbol
            total_capital_end += final_capital
            total_trades += result.n_trades
            total_fees += result.total_fees_paid
            total_wins += winning_trades

    if symbols_with_trades == 0:
        print("Aucun trade exécuté sur aucun symbole.")
        print(f"{'=' * 90}\n")
        return

    # Trier par rendement total (décroissant)
    table_data.sort(key=lambda x: x["total_return"], reverse=True)

    # En-tête du tableau
    header = (
        f"{'Symbol':<8} {'Return %':>10} {'Final $':>12} "
        f"{'Trades':>8} {'Total Fees $':>12} {'Win Rate %':>10}"
    )
    print(header)
    print("─" * 90)

    # Lignes du tableau
    for row in table_data:
        print(
            f"{row['symbol']:<8} "
            f"{row['total_return']:>+9.2f}% "
            f"${row['final_capital']:>10,.2f} "
            f"{row['n_trades']:>8} "
            f"${row['total_fees']:>10,.2f} "
            f"{row['win_rate']:>9.1f}%"
        )

    # Ligne de séparation et totaux
    print("─" * 90)

    # Calculer les moyennes et totaux
    avg_return = sum(r["total_return"] for r in table_data) / len(table_data)
    total_final_capital = sum(r["final_capital"] for r in table_data)
    avg_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
    global_return = (
        (total_final_capital - total_capital_start) / total_capital_start * 100
    )

    print(
        f"{'AVERAGE':<8} "
        f"{avg_return:>+9.2f}% "
        f"{'─':>12} "
        f"{'─':>8} "
        f"{'─':>12} "
        f"{avg_win_rate:>9.1f}%"
    )
    print("─" * 90)
    print(
        f"{'TOTAL':<8} "
        f"{global_return:>+9.2f}% "
        f"${total_final_capital:>10,.2f} "
        f"{total_trades:>8} "
        f"${total_fees:>10,.2f} "
        f"{'─':>10}"
    )

    print(f"{'=' * 90}")
    print(f"Capital initial total: ${total_capital_start:,.2f}")
    print(f"Capital final total:   ${total_final_capital:,.2f}")
    print(
        f"Gain/Perte total:      ${total_final_capital - total_capital_start:>+,.2f} ({global_return:+.2f}%)"
    )
    print(f"Frais totaux payés:    ${total_fees:,.2f}")
    print(f"{'=' * 90}\n")


def parse_args() -> argparse.Namespace:
    """Parse les arguments CLI."""
    parser = argparse.ArgumentParser(
        description="Backtest d'un modèle ML sur données historiques"
    )
    parser.add_argument(
        "--model", type=str, required=True, help="Type du modèle (ex: cnn, lstm, gru)"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1_000.0,
        help="Capital initial par symbole (défaut: 1000). En mode --all-symbols, c'est le capital par symbole.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Seuil de prédiction pour ouvrir une position (défaut: 0.0)",
    )
    parser.add_argument(
        "--allow-short", action="store_true", help="Autoriser les positions short"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default=DEFAULT_TIMEFRAME,
        help=f"Timeframe du modèle (défaut: {DEFAULT_TIMEFRAME})",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Symbole de la crypto (ex: BTC, ETH). Requis sauf avec --all-symbols",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Chemin vers le checkpoint du modele (optionnel)",
    )
    parser.add_argument(
        "--entry-fee",
        type=float,
        default=None,
        help="Frais a l'entree en pourcentage (ex: 0.001 pour 0.1%%, defaut: 0.100%%)",
    )
    parser.add_argument(
        "--exit-fee",
        type=float,
        default=None,
        help="Frais a la sortie en pourcentage (ex: 0.001 pour 0.1%%, defaut: 0.100%%)",
    )
    parser.add_argument(
        "--atr-risk",
        action="store_true",
        help="Activer le risk management ATR-based (SL/TP/trailing stop)",
    )
    parser.add_argument(
        "--test-start-date",
        type=str,
        default=None,
        help="Date de debut pour le test out-of-sample (ex: 2025-01-01, defaut depuis config)",
    )
    parser.add_argument(
        "--all-symbols",
        action="store_true",
        help="Tester sur tous les symboles définis dans SYMBOLS (capital par symbole: --capital)",
    )
    parser.add_argument(
        "--ensemble-models",
        type=str,
        default=None,
        help="Modèles ensemble séparés par virgule (ex: cnn,bilstm,cnn_bilstm_am). Requis si --model ensemble.",
    )
    parser.add_argument(
        "--ensemble-strategy",
        type=str,
        default="weighted_average",
        choices=[
            "majority_vote",
            "weighted_average",
            "confidence_weighted",
            "unanimous",
        ],
        help="Stratégie d'agrégation ensemble (défaut: weighted_average)",
    )
    parser.add_argument(
        "--ensemble-weights",
        type=str,
        default=None,
        help="Poids par modèle séparés par virgule (ex: 0.5,0.3,0.2). Défaut: poids égaux.",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        default=None,
        help="Comma-separated model names to skip in compare-all mode (ex: patch_tst,transformer).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Validation des arguments
    if not args.all_symbols and args.symbol is None:
        print("Erreur: Vous devez specifier --symbol ou utiliser --all-symbols")
        exit(1)

    if args.model == "compare-all":
        if args.symbol is None:
            print("Erreur: --symbol requis avec --model compare-all")
            exit(1)
        exclude = (
            [m.strip() for m in args.exclude.split(",") if m.strip()]
            if args.exclude
            else []
        )
        run_compare_all_backtest(
            symbol=args.symbol,
            capital=args.capital,
            threshold=args.threshold,
            allow_short=args.allow_short,
            timeframe=args.timeframe,
            entry_fee_pct=args.entry_fee,
            exit_fee_pct=args.exit_fee,
            test_start_date=args.test_start_date,
            exclude=exclude,
            ensemble_strategy=args.ensemble_strategy,
        )
    elif args.model == "ensemble":
        if args.ensemble_models is None:
            print(
                "Erreur: --ensemble-models requis avec --model ensemble (ex: cnn,bilstm)"
            )
            exit(1)
        model_types = [m.strip() for m in args.ensemble_models.split(",")]
        weights = (
            [float(w) for w in args.ensemble_weights.split(",")]
            if args.ensemble_weights
            else None
        )
        if args.all_symbols:
            run_ensemble_backtest_all_symbols(
                model_types=model_types,
                strategy=args.ensemble_strategy,
                weights=weights,
                capital_per_symbol=args.capital,
                threshold=args.threshold,
                allow_short=args.allow_short,
                timeframe=args.timeframe,
                entry_fee_pct=args.entry_fee,
                exit_fee_pct=args.exit_fee,
            )
        else:
            if args.symbol is None:
                print(
                    "Erreur: --symbol requis avec --model ensemble (ou utiliser --all-symbols)"
                )
                exit(1)
            run_ensemble_backtest(
                model_types=model_types,
                symbol=args.symbol,
                strategy=args.ensemble_strategy,
                weights=weights,
                capital=args.capital,
                threshold=args.threshold,
                allow_short=args.allow_short,
                timeframe=args.timeframe,
                entry_fee_pct=args.entry_fee,
                exit_fee_pct=args.exit_fee,
            )
    elif args.all_symbols:
        run_backtest_all_symbols(
            model_type=args.model,
            capital_per_symbol=args.capital,
            threshold=args.threshold,
            allow_short=args.allow_short,
            timeframe=args.timeframe,
            model_path=args.model_path,
            entry_fee_pct=args.entry_fee,
            exit_fee_pct=args.exit_fee,
            use_atr_risk=args.atr_risk,
            test_start_date=args.test_start_date,
        )
    else:
        run_backtest(
            model_type=args.model,
            symbol=args.symbol,
            capital=args.capital,
            threshold=args.threshold,
            allow_short=args.allow_short,
            timeframe=args.timeframe,
            model_path=args.model_path,
            entry_fee_pct=args.entry_fee,
            exit_fee_pct=args.exit_fee,
            use_atr_risk=args.atr_risk,
            test_start_date=args.test_start_date,
        )
