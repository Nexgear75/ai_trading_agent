import argparse
import json
import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from models.rl.agent import PPOAgent
from models.rl.data_preparator import prepare_rl_data
from models.rl.environment import TradingEnv
from models.rl.risk_manager import BUY_ACTIONS, SELL_ACTIONS, ACTION_SELL_100


RESULTS_DIR = "models/rl/results"


def run_backtest(agent: PPOAgent, env: TradingEnv) -> dict:
    """Run a full deterministic backtest on the given environment.

    Returns:
        Dict containing equity curve, trades, and portfolio history.
    """
    obs, _ = env.reset()
    done = False

    equity_curve = [env.initial_cash]
    drawdown_curve = [0.0]
    position_curve = [0.0]
    close_prices = [env.close_prices[env._current_step]]
    actions_taken = []
    trade_returns = []
    n_buys = 0
    n_sells = 0

    # Track trade cycles: entry when going from flat to positioned,
    # exit when position drops back to zero (or close to it)
    was_positioned = False
    entry_value = None

    while not done:
        action, _, _ = agent.select_action(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated

        equity_curve.append(info["portfolio_value"])
        drawdown_curve.append(info["drawdown"])
        position_curve.append(info["position"])
        close_prices.append(env.close_prices[min(env._current_step, len(env.close_prices) - 1)])
        actions_taken.append(info["action_taken"])

        act = info["action_taken"]
        is_positioned = info["position"] > 1e-10

        if act in BUY_ACTIONS:
            n_buys += 1
        if act in SELL_ACTIONS:
            n_sells += 1

        # Track round-trip trade returns: flat → positioned → flat
        if is_positioned and not was_positioned:
            # Just entered a new position
            entry_value = info["portfolio_value"]
        elif not is_positioned and was_positioned and entry_value is not None:
            # Just went flat — record the round-trip return
            trade_ret = (info["portfolio_value"] - entry_value) / entry_value
            trade_returns.append(trade_ret)
            entry_value = None

        was_positioned = is_positioned

    # If still in position at end, count as open trade
    if was_positioned and entry_value is not None:
        trade_ret = (equity_curve[-1] - entry_value) / entry_value
        trade_returns.append(trade_ret)

    return {
        "equity_curve": np.array(equity_curve),
        "drawdown_curve": np.array(drawdown_curve),
        "position_curve": np.array(position_curve),
        "close_prices": np.array(close_prices),
        "actions": actions_taken,
        "trade_returns": np.array(trade_returns) if trade_returns else np.array([0.0]),
        "n_buys": n_buys,
        "n_sells": n_sells,
    }


def compute_metrics(backtest: dict, initial_cash: float = 10_000.0) -> dict:
    """Compute trading performance metrics from backtest results."""
    equity = backtest["equity_curve"]
    trade_returns = backtest["trade_returns"]
    n_steps = len(equity) - 1

    # Basic returns
    total_return = (equity[-1] - initial_cash) / initial_cash
    daily_returns = np.diff(equity) / equity[:-1]
    annualized_return = (1 + total_return) ** (252 / max(n_steps, 1)) - 1

    # Sharpe ratio (annualized)
    if len(daily_returns) > 1 and np.std(daily_returns) > 1e-10:
        sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Sortino ratio (annualized, downside deviation only)
    downside = daily_returns[daily_returns < 0]
    if len(downside) > 0 and np.std(downside) > 1e-10:
        sortino = np.mean(daily_returns) / np.std(downside) * np.sqrt(252)
    else:
        sortino = 0.0

    # Maximum drawdown
    peak = np.maximum.accumulate(equity)
    drawdowns = (equity - peak) / peak
    max_drawdown = drawdowns.min()

    # Calmar ratio
    calmar = annualized_return / abs(max_drawdown) if abs(max_drawdown) > 1e-10 else 0.0

    # Trade statistics
    n_trades = len(trade_returns)
    winning_trades = trade_returns[trade_returns > 0]
    losing_trades = trade_returns[trade_returns < 0]
    win_rate = len(winning_trades) / max(n_trades, 1)
    avg_win = np.mean(winning_trades) if len(winning_trades) > 0 else 0.0
    avg_loss = np.mean(losing_trades) if len(losing_trades) > 0 else 0.0
    win_loss_ratio = abs(avg_win / avg_loss) if abs(avg_loss) > 1e-10 else float("inf")

    # Buy-and-hold comparison
    prices = backtest["close_prices"]
    bnh_return = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0.0

    # Action distribution
    from models.rl.risk_manager import N_ACTIONS as _N_ACT
    actions = backtest["actions"]
    action_counts = {i: actions.count(i) for i in range(_N_ACT)} if actions else {}

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar,
        "n_trades": n_trades,
        "n_buys": backtest.get("n_buys", 0),
        "n_sells": backtest.get("n_sells", 0),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "win_loss_ratio": win_loss_ratio,
        "buy_and_hold_return": bnh_return,
        "alpha": total_return - bnh_return,
        "n_steps": n_steps,
        "action_distribution": action_counts,
    }


