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
BASE_WINDOW_DAYS = 30        # 30 jours d'historique de référence
BASE_PREDICTION_DAYS = 3     # Prédiction à 3 jours de référence
START_DATE = "2020-01-01"

LABEL_THRESHOLD = 0.02  # seuil de 2% pour considérer un mouvement significatif

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

    Les paramètres window_size et prediction_horizon sont automatiquement
    scalés pour maintenir des durées calendaires constantes:
    - 30 jours d'historique (BASE_WINDOW_DAYS)
    - 3 jours de prédiction (BASE_PREDICTION_DAYS)

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

    # Conversion de jours en nombre de périodes du timeframe
    window_size = int(BASE_WINDOW_DAYS * 24 * 60 / minutes_per_bar)
    prediction_horizon = int(BASE_PREDICTION_DAYS * 24 * 60 / minutes_per_bar)

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

# Frais de transaction (en pourcentage, ex: 0.001 = 0.1%)
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
