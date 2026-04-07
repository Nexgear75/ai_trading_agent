import os
import pandas as pd

from config import SYMBOLS, BACKTEST_SYMBOLS, DEFAULT_TIMEFRAME, get_timeframe_config


# Correspondance entre noms courts et noms de fichiers
AVAILABLE_SYMBOLS = {s.replace("/", "_"): s for s in SYMBOLS + BACKTEST_SYMBOLS}


def load_symbol(symbol: str, timeframe: str = DEFAULT_TIMEFRAME) -> pd.DataFrame:
    """Charge le dataset d'une seule crypto monnaie.

    Args:
        symbol: Nom de la crypto, accepte plusieurs formats :
                "BTC/USDT", "BTC_USDT" ou "BTC"
        timeframe: Timeframe du dataset (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").

    Returns:
        DataFrame avec les features et le label, indexé par timestamp.

    Raises:
        ValueError: Si le symbole n'est pas reconnu.
        FileNotFoundError: Si le fichier CSV n'existe pas.
    """
    filename = _resolve_symbol(symbol)
    tf_config = get_timeframe_config(timeframe)
    output_path = tf_config["output_path"]
    path = os.path.join(output_path, f"{filename}.csv")

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Fichier introuvable : {path}. "
            f"Lance `python -m data.main --timeframe {timeframe}` pour générer les datasets."
        )

    df = pd.read_csv(path, parse_dates=["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df


def load_all(timeframe: str = DEFAULT_TIMEFRAME) -> pd.DataFrame:
    """Charge le dataset complet contenant toutes les cryptos.

    Args:
        timeframe: Timeframe du dataset (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").

    Returns:
        DataFrame combiné, indexé par timestamp, avec colonne 'symbol'.

    Raises:
        FileNotFoundError: Si full_dataset.csv n'existe pas.
    """
    tf_config = get_timeframe_config(timeframe)
    output_path = tf_config["output_path"]
    path = os.path.join(output_path, "full_dataset.csv")

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Fichier introuvable : {path}. "
            f"Lance `python -m data.main --timeframe {timeframe}` pour générer les datasets."
        )

    df = pd.read_csv(path, parse_dates=["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df


def load_symbols(symbols: list[str], timeframe: str = DEFAULT_TIMEFRAME) -> pd.DataFrame:
    """Charge et combine les datasets de plusieurs cryptos.

    Args:
        symbols: Liste de symboles (mêmes formats que load_symbol).
        timeframe: Timeframe du dataset (ex: "1d", "1h", "4h").
                   Défaut: DEFAULT_TIMEFRAME ("1d").

    Returns:
        DataFrame combiné, indexé par timestamp, avec colonne 'symbol'.
    """
    dfs = [load_symbol(s, timeframe=timeframe) for s in symbols]
    return pd.concat(dfs)


def list_available_symbols() -> list[str]:
    """Retourne la liste des symboles disponibles (format 'BTC_USDT')."""
    return list(AVAILABLE_SYMBOLS.keys())


def _resolve_symbol(symbol: str) -> str:
    """Convertit un symbole en nom de fichier (sans extension).

    Accepte : "BTC/USDT", "BTC_USDT", "BTC"
    Retourne : "BTC_USDT"
    """
    # Format "BTC/USDT" -> "BTC_USDT"
    normalized = symbol.strip().upper().replace("/", "_")

    if normalized in AVAILABLE_SYMBOLS:
        return normalized

    # Format court "BTC" -> cherche "BTC_USDT"
    for key in AVAILABLE_SYMBOLS:
        if key.startswith(normalized + "_"):
            return key

    available = ", ".join(sorted(AVAILABLE_SYMBOLS.keys()))
    raise ValueError(
        f"Symbole inconnu : '{symbol}'. Symboles disponibles : {available}"
    )
