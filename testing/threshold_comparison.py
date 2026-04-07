"""
Comparaison de seuils (threshold) pour le realtime backtest.

Usage:
    python -m testing.threshold_comparison --symbol LINK --model cnn_bilstm_am --months 6
"""

import argparse
import sys
import os
import warnings
from datetime import datetime, timedelta

import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

warnings.filterwarnings("ignore")

from testing.realtime_testing import RealtimeTester, load_config

console = Console()


def run_single_backtest(symbol: str, model: str, threshold: float,
                        start_date: str, end_date: str, capital: float = 10000.0,
                        rrr: float = 2.0, timeframe: str = "1h") -> dict:
    """Lance un backtest et retourne les métriques."""
    config = load_config("testing/config.json")
    config["symbol"] = symbol
    config["model_type"] = model
    config["capital"] = capital
    config["threshold"] = threshold
    config["rrr"] = rrr
    config["allow_short"] = False
    config["timeframe"] = timeframe

    tester = RealtimeTester(config)

    # Capturer la sortie pour ne pas polluer le terminal
    from io import StringIO
    from contextlib import redirect_stdout, redirect_stderr
    buf = StringIO()

    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            tester.run_backtest_mode(start_date=start_date, end_date=end_date, speed=0)
    except Exception as e:
        return {"error": str(e), "threshold": threshold}

    # Extraire les métriques depuis l'état
    state = tester.state
    trades = state.closed_trades
    total_trades = len(trades)

    if total_trades == 0:
        return {
            "threshold": threshold,
            "total_trades": 0,
            "win_rate": 0,
            "total_return": 0,
            "total_pnl": 0,
            "max_drawdown": 0,
            "sharpe": 0,
            "profit_factor": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "best_trade": 0,
            "worst_trade": 0,
            "total_fees": 0,
            "avg_duration": 0,
            "tp_count": 0,
            "sl_count": 0,
            "exp_count": 0,
        }

    winning = [t for t in trades if t.pnl > 0]
    losing = [t for t in trades if t.pnl <= 0]

    total_pnl = sum(t.pnl for t in trades)
    total_return = total_pnl / capital * 100
    total_fees = sum(t.total_fees for t in trades)

    pnls = [t.pnl for t in trades]

    avg_win = np.mean([t.pnl for t in winning]) if winning else 0
    avg_loss = np.mean([t.pnl for t in losing]) if losing else 0

    gross_wins = sum(t.pnl for t in winning)
    gross_losses = abs(sum(t.pnl for t in losing))
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

    # Max drawdown
    equity = [capital]
    running = capital
    for t in trades:
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

    # Sharpe
    daily_returns = [t.pnl / capital for t in trades]
    if len(daily_returns) > 1 and np.std(daily_returns) > 0:
        sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
    else:
        sharpe = 0

    # Durée moyenne
    durations = []
    for t in trades:
        entry = t.entry_date.replace(tzinfo=None) if t.entry_date.tzinfo else t.entry_date
        exit_ = t.exit_date.replace(tzinfo=None) if t.exit_date.tzinfo else t.exit_date
        durations.append((exit_ - entry).total_seconds() / 86400)
    avg_duration = np.mean(durations) if durations else 0

    return {
        "threshold": threshold,
        "total_trades": total_trades,
        "win_rate": len(winning) / total_trades * 100,
        "total_return": total_return,
        "total_pnl": total_pnl,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "best_trade": max(pnls),
        "worst_trade": min(pnls),
        "total_fees": total_fees,
        "avg_duration": avg_duration,
        "tp_count": len([t for t in trades if t.exit_reason == "TP"]),
        "sl_count": len([t for t in trades if t.exit_reason == "SL"]),
        "exp_count": len([t for t in trades if t.exit_reason == "EXPIRATION"]),
    }