def plot_results(backtest: dict, metrics: dict, save_dir: str):
    """Generate and save all evaluation visualizations."""
    os.makedirs(save_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")

    equity = backtest["equity_curve"]
    prices = backtest["close_prices"]
    drawdowns = backtest["drawdown_curve"]
    positions = backtest["position_curve"]
    trade_returns = backtest["trade_returns"]

    # 1. Equity Curve vs Buy-and-Hold
    fig, ax = plt.subplots(figsize=(14, 6))
    steps = np.arange(len(equity))
    ax.plot(steps, equity, label="RL Agent", color="blue", linewidth=1.5)
    # Buy-and-hold normalized to same initial cash
    bnh = prices / prices[0] * equity[0]
    ax.plot(steps, bnh, label="Buy & Hold", color="gray", linewidth=1, alpha=0.7)
    ax.set_xlabel("Trading Day")
    ax.set_ylabel("Portfolio Value ($)")
    ax.set_title(f"Equity Curve — Return: {metrics['total_return']:.1%} | Sharpe: {metrics['sharpe_ratio']:.2f}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(save_dir, "equity_curve.png"), dpi=150)
    plt.close(fig)

    # 2. Drawdown Over Time
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.fill_between(range(len(drawdowns)), drawdowns, 0, color="red", alpha=0.3)
    ax.plot(drawdowns, color="red", linewidth=0.8)
    ax.set_xlabel("Trading Day")
    ax.set_ylabel("Drawdown")
    ax.set_title(f"Drawdown — Max: {metrics['max_drawdown']:.1%}")
    fig.tight_layout()
    fig.savefig(os.path.join(save_dir, "drawdown.png"), dpi=150)
    plt.close(fig)

    # 3. Position Timeline
    fig, ax = plt.subplots(figsize=(14, 3))
    ax.fill_between(range(len(positions)), positions, 0, where=np.array(positions) > 0, color="green", alpha=0.4, label="Long")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("Trading Day")
    ax.set_ylabel("Position (units)")
    ax.set_title("Position Timeline")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(save_dir, "position_timeline.png"), dpi=150)
    plt.close(fig)

    # 4. Rolling Sharpe Ratio (60-day window)
    if len(equity) > 61:
        daily_ret = np.diff(equity) / equity[:-1]
        rolling_sharpe = []
        for i in range(60, len(daily_ret)):
            window = daily_ret[i - 60 : i]
            rs = np.mean(window) / (np.std(window) + 1e-10) * np.sqrt(252)
            rolling_sharpe.append(rs)

        fig, ax = plt.subplots(figsize=(14, 4))
        ax.plot(rolling_sharpe, color="purple", linewidth=1)
        ax.axhline(0, color="black", linewidth=0.5, linestyle="--")
        ax.set_xlabel("Trading Day (offset 60)")
        ax.set_ylabel("Sharpe Ratio (annualized)")
        ax.set_title("Rolling 60-Day Sharpe Ratio")
        fig.tight_layout()
        fig.savefig(os.path.join(save_dir, "rolling_sharpe.png"), dpi=150)
        plt.close(fig)

    # 5. Trade Return Distribution
    if len(trade_returns) > 1:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(trade_returns, bins=30, color="steelblue", edgecolor="white", alpha=0.8)
        ax.axvline(0, color="red", linewidth=1, linestyle="--")
        ax.set_xlabel("Trade Return")
        ax.set_ylabel("Count")
        ax.set_title(f"Trade Returns — Win Rate: {metrics['win_rate']:.1%} | Trades: {metrics['n_trades']}")
        fig.tight_layout()
        fig.savefig(os.path.join(save_dir, "trade_distribution.png"), dpi=150)
        plt.close(fig)

    print(f"Plots saved to {save_dir}/")


def print_metrics(metrics: dict):
    """Pretty-print evaluation metrics."""
    print("\n" + "=" * 50)
    print("BACKTEST RESULTS")
    print("=" * 50)
    print(f"  Total Return:       {metrics['total_return']:+.2%}")
    print(f"  Annualized Return:  {metrics['annualized_return']:+.2%}")
    print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:.3f}")
    print(f"  Sortino Ratio:      {metrics['sortino_ratio']:.3f}")
    print(f"  Max Drawdown:       {metrics['max_drawdown']:.2%}")
    print(f"  Calmar Ratio:       {metrics['calmar_ratio']:.3f}")
    print("-" * 50)
    print(f"  Round-trip Trades:  {metrics['n_trades']}")
    print(f"  Buy Orders:         {metrics.get('n_buys', '?')}")
    print(f"  Sell Orders:        {metrics.get('n_sells', '?')}")
    print(f"  Win Rate:           {metrics['win_rate']:.1%}")
    print(f"  Avg Win:            {metrics['avg_win']:+.3%}")
    print(f"  Avg Loss:           {metrics['avg_loss']:+.3%}")
    print(f"  Win/Loss Ratio:     {metrics['win_loss_ratio']:.2f}")
    print("-" * 50)
    print(f"  Buy & Hold Return:  {metrics['buy_and_hold_return']:+.2%}")
    print(f"  Alpha (vs B&H):     {metrics['alpha']:+.2%}")
    print(f"  Steps:              {metrics['n_steps']}")
    if metrics.get("action_distribution"):
        print(f"  Action Dist:        {metrics['action_distribution']}")
    print("=" * 50)


