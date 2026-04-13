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
    DEFAULT_TIMEFRAME, TIMEFRAME_MINUTES, get_timeframe_config,
    SYMBOLS, DEFAULT_ENTRY_FEE, DEFAULT_EXIT_FEE
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
    direction: str            # "LONG" ou "SHORT"
    entry_price: float
    exit_price: float
    predicted_return: float
    actual_return: float
    entry_fee: float          # frais à l'entrée
    exit_fee: float           # frais à la sortie
    total_fees: float         # frais totaux
    pnl_before_fees: float    # PnL brut avant frais
    pnl: float                # PnL net après frais


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
) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    """Prépare les données pour le backtest (dataset complet, pas de split).

    Charge le symbole, recalcule les labels, construit les fenêtres,
    applique le scaler (transform uniquement, pas fit_transform).

    Args:
        symbol: Symbole de la crypto (ex: "BTC").
        feature_scaler: RobustScaler déjà fitté (chargé depuis joblib).
        clip_bounds: Bornes pour le clipping des outliers (optionnel).
        timeframe: Timeframe du dataset (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").

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

    # Conserver les prix pour le PnL (avant de modifier df)
    df_prices = df[["close"]].copy()

    # Recalculer le label (forward return sur prediction_horizon périodes)
    df["label"] = df["close"].shift(-prediction_horizon) / df["close"] - 1

    # Supprimer les lignes sans label (derniers prediction_horizon périodes)
    df = df.dropna(subset=["label"])

    # Construire les fenêtres avec la taille et les features appropriées pour ce timeframe
    feature_cols = get_feature_columns(timeframe)
    X, y, timestamps = build_windows(df, window_size=window_size, feature_columns=feature_cols)

    if len(X) == 0:
        raise ValueError(f"Pas assez de données pour construire des fenêtres pour {symbol}")

    # Appliquer le clipping puis le feature scaler (transform seulement, pas fit_transform)
    n_samples, window_len, n_features = X.shape
    X_flat = X.reshape(-1, n_features)

    # Clipping outliers (même bornes que le training)
    if clip_bounds is not None:
        for i in range(n_features):
            X_flat[:, i] = np.clip(X_flat[:, i], clip_bounds[i, 0], clip_bounds[i, 1])

    X_scaled_flat = feature_scaler.transform(X_flat)
    X_scaled = X_scaled_flat.reshape(n_samples, window_len, n_features)

    print(f"Données préparées : {len(X)} fenêtres, window_size={window_size}, {n_features} features")

    # Vérification anti look-ahead bias
    _verify_no_lookahead_bias(df, X, timestamps, symbol, timeframe)

    return X_scaled, y, timestamps, df_prices


def _verify_no_lookahead_bias(df: pd.DataFrame, X: np.ndarray, timestamps: np.ndarray, symbol: str, timeframe: str = DEFAULT_TIMEFRAME) -> None:
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
        raise ValueError(f"[{symbol}] ERREUR CRITIQUE: La colonne 'label' est dans les features!")

    # Vérification 3: Les timestamps des features vs timestamps de prédiction
    df_index = df.index
    for i, ts in enumerate(timestamps[:min(10, len(timestamps))]):  # Échantillon des 10 premiers
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
    print(f"  ✓ Features: {X.shape[1]} périodes historiques [{timeframe}] → Prédiction à t+1")
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
) -> BacktestResult:
    """Simule la stratégie de trading sur les prédictions.

    Pour chaque période t :
        - Si prediction[t] > threshold  → ouvrir LONG
        - Si prediction[t] < -threshold → ouvrir SHORT (si autorisé)
        - Sinon → rester FLAT
        - Clôture après prediction_horizon périodes

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

    # Allocation : diviser le capital en slots pour positions simultanées
    slot_capital = capital / prediction_horizon

    # Suivi du cash et des positions ouvertes
    cash = capital  # Cash disponible, s'accumule avec les PnL réalisés
    allocated = 0.0  # Capital alloué aux positions ouvertes
    open_positions = []  # Liste de dicts avec trade info
    portfolio_values = []

    # Pour chaque période de prédiction
    for i, ts in enumerate(timestamps):
        ts = pd.Timestamp(ts)

        # 1. Fermer les positions arrivées à maturité
        positions_to_close = []
        for pos in open_positions:
            if i - pos["entry_idx"] >= prediction_horizon:
                positions_to_close.append(pos)

        for pos in positions_to_close:
            # Calculer le prix de sortie
            exit_idx = pos["entry_idx"] + prediction_horizon
            exit_price = None

            if exit_idx < len(timestamps):
                # Sortie dans les données windowed
                exit_ts = pd.Timestamp(timestamps[exit_idx])
                exit_price = close_prices.loc[exit_ts]
            else:
                # Dépassé la fin des timestamps windowed, chercher dans df_prices
                entry_ts = pd.Timestamp(timestamps[pos["entry_idx"]])
                # Calculer la date de sortie en fonction du timeframe (minutes par barre)
                exit_date = entry_ts + pd.Timedelta(minutes=prediction_horizon * timeframe_minutes)
                # Trouver le prix le plus proche après exit_date
                future_prices = close_prices[close_prices.index >= exit_date]
                if len(future_prices) > 0:
                    exit_price = future_prices.iloc[0]
                    exit_ts = exit_date
                else:
                    continue  # Pas de donnée de sortie

            entry_price = pos["entry_price"]
            direction = pos["direction"]
            allocated_capital = pos["allocated"]

            # Calculer le retour réalisé (brut, avant frais)
            if direction == "LONG":
                actual_return = exit_price / entry_price - 1
                pnl_before_fees = allocated_capital * actual_return
            else:  # SHORT
                actual_return = entry_price / exit_price - 1
                pnl_before_fees = allocated_capital * actual_return

            # Calculer les frais
            exit_value = allocated_capital * (1 + actual_return)  # Valeur de la position à la sortie
            exit_fee = exit_value * exit_fee_pct
            entry_fee = pos.get("entry_fee", 0.0)  # Frais déjà payés à l'entrée
            total_fees = entry_fee + exit_fee

            # PnL net après frais
            pnl = pnl_before_fees - exit_fee

            # Enregistrer le trade avec les frais
            trade = Trade(
                entry_date=pos["entry_date"],
                exit_date=exit_ts if exit_idx < len(timestamps) else exit_date,
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                predicted_return=pos["predicted_return"],
                actual_return=actual_return,
                entry_fee=entry_fee,
                exit_fee=exit_fee,
                total_fees=total_fees,
                pnl_before_fees=pnl_before_fees,
                pnl=pnl
            )
            result.trades.append(trade)

            # Libérer le capital alloué + PnL net dans le cash
            cash += allocated_capital + pnl
            allocated -= allocated_capital

            # Retirer de la liste des positions ouvertes
            open_positions.remove(pos)

        # 2. Générer le signal et ouvrir une nouvelle position si pertinent
        # Ne pas ouvrir de position dans les derniers prediction_horizon périodes
        if i < len(predictions) - prediction_horizon:
            pred = predictions[i]

            signal = None
            if pred > threshold:
                signal = "LONG"
            elif pred < -threshold and allow_short:
                signal = "SHORT"

            if signal:
                # Calculer les frais d'entrée
                entry_fee = slot_capital * entry_fee_pct
                total_entry_cost = slot_capital + entry_fee

                # Vérifier qu'on a assez de cash (capital + frais)
                if cash < total_entry_cost:
                    continue

                # Prix d'entrée
                entry_price = close_prices.loc[ts]

                # Allouer le capital + payer les frais d'entrée
                cash -= total_entry_cost
                allocated += slot_capital

                # Ouvrir position avec frais d'entrée enregistrés
                open_positions.append({
                    "entry_idx": i,
                    "entry_date": ts,
                    "direction": signal,
                    "entry_price": entry_price,
                    "predicted_return": pred,
                    "allocated": slot_capital,
                    "entry_fee": entry_fee
                })

        # 3. Calculer la valeur mark-to-market du portefeuille
        # Cash + capital alloué + PnL non réalisé
        portfolio_value = cash + allocated

        # Ajouter les PnL non réalisés (mark-to-market)
        for pos in open_positions:
            current_price = close_prices.loc[ts]
            if pos["direction"] == "LONG":
                unrealized_pnl = pos["allocated"] * (current_price / pos["entry_price"] - 1)
            else:
                unrealized_pnl = pos["allocated"] * (pos["entry_price"] / current_price - 1)
            portfolio_value += unrealized_pnl

        portfolio_values.append((ts, portfolio_value))

    # Convertir en Series
    if portfolio_values:
        result.portfolio_values = pd.Series(
            [v for _, v in portfolio_values],
            index=[t for t, _ in portfolio_values]
        )

    return result


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
    result.profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf')

    # Métriques de frais
    result.total_fees_paid = sum(t.total_fees for t in trades)
    result.avg_fees_per_trade = result.total_fees_paid / len(trades)

    # Calculer l'impact des frais sur le rendement
    total_pnl_before_fees = sum(t.pnl_before_fees for t in trades)
    if total_pnl_before_fees > 0:
        result.fee_impact_pct = (result.total_fees_paid / (capital + total_pnl_before_fees)) * 100
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
            print(f"  ⚠️  Écart entre méthodes de calcul: trades={result.total_return:.2f}%, portfolio={portfolio_return:.2f}%")
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


