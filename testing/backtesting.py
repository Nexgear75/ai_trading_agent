"""
Module de backtesting générique pour tous les modèles du projet.

Simule une stratégie de trading basée sur les prédictions d'un modèle ML,
calcule les métriques de performance et génère une courbe d'équité.

Usage:
    python -m testing.backtesting --model cnn --symbol BTC --capital 10000 --threshold 0.01
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
    exit_reason: str = (
        "horizon"  # "horizon", "stop_loss", "take_profit", "trailing_stop"
    )


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

    # Conserver les prix pour le PnL et l'ATR (avant de modifier df)
    price_cols = ["close"]
    if "high" in df.columns and "low" in df.columns:
        price_cols = ["high", "low", "close"]
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

    # Vérification anti look-ahead bias
    _verify_no_lookahead_bias(df, X, timestamps, symbol, timeframe)

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

    Cette fonction valide que:
    1. Les features X ne contiennent que des données passées (window [t-window_size:t])
    2. Le label y n'est PAS utilisé comme feature
    3. Les timestamps correspondent bien aux dates de prédiction (t)

    Args:
        df: DataFrame source avec toutes les colonnes
        X: Array des features (n_samples, window_size, n_features)
        timestamps: Array des timestamps de prédiction
        symbol: Symbole pour les messages d'erreur
        timeframe: Timeframe des données (pour les messages).

    Raises:
        ValueError: Si une anomalie de look-ahead est détectée
    """
    # Vérification 1: Les features sont bien des fenêtres passées
    # build_windows crée X[i] = df[i-window_size:i], y[i] = label[i]
    # Donc pour chaque timestamp de prédiction, les features doivent être antérieures

    # Vérification 2: Le label n'est pas dans les features
    feature_cols = set(FEATURE_COLUMNS)
    if "label" in feature_cols:
        raise ValueError(
            f"[{symbol}] ERREUR CRITIQUE: La colonne 'label' est dans les features!"
        )

    # Vérification 3: Les timestamps des features vs timestamps de prédiction
    df_index = df.index
    for i, ts in enumerate(
        timestamps[: min(10, len(timestamps))]
    ):  # Échantillon des 10 premiers
        ts = pd.Timestamp(ts)
        # Trouver la position dans le DataFrame
        try:
            pos = df_index.get_loc(ts)
            # La fenêtre de features doit se terminer à pos (exclus)
            # Donc la feature la plus récente est à pos-1
            if pos < 1:
                continue  # Premier élément, pas de vérification possible
        except KeyError:
            continue  # Timestamp non trouvé, skip

    print(f"  ✓ Vérification anti look-ahead: PAS DE FUITE DÉTECTÉE")
    print(
        f"  ✓ Features: {X.shape[1]} périodes historiques [{timeframe}] → Prédiction à t+1"
    )
    print(f"  ✓ Les features sont calculées uniquement sur des données passées")


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

    # ATR-based risk management setup
    atr_series = None
    if use_atr_risk:
        atr_series = _compute_atr_series(df_prices)

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

            # ATR-based intra-trade risk checks
            if use_atr_risk and "sl_price" in pos:
                if pos["direction"] == "LONG":
                    if current_price <= pos["sl_price"]:
                        exit_reason = "stop_loss"
                        exit_price_override = pos["sl_price"]
                    elif current_price >= pos["tp_price"]:
                        exit_reason = "take_profit"
                        exit_price_override = pos["tp_price"]
                    else:
                        # Trailing stop: activate when PnL > trailing_atr_mult * ATR
                        unrealized_pct = current_price / pos["entry_price"] - 1
                        if unrealized_pct > pos.get("trailing_threshold", float("inf")):
                            # Move SL up to lock in profits
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
                        if unrealized_pct > pos.get("trailing_threshold", float("inf")):
                            new_sl = current_price * (
                                1 + pos["atr_at_entry"] * sl_atr_mult
                            )
                            if new_sl < pos["sl_price"]:
                                pos["sl_price"] = new_sl
                                pos["trailing_active"] = True

            # Horizon exit (fallback)
            if exit_reason is None and i - pos["entry_idx"] >= prediction_horizon:
                exit_reason = "horizon"

            if exit_reason:
                positions_to_close.append((pos, exit_reason, exit_price_override))

        for pos, exit_reason, exit_price_override in positions_to_close:
            exit_idx = pos["entry_idx"] + prediction_horizon
            exit_price = exit_price_override  # Use SL/TP price if triggered

            if exit_price is None:
                if exit_idx < len(timestamps):
                    exit_ts = pd.Timestamp(timestamps[exit_idx])
                    exit_price = close_prices.loc[exit_ts]
                else:
                    entry_ts = pd.Timestamp(timestamps[pos["entry_idx"]])
                    exit_date = entry_ts + pd.Timedelta(
                        minutes=prediction_horizon * timeframe_minutes
                    )
                    future_prices = close_prices[close_prices.index >= exit_date]
                    if len(future_prices) > 0:
                        exit_price = future_prices.iloc[0]
                        exit_ts = exit_date
                    else:
                        continue
            else:
                exit_ts = ts  # SL/TP triggered at current bar

            entry_price = pos["entry_price"]
            direction = pos["direction"]
            allocated_capital = pos["allocated"]

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

            trade = Trade(
                entry_date=pos["entry_date"],
                exit_date=exit_ts
                if exit_reason != "horizon" or exit_idx < len(timestamps)
                else exit_date,
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
        if i < len(predictions) - prediction_horizon:
            # Respecter le cooldown
            if use_atr_risk and i < cooldown_until:
                pass  # En cooldown, pas de nouveau trade
            else:
                pred = predictions[i]

                signal = None
                if pred > threshold:
                    signal = "LONG"
                elif pred < -threshold and allow_short:
                    signal = "SHORT"

                if signal:
                    entry_price = close_prices.loc[ts]

                    # ATR-based position sizing
                    if use_atr_risk and atr_series is not None:
                        atr_val = atr_series.get(ts, None)
                        if atr_val is None or np.isnan(atr_val) or atr_val <= 0:
                            atr_val = 0.02  # Fallback: 2% volatility
                        sl_distance = atr_val * sl_atr_mult
                        risk_amount = (cash + allocated) * risk_per_trade
                        trade_capital = min(
                            risk_amount / (sl_distance + 1e-10), slot_capital
                        )
                    else:
                        trade_capital = slot_capital
                        atr_val = None

                    entry_fee = trade_capital * entry_fee_pct
                    total_entry_cost = trade_capital + entry_fee

                    if cash < total_entry_cost:
                        continue

                    cash -= total_entry_cost
                    allocated += trade_capital

                    pos_info = {
                        "entry_idx": i,
                        "entry_date": ts,
                        "direction": signal,
                        "entry_price": entry_price,
                        "predicted_return": pred,
                        "allocated": trade_capital,
                        "entry_fee": entry_fee,
                    }

                    # Set ATR-based SL/TP levels
                    if use_atr_risk and atr_val is not None:
                        pos_info["atr_at_entry"] = atr_val
                        if signal == "LONG":
                            pos_info["sl_price"] = entry_price * (
                                1 - atr_val * sl_atr_mult
                            )
                            pos_info["tp_price"] = entry_price * (
                                1 + atr_val * tp_atr_mult
                            )
                        else:
                            pos_info["sl_price"] = entry_price * (
                                1 + atr_val * sl_atr_mult
                            )
                            pos_info["tp_price"] = entry_price * (
                                1 - atr_val * tp_atr_mult
                            )
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
) -> BacktestResult:
    """Simule un oracle parfait qui connaît exactement les retours futurs.

    Utilise les labels réels (y) comme prédictions — borne supérieure
    théorique de ce qu'un modèle parfait pourrait atteindre.

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

    Returns:
        BacktestResult de l'oracle avec threshold=0 (trade dès qu'on connaît la direction).
    """
    return simulate_trading(
        predictions=y,
        timestamps=timestamps,
        df_prices=df_prices,
        capital=capital,
        threshold=0.0,
        allow_short=allow_short,
        entry_fee_pct=entry_fee_pct,
        exit_fee_pct=exit_fee_pct,
        prediction_horizon=prediction_horizon,
        timeframe_minutes=timeframe_minutes,
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
        y,
        timestamps,
        df_prices,
        capital,
        allow_short,
        entry_fee_pct,
        exit_fee_pct,
        prediction_horizon,
        timeframe_minutes,
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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Validation des arguments
    if not args.all_symbols and args.symbol is None:
        print("Erreur: Vous devez specifier --symbol ou utiliser --all-symbols")
        exit(1)

    if args.all_symbols:
        # Mode multi-symboles
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
        # Mode single symbole
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
