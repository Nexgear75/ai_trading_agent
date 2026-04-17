"""
Module de testing en temps réel avec données Binance live.

Simule une stratégie de trading sur des données temps réel,
avec gestion des positions, stop-loss et take-profit basés sur RRR.

Usage:
    # Mode temps réel (live)
    python -m testing.realtime_testing --symbol BTC/USDT --model cnn --capital 10000
    python -m testing.realtime_testing --config testing/config.json

    # Mode backtest (simulation sur historique)
    python -m testing.realtime_testing --backtest --symbol BTC --model cnn
    python -m testing.realtime_testing --backtest --start-date 2024-01-01 --end-date 2024-12-31 --speed 0.1
"""

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import ccxt
import joblib
import numpy as np
import pandas as pd
import torch
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

console = Console()


from config import (
    DEFAULT_TIMEFRAME,
    get_timeframe_config,
    DEFAULT_ENTRY_FEE,
    DEFAULT_EXIT_FEE,
    DEFAULT_SLIPPAGE_PCT,
    WINDOW_SIZE,
    PREDICTION_HORIZON,
    TIMEFRAME_MINUTES,
    SIGNAL_THRESHOLDS,
    RISK_PCTS,
)
from data.features.pipeline import build_features, FEATURE_COLUMNS, get_feature_columns
from testing.backtesting import load_model_dynamic, load_scalers
from utils.dataset_loader import load_symbol


# Fréquence de vérification SL/TP en mode live (secondes).
# Indépendante du timeframe : on surveille les prix toutes les 5 min.
SLTP_POLL_SECONDS = 300

# Nombre d'erreurs API consécutives avant arrêt gracieux.
MAX_CONSECUTIVE_ERRORS = 5


# ----- Dataclasses ----- #


@dataclass
class RealtimePosition:
    """Représente une position ouverte en temps réel."""

    entry_date: datetime
    direction: str  # "LONG" ou "SHORT"
    entry_price: float
    predicted_return: float
    stop_loss: float
    take_profit: float
    allocated_capital: float
    entry_fee: float
    position_id: int = 0


@dataclass
class RealtimeTrade:
    """Représente un trade clôturé."""

    entry_date: datetime
    exit_date: datetime
    direction: str
    entry_price: float
    exit_price: float
    exit_reason: str  # "TP", "SL", "EXPIRATION"
    predicted_return: float
    actual_return: float
    pnl: float
    total_fees: float


@dataclass
class RealtimeState:
    """État courant du système de trading."""

    capital: float
    allocated: float = 0.0
    open_positions: list[RealtimePosition] = field(default_factory=list)
    closed_trades: list[RealtimeTrade] = field(default_factory=list)
    position_counter: int = 0


# ----- Configuration ----- #


def load_config(config_path: str) -> dict:
    """Charge la configuration depuis un fichier JSON."""
    defaults = {
        "symbol": "BTC/USDT",
        "model_type": "cnn",
        "timeframe": DEFAULT_TIMEFRAME,
        "capital": 1000.0,
        "threshold": None,  # None = auto (SIGNAL_THRESHOLDS[timeframe])
        "allow_short": False,
        "rrr": 2.0,
        "risk_pct": None,  # None = auto (RISK_PCTS[timeframe])
        "check_interval_hours": None,  # None = auto (1 barre = minutes_per_bar/60 h)
        "entry_fee_pct": DEFAULT_ENTRY_FEE,
        "exit_fee_pct": DEFAULT_EXIT_FEE,
        "slippage_pct": DEFAULT_SLIPPAGE_PCT,
        "log_level": "INFO",
        # Risk management
        "sizing_mode": "fixed",  # "fixed", "periodic", "dynamic"
        "max_position_pct": 0.25,  # Max 25% du portefeuille par position
        "max_position_size": None,  # Max absolu en $ (None = pas de limite)
        "rebalance_interval": 50,  # Rebalance tous les N trades (mode periodic)
        "max_drawdown_pct": 0.20,  # Circuit breaker à 20% de drawdown
        "cooldown_bars": 3,  # Min 3 barres entre deux ouvertures
        "max_trades_per_day": 4,  # Max 4 trades par jour
        "max_expiration_rate": 0.50,  # Warning si >50% d'expirations
    }

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
            defaults.update(config)

    return defaults


# ----- Fetching données temps réel ----- #


def fetch_latest_ohlcv(
    symbol: str, limit: int = 100, exchange=None, timeframe: str = DEFAULT_TIMEFRAME
) -> pd.DataFrame:
    """
    Récupère les dernières bougies OHLCV depuis Binance.

    Args:
        symbol: Paire de trading (ex: "BTC/USDT")
        limit: Nombre de bougies à récupérer
        exchange: Instance ccxt (si None, crée une nouvelle)

    Returns:
        DataFrame avec colonnes OHLCV indexé par timestamp
    """
    if exchange is None:
        exchange = ccxt.binance()

    max_retries = 5
    for attempt in range(max_retries):
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(
                    f"Impossible de récupérer les données après {max_retries} tentatives: {e}"
                )
            wait_time = 2**attempt  # Exponential backoff
            console.print(
                f"  [yellow]RETRY[/] Erreur API, nouvelle tentative dans {wait_time}s..."
            )
            time.sleep(wait_time)

    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    return df


def fetch_initial_history(
    symbol: str,
    min_bars: int = WINDOW_SIZE + 50,
    exchange=None,
    timeframe: str = DEFAULT_TIMEFRAME,
) -> pd.DataFrame:
    """
    Récupère l'historique initial nécessaire pour calculer les features.

    Args:
        symbol: Paire de trading
        min_bars: Nombre minimum de barres (bougies) d'historique
        exchange: Instance ccxt (si None, crée une nouvelle)
        timeframe: Timeframe des bougies (ex: "1d", "1h")

    Returns:
        DataFrame OHLCV avec suffisamment d'historique
    """
    console.print(
        f"[bold]INIT[/] Récupération de l'historique {symbol} ({min_bars} bougies [{timeframe}] minimum)..."
    )
    df = fetch_latest_ohlcv(
        symbol, limit=min_bars, exchange=exchange, timeframe=timeframe
    )
    console.print(
        f"  [green]✓[/] {len(df)} bougies récupérées (du {df.index[0].date()} au {df.index[-1].date()})"
    )
    return df


# ----- Feature engineering ----- #


def prepare_live_features(
    df: pd.DataFrame,
    feature_scaler,
    clip_bounds: np.ndarray | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    window_size: int = WINDOW_SIZE,
) -> tuple[np.ndarray, pd.DataFrame]:
    """
    Calcule les features pour la dernière fenêtre de données.

    Args:
        df: DataFrame OHLCV avec suffisamment d'historique
        feature_scaler: RobustScaler fitté pendant l'entraînement
        clip_bounds: Bornes de clipping (nf, 2) fittées pendant le training
        timeframe: Timeframe du modèle (ex: "1d", "1h")
        window_size: Taille de la fenêtre glissante

    Returns:
        (X_scaled, df_features) où X_scaled est la dernière fenêtre prête pour le modèle
    """
    # Calculer toutes les features pour le timeframe
    df_features = build_features(df.copy(), timeframe=timeframe)
    feature_cols = get_feature_columns(timeframe)

    if len(df_features) < window_size:
        raise ValueError(
            f"Pas assez de données après feature engineering: {len(df_features)} < {window_size}"
        )

    # Prendre les window_size dernières lignes
    latest_window = df_features[feature_cols].iloc[-window_size:].values

    # Appliquer le scaler (reshape pour scaler 2D)
    n_features = len(feature_cols)
    X_flat = latest_window.reshape(-1, n_features)

    # Clipping outliers (même bornes que le training)
    if clip_bounds is not None:
        for i in range(n_features):
            X_flat[:, i] = np.clip(X_flat[:, i], clip_bounds[i, 0], clip_bounds[i, 1])

    X_scaled_flat = feature_scaler.transform(X_flat)
    X_scaled = X_scaled_flat.reshape(1, window_size, n_features)

    return X_scaled, df_features


# ----- Prédictions ----- #


def predict_return(model, X: np.ndarray, target_scaler, device: torch.device) -> float:
    """
    Fait une prédiction pour une seule fenêtre.

    Args:
        model: Modèle PyTorch
        X: Features scalées de shape (1, WINDOW_SIZE, n_features)
        target_scaler: StandardScaler pour inverse_transform
        device: Device pour l'inférence

    Returns:
        Prédiction de rendement en pourcentage
    """
    model.eval()
    X_tensor = torch.tensor(X, dtype=torch.float32).to(device)

    with torch.no_grad():
        pred_scaled = model(X_tensor).cpu().numpy().ravel()[0]

    # Inverse transform
    pred = target_scaler.inverse_transform([[pred_scaled]])[0][0]

    return pred