def run_evaluation(
    model_path: str,
    symbol: str | None = None,
    save_dir: str = RESULTS_DIR,
):
    """Full evaluation pipeline: load model, backtest, compute metrics, plot.

    Args:
        model_path: Path to saved agent checkpoint.
        symbol: Symbol to evaluate on. None = BTC default.
        save_dir: Directory to save results.
    """
    # Prepare data
    eval_symbol = symbol or "BTC"
    _, df_val, scaler, clip_bounds = prepare_rl_data(eval_symbol)

    # Build environment (no randomization, no noise)
    env = TradingEnv(
        df=df_val,
        feature_scaler=scaler,
        clip_bounds=clip_bounds,
        randomize_start=False,
        noise_std=0.0,
    )

    # Load agent
    agent = PPOAgent()
    agent.load(model_path)

    # Run backtest
    backtest = run_backtest(agent, env)
    metrics = compute_metrics(backtest)

    # Display and save
    print_metrics(metrics)
    plot_results(backtest, metrics, save_dir)

    # Save metrics as JSON
    serializable_metrics = {k: float(v) if isinstance(v, (np.floating, float)) else v for k, v in metrics.items()}
    with open(os.path.join(save_dir, "metrics.json"), "w") as f:
        json.dump(serializable_metrics, f, indent=2)

    return metrics