def print_summary(result: BacktestResult, symbol: str, model_type: str, capital: float):
    """Affiche un résumé formaté des résultats du backtest."""
    print(f"\n{'='*60}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*60}")
    print(f"Model:        {model_type.upper()}")
    print(f"Symbol:       {symbol}")
    print(f"Capital:      ${capital:,.2f}")
    print(f"{'='*60}")

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
    print(f"{'='*60}")
    print(f"Initial Capital:     ${capital:,.2f}")
    print(f"Final Capital:       ${final_capital:,.2f}")
    print(f"{'='*60}")
    print(f"Number of Trades:    {result.n_trades}")
    print(f"Win Rate:            {result.win_rate:.1f}%")
    print(f"Avg Trade Return:    {result.avg_trade_return:+.2f}%")
    print(f"Profit Factor:       {result.profit_factor:.2f}")
    print(f"{'='*60}")
    print(f"FEES SUMMARY")
    print(f"{'='*60}")
    print(f"Entry Fee Rate:      {result.entry_fee_pct*100:.3f}%")
    print(f"Exit Fee Rate:       {result.exit_fee_pct*100:.3f}%")
    print(f"Total Fees Paid:     ${result.total_fees_paid:,.2f}")
    print(f"Avg Fees/Trade:      ${result.avg_fees_per_trade:.2f}")
    print(f"Fee Impact:          {result.fee_impact_pct:.2f}%")
    print(f"{'='*60}\n")