# ----- Gestion des positions ----- #


def calculate_sl_tp(
    entry_price: float, direction: str, rrr: float, risk_pct: float
) -> tuple[float, float]:
    """
    Calcule les niveaux de stop-loss et take-profit basés sur le RRR.

    RRR = Risk/Reward Ratio
    risk_pct = % du capital à risquer par trade

    Pour un LONG:
    - SL = entry_price * (1 - risk_pct)
    - TP = entry_price * (1 + risk_pct * rrr)

    Pour un SHORT:
    - SL = entry_price * (1 + risk_pct)
    - TP = entry_price * (1 - risk_pct * rrr)

    Args:
        entry_price: Prix d'entrée
        direction: "LONG" ou "SHORT"
        rrr: Risk/Reward Ratio (ex: 2.0 pour 1:2)
        risk_pct: Pourcentage de risque (ex: 0.025 pour 2.5%)

    Returns:
        (stop_loss, take_profit)
    """
    if direction == "LONG":
        sl = entry_price * (1 - risk_pct)
        tp = entry_price * (1 + risk_pct * rrr)
    else:  # SHORT
        sl = entry_price * (1 + risk_pct)
        tp = entry_price * (1 - risk_pct * rrr)

    return sl, tp


def check_position_exit(
    position: RealtimePosition,
    current_price: float,
    current_time: datetime,
    slippage_pct: float = 0.0,
    prediction_horizon: int = PREDICTION_HORIZON,
    minutes_per_bar: int = 1440,
) -> tuple[bool, str, float]:
    """
    Vérifie si une position doit être clôturée.

    Args:
        position: Position ouverte
        current_price: Prix actuel
        current_time: Heure actuelle
        slippage_pct: Slippage appliqué au prix de sortie

    Returns:
        (should_exit, reason, exit_price)
    """
    # Appliquer le slippage défavorable au prix de sortie
    if position.direction == "LONG":
        exit_price = current_price * (1 - slippage_pct)
    else:
        exit_price = current_price * (1 + slippage_pct)

    # Vérifier SL/TP — exit au prix réel avec slippage (gère les gaps)
    if position.direction == "LONG":
        if current_price <= position.stop_loss:
            return True, "SL", exit_price
        if current_price >= position.take_profit:
            return True, "TP", exit_price
    else:  # SHORT
        if current_price >= position.stop_loss:
            return True, "SL", exit_price
        if current_price <= position.take_profit:
            return True, "TP", exit_price

    # Vérifier expiration (prediction_horizon barres)
    # Normaliser les dates pour éviter les problèmes de timezone
    entry_date = (
        position.entry_date.replace(tzinfo=None)
        if position.entry_date.tzinfo
        else position.entry_date
    )
    current = current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
    bars_open = (current - entry_date).total_seconds() / (minutes_per_bar * 60)
    if bars_open >= prediction_horizon:
        return True, "EXPIRATION", exit_price

    return False, "", current_price


def close_position(
    position: RealtimePosition,
    exit_price: float,
    exit_reason: str,
    current_time: datetime,
    exit_fee_pct: float,
) -> tuple[RealtimeTrade, float]:
    """
    Clôture une position et calcule le PnL.

    Args:
        position: Position à clôturer
        exit_price: Prix de sortie
        exit_reason: Raison de la sortie (SL, TP, EXPIRATION)
        current_time: Heure de clôture
        exit_fee_pct: Frais de sortie

    Returns:
        (trade, pnl_net)
    """
    # Calculer le rendement réel
    if position.direction == "LONG":
        actual_return = exit_price / position.entry_price - 1
    else:
        actual_return = position.entry_price / exit_price - 1

    # PnL brut
    pnl_before_fees = position.allocated_capital * actual_return

    # Frais de sortie
    exit_value = position.allocated_capital * (1 + actual_return)
    exit_fee = exit_value * exit_fee_pct
    total_fees = position.entry_fee + exit_fee

    # PnL net
    pnl = pnl_before_fees - exit_fee

    trade = RealtimeTrade(
        entry_date=position.entry_date,
        exit_date=current_time,
        direction=position.direction,
        entry_price=position.entry_price,
        exit_price=exit_price,
        exit_reason=exit_reason,
        predicted_return=position.predicted_return,
        actual_return=actual_return,
        pnl=pnl,
        total_fees=total_fees,
    )

    return trade, pnl


def open_position(
    state: RealtimeState,
    direction: str,
    entry_price: float,
    predicted_return: float,
    rrr: float,
    risk_pct: float,
    entry_fee_pct: float,
    slot_capital: float,
    entry_date: Optional[datetime] = None,
) -> Optional[RealtimePosition]:
    """
    Ouvre une nouvelle position.

    Args:
        state: État courant du système
        direction: "LONG" ou "SHORT"
        entry_price: Prix d'entrée
        predicted_return: Prédiction du modèle
        rrr: Risk/Reward Ratio
        risk_pct: Pourcentage de risque
        entry_fee_pct: Frais d'entrée
        slot_capital: Capital alloué par position
        entry_date: Date d'entrée (None = maintenant)

    Returns:
        La position créée ou None si pas assez de cash
    """
    # Frais déduits de la position effective (comme Binance spot)
    effective_position = slot_capital * (1 - entry_fee_pct)
    entry_fee = slot_capital * entry_fee_pct

    if state.capital < slot_capital:
        return None

    # Calculer SL/TP
    sl, tp = calculate_sl_tp(entry_price, direction, rrr, risk_pct)

    # Date d'entrée
    if entry_date is None:
        entry_date = datetime.now(timezone.utc)
    elif entry_date.tzinfo is None:
        # Rendre la date timezone-aware si elle ne l'est pas
        entry_date = entry_date.replace(tzinfo=timezone.utc)

    state.position_counter += 1
    position = RealtimePosition(
        entry_date=entry_date,
        direction=direction,
        entry_price=entry_price,
        predicted_return=predicted_return,
        stop_loss=sl,
        take_profit=tp,
        allocated_capital=effective_position,
        entry_fee=entry_fee,
        position_id=state.position_counter,
    )

    # Mettre à jour le cash (on dépense slot_capital = position + fee)
    state.capital -= slot_capital
    state.allocated += effective_position

    return position


# ----- Helpers affichage ----- #


def _pnl_color(value: float) -> str:
    """Retourne le style Rich selon le signe du PnL."""
    if value > 0:
        return "bold green"
    elif value < 0:
        return "bold red"
    return "dim"


def _pnl_text(value: float, fmt: str = "+,.2f") -> Text:
    """Crée un Text coloré pour un PnL."""
    txt = Text(f"${value:{fmt}}")
    txt.stylize(_pnl_color(value))
    return txt


def _pct_text(value: float) -> Text:
    """Crée un Text coloré pour un pourcentage."""
    txt = Text(f"{value:+.2f}%")
    txt.stylize(_pnl_color(value))
    return txt


def _calc_portfolio_metrics(
    state: RealtimeState, current_price: float, initial_capital: float = 0
) -> dict:
    """Calcule les métriques communes du portefeuille."""
    portfolio_value = state.capital + state.allocated
    for pos in state.open_positions:
        if pos.direction == "LONG":
            unrealized = pos.allocated_capital * (current_price / pos.entry_price - 1)
        else:
            unrealized = pos.allocated_capital * (pos.entry_price / current_price - 1)
        portfolio_value += unrealized

    total_trades = len(state.closed_trades)
    winning_trades = [t for t in state.closed_trades if t.pnl > 0]
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
    closed_pnl = sum(t.pnl for t in state.closed_trades)

    # PnL total = différence entre la valeur actuelle du portfolio et le capital initial
    # Inclut le PnL réalisé, non réalisé et les frais d'entrée des positions ouvertes
    total_pnl = (
        (portfolio_value - initial_capital) if initial_capital > 0 else closed_pnl
    )

    return {
        "portfolio_value": portfolio_value,
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": total_trades - len(winning_trades),
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "closed_pnl": closed_pnl,
    }


# ----- Affichage ----- #