def main():
    parser = argparse.ArgumentParser(description="Comparaison de thresholds")
    parser.add_argument("--symbol", type=str, default="LINK")
    parser.add_argument("--model", type=str, default="cnn_bilstm_am")
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--capital", type=float, default=10000.0)
    parser.add_argument("--rrr", type=float, default=2.0)
    parser.add_argument("--timeframe", type=str, default="1h")
    parser.add_argument("--thresholds", type=str, default=None,
                        help="Thresholds séparés par virgule (ex: 0.005,0.01,0.02)")
    args = parser.parse_args()

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=args.months * 30)).strftime("%Y-%m-%d")

    if args.thresholds:
        thresholds = [float(x) for x in args.thresholds.split(",")]
    else:
        # Adapter les thresholds au timeframe
        if args.timeframe == "1h":
            thresholds = [0.001, 0.002, 0.003, 0.005, 0.008, 0.01, 0.015, 0.02]
        else:
            thresholds = [0.003, 0.005, 0.008, 0.01, 0.015, 0.02, 0.025, 0.03]

    console.print(Panel(
        f"Symbol: {args.symbol}  |  Model: {args.model}  |  Timeframe: {args.timeframe}  |  RRR: 1:{args.rrr}\n"
        f"Période: {start_date} → {end_date}  ({args.months} mois)\n"
        f"Thresholds: {', '.join(f'{t*100:.1f}%' for t in thresholds)}",
        title="THRESHOLD COMPARISON", border_style="cyan"
    ))

    results = []
    for i, threshold in enumerate(thresholds):
        console.print(f"\n[bold cyan][{i+1}/{len(thresholds)}][/] Threshold = {threshold*100:.1f}% ...", end=" ")
        result = run_single_backtest(
            symbol=args.symbol, model=args.model, threshold=threshold,
            start_date=start_date, end_date=end_date,
            capital=args.capital, rrr=args.rrr, timeframe=args.timeframe,
        )
        if "error" in result:
            console.print(f"[red]ERREUR: {result['error']}[/]")
        else:
            console.print(f"[green]{result['total_trades']} trades, {result['total_return']:+.2f}%[/]")
        results.append(result)

    # Trouver le meilleur par Sharpe
    valid = [r for r in results if "error" not in r and r["total_trades"] > 0]
    best_sharpe = max(valid, key=lambda r: r["sharpe"]) if valid else None
    best_return = max(valid, key=lambda r: r["total_return"]) if valid else None
    best_pf = max(valid, key=lambda r: r["profit_factor"] if r["profit_factor"] != float("inf") else -1) if valid else None

    # Tableau comparatif
    table = Table(title=f"\nComparaison des Thresholds — {args.symbol} / {args.model.upper()} ({start_date} → {end_date})",
                  show_lines=True)
    table.add_column("Threshold", justify="center", style="bold")
    table.add_column("Trades", justify="center")
    table.add_column("Win Rate", justify="center")
    table.add_column("Return", justify="center")
    table.add_column("PnL ($)", justify="right")
    table.add_column("Max DD", justify="center")
    table.add_column("Sharpe", justify="center")
    table.add_column("P.Factor", justify="center")
    table.add_column("Fees ($)", justify="right", style="dim")
    table.add_column("TP/SL/EXP", justify="center")

    for r in results:
        if "error" in r:
            table.add_row(f"{r['threshold']*100:.1f}%", "ERROR", "", "", "", "", "", "", "", "")
            continue

        is_best_sharpe = best_sharpe and r["threshold"] == best_sharpe["threshold"]
        is_best_return = best_return and r["threshold"] == best_return["threshold"]

        th_str = f"{r['threshold']*100:.1f}%"
        if is_best_sharpe:
            th_str += " *"

        ret_style = "green" if r["total_return"] > 0 else "red"
        pnl_style = "green" if r["total_pnl"] > 0 else "red"
        wr_style = "green" if r["win_rate"] >= 50 else "red"
        dd_style = "red" if r["max_drawdown"] > 10 else "yellow" if r["max_drawdown"] > 5 else "green"

        pf_str = f"{r['profit_factor']:.2f}" if r["profit_factor"] != float("inf") else "inf"

        row_style = "bold" if is_best_sharpe else ""

        table.add_row(
            th_str,
            str(r["total_trades"]),
            Text(f"{r['win_rate']:.1f}%", style=wr_style),
            Text(f"{r['total_return']:+.2f}%", style=ret_style),
            Text(f"${r['total_pnl']:+,.2f}", style=pnl_style),
            Text(f"{r['max_drawdown']:.2f}%", style=dd_style),
            f"{r['sharpe']:.2f}",
            pf_str,
            f"${r['total_fees']:,.2f}",
            f"{r['tp_count']}/{r['sl_count']}/{r['exp_count']}",
            style=row_style,
        )

    console.print(table)

    # Recommandation
    if best_sharpe:
        console.print(f"\n[bold green]MEILLEUR SHARPE:[/] Threshold = {best_sharpe['threshold']*100:.1f}% "
                       f"(Sharpe: {best_sharpe['sharpe']:.2f}, Return: {best_sharpe['total_return']:+.2f}%, "
                       f"Win Rate: {best_sharpe['win_rate']:.1f}%, Trades: {best_sharpe['total_trades']})")
    if best_return and best_return != best_sharpe:
        console.print(f"[bold cyan]MEILLEUR RETURN:[/] Threshold = {best_return['threshold']*100:.1f}% "
                       f"(Return: {best_return['total_return']:+.2f}%, Sharpe: {best_return['sharpe']:.2f})")
    if best_pf and best_pf != best_sharpe and best_pf != best_return:
        console.print(f"[bold yellow]MEILLEUR P.FACTOR:[/] Threshold = {best_pf['threshold']*100:.1f}% "
                       f"(PF: {best_pf['profit_factor']:.2f}, Return: {best_pf['total_return']:+.2f}%)")


if __name__ == "__main__":
    main()