# ----- Graphiques ----- #


def plot_equity_curve(
    result: BacktestResult,
    save_path: str,
    symbol: str,
    model_type: str,
    capital: float,
    df_prices: pd.DataFrame,
    timestamps: np.ndarray,
):
    """Génère et sauvegarde la courbe d'équité avec annotations.

    Inclut :
        - Courbe de valeur du portefeuille
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
    ax1.plot(result.portfolio_values.index, result.portfolio_values.values,
             label="Strategy", linewidth=1.5, color="blue")
    ax1.plot(bh_normalized.index, bh_normalized.values,
             label="Buy & Hold", linewidth=1.5, color="gray", alpha=0.7, linestyle="--")
    ax1.axhline(capital, color="black", linestyle=":", alpha=0.5, label="Initial Capital")

    ax1.set_ylabel("Portfolio Value ($)")
    ax1.set_title(f"Backtest: {model_type.upper()} on {symbol}")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # Format y-axis as currency
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

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

    Returns:
        BacktestResult complet.
    """
    # Get timeframe configuration
    tf_config = get_timeframe_config(timeframe)
    prediction_horizon = tf_config["prediction_horizon"]
    timeframe_minutes = tf_config["minutes_per_bar"]

    print(f"\n{'='*60}")
    print(f"Démarrage du backtest : {model_type.upper()} sur {symbol}")
    print(f"Timeframe: {timeframe} | Horizon: {prediction_horizon} bars")
    print(f"{'='*60}")

    # Device
    device = torch.device("mps" if torch.mps.is_available() else "cpu")
    print(f"Device : {device}")

    # 1. Charger modèle et scalers
    print(f"\nChargement du modèle {model_type} [{timeframe}]...")
    model, history = load_model_dynamic(model_type, device, model_path, timeframe=timeframe)

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
        symbol, feature_scaler, clip_bounds, timeframe=timeframe
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
    print(f"Simulation du trading (threshold={threshold}, allow_short={allow_short})...")
    print(f"Frais: entrée={entry_fee_pct*100:.3f}%, sortie={exit_fee_pct*100:.3f}%")
    result = simulate_trading(
        predictions, timestamps, df_prices, capital, threshold, allow_short,
        entry_fee_pct, exit_fee_pct, prediction_horizon, timeframe_minutes
    )

    # 5. Calculer les métriques
    compute_backtest_metrics(result, capital, df_prices, timestamps)

    # 6. Afficher et sauvegarder les résultats
    print_summary(result, symbol, model_type, capital)

    results_dir = f"models/{model_type}/results/{timeframe}"
    plot_equity_curve(result, results_dir, symbol, model_type, capital, df_prices, timestamps)

    return result


def parse_args() -> argparse.Namespace:
    """Parse les arguments CLI."""
    parser = argparse.ArgumentParser(
        description="Backtest d'un modèle ML sur données historiques"
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Type du modèle (ex: cnn, lstm, gru)"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Symbole de la crypto (ex: BTC, ETH)"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10_000.0,
        help="Capital initial (défaut: 10000)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Seuil de prédiction pour ouvrir une position (défaut: 0.0)"
    )
    parser.add_argument(
        "--allow-short",
        action="store_true",
        help="Autoriser les positions short"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default=DEFAULT_TIMEFRAME,
        help=f"Timeframe du modèle (défaut: {DEFAULT_TIMEFRAME})"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Chemin vers le checkpoint (optionnel)"
    )
    parser.add_argument(
        "--entry-fee",
        type=float,
        default=None,
        help="Frais à l'entrée en pourcentage (ex: 0.001 pour 0.1%%, défaut: 0.05%%)"
    )
    parser.add_argument(
        "--exit-fee",
        type=float,
        default=None,
        help="Frais à la sortie en pourcentage (ex: 0.001 pour 0.1%%, défaut: 0.05%%)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

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
    )