def print_header(
    symbol: str,
    model_type: str,
    capital: float,
    rrr: float,
    prediction_horizon: int = PREDICTION_HORIZON,
    timeframe: str = DEFAULT_TIMEFRAME,
    threshold: float = 0.01,
    risk_pct: float = 0.025,
    sizing_mode: str = "fixed",
    max_drawdown_pct: float = 0.20,
    cooldown_bars: int = 3,
    max_trades_per_day: int = 4,
):
    """Affiche l'en-tête du système."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Symbol", symbol)
    table.add_row("Model", model_type.upper())
    table.add_row("Capital", f"${capital:,.2f}")
    table.add_row("RRR", f"1:{rrr}")
    table.add_row("Horizon", f"{prediction_horizon} bars [{timeframe}]")
    table.add_row("Threshold", f"{threshold * 100:.2f}%")
    table.add_row("SL / TP", f"{risk_pct * 100:.2f}% / {risk_pct * rrr * 100:.2f}%")
    table.add_row("Sizing", sizing_mode)
    table.add_row("Max DD", f"{max_drawdown_pct:.0%}")
    table.add_row("Cooldown", f"{cooldown_bars} bars")
    table.add_row("Max/Day", str(max_trades_per_day))

    console.print(
        Panel(table, title="REALTIME TRADING SIMULATION", border_style="cyan")
    )


def print_status(
    state: RealtimeState, current_price: float, symbol: str, initial_capital: float = 0
):
    """Affiche le statut courant du portefeuille (mode live)."""
    m = _calc_portfolio_metrics(state, current_price, initial_capital)

    # Table métriques
    table = Table(box=None, show_header=True, padding=(0, 2))
    table.add_column("Portfolio", justify="right")
    table.add_column("Total PnL", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Trades", justify="center")

    pnl_style = _pnl_color(m["total_pnl"])
    wr_style = "green" if m["win_rate"] >= 50 else "red"

    table.add_row(
        f"${m['portfolio_value']:,.2f}",
        Text(f"${m['total_pnl']:+,.2f}", style=pnl_style),
        Text(f"{m['win_rate']:.1f}%", style=wr_style),
        f"{m['winning_trades']} / {m['total_trades']}  ({len(state.open_positions)} open)",
    )

    # Positions ouvertes
    pos_lines = []
    for pos in state.open_positions:
        if pos.direction == "LONG":
            unrealized_pct = (current_price / pos.entry_price - 1) * 100
        else:
            unrealized_pct = (pos.entry_price / current_price - 1) * 100
        unrealized_val = pos.allocated_capital * unrealized_pct / 100
        pnl_s = _pnl_color(unrealized_val)

        pos_lines.append(
            f"  [bold]#{pos.position_id}[/] {pos.direction}  "
            f"${pos.entry_price:,.2f} -> ${current_price:,.2f}  "
            f"[{pnl_s}]${unrealized_val:+.2f} ({unrealized_pct:+.2f}%)[/]"
        )
        pos_lines.append(
            f"     [dim]SL: ${pos.stop_loss:,.2f}  TP: ${pos.take_profit:,.2f}  "
            f"Pred: {pos.predicted_return * 100:+.2f}%[/]"
        )

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = f"{now_str}  {symbol}  Price: ${current_price:,.2f}"

    content = table
    if pos_lines:
        # Render table + positions together
        console.print()
        console.print(
            Panel(table, title=title, subtitle="OPEN POSITIONS ↓", border_style="blue")
        )
        for line in pos_lines:
            console.print(line)
        console.print()
    else:
        console.print()
        console.print(Panel(table, title=title, border_style="blue"))


def print_status_backtest(
    state: RealtimeState,
    current_price: float,
    symbol: str,
    current_time: datetime,
    progress: int,
    total: int,
    initial_capital: float = 0,
):
    """Affiche le statut courant du portefeuille en mode backtest."""
    m = _calc_portfolio_metrics(state, current_price, initial_capital)
    progress_pct = (progress / total * 100) if total > 0 else 0

    current_time_naive = (
        current_time.replace(tzinfo=None) if current_time.tzinfo else current_time
    )

    # Table métriques
    table = Table(box=None, show_header=True, padding=(0, 2))
    table.add_column("Portfolio", justify="right")
    table.add_column("Total PnL", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Trades", justify="center")

    pnl_style = _pnl_color(m["total_pnl"])
    wr_style = "green" if m["win_rate"] >= 50 else "red"

    table.add_row(
        f"${m['portfolio_value']:,.2f}",
        Text(f"${m['total_pnl']:+,.2f}", style=pnl_style),
        Text(f"{m['win_rate']:.1f}%", style=wr_style),
        f"{m['winning_trades']} / {m['total_trades']}  ({len(state.open_positions)} open)",
    )

    # Positions ouvertes
    pos_lines = []
    for pos in state.open_positions:
        if pos.direction == "LONG":
            unrealized_pct = (current_price / pos.entry_price - 1) * 100
        else:
            unrealized_pct = (pos.entry_price / current_price - 1) * 100
        unrealized_val = pos.allocated_capital * unrealized_pct / 100
        pnl_s = _pnl_color(unrealized_val)

        entry_date_naive = (
            pos.entry_date.replace(tzinfo=None)
            if pos.entry_date.tzinfo
            else pos.entry_date
        )
        days_open = (current_time_naive - entry_date_naive).days
        pos_lines.append(
            f"  [bold]#{pos.position_id}[/] {pos.direction}  "
            f"${pos.entry_price:,.2f} -> ${current_price:,.2f}  "
            f"[{pnl_s}]${unrealized_val:+.2f} ({unrealized_pct:+.2f}%)[/]  "
            f"[dim]{days_open}d[/]"
        )
        pos_lines.append(
            f"     [dim]SL: ${pos.stop_loss:,.2f}  TP: ${pos.take_profit:,.2f}[/]"
        )

    title = (
        f"[bold cyan]{symbol}[/]  {current_time_naive.date()}  "
        f"Price: ${current_price:,.2f}  [dim][{progress_pct:.1f}%][/]"
    )

    console.print()
    console.print(Panel(table, title=title, border_style="blue"))
    if pos_lines:
        for line in pos_lines:
            console.print(line)


def _build_equity_curve(state: RealtimeState, initial_capital: float) -> str:
    """Construit une equity curve ASCII à partir des trades clôturés."""
    if not state.closed_trades:
        return ""

    # Reconstruire l'évolution du capital
    equity = [initial_capital]
    running = initial_capital
    for t in state.closed_trades:
        running += t.pnl
        equity.append(running)

    # Dimensions du graphique
    width = 60
    height = 12

    min_val = min(equity)
    max_val = max(equity)
    val_range = max_val - min_val if max_val != min_val else 1

    # Résampler si trop de points
    if len(equity) > width:
        step = len(equity) / width
        sampled = [equity[int(i * step)] for i in range(width)]
    else:
        sampled = equity

    # Construire la grille
    lines = []
    for row in range(height):
        threshold = max_val - (row / (height - 1)) * val_range
        line = ""
        for val in sampled:
            if val >= threshold:
                line += "█"
            else:
                line += " "
        # Label à gauche
        if row == 0:
            label = f"${max_val:>10,.0f} │"
        elif row == height - 1:
            label = f"${min_val:>10,.0f} │"
        elif row == height // 2:
            mid = (max_val + min_val) / 2
            label = f"${mid:>10,.0f} │"
        else:
            label = f"{'':>11}│"
        lines.append(label + line)

    # Axe horizontal
    lines.append(f"{'':>11}└{'─' * len(sampled)}")
    start_label = "Start"
    end_label = "End"
    padding = len(sampled) - len(start_label) - len(end_label)
    if padding > 0:
        lines.append(f"{'':>12}{start_label}{' ' * padding}{end_label}")

    return "\n".join(lines)


def print_summary(state: RealtimeState, initial_capital: float):
    """Affiche le résumé final enrichi avec métriques avancées et equity curve."""
    total_trades = len(state.closed_trades)
    if total_trades == 0:
        console.print(
            Panel(
                "[dim]Aucun trade exécuté.[/]",
                title="FINAL SUMMARY",
                border_style="yellow",
            )
        )
        return

    winning_trades = [t for t in state.closed_trades if t.pnl > 0]
    losing_trades = [t for t in state.closed_trades if t.pnl <= 0]

    total_pnl = sum(t.pnl for t in state.closed_trades)
    total_return = total_pnl / initial_capital * 100
    total_fees = sum(t.total_fees for t in state.closed_trades)
    final_capital = initial_capital + total_pnl

    # Métriques avancées
    pnls = [t.pnl for t in state.closed_trades]
    best_trade = max(pnls)
    worst_trade = min(pnls)

    avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
    avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
    profit_factor = (
        abs(sum(t.pnl for t in winning_trades) / sum(t.pnl for t in losing_trades))
        if losing_trades and sum(t.pnl for t in losing_trades) != 0
        else float("inf")
    )

    # Max drawdown
    equity = [initial_capital]
    running = initial_capital
    for t in state.closed_trades:
        running += t.pnl
        equity.append(running)
    peak = equity[0]
    max_dd = 0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Durée moyenne des trades
    durations = []
    for t in state.closed_trades:
        entry = (
            t.entry_date.replace(tzinfo=None) if t.entry_date.tzinfo else t.entry_date
        )
        exit_ = t.exit_date.replace(tzinfo=None) if t.exit_date.tzinfo else t.exit_date
        durations.append((exit_ - entry).total_seconds() / 86400)
    avg_duration = np.mean(durations) if durations else 0

    # Sharpe ratio simplifié (daily returns)
    daily_returns = [t.pnl / initial_capital for t in state.closed_trades]
    if len(daily_returns) > 1 and np.std(daily_returns) > 0:
        sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
    else:
        sharpe = 0

    # ----- Table performance (pleine largeur, ligne horizontale) ----- #
    perf_table = Table(show_header=True, box=None, padding=(0, 1))
    perf_table.add_column("Initial", justify="right", style="dim")
    perf_table.add_column("Final", justify="right")
    perf_table.add_column("Return", justify="right")
    perf_table.add_column("PnL", justify="right")
    perf_table.add_column("Fees", justify="right", style="dim")
    perf_table.add_column("Max DD", justify="right")
    perf_table.add_column("Sharpe", justify="right")

    return_style = _pnl_color(total_pnl)
    dd_style = "red" if max_dd > 10 else "yellow"

    perf_table.add_row(
        f"${initial_capital:,.2f}",
        Text(f"${final_capital:,.2f}", style=return_style),
        Text(f"{total_return:+.2f}%", style=return_style),
        _pnl_text(total_pnl),
        f"${total_fees:,.2f}",
        Text(f"{max_dd:.2f}%", style=dd_style),
        f"{sharpe:.2f}",
    )

    # ----- Table trades + details (côte à côte) ----- #
    win_rate = len(winning_trades) / total_trades * 100
    wr_style = "green" if win_rate >= 50 else "red"

    trade_table = Table(show_header=False, box=None, padding=(0, 1))
    trade_table.add_column(style="bold", no_wrap=True)
    trade_table.add_column(justify="right", no_wrap=True)

    trade_table.add_row(
        "Trades",
        f"{len(winning_trades)} W / {len(losing_trades)} L  ({total_trades} total)",
    )
    trade_table.add_row("Win Rate", Text(f"{win_rate:.1f}%", style=wr_style))
    pf_str = f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞"
    trade_table.add_row("P. Factor", pf_str)
    trade_table.add_row(
        "Avg Win", Text(f"${avg_win:,.2f}", style="green") if avg_win > 0 else "$0.00"
    )
    trade_table.add_row(
        "Avg Loss", Text(f"${avg_loss:,.2f}", style="red") if avg_loss < 0 else "$0.00"
    )
    trade_table.add_row("Best", _pnl_text(best_trade))
    trade_table.add_row("Worst", _pnl_text(worst_trade))
    trade_table.add_row("Avg Dur.", f"{avg_duration:.1f} days")

    sl_exits = [t for t in state.closed_trades if t.exit_reason == "SL"]
    tp_exits = [t for t in state.closed_trades if t.exit_reason == "TP"]
    exp_exits = [t for t in state.closed_trades if t.exit_reason == "EXPIRATION"]

    exit_table = Table(show_header=False, box=None, padding=(0, 1))
    exit_table.add_column(style="bold", no_wrap=True)
    exit_table.add_column(justify="right", no_wrap=True)

    exit_table.add_row("Take Profit", Text(str(len(tp_exits)), style="green"))
    exit_table.add_row("Stop Loss", Text(str(len(sl_exits)), style="red"))
    exit_table.add_row("Expiration", Text(str(len(exp_exits)), style="yellow"))

    # ----- Layout ----- #
    bottom_layout = Table.grid(padding=(0, 4))
    bottom_layout.add_column()
    bottom_layout.add_column()
    bottom_layout.add_row(trade_table, exit_table)

    # Assemble all sections
    full_layout = Table.grid()
    full_layout.add_column()
    full_layout.add_row(perf_table)
    full_layout.add_row(Text(""))
    full_layout.add_row(bottom_layout)

    console.print()
    console.print(
        Panel(full_layout, title="[bold]FINAL SUMMARY[/]", border_style="cyan")
    )

    # ----- Equity curve ----- #
    curve = _build_equity_curve(state, initial_capital)
    if curve:
        console.print(Panel(curve, title="[bold]EQUITY CURVE[/]", border_style="cyan"))


# ----- Main class ----- #


class RealtimeTester:
    """Système de testing en temps réel."""

    def __init__(self, config: dict):
        self.config = config
        self.symbol = config["symbol"]
        self.model_type = config["model_type"]
        self.timeframe = config.get("timeframe", DEFAULT_TIMEFRAME)
        self.initial_capital = config["capital"]
        self.allow_short = config["allow_short"]
        self.rrr = config["rrr"]
        self.entry_fee_pct = config["entry_fee_pct"]
        self.exit_fee_pct = config["exit_fee_pct"]
        self.slippage_pct = config["slippage_pct"]

        # Timeframe-aware config
        tf_config = get_timeframe_config(self.timeframe)
        self.window_size = tf_config["window_size"]
        self.prediction_horizon = tf_config["prediction_horizon"]
        self.minutes_per_bar = tf_config["minutes_per_bar"]

        # Threshold auto : adapté à l'horizon temporel du timeframe
        raw_threshold = config.get("threshold")
        self.threshold = (
            raw_threshold
            if raw_threshold is not None
            else SIGNAL_THRESHOLDS.get(self.timeframe, 0.01)
        )

        # risk_pct auto : calibré sur ~1 ATR du timeframe
        raw_risk = config.get("risk_pct")
        self.risk_pct = (
            raw_risk if raw_risk is not None else RISK_PCTS.get(self.timeframe, 0.025)
        )

        # Intervalle de check auto : 1 barre = minutes_per_bar minutes
        raw_interval = config.get("check_interval_hours")
        check_hours = (
            raw_interval if raw_interval is not None else self.minutes_per_bar / 60
        )
        self.check_interval = check_hours * 3600  # en secondes

        # ----- Risk management -----
        self.sizing_mode = config.get("sizing_mode", "fixed")
        self.max_position_pct = config.get("max_position_pct", 0.25)
        self.max_position_size = config.get("max_position_size")
        self.rebalance_interval = config.get("rebalance_interval", 50)
        self.max_drawdown_pct = config.get("max_drawdown_pct", 0.20)
        self.cooldown_bars = config.get("cooldown_bars", 3)
        self.max_trades_per_day = config.get("max_trades_per_day", 4)
        self.max_expiration_rate = config.get("max_expiration_rate", 0.50)

        # État interne risk management
        self._rebalance_base = self.initial_capital
        self._trades_since_rebalance = 0
        self._peak_value = self.initial_capital
        self._circuit_breaker_active = False
        self._last_entry_time: Optional[datetime] = None
        self._daily_trade_count = 0
        self._current_trade_day: Optional[object] = None  # date object

        self.state = RealtimeState(capital=self.initial_capital)
        self.df_history: Optional[pd.DataFrame] = None
        self.model = None
        self.scalers = None
        self.device = None
        self.feature_scaler = None
        self.target_scaler = None
        self.clip_bounds = None

        self.exchange = None
        self.last_candle_time: Optional[datetime] = None
        self.running = False

        # Chemin du fichier d'état persistant
        symbol_code = self.symbol.replace("/", "_")
        self.state_path = f"testing/state_{symbol_code}.json"

    def _save_state(self):
        """Sauvegarde l'état courant dans un fichier JSON."""
        state_data = {
            "capital": self.state.capital,
            "allocated": self.state.allocated,
            "position_counter": self.state.position_counter,
            "last_candle_time": str(self.last_candle_time)
            if self.last_candle_time
            else None,
            "open_positions": [
                {
                    "entry_date": pos.entry_date.isoformat(),
                    "direction": pos.direction,
                    "entry_price": pos.entry_price,
                    "predicted_return": pos.predicted_return,
                    "stop_loss": pos.stop_loss,
                    "take_profit": pos.take_profit,
                    "allocated_capital": pos.allocated_capital,
                    "entry_fee": pos.entry_fee,
                    "position_id": pos.position_id,
                }
                for pos in self.state.open_positions
            ],
            "closed_trades": [
                {
                    "entry_date": t.entry_date.isoformat()
                    if hasattr(t.entry_date, "isoformat")
                    else str(t.entry_date),
                    "exit_date": t.exit_date.isoformat()
                    if hasattr(t.exit_date, "isoformat")
                    else str(t.exit_date),
                    "direction": t.direction,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "exit_reason": t.exit_reason,
                    "predicted_return": t.predicted_return,
                    "actual_return": t.actual_return,
                    "pnl": t.pnl,
                    "total_fees": t.total_fees,
                }
                for t in self.state.closed_trades
            ],
            # Risk management state
            "risk_management": {
                "peak_portfolio_value": self._peak_value,
                "circuit_breaker_active": self._circuit_breaker_active,
                "last_entry_time": self._last_entry_time.isoformat()
                if self._last_entry_time
                else None,
                "daily_trade_count": self._daily_trade_count,
                "current_trade_day": str(self._current_trade_day)
                if self._current_trade_day
                else None,
                "trades_since_rebalance": self._trades_since_rebalance,
                "rebalance_base_capital": self._rebalance_base,
            },
        }
        # Écriture atomique : on écrit dans un tmp puis on rename
        # pour éviter la corruption si le process crash pendant l'écriture.
        tmp_path = self.state_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(state_data, f, indent=2)
        os.replace(tmp_path, self.state_path)

    def _load_state(self) -> bool:
        """Charge l'état depuis un fichier JSON. Retourne True si chargé."""
        if not os.path.exists(self.state_path):
            return False

        with open(self.state_path, "r") as f:
            data = json.load(f)

        self.state.capital = data["capital"]
        self.state.allocated = data["allocated"]
        self.state.position_counter = data["position_counter"]

        if data.get("last_candle_time"):
            self.last_candle_time = pd.Timestamp(data["last_candle_time"])

        self.state.open_positions = [
            RealtimePosition(
                entry_date=datetime.fromisoformat(p["entry_date"]),
                direction=p["direction"],
                entry_price=p["entry_price"],
                predicted_return=p["predicted_return"],
                stop_loss=p["stop_loss"],
                take_profit=p["take_profit"],
                allocated_capital=p["allocated_capital"],
                entry_fee=p["entry_fee"],
                position_id=p["position_id"],
            )
            for p in data["open_positions"]
        ]

        self.state.closed_trades = [
            RealtimeTrade(
                entry_date=datetime.fromisoformat(t["entry_date"]),
                exit_date=datetime.fromisoformat(t["exit_date"]),
                direction=t["direction"],
                entry_price=t["entry_price"],
                exit_price=t["exit_price"],
                exit_reason=t["exit_reason"],
                predicted_return=t["predicted_return"],
                actual_return=t["actual_return"],
                pnl=t["pnl"],
                total_fees=t["total_fees"],
            )
            for t in data["closed_trades"]
        ]

        # Restaurer l'état risk management
        rm = data.get("risk_management", {})
        self._peak_value = rm.get("peak_portfolio_value", self.initial_capital)
        self._circuit_breaker_active = rm.get("circuit_breaker_active", False)
        last_entry = rm.get("last_entry_time")
        self._last_entry_time = (
            datetime.fromisoformat(last_entry) if last_entry else None
        )
        self._daily_trade_count = rm.get("daily_trade_count", 0)
        trade_day = rm.get("current_trade_day")
        self._current_trade_day = (
            datetime.fromisoformat(trade_day).date() if trade_day else None
        )
        self._trades_since_rebalance = rm.get("trades_since_rebalance", 0)
        self._rebalance_base = rm.get("rebalance_base_capital", self.initial_capital)

        n_pos = len(self.state.open_positions)
        n_trades = len(self.state.closed_trades)
        console.print(
            f"  [green]✓[/] État restauré: {n_pos} positions ouvertes, {n_trades} trades passés"
        )
        if self._circuit_breaker_active:
            console.print(
                f"  [bold red]⚠ Circuit breaker actif[/] (drawdown >= {self.max_drawdown_pct:.0%})"
            )
        return True

    def initialize(self):
        """Initialise le système: charge le modèle, récupère l'historique."""
        print_header(
            self.symbol,
            self.model_type,
            self.initial_capital,
            self.rrr,
            prediction_horizon=self.prediction_horizon,
            timeframe=self.timeframe,
            threshold=self.threshold,
            risk_pct=self.risk_pct,
            sizing_mode=self.sizing_mode,
            max_drawdown_pct=self.max_drawdown_pct,
            cooldown_bars=self.cooldown_bars,
            max_trades_per_day=self.max_trades_per_day,
        )

        # Device
        self.device = torch.device("mps" if torch.mps.is_available() else "cpu")
        console.print(f"[bold]INIT[/] Device: {self.device}")

        # Initialiser l'exchange une seule fois (préserve le rate limiter)
        self.exchange = ccxt.binance()
        console.print("  [green]✓[/] Exchange Binance initialisé")

        # Charger modèle et scalers
        console.print(
            f"[bold]INIT[/] Chargement du modèle {self.model_type} [{self.timeframe}]..."
        )
        self.model, _ = load_model_dynamic(
            self.model_type, self.device, timeframe=self.timeframe
        )
        self.scalers = load_scalers(self.model_type, timeframe=self.timeframe)
        self.feature_scaler = self.scalers["feature_scaler"]
        self.target_scaler = self.scalers["target_scaler"]
        self.clip_bounds = self.scalers.get("clip_bounds")
        if self.clip_bounds is not None:
            console.print("  [green]✓[/] Modèle, scalers et clip_bounds chargés")
        else:
            console.print(
                "  [yellow]✓[/] Modèle et scalers chargés [dim](clip_bounds absent, re-entraîner le modèle)[/]"
            )

        # Verrouiller short en mode live (spot Binance ne supporte pas le short)
        if self.allow_short:
            console.print(
                "  [bold yellow]WARNING[/] Short selling non supporté en spot Binance. Désactivé."
            )
            self.allow_short = False

        # Restaurer l'état si disponible
        self._load_state()

        # Récupérer l'historique initial
        self.df_history = fetch_initial_history(
            self.symbol,
            min_bars=self.window_size + 50,
            exchange=self.exchange,
            timeframe=self.timeframe,
        )
        if self.last_candle_time is None:
            self.last_candle_time = self.df_history.index[-1]
        console.print(f"  [green]✓[/] Dernière bougie: {self.last_candle_time}")

        check_h = self.check_interval / 3600
        console.print(f"\n[bold]INIT[/] Démarrage de la boucle principale...")
        console.print(
            f"       Threshold: {self.threshold * 100:.2f}%  |  Intervalle: {check_h:.1f}h par bougie [{self.timeframe}]"
        )
        console.print("       Appuyez sur Ctrl+C pour arrêter\n")

    def process_new_candle(self, current_price: float, candle_time) -> None:
        """
        Traite une nouvelle bougie clôturée : prédiction + ouverture de position.

        On re-fetch l'historique complet depuis Binance pour s'assurer que
        les features sont calculées sur des bougies CLÔTURÉES uniquement
        (on exclut la bougie en cours de formation = la dernière retournée).

        Args:
            current_price: Prix actuel du marché (bougie en formation) = prix d'entrée.
            candle_time: Timestamp de la nouvelle bougie détectée (pour le log).
        """
        console.print(
            f"\n[bold cyan][NEW CANDLE][/] {candle_time} | Entry price: ${current_price:,.2f}"
        )

        # Re-fetch l'historique pour avoir les OHLCV finalisés des bougies clôturées.
        # On prend window_size + 50 bougies et on exclut la dernière (en formation).
        try:
            df_fresh = fetch_latest_ohlcv(
                self.symbol,
                limit=self.window_size + 52,
                exchange=self.exchange,
                timeframe=self.timeframe,
            )
            # Exclure la bougie en cours de formation (dernière entrée)
            df_closed = df_fresh.iloc[:-1]
            self.df_history = df_fresh  # mise à jour du cache complet
        except Exception as e:
            console.print(
                f"  [yellow]WARN[/] Re-fetch échoué ({e}), utilisation du cache"
            )
            df_closed = self.df_history.iloc[:-1]

        # Calculer les features sur les bougies clôturées uniquement
        try:
            X_scaled, _ = prepare_live_features(
                df_closed,
                self.feature_scaler,
                self.clip_bounds,
                timeframe=self.timeframe,
                window_size=self.window_size,
            )
            prediction = predict_return(
                self.model, X_scaled, self.target_scaler, self.device
            )
            pred_style = (
                "green" if prediction > 0 else "red" if prediction < 0 else "dim"
            )
            console.print(
                f"  [bold]PREDICTION[/] [{pred_style}]{prediction * 100:+.2f}%[/]  "
                f"[dim](seuil: ±{self.threshold * 100:.2f}%)[/]"
            )
        except Exception as e:
            console.print(f"  [bold red]ERROR[/] Erreur prédiction: {e}")
            return

        # Générer le signal
        if prediction > self.threshold:
            self._open_new_position("LONG", current_price, prediction)
        elif prediction < -self.threshold and self.allow_short:
            self._open_new_position("SHORT", current_price, prediction)

    def _check_and_close_positions(self, current_price: float, current_time: datetime):
        """Vérifie et ferme les positions qui ont atteint SL/TP ou expiré."""
        positions_to_close = []

        for pos in self.state.open_positions:
            should_exit, reason, exit_price = check_position_exit(
                pos,
                current_price,
                current_time,
                self.slippage_pct,
                prediction_horizon=self.prediction_horizon,
                minutes_per_bar=self.minutes_per_bar,
            )
            if should_exit:
                positions_to_close.append((pos, reason, exit_price))

        for pos, reason, exit_price in positions_to_close:
            trade, pnl = close_position(
                pos, exit_price, reason, current_time, self.exit_fee_pct
            )

            self.state.closed_trades.append(trade)
            self.state.allocated -= pos.allocated_capital
            self.state.capital += pos.allocated_capital + pnl
            self.state.open_positions.remove(pos)

            pnl_pct = pnl / pos.allocated_capital * 100
            reason_style = {"TP": "green", "SL": "red", "EXPIRATION": "yellow"}.get(
                reason, "dim"
            )
            pnl_style = _pnl_color(pnl)

            close_text = (
                f"  {pos.direction}  ${pos.entry_price:,.2f} -> ${exit_price:,.2f}\n"
                f"  PnL: [{pnl_style}]${pnl:+.2f} ({pnl_pct:+.2f}%)[/]   Fees: ${trade.total_fees:.2f}"
            )
            console.print(
                Panel(
                    close_text,
                    title=f"[bold]CLOSE #{pos.position_id}[/]  [{reason_style}]{reason}[/]",
                    border_style=reason_style,
                    width=50,
                )
            )

        if positions_to_close:
            # Rebalance check (mode periodic)
            for _ in positions_to_close:
                self._check_rebalance()

            # Mise à jour du drawdown
            portfolio_value = self.state.capital + self.state.allocated
            self._update_drawdown(portfolio_value)

            # Warning taux d'expiration (tous les 50 trades)
            total_closed = len(self.state.closed_trades)
            if total_closed > 0 and total_closed % 50 == 0:
                exp_count = sum(
                    1 for t in self.state.closed_trades if t.exit_reason == "EXPIRATION"
                )
                exp_rate = exp_count / total_closed
                if exp_rate > self.max_expiration_rate:
                    console.print(
                        f"\n[bold yellow]⚠ EXPIRATION RATE[/] {exp_rate:.0%} des trades expirent "
                        f"(seuil: {self.max_expiration_rate:.0%}).\n"
                        f"  Considérez augmenter risk_pct ({self.risk_pct}) ou réduire RRR ({self.rrr})."
                    )

            self._save_state()

    # ----- Risk management methods ----- #

    def _calculate_slot_capital(
        self, predicted_return: float = 0.0, atr_value: float | None = None
    ) -> tuple[float, float, float]:
        """
        Calcule la taille de position selon le mode de sizing configuré.

        Returns:
            (slot_capital, sl_pct, tp_pct) où:
            - slot_capital: Montant alloué pour la position
            - sl_pct: Pourcentage pour le stop-loss
            - tp_pct: Pourcentage pour le take-profit
        """
        current_total = self.state.capital + self.state.allocated

        # Nouveaux modes: "kelly", "atr_risk", "confidence_weighted", "optimal_rrr"
        if self.sizing_mode in [
            "kelly",
            "atr_risk",
            "confidence_weighted",
            "optimal_rrr",
        ]:
            from testing.position_sizing import PositionSizer, suggest_improvements

            sizer = PositionSizer(
                strategy=self.sizing_mode,
                max_position_pct=self.max_position_pct,
                max_position_size=self.max_position_size,
                risk_per_trade=self.risk_pct,
            )

            # Mettre à jour les stats avec l'historique des trades
            for trade in self.state.closed_trades:
                sizer.update_stats(trade.pnl, trade.predicted_return)

            # Calculer le sizing
            confidence = (
                min(abs(predicted_return) / self.threshold, 2.0)
                if self.threshold > 0
                else 1.0
            )
            result = sizer.calculate(
                portfolio_value=current_total,
                current_price=0,  # Pas utilisé dans les calculs actuels
                predicted_return=predicted_return,
                atr_value=atr_value,
                confidence=confidence,
            )

            return result.position_size, result.stop_loss_pct, result.take_profit_pct

        # Modes legacy
        if self.sizing_mode == "fixed":
            slot = self._rebalance_base / self.prediction_horizon
        elif self.sizing_mode == "periodic":
            slot = self._rebalance_base / self.prediction_horizon
        else:  # "dynamic" — ancien comportement
            slot = current_total / self.prediction_horizon

        # Cap : max % du portefeuille
        if self.max_position_pct is not None:
            slot = min(slot, current_total * self.max_position_pct)

        # Cap : max absolu
        if self.max_position_size is not None:
            slot = min(slot, self.max_position_size)

        # SL/TP legacy
        sl_pct = self.risk_pct * 100
        tp_pct = sl_pct * self.rrr

        return max(slot, 0.0), sl_pct, tp_pct

    def _update_drawdown(self, portfolio_value: float):
        """Met à jour le high-water mark et active le circuit breaker si nécessaire."""
        self._peak_value = max(self._peak_value, portfolio_value)
        if self._peak_value > 0:
            drawdown = (self._peak_value - portfolio_value) / self._peak_value
        else:
            drawdown = 0.0

        if not self._circuit_breaker_active and drawdown >= self.max_drawdown_pct:
            self._circuit_breaker_active = True
            console.print(
                f"\n[bold red]⚠ CIRCUIT BREAKER[/] Drawdown {drawdown:.1%} >= "
                f"seuil {self.max_drawdown_pct:.0%}. Nouvelles positions bloquées."
            )

    def _check_rebalance(self):
        """Rebalance la base de capital en mode 'periodic' après N trades fermés."""
        if self.sizing_mode != "periodic":
            return
        self._trades_since_rebalance += 1
        if self._trades_since_rebalance >= self.rebalance_interval:
            old_base = self._rebalance_base
            self._rebalance_base = self.state.capital + self.state.allocated
            self._trades_since_rebalance = 0
            console.print(
                f"  [bold cyan]REBALANCE[/] Base capital: "
                f"${old_base:,.2f} → ${self._rebalance_base:,.2f}"
            )

    def _open_new_position(
        self,
        direction: str,
        entry_price: float,
        prediction: float,
        entry_date: Optional[datetime] = None,
    ):
        """Ouvre une nouvelle position avec guards de risk management."""
        # Guard 1 : Circuit breaker
        if self._circuit_breaker_active:
            return

        # Guard 2 : Limite journalière
        trade_day = (entry_date or datetime.now(timezone.utc)).date()
        if trade_day != self._current_trade_day:
            self._current_trade_day = trade_day
            self._daily_trade_count = 0
        if self._daily_trade_count >= self.max_trades_per_day:
            console.print(
                f"  [dim]SKIP — Limite journalière atteinte ({self.max_trades_per_day})[/]"
            )
            return

        # Guard 3 : Cooldown
        if self._last_entry_time is not None and entry_date is not None:
            bars_since = (entry_date - self._last_entry_time).total_seconds() / (
                self.minutes_per_bar * 60
            )
            if bars_since < self.cooldown_bars:
                return

        # Guard 4 : Max positions simultanées
        if len(self.state.open_positions) >= self.prediction_horizon:
            console.print(
                f"  [dim]SKIP — Max positions atteint ({self.prediction_horizon})[/]"
            )
            return

        # Appliquer le slippage à l'entrée
        if direction == "LONG":
            entry_price = entry_price * (1 + self.slippage_pct)
        else:
            entry_price = entry_price * (1 - self.slippage_pct)

        # Calculer la taille de position et les niveaux SL/TP
        slot_capital, sl_pct, tp_pct = self._calculate_slot_capital(prediction)

        # Ajuster RRR si on utilise les nouveaux modes
        if self.sizing_mode in [
            "kelly",
            "atr_risk",
            "confidence_weighted",
            "optimal_rrr",
        ]:
            rrr = tp_pct / sl_pct if sl_pct > 0 else self.rrr
            risk_pct = sl_pct / 100
        else:
            rrr = self.rrr
            risk_pct = self.risk_pct

        position = open_position(
            self.state,
            direction,
            entry_price,
            prediction,
            rrr,
            risk_pct,
            self.entry_fee_pct,
            slot_capital,
            entry_date,
        )

        if position:
            self.state.open_positions.append(position)
            self._last_entry_time = entry_date or datetime.now(timezone.utc)
            self._daily_trade_count += 1
            self._save_state()

            qty = position.allocated_capital / entry_price
            pred_style = "green" if prediction > 0 else "red"
            open_text = (
                f"  {direction}  Entry: ${entry_price:,.2f}\n"
                f"  Size: ${position.allocated_capital:,.2f}  ({qty:,.4f} {self.symbol.replace('/USDT', '')})\n"
                f"  Pred: [{pred_style}]{prediction * 100:+.2f}%[/]  "
                f"SL: ${position.stop_loss:,.2f}  TP: ${position.take_profit:,.2f}"
            )
            console.print(
                Panel(
                    open_text,
                    title=f"[bold]OPEN #{position.position_id}[/]",
                    border_style="cyan",
                    width=50,
                )
            )
        else:
            console.print(f"  [dim]SKIP — Pas assez de cash[/]")

    def _wait_with_progress(self, seconds: float):
        """Affiche une barre de progression Rich pendant l'attente."""
        update_interval = 1

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Prochain check SL/TP"),
            BarColumn(bar_width=30),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("wait", total=seconds)
            elapsed = 0
            while elapsed < seconds and self.running:
                sleep_step = min(update_interval, seconds - elapsed)
                time.sleep(sleep_step)
                elapsed += sleep_step
                progress.update(task, completed=elapsed)

    def _is_candle_complete(self, candle_time) -> bool:
        """Vérifie si la bougie précédente est clôturée.

        Quand une nouvelle bougie timestamp apparaît dans les données Binance,
        la bougie précédente est fermée. On attend juste 5% du timeframe (≥1 min)
        comme marge de sécurité pour laisser Binance finaliser les données.

        Ex : timeframe 1h → nouvelle bougie à 15:00 → on traite dès 15:03.
        """
        now = datetime.now(timezone.utc)
        candle_dt = (
            candle_time.to_pydatetime()
            if hasattr(candle_time, "to_pydatetime")
            else candle_time
        )
        if candle_dt.tzinfo is None:
            candle_dt = candle_dt.replace(tzinfo=timezone.utc)
        age = now - candle_dt
        min_age = timedelta(minutes=max(1, self.minutes_per_bar * 0.05))
        return age >= min_age

    def run(self):
        """Boucle principale.

        Deux fréquences distinctes :
        - Toutes les SLTP_POLL_SECONDS (5 min) : fetch prix + check SL/TP.
        - À chaque nouvelle bougie clôturée (~1h pour 1h TF) : prédiction + signal.
        - Affichage du statut portefeuille toutes les bars (1h).

        Arrêt automatique après MAX_CONSECUTIVE_ERRORS erreurs API.
        """
        self.running = True
        consecutive_errors = 0
        last_status_time = datetime.now(timezone.utc)

        try:
            while self.running:
                current_time = datetime.now(timezone.utc)

                try:
                    # Fetch le prix courant (quelques bougies récentes suffisent)
                    df_latest = fetch_latest_ohlcv(
                        self.symbol,
                        limit=5,
                        exchange=self.exchange,
                        timeframe=self.timeframe,
                    )
                    current_price = df_latest["close"].iloc[-1]
                    consecutive_errors = 0

                    # 1. Toujours : monitorer SL/TP (toutes les 5 min)
                    if self.state.open_positions:
                        self._check_and_close_positions(current_price, current_time)

                    # 2. Détecter une nouvelle bougie clôturée
                    latest_time = df_latest.index[-1]
                    if latest_time > self.last_candle_time:
                        if self._is_candle_complete(latest_time):
                            # Nouvelle bougie confirmée → signal
                            self.last_candle_time = latest_time
                            self.process_new_candle(current_price, latest_time)
                            print_status(
                                self.state,
                                current_price,
                                self.symbol,
                                self.initial_capital,
                            )
                            last_status_time = current_time
                        else:
                            console.print(
                                f"[dim][{current_time.strftime('%H:%M')}] "
                                f"Nouvelle bougie {latest_time} en attente de confirmation...[/]"
                            )
                    else:
                        # Afficher le statut au rythme d'une barre (pas toutes les 5 min)
                        secs_since_status = (
                            current_time - last_status_time
                        ).total_seconds()
                        if secs_since_status >= self.minutes_per_bar * 60:
                            print_status(
                                self.state,
                                current_price,
                                self.symbol,
                                self.initial_capital,
                            )
                            last_status_time = current_time
                        else:
                            console.print(
                                f"[dim][{current_time.strftime('%H:%M')}] "
                                f"Prix: ${current_price:,.2f}  "
                                f"| Prochaine bougie: {self.last_candle_time}  "
                                f"| Positions: {len(self.state.open_positions)}[/]"
                            )

                except Exception as e:
                    consecutive_errors += 1
                    console.print(f"[bold red]ERROR[/] {current_time}: {e}")
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        console.print(
                            f"  [bold red]FATAL[/] {MAX_CONSECUTIVE_ERRORS} erreurs consécutives "
                            f"— arrêt du système."
                        )
                        break

                # Attendre 5 min avant le prochain check SL/TP
                self._wait_with_progress(SLTP_POLL_SECONDS)

        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]STOP[/] Interruption détectée (Ctrl+C)")
            self.shutdown()

    def shutdown(self):
        """Arrêt gracieux du système."""
        self.running = False

        # Afficher le résumé final
        print_summary(self.state, self.initial_capital)

        # Fermer les positions ouvertes au prix courant (simulation)
        if self.state.open_positions:
            console.print(
                f"\n[bold yellow]WARNING[/] {len(self.state.open_positions)} positions encore ouvertes:"
            )
            for pos in self.state.open_positions:
                console.print(
                    f"   [bold]#{pos.position_id}[/] {pos.direction} | Entry: ${pos.entry_price:,.2f}"
                )

        console.print("\n[bold]SHUTDOWN[/] Système arrêté.")

    def run_backtest_mode(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        speed: float = 0,
    ):
        """
        Mode backtest - simule le temps réel sur des données historiques.

        Args:
            start_date: Date de début (format: YYYY-MM-DD). Si None, utilise les 3 derniers mois.
            end_date: Date de fin (format: YYYY-MM-DD). Si None, utilise aujourd'hui.
            speed: Délai entre chaque bougie en secondes (0 = instantané)
        """
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold cyan")
        table.add_column()
        table.add_row("Symbol", self.symbol)
        table.add_row("Model", self.model_type.upper())
        table.add_row("Capital", f"${self.initial_capital:,.2f}")
        table.add_row("RRR", f"1:{self.rrr}")
        table.add_row("Horizon", f"{self.prediction_horizon} bars [{self.timeframe}]")
        table.add_row("Threshold", f"{self.threshold * 100:.2f}%")
        table.add_row(
            "SL / TP",
            f"{self.risk_pct * 100:.2f}% / {self.risk_pct * self.rrr * 100:.2f}%",
        )
        table.add_row("Sizing", self.sizing_mode)
        table.add_row("Max DD", f"{self.max_drawdown_pct:.0%}")
        table.add_row("Cooldown", f"{self.cooldown_bars} bars")
        table.add_row("Max/Day", str(self.max_trades_per_day))
        console.print(
            Panel(
                table, title="BACKTEST MODE (Realtime Simulation)", border_style="cyan"
            )
        )

        # Device
        self.device = torch.device("mps" if torch.mps.is_available() else "cpu")
        console.print(f"[bold]INIT[/] Device: {self.device}")

        # Charger modèle et scalers
        console.print(
            f"[bold]INIT[/] Chargement du modèle {self.model_type} [{self.timeframe}]..."
        )
        self.model, _ = load_model_dynamic(
            self.model_type, self.device, timeframe=self.timeframe
        )
        self.scalers = load_scalers(self.model_type, timeframe=self.timeframe)
        self.feature_scaler = self.scalers["feature_scaler"]
        self.target_scaler = self.scalers["target_scaler"]
        self.clip_bounds = self.scalers.get("clip_bounds")
        if self.clip_bounds is not None:
            console.print("  [green]✓[/] Modèle, scalers et clip_bounds chargés")
        else:
            console.print(
                "  [yellow]✓[/] Modèle et scalers chargés [dim](clip_bounds absent, re-entraîner le modèle)[/]"
            )

        # Verrouiller short (spot Binance ne supporte pas le short)
        if self.allow_short:
            console.print(
                "  [bold yellow]WARNING[/] Short selling non supporté en spot Binance. Désactivé."
            )
            self.allow_short = False

        # Charger les données historiques depuis le CSV local
        console.print(
            f"[bold]INIT[/] Chargement des données historiques {self.symbol}..."
        )
        symbol_code = self.symbol.replace("/USDT", "").replace("/USD", "")
        df_full = load_symbol(symbol_code, timeframe=self.timeframe)

        # Filtrer par dates si spécifié
        if start_date:
            df_full = df_full[df_full.index >= start_date]
        if end_date:
            df_full = df_full[df_full.index <= end_date]

        # S'assurer qu'on a assez d'historique pour les features
        min_required = self.window_size + 100
        if len(df_full) < min_required:
            raise ValueError(
                f"Pas assez de données: {len(df_full)} < {min_required} requis"
            )

        console.print(
            f"  [green]✓[/] {len(df_full)} bougies chargées ({df_full.index[0].date()} → {df_full.index[-1].date()})"
        )
        speed_str = "instantané" if speed == 0 else f"{speed}s par bougie"
        console.print(
            f"\n[bold]BACKTEST[/] Démarrage de la simulation...  Speed: {speed_str}\n"
        )

        # Simuler le passage du temps
        # Commencer à window_size + 50 pour avoir assez d'historique pour les features
        start_idx = self.window_size + 50

        self.running = True

        try:
            for i in range(start_idx, len(df_full)):
                if not self.running:
                    break

                # Simuler l'historique disponible à ce moment
                df_history = df_full.iloc[: i + 1].copy()
                current_time = df_history.index[-1]
                current_price = df_history["close"].iloc[-1]

                # Vérifier et fermer les positions
                self._check_and_close_positions(current_price, current_time)

                # Circuit breaker : stop trading si drawdown trop élevé
                if self._circuit_breaker_active:
                    continue

                # Calculer les features et prédire
                try:
                    X_scaled, _ = prepare_live_features(
                        df_history,
                        self.feature_scaler,
                        self.clip_bounds,
                        timeframe=self.timeframe,
                        window_size=self.window_size,
                    )
                    prediction = predict_return(
                        self.model, X_scaled, self.target_scaler, self.device
                    )
                except Exception as e:
                    console.print(
                        f"  [bold red]ERROR[/] Erreur prédiction à {current_time}: {e}"
                    )
                    continue

                # Générer le signal
                signal = None
                if prediction > self.threshold:
                    signal = "LONG"
                elif prediction < -self.threshold and self.allow_short:
                    signal = "SHORT"

                # Ouvrir une position si signal
                if signal:
                    self._open_new_position(
                        signal, current_price, prediction, current_time
                    )

                # Afficher le statut ~1x par jour calendaire (adapté au timeframe)
                bars_per_day = max(1, round(1440 / self.minutes_per_bar))
                if (i - start_idx) % bars_per_day == 0 or i == len(df_full) - 1:
                    print_status_backtest(
                        self.state,
                        current_price,
                        self.symbol,
                        current_time,
                        i - start_idx,
                        len(df_full) - start_idx,
                        self.initial_capital,
                    )

                # Petite pause si demandée
                if speed > 0:
                    time.sleep(speed)

            # Simulation terminée
            console.print("\n[bold green]BACKTEST[/] Simulation terminée!")
            self.shutdown()

        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]STOP[/] Interruption détectée (Ctrl+C)")
            self.shutdown()


