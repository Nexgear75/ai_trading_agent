"""
Module de grid search pour optimisation des paramètres de trading.

Teste systématiquement les combinaisons de paramètres et identifie
la configuration avec le meilleur Sharpe Ratio.

Usage:
    # Grid search complet
    python -m testing.grid_search --symbol BTC --model cnn

    # Grille réduite (test rapide)
    python -m testing.grid_search --symbol BTC --model cnn --quick-test

    # Périodes personnalisées
    python -m testing.grid_search --symbol BTC --model cnn \
        --train-start 2020-01-01 --train-end 2022-12-31 \
        --val-start 2023-01-01 --val-end 2023-12-31 \
        --test-start 2024-01-01

    # Limite les workers
    python -m testing.grid_search --symbol BTC --model cnn --max-workers 4
"""

import argparse
import itertools
import os
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

# Ajouter le parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PREDICTION_HORIZON, WINDOW_SIZE

# Supprimer les warnings pour un output propre
warnings.filterwarnings("ignore")

# ----- Configuration des grilles -----

PARAM_GRID_FULL = {
    "threshold": [0.005, 0.01, 0.015, 0.02, 0.025, 0.03],
    "rrr": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
    "risk_pct": [0.01, 0.02, 0.025, 0.03, 0.04, 0.05],
    "allow_short": [True, False],
    "entry_fee_pct": [0.0010],
    "exit_fee_pct": [0.0010],
}

PARAM_GRID_QUICK = {
    "threshold": [0.01, 0.02],
    "rrr": [2.0, 3.0],
    "risk_pct": [0.025, 0.05],
    "allow_short": [True, False],
    "entry_fee_pct": [0.0010],
    "exit_fee_pct": [0.0010],
}

# Configuration des périodes par défaut
DEFAULT_PERIODS = {
    "train": {"start": "2020-01-01", "end": "2022-12-31"},
    "val": {"start": "2023-01-01", "end": "2023-12-31"},
    "test": {"start": "2024-01-01", "end": None},  # None = jusqu'à aujourd'hui
}


@dataclass
class BacktestMetrics:
    """Métriques calculées pour une période de backtest."""
    sharpe_ratio: float = 0.0
    total_return: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    n_trades: int = 0
    avg_trade_return: float = 0.0
    profit_factor: float = 0.0
    total_fees: float = 0.0


def calculate_metrics(trades: list, initial_capital: float, start_date: datetime, end_date: datetime) -> BacktestMetrics:
    """
    Calcule les métriques de performance à partir des trades.

    Args:
        trades: Liste des trades clôturés
        initial_capital: Capital initial
        start_date: Date de début de la période
        end_date: Date de fin de la période

    Returns:
        BacktestMetrics avec toutes les métriques calculées
    """
    metrics = BacktestMetrics()

    if not trades:
        return metrics

    # Nombre de trades
    metrics.n_trades = len(trades)

    # Win rate
    winning_trades = [t for t in trades if t.pnl > 0]
    metrics.win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0

    # Returns
    total_pnl = sum(t.pnl for t in trades)
    metrics.total_return = (total_pnl / initial_capital) * 100

    # Annualized return
    days = (end_date - start_date).total_seconds() / (24 * 3600)
    if days > 0:
        metrics.annualized_return = ((1 + metrics.total_return / 100) ** (365 / days) - 1) * 100

    # Sharpe Ratio (approximé via les trades)
    if len(trades) > 1:
        returns = [t.pnl / initial_capital for t in trades]
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        if std_return > 0:
            # Annualisé (approximation: trades indépendants)
            metrics.sharpe_ratio = (mean_return / std_return) * np.sqrt(len(trades) / (days / 365)) if days > 0 else 0

    # Max Drawdown (simplifié - basé sur les trades)
    cumulative = 0
    peak = 0
    max_dd = 0
    for t in trades:
        cumulative += t.pnl / initial_capital * 100
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    metrics.max_drawdown = max_dd

    # Avg trade return
    metrics.avg_trade_return = metrics.total_return / len(trades) if trades else 0

    # Profit Factor
    gross_profits = sum(t.pnl for t in winning_trades)
    gross_losses = abs(sum(t.pnl for t in trades if t.pnl <= 0))
    metrics.profit_factor = gross_profits / gross_losses if gross_losses > 0 else float("inf")

    # Total fees
    metrics.total_fees = sum(t.total_fees for t in trades)

    return metrics