def run_evaluation_all(
    model_path: str,
    save_dir: str = RESULTS_DIR,
    use_finetuned: bool = False,
):
    """Evaluate the agent on all 10 symbols and print a summary table.

    Args:
        model_path: Path to the base agent checkpoint.
        save_dir: Directory to save results.
        use_finetuned: If True, use per-symbol fine-tuned checkpoints
                       (best_agent_{SYMBOL}.pth) when available.
    """
    from config import SYMBOLS

    checkpoint_dir = os.path.dirname(model_path)
    all_metrics = {}

    for symbol in SYMBOLS:
        short_name = symbol.replace("/USDT", "")
        print(f"\n--- Evaluating {symbol} ---")

        # Use fine-tuned checkpoint if available and requested
        effective_path = model_path
        if use_finetuned:
            ft_path = os.path.join(checkpoint_dir, f"best_agent_{short_name}.pth")
            if os.path.isfile(ft_path):
                effective_path = ft_path
                print(f"  Using fine-tuned model: {ft_path}")
            else:
                print(f"  No fine-tuned model for {short_name}, using base model")

        try:
            sym_dir = os.path.join(save_dir, short_name)
            metrics = run_evaluation(effective_path, short_name, sym_dir)
            all_metrics[short_name] = metrics
        except Exception as e:
            print(f"  Skipped {symbol}: {e}")

    # Summary table
    print("\n" + "=" * 115)
    print(f"{'Symbol':<8} {'Return':>10} {'B&H':>10} {'Alpha':>10} {'Sharpe':>8} {'Sortino':>8} {'MaxDD':>8} {'WinRate':>8} {'Trips':>6} {'Buys':>6} {'Sells':>6}")
    print("-" * 115)

    total_return = 0.0
    total_bnh = 0.0

    for sym, m in all_metrics.items():
        print(
            f"{sym:<8} "
            f"{m['total_return']:>+9.2%} "
            f"{m['buy_and_hold_return']:>+9.2%} "
            f"{m['alpha']:>+9.2%} "
            f"{m['sharpe_ratio']:>8.3f} "
            f"{m['sortino_ratio']:>8.3f} "
            f"{m['max_drawdown']:>8.2%} "
            f"{m['win_rate']:>7.1%} "
            f"{m['n_trades']:>6d} "
            f"{m.get('n_buys', 0):>6d} "
            f"{m.get('n_sells', 0):>6d}"
        )
        total_return += m["total_return"]
        total_bnh += m["buy_and_hold_return"]

    n = len(all_metrics)
    if n > 0:
        avg_sharpe = np.mean([m["sharpe_ratio"] for m in all_metrics.values()])
        avg_sortino = np.mean([m["sortino_ratio"] for m in all_metrics.values()])
        avg_dd = np.mean([m["max_drawdown"] for m in all_metrics.values()])
        avg_wr = np.mean([m["win_rate"] for m in all_metrics.values()])
        total_buys = sum(m.get("n_buys", 0) for m in all_metrics.values())
        total_sells = sum(m.get("n_sells", 0) for m in all_metrics.values())
        total_trips = sum(m["n_trades"] for m in all_metrics.values())
        print("-" * 115)
        print(
            f"{'AVG':<8} "
            f"{total_return / n:>+9.2%} "
            f"{total_bnh / n:>+9.2%} "
            f"{(total_return - total_bnh) / n:>+9.2%} "
            f"{avg_sharpe:>8.3f} "
            f"{avg_sortino:>8.3f} "
            f"{avg_dd:>8.2%} "
            f"{avg_wr:>7.1%} "
            f"{total_trips:>6d} "
            f"{total_buys:>6d} "
            f"{total_sells:>6d}"
        )
    print("=" * 115)

    # Save combined metrics
    serializable = {}
    for sym, m in all_metrics.items():
        serializable[sym] = {k: float(v) if isinstance(v, (np.floating, float)) else v for k, v in m.items()}
    with open(os.path.join(save_dir, "all_metrics.json"), "w") as f:
        json.dump(serializable, f, indent=2)

    return all_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RL trading agent")
    parser.add_argument("--model-path", type=str, default="models/rl/checkpoints/best_agent.pth", help="Path to agent checkpoint.")
    parser.add_argument("--symbol", type=str, default=None, help="Symbol to evaluate (e.g. BTC).")
    parser.add_argument("--all", action="store_true", help="Evaluate on all 10 symbols.")
    parser.add_argument("--finetuned", action="store_true", help="Use per-symbol fine-tuned checkpoints when available.")
    parser.add_argument("--save-dir", type=str, default=RESULTS_DIR, help="Directory to save results.")

    args = parser.parse_args()
    if args.all:
        run_evaluation_all(args.model_path, args.save_dir, use_finetuned=args.finetuned)
    else:
        run_evaluation(args.model_path, args.symbol, args.save_dir)