# ----- CLI ----- #


def parse_args():
    """Parse les arguments CLI."""
    parser = argparse.ArgumentParser(
        description="Testing en temps réel avec données Binance"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="testing/config.json",
        help="Chemin vers le fichier de configuration",
    )
    parser.add_argument(
        "--symbol", type=str, default=None, help="Symbole à trader (ex: BTC/USDT)"
    )
    parser.add_argument(
        "--model", type=str, default=None, help="Type de modèle (cnn, lstm, gru)"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default=None,
        help=f"Timeframe du modèle (ex: 1d, 1h, 4h — défaut: {DEFAULT_TIMEFRAME})",
    )
    parser.add_argument("--capital", type=float, default=None, help="Capital initial")
    parser.add_argument(
        "--rrr", type=float, default=None, help="Risk/Reward Ratio (ex: 2.0 pour 1:2)"
    )
    parser.add_argument(
        "--risk",
        type=float,
        default=None,
        help="Pourcentage de risque par trade (ex: 0.025 pour 2.5%%)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Seuil de prédiction pour ouvrir une position",
    )
    parser.add_argument(
        "--allow-short", action="store_true", help="Autoriser les positions short"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Intervalle de vérification en heures",
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Mode backtest - simule sur données historiques locales",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Date de début pour le backtest (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Date de fin pour le backtest (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=0,
        help="Délai entre bougies en mode backtest (secondes, 0 = instantané)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignorer l'état sauvegardé et repartir à zéro",
    )
    # Risk management
    parser.add_argument(
        "--sizing-mode",
        type=str,
        default=None,
        choices=["fixed", "periodic", "dynamic"],
        help="Mode de sizing des positions (defaut: fixed)",
    )
    parser.add_argument(
        "--max-drawdown",
        type=float,
        default=None,
        help="Max drawdown avant circuit breaker (ex: 0.20 pour 20%%)",
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        default=None,
        help="Barres minimum entre deux ouvertures de position",
    )
    parser.add_argument(
        "--max-daily-trades",
        type=int,
        default=None,
        help="Nombre max de trades par jour",
    )
    parser.add_argument(
        "--max-position-pct",
        type=float,
        default=None,
        help="Max %% du portefeuille par position (ex: 0.25 pour 25%%)",
    )
    parser.add_argument(
        "--max-position-size",
        type=float,
        default=None,
        help="Max absolu en $ par position",
    )
    return parser.parse_args()