def run_single_backtest(
    params: dict,
    symbol: str,
    model_type: str,
    capital: float,
    period_name: str,
    start_date: str,
    end_date: Optional[str],
) -> dict:
    """
    Exécute un backtest avec une configuration spécifique.

    Cette fonction est conçue pour être appelée en parallèle.
    Elle crée son propre RealtimeTester pour éviter les problèmes de multiprocessing.

    Args:
        params: Dictionnaire des paramètres à tester
        symbol: Symbole à trader
        model_type: Type de modèle (cnn, lstm, etc.)
        capital: Capital initial
        period_name: Nom de la période (train/val/test)
        start_date: Date de début
        end_date: Date de fin (None = jusqu'à aujourd'hui)

    Returns:
        Dict avec les résultats et métriques
    """
    # Import local pour éviter les problèmes avec multiprocessing
    from testing.realtime_testing import RealtimeTester

    # Configuration
    config = {
        "symbol": symbol,
        "model_type": model_type,
        "capital": capital,
        "threshold": params["threshold"],
        "allow_short": params["allow_short"],
        "rrr": params["rrr"],
        "risk_pct": params["risk_pct"],
        "check_interval_hours": 4,
        "entry_fee_pct": params["entry_fee_pct"],
        "exit_fee_pct": params["exit_fee_pct"],
        "log_level": "ERROR",  # Supprimer les logs pour la parallélisation
    }

    # Créer et exécuter le tester
    tester = RealtimeTester(config)

    # Rediriger stdout pour supprimer les prints
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        # Initialisation (charge le modèle)
        tester.device = __import__("torch").device("cpu")  # Force CPU pour multiprocessing
        tester.model, _ = __import__("testing.realtime_testing", fromlist=["load_model_dynamic"]).load_model_dynamic(model_type, tester.device)
        tester.scalers = __import__("testing.realtime_testing", fromlist=["load_scalers"]).load_scalers(model_type)
        tester.feature_scaler = tester.scalers["feature_scaler"]
        tester.target_scaler = tester.scalers["target_scaler"]
        tester.clip_bounds = tester.scalers.get("clip_bounds")

        # Exécuter le backtest
        symbol_code = symbol.replace("/USDT", "").replace("/USD", "")
        df_full = __import__("testing.realtime_testing", fromlist=["load_symbol"]).load_symbol(symbol_code)

        if start_date:
            df_full = df_full[df_full.index >= start_date]
        if end_date:
            df_full = df_full[df_full.index <= end_date]

        min_required = WINDOW_SIZE + 100
        if len(df_full) < min_required:
            sys.stdout = old_stdout
            return {"error": f"Pas assez de données: {len(df_full)} < {min_required}"}

        # Simuler le backtest
        start_idx = WINDOW_SIZE + 50
        tester.running = True

        for i in range(start_idx, len(df_full)):
            if not tester.running:
                break

            df_history = df_full.iloc[:i + 1].copy()
            current_time = df_history.index[-1]
            current_price = df_history["close"].iloc[-1]

            # Vérifier et fermer les positions
            tester._check_and_close_positions(current_price, current_time)

            # Calculer features et prédire
            try:
                X_scaled, _ = __import__("testing.realtime_testing", fromlist=["prepare_live_features"]).prepare_live_features(df_history, tester.feature_scaler, tester.clip_bounds)
                prediction = __import__("testing.realtime_testing", fromlist=["predict_return"]).predict_return(tester.model, X_scaled, tester.target_scaler, tester.device)
            except Exception:
                continue

            # Générer signal
            signal = None
            if prediction > tester.threshold:
                signal = "LONG"
            elif prediction < -tester.threshold and tester.allow_short:
                signal = "SHORT"

            if signal:
                tester._open_new_position(signal, current_price, prediction, current_time)

        # Restaurer stdout
        sys.stdout = old_stdout

        # Calculer les métriques
        end_dt = pd.to_datetime(df_full.index[-1])
        start_dt = pd.to_datetime(df_full.index[start_idx])
        metrics = calculate_metrics(tester.state.closed_trades, capital, start_dt, end_dt)

        return {
            "params": params,
            "period": period_name,
            "metrics": metrics,
            "n_trades": len(tester.state.closed_trades),
        }

    except Exception as e:
        sys.stdout = old_stdout
        return {"error": str(e)}


