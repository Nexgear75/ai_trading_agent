"""
Module de testing en temps réel avec données Binance live.

Simule une stratégie de trading sur des données temps réel,
avec gestion des positions, stop-loss et take-profit basés sur RRR.

================================================================================
EXEMPLES D'UTILISATION
================================================================================

MODE TEMPS RÉEL (LIVE):
-----------------------

1) Mode live basique:
   python -m testing.realtime_testing --symbol BTC/USDT --model cnn --capital 10000

2) Mode live avec fichier de configuration:
   python -m testing.realtime_testing --config testing/config.json

3) Mode live avec paramètres de trading personnalisés:
   python -m testing.realtime_testing --symbol BTC/USDT --model cnn --capital 5000 --threshold 0.015 --rrr 2.5 --risk 0.02

4) Mode live avec risk management avancé:
   python -m testing.realtime_testing --symbol BTC/USDT --model cnn --capital 10000 --sizing-mode dynamic --max-drawdown 0.15 --cooldown 5 --max-daily-trades 3

5) Mode live repartir à zéro (ignorer l'état sauvegardé):
   python -m testing.realtime_testing --symbol BTC/USDT --model cnn --fresh

MODE BACKTEST (SIMULATION):
---------------------------

6) Backtest basique sur historique:
   python -m testing.realtime_testing --backtest --symbol BTC --model cnn

7) Backtest sur période spécifique:
   python -m testing.realtime_testing --backtest --symbol BTC --model cnn --start-date 2024-01-01 --end-date 2024-06-30

8) Backtest avec visualisation lente (pour présentation):
   python -m testing.realtime_testing --backtest --symbol BTC --model cnn --speed 0.1

9) Backtest rapide (instantané):
   python -m testing.realtime_testing --backtest --symbol BTC --model cnn --speed 0

================================================================================
OPTIONS DISPONIBLES
================================================================================

OPTIONS GÉNÉRALES:
------------------

--config                    Chemin vers un fichier JSON de configuration.
                            Les options CLI écrasent celles du fichier config.
                            (défaut: testing/config.json)

--symbol                    Paire de trading (ex: BTC/USDT, ETH/USDT).
                            Format: CRYPTO/USDT ou CRYPTO/USD

--model                     Type de modèle ML: cnn, lstm, gru, bilstm, xgboost
                            Doit avoir été entraîné au préalable sur le même timeframe

--timeframe                 Timeframe des bougies: 1d, 1h, 4h, 15m (défaut: 1d)
                            Doit correspondre au timeframe d'entraînement du modèle

--capital                   Capital initial en USD (défaut: 1000)

--threshold                 Seuil de prédiction pour ouvrir une position (défaut: auto).
                            Valeurs typiques:
                            - 1d (daily): 0.01 (1%)
                            - 1h (hourly): 0.005 (0.5%)
                            - 4h: 0.008 (0.8%)
                            Une prédiction > threshold → LONG, < -threshold → SHORT

--allow-short               Autorise les positions SHORT (non supporté en spot Binance live,
                            uniquement en mode backtest/simulation)

--interval                  Intervalle de vérification en heures (défaut: auto)
                            Auto = 1 barre = timeframe en heures (ex: 24h pour 1d)

OPTIONS DE RISK MANAGEMENT (RRR):
---------------------------------

--rrr                       Risk/Reward Ratio (défaut: 2.0 pour 1:2)
                            Ex: 1.5 pour 1:1.5, 3.0 pour 1:3
                            Plus élevé = TP plus loin, moins de trades gagnants mais plus gros

--risk                      Pourcentage de risque par trade (défaut: auto)
                            Valeurs typiques:
                            - 1d: 0.025 (2.5%)
                            - 1h: 0.015 (1.5%)
                            Détermine la distance du SL: SL = entry * (1 ± risk)

OPTIONS DE RISK MANAGEMENT AVANCÉ:
----------------------------------

--sizing-mode               Mode de sizing des positions:
                            - fixed: Capital fixe par position (défaut)
                            - periodic: Rebalance périodique du capital de base
                            - dynamic: Pourcentage dynamique du portefeuille

--max-drawdown              Circuit breaker: drawdown max avant arrêt (défaut: 0.20 = 20%)
                            Quand atteint, plus aucune nouvelle position n'est ouverte

--cooldown                  Nombre minimum de barres entre deux ouvertures (défaut: 3)
                            Évite le sur-trading dans les marchés range

--max-daily-trades          Nombre maximum de trades par jour (défaut: 4)
                            Protection contre les séries de pertes

--max-position-pct          Pourcentage max du portefeuille par position (défaut: 0.25 = 25%)
                            Uniquement en mode sizing-mode=dynamic

--max-position-size         Taille max absolue en $ par position (optionnel)

OPTIONS MODE BACKTEST:
----------------------

--backtest                  Active le mode backtest sur données historiques locales

--start-date                Date de début du backtest (YYYY-MM-DD)
                            Si non spécifié, utilise les 3 derniers mois d'historique

--end-date                  Date de fin du backtest (YYYY-MM-DD)
                            Si non spécifié, utilise aujourd'hui

--speed                     Délai entre bougies en secondes (défaut: 0 = instantané)
                            - 0: Exécution rapide (min 25ms pour affichage dashboard)
                            - 0.1: Présentation (100ms par bougie, ~2min pour 1 an)
                            Plus élevé = plus lent, permet de visualiser le trading

--fresh                     Ignore l'état sauvegardé et repart de zéro
                            Utile pour refaire un backtest propre

================================================================================
FICHIER DE CONFIGURATION (config.json)
================================================================================

Exemple de fichier testing/config.json:

{
  "symbol": "BTC/USDT",
  "model_type": "cnn",
  "timeframe": "1d",
  "capital": 10000.0,
  "threshold": 0.01,
  "allow_short": false,
  "rrr": 2.0,
  "risk_pct": 0.025,
  "check_interval_hours": null,
  "entry_fee_pct": 0.001,
  "exit_fee_pct": 0.001,
  "slippage_pct": 0.001,
  "log_level": "INFO",
  "sizing_mode": "dynamic",
  "max_position_pct": 0.25,
  "max_position_size": null,
  "rebalance_interval": 50,
  "max_drawdown_pct": 0.20,
  "cooldown_bars": 3,
  "max_trades_per_day": 4,
  "max_expiration_rate": 0.50
}

================================================================================
EXEMPLES DE SCÉNARIOS
================================================================================

# SCÉNARIO 1: Trading live conservateur sur BTC (recommandé pour débuter)
# - Capital: 5000$
# - Seuil élevé (1.5%) pour éviter les faux signaux
# - RRR 1:2, risque 2% par trade
# - Max 3 trades/jour, cooldown de 5 barres
# - Circuit breaker à 15% de drawdown
python -m testing.realtime_testing \
  --symbol BTC/USDT \
  --model cnn \
  --capital 5000 \
  --threshold 0.015 \
  --rrr 2.0 \
  --risk 0.02 \
  --max-daily-trades 3 \
  --cooldown 5 \
  --max-drawdown 0.15

# SCÉNARIO 2: Trading live agressif avec sizing dynamique
# - Sizing dynamique: 25% du portefeuille par position
# - Plus de trades journaliers (6)
# - Seuil plus bas (0.8%)
python -m testing.realtime_testing \
  --symbol BTC/USDT \
  --model cnn \
  --capital 10000 \
  --threshold 0.008 \
  --sizing-mode dynamic \
  --max-position-pct 0.25 \
  --max-daily-trades 6 \
  --cooldown 2

# SCÉNARIO 3: Backtest rapide pour valider une stratégie
# - Période: Janvier à Juin 2024
# - Exécution instantanée
# - Affiche le dashboard avec les métriques en temps réel
python -m testing.realtime_testing \
  --backtest \
  --symbol BTC \
  --model cnn \
  --start-date 2024-01-01 \
  --end-date 2024-06-30 \
  --speed 0

# SCÉNARIO 4: Backtest visuel pour présentation/démo
# - Vitesse lente (0.1s par bougie)
# - Permet de visualiser chaque décision de trading
# - ~1min30 de démo pour 1 an de données (1d)
python -m testing.realtime_testing \
  --backtest \
  --symbol BTC \
  --model cnn \
  --start-date 2023-01-01 \
  --end-date 2023-12-31 \
  --speed 0.1

# SCÉNARIO 5: Reprise d'un trading live après arrêt
# - Le système sauvegarde automatiquement l'état dans testing/state_<symbol>.json
# - Relance simple reprend où ça s'est arrêté
python -m testing.realtime_testing \
  --symbol BTC/USDT \
  --model cnn \
  --capital 10000

# SCÉNARIO 6: Reset complet et nouveau départ
# --fresh supprime le fichier d'état sauvegardé
python -m testing.realtime_testing \
  --symbol BTC/USDT \
  --model cnn \
  --capital 10000 \
  --fresh

# SCÉNARIO 7: Trading sur timeframe court (1h) - Day trading
# - Utilise un modèle entraîné sur 1h
# - Seuil adapté à la volatilité intraday
python -m testing.realtime_testing \
  --symbol BTC/USDT \
  --model cnn \
  --timeframe 1h \
  --capital 5000 \
  --threshold 0.005 \
  --risk 0.015 \
  --max-daily-trades 8

# SCÉNARIO 8: Comparaison de modèles via backtest
# Test CNN:
python -m testing.realtime_testing --backtest --symbol BTC --model cnn --start-date 2024-01-01 --end-date 2024-06-30
# Test LSTM:
python -m testing.realtime_testing --backtest --symbol BTC --model lstm --start-date 2024-01-01 --end-date 2024-06-30
# Test BiLSTM:
python -m testing.realtime_testing --backtest --symbol BTC --model bilstm --start-date 2024-01-01 --end-date 2024-06-30

# SCÉNARIO 9: Test avec frais réalistes Binance
# - Entry fee: 0.1% (spot standard)
# - Slippage: 0.1% (estimation réaliste)
python -m testing.realtime_testing \
  --backtest \
  --symbol BTC \
  --model cnn \
  --capital 10000 \
  --threshold 0.012

# SCÉNARIO 10: Risk management très conservateur
# - Circuit breaker bas (10%)
# - Sizing fixe et faible
# - Cooldown long (10 barres)
python -m testing.realtime_testing \
  --symbol BTC/USDT \
  --model cnn \
  --capital 10000 \
  --sizing-mode fixed \
  --max-drawdown 0.10 \
  --cooldown 10 \
  --max-daily-trades 2

================================================================================
AFFICHAGE EN TEMPS RÉEL (DASHBOARD)
================================================================================

Le dashboard affiche en temps réel:
- Status WebSocket (ONLINE/RECONNECTING/OFFLINE)
- Prix courant et uptime
- Valeur du portefeuille
- PnL total (réalisé + non réalisé)
- Win rate
- Nombre de trades (gagnants/perdants/ouverts)
- Positions ouvertes avec:
  * Direction (LONG/SHORT)
  * Prix d'entrée et prix courant
  * PnL non réalisé
  * Stop-loss et Take-profit
  * Prédiction du modèle

Event log (40 derniers événements):
- NEW CANDLE: Nouvelle bougie détectée
- PREDICTION: Prédiction du modèle
- OPEN #X: Nouvelle position ouverte
- CLOSE #X TP/SL/EXPIRATION: Position fermée avec raison et PnL
- CIRCUIT BREAKER: Activation du circuit breaker
- REBALANCE: Rebalance du capital (mode periodic)

Commandes durant l'exécution:
- Ctrl+C: Arrêt gracieux du système

================================================================================
FICHIERS GÉNÉRÉS
================================================================================

- testing/state_<symbol>.json: État persistant (positions, trades, capital)
- testing/config.json: Configuration par défaut

================================================================================
"""

