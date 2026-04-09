"""
Simulate 1 year of trading with 1000€ per crypto.
Compares the RL agent strategy vs simple buy-and-hold.

Usage:
    python simulate.py
    python simulate.py --model models/rl/checkpoints/best_agent.pth
    python simulate.py --finetuned
"""

import argparse
import os

import numpy as np

from config import SYMBOLS
from models.rl.agent import PPOAgent
from models.rl.data_preparator import prepare_rl_data
from models.rl.environment import TradingEnv


INITIAL_CAPITAL = 1000.0  # € per crypto


def simulate_symbol(agent, symbol, use_finetuned=False, checkpoint_dir="models/rl/checkpoints"):
    """Run simulation for one symbol. Returns (agent_final, bnh_final, details)."""
    short = symbol.replace("/USDT", "")

    # Load fine-tuned model if available
    if use_finetuned:
        ft_path = os.path.join(checkpoint_dir, f"best_agent_{short}.pth")
        if os.path.isfile(ft_path):
            agent.load(ft_path)

    _, df_val, scaler, clip_bounds = prepare_rl_data(short, verbose=False)

    env = TradingEnv(
        df=df_val,
        feature_scaler=scaler,
        clip_bounds=clip_bounds,
        initial_cash=INITIAL_CAPITAL,
        randomize_start=False,
        noise_std=0.0,
    )

    # --- RL Agent simulation ---
    obs, _ = env.reset()
    done = False
    n_buys, n_sells = 0, 0

    while not done:
        action, _, _ = agent.select_action(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        act = info["action_taken"]
        if act in (1, 2, 3):
            n_buys += 1
        if act in (4, 5, 6):
            n_sells += 1

    agent_final = info["portfolio_value"]

    # --- Buy & Hold simulation ---
    # Always use full 252-day window, regardless of when the agent's episode ended
    start_price = env.close_prices[env._start_idx]
    bnh_end_idx = min(env._start_idx + 252, len(env.close_prices) - 1)
    end_price = env.close_prices[bnh_end_idx]
    units_bought = INITIAL_CAPITAL / start_price
    bnh_final = units_bought * end_price

    return agent_final, bnh_final, {
        "buys": n_buys,
        "sells": n_sells,
        "agent_return": (agent_final - INITIAL_CAPITAL) / INITIAL_CAPITAL,
        "bnh_return": (bnh_final - INITIAL_CAPITAL) / INITIAL_CAPITAL,
    }


def main(model_path, use_finetuned=False):
    checkpoint_dir = os.path.dirname(model_path)

    # Load base agent once
    agent = PPOAgent()
    agent.load(model_path, verbose=False)

    print(f"\n{'='*80}")
    print(f"  1-YEAR SIMULATION — {INITIAL_CAPITAL:.0f}€ per crypto ({len(SYMBOLS)} cryptos)")
    print(f"  Total portfolio: {INITIAL_CAPITAL * len(SYMBOLS):.0f}€")
    print(f"{'='*80}")
    print(f"  Loading data...\n")

    total_agent = 0.0
    total_bnh = 0.0
    results = {}

    print(f"{'Symbol':<12} {'Agent':>12} {'B&H':>12} {'Agent %':>10} {'B&H %':>10} {'Diff':>10} {'Orders':>10}")
    print("-" * 80)

    for symbol in SYMBOLS:
        short = symbol.replace("/USDT", "")

        # Reload base model each time (fine-tuning modifies it)
        if use_finetuned:
            agent_copy = PPOAgent()
            ft_path = os.path.join(checkpoint_dir, f"best_agent_{short}.pth")
            if os.path.isfile(ft_path):
                agent_copy.load(ft_path, verbose=False)
            else:
                agent_copy.load(model_path, verbose=False)
        else:
            agent_copy = agent

        try:
            agent_val, bnh_val, details = simulate_symbol(agent_copy, symbol)
            results[short] = details
            total_agent += agent_val
            total_bnh += bnh_val

            diff = agent_val - bnh_val
            sign = "+" if diff >= 0 else ""

            print(
                f"{short:<12} "
                f"  {agent_val:>9.2f}€ "
                f"  {bnh_val:>9.2f}€ "
                f"  {details['agent_return']:>+8.2%} "
                f"  {details['bnh_return']:>+8.2%} "
                f"  {sign}{diff:>8.2f}€ "
                f"  {details['buys']}B/{details['sells']}S"
            )
        except Exception as e:
            print(f"{short:<12}  ERROR: {e}")

    # Portfolio totals
    initial_total = INITIAL_CAPITAL * len(SYMBOLS)
    agent_profit = total_agent - initial_total
    bnh_profit = total_bnh - initial_total

    print("-" * 80)
    print(f"\n{'PORTFOLIO SUMMARY':^80}")
    print(f"{'='*80}")
    print(f"  Initial Investment:      {initial_total:>10.2f}€")
    print()
    print(f"  RL Agent Final Value:    {total_agent:>10.2f}€")
    print(f"  RL Agent Profit/Loss:    {agent_profit:>+10.2f}€  ({agent_profit/initial_total:>+.2%})")
    print()
    print(f"  Buy & Hold Final Value:  {total_bnh:>10.2f}€")
    print(f"  Buy & Hold Profit/Loss:  {bnh_profit:>+10.2f}€  ({bnh_profit/initial_total:>+.2%})")
    print()
    edge = total_agent - total_bnh
    print(f"  Agent Edge over B&H:     {edge:>+10.2f}€  ({edge/initial_total:>+.2%})")
    print(f"{'='*80}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate 1 year of trading with 1000€ per crypto")
    parser.add_argument("--model", type=str, default="models/rl/checkpoints/best_agent.pth", help="Path to agent checkpoint.")
    parser.add_argument("--finetuned", action="store_true", help="Use per-symbol fine-tuned models.")
    args = parser.parse_args()

    main(args.model, args.finetuned)