def generate_param_combinations(param_grid: dict) -> list[dict]:
    """Génère toutes les combinaisons de paramètres."""
    keys = list(param_grid.keys())
    values = list(param_grid.values())

    combinations = []
    for combo in itertools.product(*values):
        combinations.append(dict(zip(keys, combo)))

    return combinations


def run_grid_search(
    symbol: str,
    model_type: str,
    capital: float,
    param_grid: dict,
    periods: dict,
    max_workers: int = None,
    output_dir: str = "output",
) -> str:
    """
    Exécute le grid search complet sur toutes les combinaisons.

    Args:
        symbol: Symbole à trader
        model_type: Type de modèle
        capital: Capital initial
        param_grid: Grille de paramètres à tester
        periods: Dict avec les périodes train/val/test
        max_workers: Nombre de workers parallèles (None = auto)
        output_dir: Répertoire de sortie

    Returns:
        Chemin du fichier CSV généré
    """
    # Générer les combinaisons
    combinations = generate_param_combinations(param_grid)
    total_combos = len(combinations)

    print(f"\n{'=' * 70}")
    print(f" GRID SEARCH TRADING PARAMETERS ".center(70, "="))
    print(f"{'=' * 70}")
    print(f"Symbol:      {symbol}")
    print(f"Model:       {model_type.upper()}")
    print(f"Capital:     ${capital:,.2f}")
    print(f"Combinations: {total_combos}")
    print(f"Workers:     {max_workers or 'auto (CPU count)'}")
    print(f"Periods:")
    for name, dates in periods.items():
        end_str = dates['end'] or 'today'
        print(f"  {name:8}: {dates['start']} → {end_str}")
    print(f"{'=' * 70}\n")

    # Résultats collectés
    all_results = []

    # Utiliser les périodes définies
    for period_name, period_dates in periods.items():
        print(f"\n[PHASE] Testing on {period_name.upper()} period...")

        # Exécuter les backtests en parallèle
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre tous les jobs
            future_to_params = {
                executor.submit(
                    run_single_backtest,
                    params,
                    symbol,
                    model_type,
                    capital,
                    period_name,
                    period_dates["start"],
                    period_dates["end"],
                ): params
                for params in combinations
            }

            # Collecter les résultats avec barre de progression
            with tqdm(total=len(future_to_params), desc=f"  {period_name}") as pbar:
                for future in as_completed(future_to_params):
                    result = future.result()
                    if "error" not in result:
                        all_results.append(result)
                    pbar.update(1)

    print(f"\n[OK] {len(all_results)} backtests completed successfully")

    # Créer le DataFrame de résultats
    results_df = create_results_dataframe(all_results, total_combos)

    # Sauvegarder
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"grid_search_{symbol.replace('/', '_')}_{model_type}_{timestamp}.csv")

    results_df.to_csv(output_path, index=False)
    print(f"[SAVED] Results saved to: {output_path}")

    # Afficher le top 5
    print(f"\n{'=' * 70}")
    print(" TOP 5 CONFIGURATIONS (by Validation Sharpe) ".center(70, "="))
    print(f"{'=' * 70}")
    top5 = results_df.head(5)
    for idx, row in top5.iterrows():
        print(f"\n#{idx + 1} | Val Sharpe: {row['val_sharpe']:.3f}")
        print(f"    Params: threshold={row['threshold']}, rrr={row['rrr']}, "
              f"risk_pct={row['risk_pct']:.3f}, allow_short={row['allow_short']}")
        print(f"    Train: {row['train_return']:+.2f}% (Sharpe: {row['train_sharpe']:.2f}) | "
              f"Val: {row['val_return']:+.2f}% (Sharpe: {row['val_sharpe']:.2f}) | "
              f"Test: {row['test_return']:+.2f}% (Sharpe: {row['test_sharpe']:.2f})")

    return output_path


