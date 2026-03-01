"""Feature engineering — pluggable registry and pipeline.

Importing this package triggers registration of all built-in features
in ``FEATURE_REGISTRY``. Pipeline code should ``import ai_trading.features``
before accessing the registry.
"""

from ai_trading.features import ema as _ema  # noqa: F401
from ai_trading.features import log_returns as _log_returns  # noqa: F401
from ai_trading.features import rsi as _rsi  # noqa: F401
from ai_trading.features import volatility as _volatility  # noqa: F401