import argparse
import asyncio
import json
import os
import queue
import threading
import time
import urllib.request
import urllib.parse
from collections import deque

# Tentative de chargement des variables d'environnement depuis .env
def load_env_file(path=".env"):
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

load_env_file()
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import ccxt
import joblib
import numpy as np
import pandas as pd
import torch
import websockets
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
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


# ----- Connection / streaming ----- #


class ConnStatus(Enum):
    ONLINE = "ONLINE"
    RECONNECTING = "RECONNECTING"
    OFFLINE = "OFFLINE"


@dataclass
class ConnectionState:
    """État de la connexion WebSocket partagé entre le thread stream et le main loop."""

    status: ConnStatus = ConnStatus.OFFLINE
    last_kline_ts: Optional[datetime] = None
    current_price: Optional[float] = None
    reconnect_attempts: int = 0
    connected_since: Optional[datetime] = None
    next_retry_in: float = 0.0
    last_error: Optional[str] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def update(self, **kwargs) -> None:
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "status": self.status,
                "last_kline_ts": self.last_kline_ts,
                "current_price": self.current_price,
                "reconnect_attempts": self.reconnect_attempts,
                "connected_since": self.connected_since,
                "next_retry_in": self.next_retry_in,
                "last_error": self.last_error,
            }


@dataclass
class KlineEvent:
    """Événement de bougie clôturée reçu depuis la WebSocket."""

    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class ReconnectEvent:
    """Sentinelle envoyée après une reconnexion réussie pour déclencher un refetch REST."""

    attempts: int


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
        "sizing_mode": "dynamic",  # "fixed", "periodic", "dynamic"
        "max_position_pct": 0.25,  # 25% du portefeuille par position (mode dynamic)
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