def main():
    """Point d'entrée principal."""
    args = parse_args()

    # Charger la config
    config = load_config(args.config)

    # Override avec les arguments CLI
    if args.symbol:
        config["symbol"] = args.symbol
    if args.model:
        config["model_type"] = args.model
    if args.timeframe:
        config["timeframe"] = args.timeframe
    if args.capital is not None:
        config["capital"] = args.capital
    if args.rrr is not None:
        config["rrr"] = args.rrr
    if args.risk is not None:
        config["risk_pct"] = args.risk
    if args.threshold is not None:
        config["threshold"] = args.threshold
    if args.allow_short:
        config["allow_short"] = True
    if args.interval is not None:
        config["check_interval_hours"] = args.interval
    # Risk management overrides
    if args.sizing_mode is not None:
        config["sizing_mode"] = args.sizing_mode
    if args.max_drawdown is not None:
        config["max_drawdown_pct"] = args.max_drawdown
    if args.cooldown is not None:
        config["cooldown_bars"] = args.cooldown
    if args.max_daily_trades is not None:
        config["max_trades_per_day"] = args.max_daily_trades
    if args.max_position_pct is not None:
        config["max_position_pct"] = args.max_position_pct
    if args.max_position_size is not None:
        config["max_position_size"] = args.max_position_size

    # Supprimer l'état sauvegardé si --fresh
    if args.fresh:
        symbol_code = config["symbol"].replace("/", "_")
        state_path = f"testing/state_{symbol_code}.json"
        if os.path.exists(state_path):
            os.remove(state_path)
            console.print(f"[bold cyan]FRESH[/] État supprimé: {state_path}")

    # Lancer le système
    tester = RealtimeTester(config)

    if args.backtest:
        # Mode backtest sur données historiques
        tester.run_backtest_mode(
            start_date=args.start_date, end_date=args.end_date, speed=args.speed
        )
    else:
        # Mode temps réel
        tester.initialize()
        tester.run()


if __name__ == "__main__":
    main()
