# 16-feature list frozen at the time the +14.07% checkpoint was trained.
# Kept local to models/rl/ so the feature pipeline can evolve (e.g. for
# transformer/CNN) without breaking the pretrained RL weights.
FEATURE_COLUMNS = [
    "body",
    "upper_wick",
    "lower_wick",
    "range",
    "return_1d",
    "ema9_ratio",
    "ema21_ratio",
    "ema50_ratio",
    "ema100_ratio",
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "volume_ratio",
    "volume_return",
    "volatility",
]
