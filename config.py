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

TIMEFRAME = "6h"
START_DATE = "2020-01-01"

LABEL_THRESHOLD = 0.01
PREDICTION_HORIZON = 4  # predict 4 candles ahead (24h)

WINDOW_SIZE = 120  # 120 candles x 6h = 30 days of context

RAW_DATA_PATH = "data/raw/"
OUTPUT_PATH = "output/"
