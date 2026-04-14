SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "ADA/USDT",
    "DOGE/USDT",
    "AVAX/USDT",
    "MATIC/USDT",
    "DOT/USDT",
]

BACKTEST_SYMBOLS = [
    "LINK/USDT",
]

# ----- Timeframes Supportés -----
DEFAULT_TIMEFRAME = "1d"
AVAILABLE_TIMEFRAMES = [
    "1m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M"
]

TIMEFRAME_MINUTES = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "2h": 120, "4h": 240, "6h": 360, "8h": 480, "12h": 720,
    "1d": 1440, "3d": 4320, "1w": 10080, "1M": 43200
}

# ----- Paramètres de Base (référence 1d) -----
# Ces valeurs sont en "périodes" mais représentent des durées calendaires
BASE_WINDOW_DAYS = 15        # 15 jours d'historique de référence (fallback pour les timeframes non listés dans WINDOW_SIZES)
BASE_PREDICTION_DAYS = 3     # Prédiction à 3 jours de référence

# Window size explicite par timeframe (en nombre de barres).
# Prioritaire sur le calcul automatique BASE_WINDOW_DAYS.
# Fallback pour les timeframes non listés : int(BASE_WINDOW_DAYS * 24 * 60 / minutes_per_bar)
WINDOW_SIZES: dict = {
    "1d": 30,   # 30 jours
    "1h": 72,   # 3 jours
    "4h": 120,  # 20 jours
    "6h": 120,  # 30 jours (contexte utilisé par l'agent RL PPO)
    "1w": 20,   # 20 semaines
}

# Horizon de prédiction explicite par timeframe (en nombre de barres).
# Définit ce que le modèle cherche à prédire : le rendement N barres plus tard.
# Prioritaire sur le calcul automatique BASE_PREDICTION_DAYS.
# Fallback pour les timeframes non listés : int(BASE_PREDICTION_DAYS * 24 * 60 / minutes_per_bar)
PREDICTION_HORIZONS: dict = {
    "1d": 3,    # prédire le rendement 3 jours plus tard
    "1h": 6,    # prédire le rendement 6 heures plus tard
    "4h": 1,    # prédire le rendement de la prochaine bougie 4h
    "6h": 4,    # prédire le rendement 24 heures plus tard
    "1w": 1,    # prédire le rendement de la semaine suivante
}
START_DATE = "2020-01-01"

LABEL_THRESHOLD = 0.02  # seuil de 2% pour considérer un mouvement significatif

# Seuil de prédiction pour ouvrir une position (en rendement brut, ex: 0.005 = 0.5%).
# Adapté à l'horizon : plus l'horizon est court, plus les returns attendus sont petits.
SIGNAL_THRESHOLDS: dict = {
    "1d": 0.010,   # 1.0%  sur 3 jours
    "1h": 0.003,   # 0.3%  sur 6 heures
    "4h": 0.005,   # 0.5%  sur 4 heures
    "6h": 0.005,   # 0.5%  sur 24 heures (non utilisé par RL)
    "1w": 0.020,   # 2.0%  sur 1 semaine
}

# Pourcentage de risque par trade, adapté à la volatilité de chaque timeframe.
# SL = entry × (1 - risk_pct)   TP = entry × (1 + risk_pct × rrr)
# Calibré sur ~1 ATR de l'horizon (6h BTC σ ≈ 0.8%, 3d BTC σ ≈ 2.5%)
RISK_PCTS: dict = {
    "1d": 0.025,   # 2.5%  SL / 5.0% TP (rrr=2)
    "1h": 0.008,   # 0.8%  SL / 1.6% TP (rrr=2)  ← 1 ATR sur 6h
    "4h": 0.015,   # 1.5%  SL / 3.0% TP (rrr=2)
    "6h": 0.012,   # 1.2%  SL / 2.4% TP (rrr=2) — entre 4h et 1d
    "1w": 0.040,   # 4.0%  SL / 8.0% TP (rrr=2)
}

# Paramètres legacy - pour rétro-compatibilité
def _get_legacy_config():
    """Retourne les valeurs par défaut pour rétro-compatibilité."""
    return {
        "window_size": 30,
        "prediction_horizon": 3,
        "raw_data_path": "data/raw/",
        "output_path": "output/"
    }

# Valeurs globales pour les imports legacy
# Ces valeurs seront mises à jour selon le timeframe utilisé
WINDOW_SIZE = 30
PREDICTION_HORIZON = 3
RAW_DATA_PATH = "data/raw/"
OUTPUT_PATH = "output/"
TIMEFRAME = DEFAULT_TIMEFRAME  # Pour rétro-compatibilité


def get_timeframe_config(timeframe: str = DEFAULT_TIMEFRAME) -> dict:
    """
    Retourne les paramètres scalés pour un timeframe donné.

    window_size : utilise WINDOW_SIZES[timeframe] si défini, sinon calcule
    automatiquement depuis BASE_WINDOW_DAYS pour maintenir une durée calendaire constante.
    prediction_horizon : toujours calculé depuis BASE_PREDICTION_DAYS.

    Args:
        timeframe: Le timeframe ("1m", "5m", "15m", "30m", "1h", "2h",
                   "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M")

    Returns:
        dict avec: window_size, prediction_horizon, raw_data_path, output_path

    Raises:
        ValueError: Si le timeframe n'est pas supporté
    """
    if timeframe not in AVAILABLE_TIMEFRAMES:
        raise ValueError(
            f"Timeframe '{timeframe}' non supporté. "
            f"Timeframes disponibles: {AVAILABLE_TIMEFRAMES}"
        )

    minutes_per_bar = TIMEFRAME_MINUTES[timeframe]

    # window_size : valeur explicite si disponible, sinon fallback calendaire
    window_size = WINDOW_SIZES.get(
        timeframe,
        int(BASE_WINDOW_DAYS * 24 * 60 / minutes_per_bar)
    )
    # prediction_horizon : valeur explicite si disponible, sinon fallback calendaire
    prediction_horizon = PREDICTION_HORIZONS.get(
        timeframe,
        int(BASE_PREDICTION_DAYS * 24 * 60 / minutes_per_bar)
    )

    return {
        "timeframe": timeframe,
        "window_size": window_size,
        "prediction_horizon": prediction_horizon,
        "minutes_per_bar": minutes_per_bar,
        "raw_data_path": f"data/raw/{timeframe}/",
        "output_path": f"output/{timeframe}/"
    }