# ----- WebSocket stream ----- #


BINANCE_WS_URL = "wss://stream.binance.com:443/ws"


class BinanceKlineStream:
    """WebSocket Binance kline stream running in a background asyncio thread.

    Expose une queue thread-safe produisant :
      - `KlineEvent` à chaque bougie clôturée (k.x == true).
      - `ReconnectEvent` à chaque reconnexion réussie (pour refetch REST).
    Met à jour `ConnectionState` (current_price, status, reconnect_attempts) sous lock.
    Reconnexion infinie avec backoff exponentiel (1→60s).
    """

    def __init__(self, symbol: str, timeframe: str, conn_state: ConnectionState):
        self.symbol = symbol
        self.timeframe = timeframe
        self.conn_state = conn_state
        self.queue: "queue.Queue[object]" = queue.Queue(maxsize=100)

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        symbol_ws = symbol.replace("/", "").lower()
        self.url = f"{BINANCE_WS_URL}/{symbol_ws}@kline_{timeframe}"

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_in_thread, daemon=True, name="binance-ws"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(lambda: None)
        if self._thread is not None:
            self._thread.join(timeout=3.0)

    def _run_in_thread(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._consume_forever())
        finally:
            self._loop.close()

    async def _consume_forever(self) -> None:
        attempts = 0
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(
                    self.url,
                    ping_interval=180,
                    ping_timeout=600,
                    close_timeout=5,
                    open_timeout=10,
                ) as ws:
                    attempts = 0
                    self.conn_state.update(
                        status=ConnStatus.ONLINE,
                        connected_since=datetime.now(timezone.utc),
                        reconnect_attempts=0,
                        next_retry_in=0.0,
                        last_error=None,
                    )
                    # Signal reconnect (useful even for the first connect : triggers initial refetch
                    # only on re-opens; the main loop can choose to ignore the first one if needed)
                    try:
                        self.queue.put_nowait(ReconnectEvent(attempts=0))
                    except queue.Full:
                        pass

                    async for raw in ws:
                        if self._stop_event.is_set():
                            break
                        self._handle_message(raw)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.conn_state.update(last_error=f"{type(exc).__name__}: {exc}"[:200])

            if self._stop_event.is_set():
                break

            attempts += 1
            delay = min(60.0, 2 ** min(attempts - 1, 6))
            self.conn_state.update(
                status=ConnStatus.RECONNECTING,
                reconnect_attempts=attempts,
                next_retry_in=delay,
                connected_since=None,
            )
            # Sleep en petits slices pour pouvoir s'arrêter rapidement
            slept = 0.0
            while slept < delay and not self._stop_event.is_set():
                step = min(0.5, delay - slept)
                await asyncio.sleep(step)
                slept += step
                self.conn_state.update(next_retry_in=max(0.0, delay - slept))

        self.conn_state.update(status=ConnStatus.OFFLINE, next_retry_in=0.0)

    def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except (ValueError, TypeError):
            return
        k = msg.get("k")
        if not isinstance(k, dict):
            return

        try:
            close = float(k["c"])
            open_ = float(k["o"])
            high = float(k["h"])
            low = float(k["l"])
            volume = float(k["v"])
            open_ts_ms = int(k["t"])
            is_closed = bool(k["x"])
        except (KeyError, TypeError, ValueError):
            return

        ts = datetime.fromtimestamp(open_ts_ms / 1000, tz=timezone.utc).replace(
            tzinfo=None
        )
        self.conn_state.update(current_price=close, last_kline_ts=ts)

        if is_closed:
            event = KlineEvent(
                ts=ts, open=open_, high=high, low=low, close=close, volume=volume
            )
            try:
                self.queue.put_nowait(event)
            except queue.Full:
                # Main loop en retard — on drop le plus ancien pour garder le plus récent.
                try:
                    self.queue.get_nowait()
                    self.queue.put_nowait(event)
                except queue.Empty:
                    pass


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