def create_results_dataframe(results: list, total_combos: int) -> pd.DataFrame:
    """
    Crée un DataFrame à partir des résultats collectés.

    Agrège les métriques des 3 périodes (train/val/test) par combinaison de paramètres.
    """
    # Grouper par paramètres
    grouped = {}
    for result in results:
        params = result["params"]
        period = result["period"]
        metrics = result["metrics"]

        # Clé unique pour cette combinaison
        key = tuple(sorted(params.items()))

        if key not in grouped:
            grouped[key] = {"params": params}

        grouped[key][f"{period}_sharpe"] = metrics.sharpe_ratio
        grouped[key][f"{period}_return"] = metrics.total_return
        grouped[key][f"{period}_maxdd"] = metrics.max_drawdown
        grouped[key][f"{period}_winrate"] = metrics.win_rate
        grouped[key][f"{period}_trades"] = metrics.n_trades
        grouped[key][f"{period}_profit_factor"] = metrics.profit_factor
        grouped[key][f"{period}_fees"] = metrics.total_fees

    # Créer les lignes du DataFrame
    rows = []
    for key, data in grouped.items():
        row = {
            # Paramètres
            "threshold": data["params"]["threshold"],
            "rrr": data["params"]["rrr"],
            "risk_pct": data["params"]["risk_pct"],
            "allow_short": data["params"]["allow_short"],
            "entry_fee_pct": data["params"]["entry_fee_pct"],
            "exit_fee_pct": data["params"]["exit_fee_pct"],
            # Train metrics
            "train_sharpe": data.get("train_sharpe", 0),
            "train_return": data.get("train_return", 0),
            "train_max_dd": data.get("train_maxdd", 0),
            "train_win_rate": data.get("train_winrate", 0),
            "train_trades": data.get("train_trades", 0),
            "train_profit_factor": data.get("train_profit_factor", 0),
            "train_fees": data.get("train_fees", 0),
            # Val metrics
            "val_sharpe": data.get("val_sharpe", 0),
            "val_return": data.get("val_return", 0),
            "val_max_dd": data.get("val_maxdd", 0),
            "val_win_rate": data.get("val_winrate", 0),
            "val_trades": data.get("val_trades", 0),
            "val_profit_factor": data.get("val_profit_factor", 0),
            "val_fees": data.get("val_fees", 0),
            # Test metrics
            "test_sharpe": data.get("test_sharpe", 0),
            "test_return": data.get("test_return", 0),
            "test_max_dd": data.get("test_maxdd", 0),
            "test_win_rate": data.get("test_winrate", 0),
            "test_trades": data.get("test_trades", 0),
            "test_profit_factor": data.get("test_profit_factor", 0),
            "test_fees": data.get("test_fees", 0),
            # Metadata
            "total_combinations": total_combos,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Trier par Sharpe Ratio de validation (descendant)
    df = df.sort_values("val_sharpe", ascending=False)

    # Ajouter le rang
    df.insert(0, "rank", range(1, len(df) + 1))

    return df


def parse_args():
    """Parse les arguments CLI."""
    parser = argparse.ArgumentParser(
        description="Grid search pour optimisation des paramètres de trading"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Symbole à trader (ex: BTC/USDT)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="cnn",
        help="Type de modèle (cnn, lstm, gru)"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=10000.0,
        help="Capital initial"
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Utiliser une grille réduite pour test rapide"
    )
    parser.add_argument(
        "--train-start",
        type=str,
        default=DEFAULT_PERIODS["train"]["start"],
        help="Date de début train (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--train-end",
        type=str,
        default=DEFAULT_PERIODS["train"]["end"],
        help="Date de fin train (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--val-start",
        type=str,
        default=DEFAULT_PERIODS["val"]["start"],
        help="Date de début validation (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--val-end",
        type=str,
        default=DEFAULT_PERIODS["val"]["end"],
        help="Date de fin validation (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--test-start",
        type=str,
        default=DEFAULT_PERIODS["test"]["start"],
        help="Date de début test (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--test-end",
        type=str,
        default=DEFAULT_PERIODS["test"]["end"],
        help="Date de fin test (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Nombre de workers parallèles (défaut: auto)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Répertoire de sortie pour les résultats"
    )
    return parser.parse_args()


def main():
    """Point d'entrée principal."""
    args = parse_args()

    # Choisir la grille
    param_grid = PARAM_GRID_QUICK if args.quick_test else PARAM_GRID_FULL

    # Configurer les périodes
    periods = {
        "train": {"start": args.train_start, "end": args.train_end},
        "val": {"start": args.val_start, "end": args.val_end},
        "test": {"start": args.test_start, "end": args.test_end},
    }

    # Exécuter le grid search
    output_path = run_grid_search(
        symbol=args.symbol,
        model_type=args.model,
        capital=args.capital,
        param_grid=param_grid,
        periods=periods,
        max_workers=args.max_workers,
        output_dir=args.output_dir,
    )

    print(f"\n[COMPLETE] Grid search finished. Results: {output_path}")


if __name__ == "__main__":
    main()