def update_global_config(timeframe: str = DEFAULT_TIMEFRAME):
    """
    Met à jour les variables globales pour le timeframe spécifié.
    À utiliser pour la rétro-compatibilité.
    """
    global WINDOW_SIZE, PREDICTION_HORIZON, RAW_DATA_PATH, OUTPUT_PATH, TIMEFRAME
    config = get_timeframe_config(timeframe)
    WINDOW_SIZE = config["window_size"]
    PREDICTION_HORIZON = config["prediction_horizon"]
    RAW_DATA_PATH = config["raw_data_path"]
    OUTPUT_PATH = config["output_path"]
    TIMEFRAME = timeframe
    return config

# ----- Architecture CNN par timeframe -----
# Deux profils distincts : 1d (original) et 1h (optimisé).
# Fallback pour les autres timeframes : pool_size calculé dynamiquement.
CNN_CONFIGS: dict = {
    "1d": {
        "channels": [16, 32, 64],
        "kernel_sizes": [3, 3, 3],
        "dropout_conv": 0.2,
        "dropout_fc": 0.3,
        "pool_size": 5,       # 30 % 5 == 0 ✓ MPS
    },
    "1h": {
        "channels": [16, 32, 64],
        "kernel_sizes": [5, 5, 3],
        "dropout_conv": 0.2,
        "dropout_fc": 0.3,
        "pool_size": 8,       # 72 % 8 == 0 ✓ MPS
    },
}


def get_cnn_config(timeframe: str = DEFAULT_TIMEFRAME) -> dict:
    """Retourne la config d'architecture CNN pour le timeframe donné."""
    if timeframe in CNN_CONFIGS:
        return CNN_CONFIGS[timeframe]
    # Fallback : pool_size calculé comme le plus grand diviseur de window_size <= 8
    window_size = get_timeframe_config(timeframe)["window_size"]
    pool_size = next(p for p in range(8, 0, -1) if window_size % p == 0)
    return {
        "channels": [16, 32, 64],
        "kernel_sizes": [3, 3, 3],
        "dropout_conv": 0.2,
        "dropout_fc": 0.3,
        "pool_size": pool_size,
    }


# ----- Architecture CNN-BiLSTM-AM par timeframe -----
CNN_BILSTM_AM_CONFIGS: dict = {
    "1d": {
        "channels": [16, 32, 64],
        "kernel_sizes": [3, 3, 3],
        "dropout_conv": 0.2,
        "pool_size": 15,          # 30 % 15 == 0 ✓ MPS — conserve plus de contexte pour BiLSTM
        "lstm_hidden": 64,
        "lstm_layers": 1,
        "dropout_lstm": 0.0,
        "dropout_fc": 0.3,
    },
    "1h": {
        "channels": [16, 32, 64],
        "kernel_sizes": [5, 5, 3],
        "dropout_conv": 0.2,
        "pool_size": 24,          # 72 % 24 == 0 ✓ MPS — conserve plus de contexte pour BiLSTM
        "lstm_hidden": 64,
        "lstm_layers": 1,
        "dropout_lstm": 0.0,
        "dropout_fc": 0.3,
    },
}


def get_cnn_bilstm_am_config(timeframe: str = DEFAULT_TIMEFRAME) -> dict:
    """Retourne la config d'architecture CNN-BiLSTM-AM pour le timeframe donné."""
    if timeframe in CNN_BILSTM_AM_CONFIGS:
        return CNN_BILSTM_AM_CONFIGS[timeframe]
    # Fallback : pool_size ~ window_size/3 (arrondi au diviseur le plus proche)
    # Le BiLSTM a besoin de suffisamment de timesteps pour capturer les dépendances
    window_size = get_timeframe_config(timeframe)["window_size"]
    target = max(window_size // 3, 4)
    pool_size = next(p for p in range(target, 0, -1) if window_size % p == 0)
    return {
        "channels": [16, 32, 64],
        "kernel_sizes": [3, 3, 3],
        "dropout_conv": 0.2,
        "pool_size": pool_size,
        "lstm_hidden": 64,
        "lstm_layers": 1,
        "dropout_lstm": 0.0,
        "dropout_fc": 0.3,
    }


# ----- Frais de transaction (en pourcentage, ex: 0.001 = 0.1%)
# Centralized Exchange (Binance, Coinbase)
MAKER_FEE_CEX = 0.0010  # 0.100% - Binance VIP 0 spot
TAKER_FEE_CEX = 0.0010  # 0.100% - Binance VIP 0 spot

# DEX (Uniswap, etc.)
DEX_FEE = 0.003  # 0.3% typique sur Uniswap

# Slippage estimé pour les ordres market (0.05% = 0.0005)
DEFAULT_SLIPPAGE_PCT = 0.0005

# Frais par défaut pour le backtesting (conservateur: taker fee)
DEFAULT_ENTRY_FEE = TAKER_FEE_CEX  # 0.100%
DEFAULT_EXIT_FEE = TAKER_FEE_CEX   # 0.100%