# ----- Live dashboard ----- #


class DashboardView:
    """Rich Live dashboard : status bar + portfolio body + rolling event log.

    Le layout est redrawé ~2 fois/seconde par `Live`. Les events (nouvelles bougies,
    ouvertures / fermetures de position, prédictions, warnings) sont poussés via
    `log()` pour apparaître dans le panel du bas — `console.print()` direct est à
    proscrire pendant le rendu Live.
    """

    LOG_CAPACITY = 40

    def __init__(self, initial_log: Optional[list[str]] = None):
        self._log_lock = threading.Lock()
        self._log: deque[str] = deque(maxlen=self.LOG_CAPACITY)
        if initial_log:
            for line in initial_log:
                self._log.append(line)

        self.layout = Layout()
        self.layout.split_column(
            Layout(name="status", size=3),
            Layout(name="body", ratio=2),
            Layout(name="log", ratio=3),
        )

    def log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        with self._log_lock:
            self._log.append(f"[dim]{ts}[/] {message}")

    def _render_status_bar(self, conn: ConnectionState, symbol: str) -> Panel:
        snap = conn.snapshot()
        status = snap["status"]

        if status == ConnStatus.ONLINE:
            dot = Text("●", style="bold green")
            label = Text(" ONLINE", style="bold green")
            border = "green"
        elif status == ConnStatus.RECONNECTING:
            dot = Text("●", style="bold yellow")
            retry = snap["next_retry_in"]
            attempts = snap["reconnect_attempts"]
            label = Text(
                f" RECONNECTING  attempt {attempts}  retry in {retry:.0f}s",
                style="bold yellow",
            )
            border = "yellow"
        else:
            dot = Text("●", style="bold red")
            label = Text(" OFFLINE", style="bold red")
            border = "red"

        price = snap["current_price"]
        price_txt = f"${price:,.2f}" if price is not None else "—"

        last_ts = snap["last_kline_ts"]
        if last_ts is not None:
            age = (
                datetime.now(timezone.utc).replace(tzinfo=None) - last_ts
            ).total_seconds()
            age_txt = f"{age:.0f}s ago" if age < 120 else f"{age / 60:.0f}m ago"
        else:
            age_txt = "—"

        since = snap["connected_since"]
        if since is not None:
            uptime_sec = (datetime.now(timezone.utc) - since).total_seconds()
            if uptime_sec < 60:
                up_txt = f"{uptime_sec:.0f}s"
            elif uptime_sec < 3600:
                up_txt = f"{uptime_sec / 60:.0f}m"
            else:
                up_txt = f"{uptime_sec / 3600:.1f}h"
        else:
            up_txt = "—"

        line = Text()
        line.append_text(dot)
        line.append_text(label)
        line.append(f"   {symbol}  ", style="bold cyan")
        line.append(f"Price: {price_txt}  ", style="white")
        line.append(f"| Last kline: {age_txt}  ", style="dim")
        line.append(f"| Uptime: {up_txt}", style="dim")
        err = snap.get("last_error")
        if status == ConnStatus.RECONNECTING and err:
            line.append(f"  | {err}", style="red")
        return Panel(line, border_style=border, padding=(0, 1))

    def _render_body(
        self,
        state: RealtimeState,
        current_price: Optional[float],
        symbol: str,
        initial_capital: float,
    ) -> Panel:
        if current_price is None:
            return Panel(
                Text("En attente du premier tick WebSocket...", style="dim italic"),
                title="Portfolio",
                border_style="blue",
            )

        m = _calc_portfolio_metrics(state, current_price, initial_capital)

        table = Table(box=None, show_header=True, padding=(0, 2), expand=True)
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

        renderables: list = [table]

        if state.open_positions:
            pos_table = Table(
                title="Open positions",
                title_style="bold",
                show_header=True,
                box=None,
                padding=(0, 1),
                expand=True,
            )
            pos_table.add_column("#", style="bold")
            pos_table.add_column("Dir")
            pos_table.add_column("Entry", justify="right")
            pos_table.add_column("Now", justify="right")
            pos_table.add_column("PnL", justify="right")
            pos_table.add_column("SL / TP", justify="right", style="dim")
            pos_table.add_column("Pred", justify="right", style="dim")

            for pos in state.open_positions:
                if pos.direction == "LONG":
                    unrealized_pct = (current_price / pos.entry_price - 1) * 100
                else:
                    unrealized_pct = (pos.entry_price / current_price - 1) * 100
                unrealized_val = pos.allocated_capital * unrealized_pct / 100
                pnl_s = _pnl_color(unrealized_val)

                pos_table.add_row(
                    str(pos.position_id),
                    Text(
                        pos.direction,
                        style="green" if pos.direction == "LONG" else "red",
                    ),
                    f"${pos.entry_price:,.2f}",
                    f"${current_price:,.2f}",
                    Text(
                        f"${unrealized_val:+.2f} ({unrealized_pct:+.2f}%)", style=pnl_s
                    ),
                    f"${pos.stop_loss:,.2f} / ${pos.take_profit:,.2f}",
                    f"{pos.predicted_return * 100:+.2f}%",
                )
            renderables.append(pos_table)

        title = (
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  "
            f"{symbol}  Price: ${current_price:,.2f}"
        )
        return Panel(Group(*renderables), title=title, border_style="blue")

    def _render_log(self) -> Panel:
        with self._log_lock:
            lines = list(self._log)
        if not lines:
            content: Text | Group = Text("(no events yet)", style="dim italic")
        else:
            text = Text()
            for i, line in enumerate(lines):
                if i > 0:
                    text.append("\n")
                text.append_text(Text.from_markup(line))
            content = text
        return Panel(content, title="Event log", border_style="dim", padding=(0, 1))

    def refresh(
        self,
        state: RealtimeState,
        conn: ConnectionState,
        symbol: str,
        current_price: Optional[float],
        initial_capital: float,
    ) -> None:
        self.layout["status"].update(self._render_status_bar(conn, symbol))
        self.layout["body"].update(
            self._render_body(state, current_price, symbol, initial_capital)
        )
        self.layout["log"].update(self._render_log())


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
        self.sizing_mode = config.get("sizing_mode", "dynamic")
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

        # Streaming + dashboard (initialisés dans run()/initialize())
        self.conn_state = ConnectionState()
        self.stream: Optional[BinanceKlineStream] = None
        self.dashboard: Optional[DashboardView] = None

        # Chemin du fichier d'état persistant
        symbol_code = self.symbol.replace("/", "_")
        self.state_path = f"testing/state_{symbol_code}.json"

    def _log(self, message: str) -> None:
        """Log vers le dashboard si actif, sinon vers console directement."""
        if self.dashboard is not None:
            self.dashboard.log(message)
        else:
            console.print(message)

    def _notify(self, message: str) -> None:
        """Envoie une notification Telegram."""
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not token or not chat_id:
            return

        # Nettoyer les tags Rich [bold], [green], etc. pour Telegram (HTML)
        clean_msg = message.replace("[bold]", "<b>").replace("[/bold]", "</b>")
        clean_msg = clean_msg.replace("[green]", "<b>").replace("[/green]", "</b>")
        clean_msg = clean_msg.replace("[red]", "<b>").replace("[/red]", "</b>")
        clean_msg = clean_msg.replace("[cyan]", "<b>").replace("[/cyan]", "</b>")
        clean_msg = clean_msg.replace("[yellow]", "<b>").replace("[/yellow]", "</b>")
        clean_msg = clean_msg.replace("[dim]", "<i>").replace("[/dim]", "</i>")
        # Supprimer les tags restants
        import re
        clean_msg = re.sub(r"\[/?.*?\]", "", clean_msg)

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": clean_msg,
                "parse_mode": "HTML"
            }).encode()
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=5) as response:
                pass
        except Exception as e:
            # On log l'erreur sans notifier (pour éviter une boucle infinie)
            if self.dashboard is not None:
                self.dashboard.log(f"[red]Telegram Error:[/] {e}")
            else:
                print(f"Telegram Error: {e}")

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

        # Récupérer l'historique initial.
        # +110 = warmup pour les indicateurs techniques (rolling(100) dans
        # add_trend_features crée 99 NaN rows supprimés par dropna).
        self.df_history = fetch_initial_history(
            self.symbol,
            min_bars=self.window_size + 110,
            exchange=self.exchange,
            timeframe=self.timeframe,
        )
        if self.last_candle_time is None:
            # df_history.index[-1] = bougie en cours de formation (open_time courant).
            # Le WS émet KlineEvent(ts=open_time) quand cette bougie clôture, soit la
            # même valeur que index[-1] : le test `event.ts > last_candle_time` dans
            # run() filtrerait alors la première clôture et aucune prédiction ne serait
            # émise. On ancre last_candle_time sur la dernière bougie CLÔTURÉE.
            self.last_candle_time = (
                self.df_history.index[-2]
                if len(self.df_history) >= 2
                else self.df_history.index[-1]
            )
        console.print(f"  [green]✓[/] Dernière bougie clôturée: {self.last_candle_time}")

        check_h = self.check_interval / 3600
        console.print(f"\n[bold]INIT[/] Démarrage de la boucle principale...")
        self._notify(
            f"🤖 <b>AI Trading Agent Started</b>\n"
            f"📈 Symbol: {self.symbol}\n"
            f"💰 Capital: ${self.initial_capital:,.2f}\n"
            f"🕒 Timeframe: {self.timeframe}"
        )
        console.print(
            f"       Threshold: {self.threshold * 100:.2f}%  |  Intervalle: {check_h:.1f}h par bougie [{self.timeframe}]"
        )
        console.print("       Appuyez sur Ctrl+C pour arrêter\n")

        # Démarrer le stream WebSocket (live mode uniquement — pas en backtest)
        self.stream = BinanceKlineStream(
            symbol=self.symbol,
            timeframe=self.timeframe,
            conn_state=self.conn_state,
        )
        self.stream.start()
        console.print(
            f"  [green]✓[/] WebSocket stream démarré ([dim]{self.stream.url}[/])"
        )

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
        self._log(
            f"[bold cyan]NEW CANDLE[/] {candle_time} | Entry price: ${current_price:,.2f}"
        )

        # Re-fetch l'historique pour avoir les OHLCV finalisés des bougies clôturées.
        # +115 = window_size + warmup (rolling(100) crée 99 NaN) + 1 (bougie en
        # formation exclue) + 15 de marge.
        try:
            df_fresh = fetch_latest_ohlcv(
                self.symbol,
                limit=self.window_size + 115,
                exchange=self.exchange,
                timeframe=self.timeframe,
            )
            # Exclure la bougie en cours de formation (dernière entrée)
            df_closed = df_fresh.iloc[:-1]
            self.df_history = df_fresh  # mise à jour du cache complet
        except Exception as e:
            self._log(f"[yellow]WARN[/] Re-fetch échoué ({e}), utilisation du cache")
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
            self._log(
                f"[bold]PREDICTION[/] [{pred_style}]{prediction * 100:+.2f}%[/]  "
                f"[dim](seuil: ±{self.threshold * 100:.2f}%)[/]"
            )
        except Exception as e:
            self._log(f"[bold red]ERROR[/] Erreur prédiction: {e}")
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

            self._log(
                f"[bold][{reason_style}]CLOSE #{pos.position_id} {reason}[/][/]  "
                f"{pos.direction}  ${pos.entry_price:,.2f} → ${exit_price:,.2f}  "
                f"[{pnl_style}]${pnl:+.2f} ({pnl_pct:+.2f}%)[/]  "
                f"[dim]fees: ${trade.total_fees:.2f}[/]"
            )
            emoji = "✅" if pnl > 0 else "❌"
            self._notify(
                f"{emoji} <b>CLOSE #{pos.position_id} {reason}</b> on {self.symbol}\n"
                f"{pos.direction}: ${pos.entry_price:,.2f} → ${exit_price:,.2f}\n"
                f"💰 PnL: <b>${pnl:+.2f} ({pnl_pct:+.2f}%)</b>"
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
                    self._log(
                        f"[bold yellow]⚠ EXPIRATION RATE[/] {exp_rate:.0%} des trades expirent "
                        f"(seuil: {self.max_expiration_rate:.0%}). "
                        f"Considérez augmenter risk_pct ({self.risk_pct}) ou réduire RRR ({self.rrr})."
                    )

            self._save_state()

    # ----- Risk management methods ----- #

    def _calculate_slot_capital(self) -> float:
        """Calcule la taille de position selon le mode de sizing configuré."""
        current_total = self.state.capital + self.state.allocated

        if self.sizing_mode == "fixed":
            slot = self._rebalance_base / self.prediction_horizon
        elif self.sizing_mode == "periodic":
            slot = self._rebalance_base / self.prediction_horizon
        else:  # "dynamic" — % fixe du portfolio courant
            slot = current_total * self.max_position_pct

        # Cap : max % du portefeuille (appliqué aussi pour fixed/periodic)
        if self.max_position_pct is not None and self.sizing_mode != "dynamic":
            slot = min(slot, current_total * self.max_position_pct)

        # Cap : max absolu
        if self.max_position_size is not None:
            slot = min(slot, self.max_position_size)

        return max(slot, 0.0)

    def _update_drawdown(self, portfolio_value: float):
        """Met à jour le high-water mark et active le circuit breaker si nécessaire."""
        self._peak_value = max(self._peak_value, portfolio_value)
        if self._peak_value > 0:
            drawdown = (self._peak_value - portfolio_value) / self._peak_value
        else:
            drawdown = 0.0

        if not self._circuit_breaker_active and drawdown >= self.max_drawdown_pct:
            self._circuit_breaker_active = True
            msg = (
                f"[bold red]⚠ CIRCUIT BREAKER[/] Drawdown {drawdown:.1%} >= "
                f"seuil {self.max_drawdown_pct:.0%}. Nouvelles positions bloquées."
            )
            self._log(msg)
            self._notify(f"🛑 <b>CIRCUIT BREAKER ACTIVATED</b>\nDrawdown: {drawdown:.1%}\nSystem will stop opening new positions.")

    def _check_rebalance(self):
        """Rebalance la base de capital en mode 'periodic' après N trades fermés."""
        if self.sizing_mode != "periodic":
            return
        self._trades_since_rebalance += 1
        if self._trades_since_rebalance >= self.rebalance_interval:
            old_base = self._rebalance_base
            self._rebalance_base = self.state.capital + self.state.allocated
            self._trades_since_rebalance = 0
            self._log(
                f"[bold cyan]REBALANCE[/] Base capital: "
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
            self._log(
                f"[dim]SKIP — Limite journalière atteinte ({self.max_trades_per_day})[/]"
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
            self._log(
                f"[dim]SKIP — Max positions atteint ({self.prediction_horizon})[/]"
            )
            return

        # Appliquer le slippage à l'entrée
        if direction == "LONG":
            entry_price = entry_price * (1 + self.slippage_pct)
        else:
            entry_price = entry_price * (1 - self.slippage_pct)

        # Calculer la taille de position
        slot_capital = self._calculate_slot_capital()

        position = open_position(
            self.state,
            direction,
            entry_price,
            prediction,
            self.rrr,
            self.risk_pct,
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
            coin = self.symbol.replace("/USDT", "")
            self._log(
                f"[bold cyan]OPEN #{position.position_id}[/]  {direction}  "
                f"Entry: ${entry_price:,.2f}  "
                f"Size: ${position.allocated_capital:,.2f} ({qty:,.4f} {coin})  "
                f"Pred: [{pred_style}]{prediction * 100:+.2f}%[/]  "
                f"SL: ${position.stop_loss:,.2f}  TP: ${position.take_profit:,.2f}"
            )
            self._notify(
                f"🚀 <b>OPEN #{position.position_id}</b> {direction} on {self.symbol}\n"
                f"💰 Entry: ${entry_price:,.2f}\n"
                f"🛡️ SL: ${position.stop_loss:,.2f} | 🎯 TP: ${position.take_profit:,.2f}\n"
                f"📊 Prediction: {prediction * 100:+.2f}%"
            )
        else:
            self._log(f"[dim]SKIP — Pas assez de cash[/]")

    def _refetch_history_after_reconnect(self) -> None:
        """Après une reconnexion WS, refait un fetch REST pour combler les bougies manquées."""
        try:
            df_fresh = fetch_latest_ohlcv(
                self.symbol,
                limit=self.window_size + 115,
                exchange=self.exchange,
                timeframe=self.timeframe,
            )
        except Exception as exc:
            self._log(f"[yellow]WARN[/] Refetch post-reconnect échoué: {exc}")
            return

        self.df_history = df_fresh
        latest_closed_ts = (
            df_fresh.index[-2] if len(df_fresh) >= 2 else df_fresh.index[-1]
        )

        # Si une (ou plusieurs) bougie(s) ont été clôturées pendant l'offline, rattraper la dernière.
        if (
            self.last_candle_time is not None
            and latest_closed_ts > self.last_candle_time
        ):
            missed_close_price = float(df_fresh["close"].iloc[-2])
            self._log(
                f"[cyan]GAP FILL[/] bougie manquée {latest_closed_ts} → rattrapage"
            )
            self.last_candle_time = latest_closed_ts
            try:
                self.process_new_candle(missed_close_price, latest_closed_ts)
            except Exception as exc:
                self._log(
                    f"[red]ERROR[/] process_new_candle (gap fill) a échoué: {exc}"
                )

    def run(self):
        """Boucle principale event-driven, alimentée par la WebSocket Binance.

        - À chaque tick (prix courant dans `conn_state.current_price`) : check SL/TP.
        - À chaque bougie clôturée (`KlineEvent`) : prédiction + ouverture position.
        - À chaque reconnexion (`ReconnectEvent`) : refetch REST pour combler le gap.
        - Dashboard Rich `Live` rafraîchi ~2×/sec. Reconnexion infinie gérée par le stream.
        """
        self.running = True
        self.dashboard = DashboardView()
        self.dashboard.log("[green]System started[/] — waiting for first WS tick")

        # Premier tick hérité : si la WS a déjà un prix, pas besoin d'attendre
        first_reconnect_seen = False

        with Live(
            self.dashboard.layout,
            console=console,
            refresh_per_second=2,
            screen=False,
            transient=False,
        ):
            try:
                while self.running:
                    try:
                        event = self.stream.queue.get(timeout=1.0)
                    except queue.Empty:
                        event = None

                    snap = self.conn_state.snapshot()
                    current_price = snap["current_price"]
                    now_utc = datetime.now(timezone.utc)

                    if isinstance(event, ReconnectEvent):
                        if not first_reconnect_seen:
                            # Première connexion : pas besoin de refetch, l'init a déjà amorcé
                            first_reconnect_seen = True
                            self.dashboard.log(
                                "[green]WebSocket connected[/] — streaming klines"
                            )
                        else:
                            self.dashboard.log(
                                f"[cyan]Reconnected[/] (after {event.attempts} attempts) — "
                                f"refetching history via REST"
                            )
                            self._refetch_history_after_reconnect()
                    elif isinstance(event, KlineEvent):
                        # Bougie clôturée confirmée par le WS (k.x == true)
                        if (
                            self.last_candle_time is None
                            or event.ts > self.last_candle_time
                        ):
                            self.last_candle_time = event.ts
                            try:
                                self.process_new_candle(event.close, event.ts)
                            except Exception as exc:
                                self._log(
                                    f"[red]ERROR[/] process_new_candle a échoué: {exc}"
                                )

                    # Check SL/TP à chaque itération (réactivité ~1s)
                    if current_price is not None and self.state.open_positions:
                        try:
                            self._check_and_close_positions(current_price, now_utc)
                        except Exception as exc:
                            self._log(
                                f"[red]ERROR[/] _check_and_close_positions: {exc}"
                            )

                    # Refresh le dashboard (uptime/status evolue même sans event)
                    self.dashboard.refresh(
                        state=self.state,
                        conn=self.conn_state,
                        symbol=self.symbol,
                        current_price=current_price,
                        initial_capital=self.initial_capital,
                    )

            except KeyboardInterrupt:
                self.dashboard.log("[yellow]STOP[/] Interruption détectée (Ctrl+C)")

        # Hors du Live context : prints redeviennent directs
        self.shutdown()

    def shutdown(self):
        """Arrêt gracieux du système."""
        self.running = False

        # Stopper le stream WS
        if self.stream is not None:
            self.stream.stop()
            self.stream = None

        # Désactiver le routage dashboard (les prints finaux vont à la console)
        self.dashboard = None

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

        # Warm-up : la plus longue fenêtre de build_features est SMA(max(periods))
        # = SMA(100) dans le pipeline trend (1d et 1h). Tant qu'on n'a pas 100 barres
        # valides, dropna() supprime quasiment tout et prepare_live_features lève
        # ValueError. On démarre donc à window_size + INDICATOR_WARMUP pour que la
        # toute première itération produise déjà une fenêtre complète.
        INDICATOR_WARMUP = 100
        start_idx = self.window_size + INDICATOR_WARMUP

        # S'assurer qu'on a assez d'historique pour la 1ère fenêtre + ≥1 itération
        min_required = start_idx + 1
        if len(df_full) < min_required:
            raise ValueError(
                f"Pas assez de données: {len(df_full)} < {min_required} requis "
                f"(window_size={self.window_size} + warm-up indicateurs={INDICATOR_WARMUP} + 1 itération)"
            )

        console.print(
            f"  [green]✓[/] {len(df_full)} bougies chargées ({df_full.index[0].date()} → {df_full.index[-1].date()})"
        )

        # Initialiser le dashboard et simuler une connexion ONLINE
        self.dashboard = DashboardView(
            initial_log=[
                "[dim]BACKTEST MODE — Simulating live trading on historical data[/]",
                f"[dim]Period: {df_full.index[start_idx].date()} → {df_full.index[-1].date()}[/]",
            ]
        )
        self.conn_state.update(
            status=ConnStatus.ONLINE,
            connected_since=datetime.now(timezone.utc),
            reconnect_attempts=0,
            next_retry_in=0.0,
            last_error=None,
        )

        speed_str = "instantané" if speed == 0 else f"{speed}s par bougie"
        console.print(
            f"\n[bold]BACKTEST[/] Démarrage de la simulation...  Speed: {speed_str}\n"
        )

        self.running = True

        with Live(
            self.dashboard.layout,
            console=console,
            refresh_per_second=4,
            screen=False,
            transient=False,
        ):
            try:
                for i in range(start_idx, len(df_full)):
                    if not self.running:
                        break

                    # Simuler l'historique disponible à ce moment
                    df_history = df_full.iloc[: i + 1].copy()
                    current_time = df_history.index[-1]
                    current_price = float(df_history["close"].iloc[-1])

                    # Mettre à jour le prix dans la conn_state (last_kline_ts = now pour afficher "0s ago")
                    self.conn_state.update(
                        current_price=current_price,
                        last_kline_ts=datetime.now(timezone.utc).replace(tzinfo=None),
                    )

                    # Événement bougie dans le log
                    self._log(
                        f"[bold cyan]CANDLE[/] {current_time} | Price: ${current_price:,.2f}"
                    )

                    # Vérifier et fermer les positions
                    self._check_and_close_positions(current_price, current_time)

                    # Refresh après les fermetures éventuelles
                    self.dashboard.refresh(
                        state=self.state,
                        conn=self.conn_state,
                        symbol=self.symbol,
                        current_price=current_price,
                        initial_capital=self.initial_capital,
                    )

                    # Circuit breaker : stop trading si drawdown trop élevé
                    if self._circuit_breaker_active:
                        time.sleep(max(speed, 0.025))
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
                        pred_style = (
                            "green"
                            if prediction > 0
                            else "red"
                            if prediction < 0
                            else "dim"
                        )
                        self._log(
                            f"[bold]PREDICTION[/] [{pred_style}]{prediction * 100:+.2f}%[/]  "
                            f"[dim](threshold: ±{self.threshold * 100:.2f}%)[/]"
                        )
                    except Exception as e:
                        self._log(
                            f"[bold red]ERROR[/] Prédiction à {current_time}: {e}"
                        )
                        time.sleep(max(speed, 0.025))
                        continue

                    # Générer le signal
                    if prediction > self.threshold:
                        self._open_new_position(
                            "LONG", current_price, prediction, current_time
                        )
                    elif prediction < -self.threshold and self.allow_short:
                        self._open_new_position(
                            "SHORT", current_price, prediction, current_time
                        )

                    # Refresh dashboard
                    self.dashboard.refresh(
                        state=self.state,
                        conn=self.conn_state,
                        symbol=self.symbol,
                        current_price=current_price,
                        initial_capital=self.initial_capital,
                    )

                    time.sleep(max(speed, 0.025))

            except KeyboardInterrupt:
                self.dashboard.log("[yellow]STOP[/] Interruption détectée (Ctrl+C)")

        # Hors du contexte Live — affichage final
        self.dashboard = None
        self.running = False
        console.print("\n[bold green]BACKTEST[/] Simulation terminée!")
        print_summary(self.state, self.initial_capital)
        if self.state.open_positions:
            console.print(
                f"\n[bold yellow]WARNING[/] {len(self.state.open_positions)} positions encore ouvertes:"
            )
            for pos in self.state.open_positions:
                console.print(
                    f"   [bold]#{pos.position_id}[/] {pos.direction} | Entry: ${pos.entry_price:,.2f}"
                )
        console.print("\n[bold]SHUTDOWN[/] Backtest terminé.")


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
        help="Délai entre bougies en mode backtest (secondes, 0 = min 25ms pour afficher le dashboard, 0.1 recommandé pour présentation)",
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
        sym = args.symbol
        if "/" not in sym:
            sym = sym + "/USDT"
        config["symbol"] = sym
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
