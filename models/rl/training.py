import argparse
import os
import time

import numpy as np

from config import SYMBOLS, update_global_config

update_global_config("6h")
from models.rl.agent import PPOAgent, PPOConfig
from models.rl.data_preparator import prepare_multi_symbol_data, prepare_rl_data
from models.rl.environment import TradingEnv
from models.rl.risk_manager import RiskConfig, N_ACTIONS


CHECKPOINT_DIR = "models/rl/checkpoints"
RESULTS_DIR = "models/rl/results"


def make_env(df, feature_scaler, clip_bounds, reward_mode="dsr", noise_std=0.0, randomize_start=True, risk_config=None):
    """Create a TradingEnv from prepared data."""
    return TradingEnv(
        df=df,
        feature_scaler=feature_scaler,
        clip_bounds=clip_bounds,
        reward_mode=reward_mode,
        noise_std=noise_std,
        randomize_start=randomize_start,
        risk_config=risk_config,
    )


def _make_training_risk_config() -> RiskConfig:
    """Permissive RiskConfig for training: disables the auto-exit overrides
    (take-profit, adaptive stop-loss, buy cooldown) so the agent gets honest
    credit assignment for its own buy/sell decisions. Keeps only structural
    constraints (can't buy beyond max_position, can't sell without one) and
    a loose drawdown safety net.

    The predictor uses its own default RiskConfig at inference time, so this
    only affects the training environment.
    """
    return RiskConfig(
        take_profit=999.0,
        stop_loss_min=999.0,
        stop_loss_max=999.0,
        max_drawdown=0.50,
        max_consecutive_buys=999,
    )


def evaluate_agent(agent, env, n_episodes=5):
    """Run deterministic evaluation episodes.

    Returns:
        Dict with average metrics across episodes.
    """
    returns = []
    sharpe_values = []
    max_drawdowns = []

    for _ in range(n_episodes):
        obs, _ = env.reset()
        episode_returns = []
        done = False

        while not done:
            action, _, _ = agent.select_action(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_returns.append(info["portfolio_return"])
            done = terminated or truncated

        final_return = episode_returns[-1] if episode_returns else 0.0
        returns.append(final_return)

        # Compute Sharpe from step returns
        if len(episode_returns) > 1:
            step_returns = np.diff([0.0] + episode_returns)
            sharpe = np.mean(step_returns) / (np.std(step_returns) + 1e-8) * np.sqrt(1460)  # annualized for 6h candles
        else:
            sharpe = 0.0
        sharpe_values.append(sharpe)

        max_dd = min(info.get("drawdown", 0.0) for _ in [0])  # Last drawdown
        max_drawdowns.append(info.get("drawdown", 0.0))

    return {
        "avg_return": np.mean(returns),
        "avg_sharpe": np.mean(sharpe_values),
        "avg_max_drawdown": np.mean(max_drawdowns),
    }


def train(
    symbol: str | None = None,
    total_timesteps: int = 2_000_000,
    reward_mode: str = "dsr",
    pretrained_backbone: str | None = None,
    curriculum: bool = True,
    eval_interval: int = 50_000,
    eval_episodes: int = 5,
    rollout_length: int = 336,
):
    """Main training loop.

    Args:
        symbol: Single symbol to train on, or None for multi-asset.
        total_timesteps: Total training steps across all environments.
        reward_mode: Reward function type.
        pretrained_backbone: Path to pretrained CNN1D checkpoint.
        curriculum: Whether to use curriculum learning (3 phases).
        eval_interval: Steps between validation evaluations.
        eval_episodes: Number of episodes per evaluation.
        rollout_length: Steps per rollout before PPO update.
    """
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Prepare data
    train_risk = _make_training_risk_config()

    if symbol:
        df_train, df_val, scaler, clip_bounds = prepare_rl_data(symbol)
        train_envs = [make_env(df_train, scaler, clip_bounds, reward_mode, noise_std=0.02, risk_config=train_risk)]
        val_env = make_env(df_val, scaler, clip_bounds, reward_mode, noise_std=0.0, randomize_start=False, risk_config=train_risk)
    else:
        data = prepare_multi_symbol_data()
        scaler = data["feature_scaler"]
        clip_bounds = data["clip_bounds"]
        train_envs = [
            make_env(df, scaler, clip_bounds, reward_mode, noise_std=0.02, risk_config=train_risk)
            for df in data["train_dfs"].values()
        ]
        # Use BTC validation as primary eval
        btc_key = next((k for k in data["val_dfs"] if "BTC" in k), list(data["val_dfs"].keys())[0])
        val_env = make_env(data["val_dfs"][btc_key], scaler, clip_bounds, reward_mode, noise_std=0.0, randomize_start=False, risk_config=train_risk)

    # Build agent
    config = PPOConfig()
    agent = PPOAgent(config=config, pretrained_backbone_path=pretrained_backbone)
    print(f"Device: {agent.device}")
    print(f"Training with {len(train_envs)} environment(s), {total_timesteps} total steps")

    # Curriculum learning phases
    if curriculum and pretrained_backbone:
        phases = [
            {"name": "Phase 1: Frozen backbone, 50% costs", "steps": int(total_timesteps * 0.1), "freeze": True, "cost_mult": 0.5},
            {"name": "Phase 2: Unfrozen backbone, 50% costs", "steps": int(total_timesteps * 0.5), "freeze": False, "cost_mult": 0.5},
            {"name": "Phase 3: Full realistic costs", "steps": int(total_timesteps * 0.4), "freeze": False, "cost_mult": 1.0},
        ]
    else:
        phases = [
            {"name": "Training", "steps": total_timesteps, "freeze": False, "cost_mult": 1.0},
        ]

    # Training loop
    best_sharpe = -np.inf
    eval_degradation_count = 0
    early_stop_patience = 10          # more patience before stopping
    warmup_steps = 100_000            # no early stopping during warmup
    global_step = 0
    training_history = []

    for phase in phases:
        print(f"\n{'='*60}")
        print(f"{phase['name']} — {phase['steps']} steps")
        print(f"{'='*60}")

        if phase["freeze"]:
            agent.freeze_backbone()
        else:
            agent.unfreeze_backbone()

        # Adjust transaction costs for curriculum
        for env in train_envs:
            original_cost = RiskConfig().trade_cost
            env.risk_manager.config.trade_cost = original_cost * phase["cost_mult"]

        phase_steps = 0
        env_idx = 0

        # Reset all environments
        observations = [env.reset()[0] for env in train_envs]

        while phase_steps < phase["steps"]:
            # Cycle through environments
            env = train_envs[env_idx]
            obs = observations[env_idx]

            # Collect rollout
            episode_rewards = []
            episode_actions = []
            for _ in range(rollout_length):
                action, log_prob, value = agent.select_action(obs)
                next_obs, reward, terminated, truncated, info = env.step(action)
                done = terminated or truncated

                agent.store_transition(obs, action, log_prob, reward, value, done)
                episode_rewards.append(reward)
                episode_actions.append(info["action_taken"])

                if done:
                    next_obs, _ = env.reset()

                obs = next_obs
                phase_steps += 1
                global_step += 1

                if phase_steps >= phase["steps"]:
                    break

            observations[env_idx] = obs

            # PPO update
            metrics = agent.update(obs)
            if metrics:
                training_history.append({
                    "step": global_step,
                    **metrics,
                })

            # Cycle to next environment
            env_idx = (env_idx + 1) % len(train_envs)

            # Log rollout stats
            if episode_actions:
                from collections import Counter
                action_dist = Counter(episode_actions)
                avg_reward = np.mean(episode_rewards)
                act_short = " ".join(f"{a}:{action_dist.get(a,0)}" for a in range(N_ACTIONS))
                pct = global_step / total_timesteps * 100
                print(
                    f"    [{pct:5.1f}%] step {global_step:>8d} | "
                    f"avgR: {avg_reward:+.5f} | "
                    f"PLoss: {metrics.get('policy_loss', 0):+.4f} | "
                    f"VLoss: {metrics.get('value_loss', 0):.4f} | "
                    f"Ent: {metrics.get('entropy', 0):.3f} | "
                    f"EntC: {agent.entropy_coeff:.4f} | "
                    f"Act: [{act_short}]"
                )

            # Periodic evaluation
            if global_step % eval_interval < rollout_length:
                eval_metrics = evaluate_agent(agent, val_env, n_episodes=eval_episodes)
                act_str = " ".join(f"{a}:{action_dist.get(a,0)}" for a in range(N_ACTIONS))
                print(
                    f"  Step {global_step:>8d} | "
                    f"Return: {eval_metrics['avg_return']:+.4f} | "
                    f"Sharpe: {eval_metrics['avg_sharpe']:+.3f} | "
                    f"AvgR: {avg_reward:+.5f} | "
                    f"PLoss: {metrics.get('policy_loss', 0):.4f} | "
                    f"VLoss: {metrics.get('value_loss', 0):.4f} | "
                    f"Ent: {metrics.get('entropy', 0):.3f} | "
                    f"Act: [{act_str}]"
                )

                # Save best model
                if eval_metrics["avg_sharpe"] > best_sharpe:
                    best_sharpe = eval_metrics["avg_sharpe"]
                    agent.save(os.path.join(CHECKPOINT_DIR, "best_agent.pth"))
                    eval_degradation_count = 0
                elif global_step > warmup_steps:
                    # Only count degradation after warmup
                    eval_degradation_count += 1

                # Early stopping (only after warmup)
                if eval_degradation_count >= early_stop_patience and global_step > warmup_steps:
                    print(f"\nEarly stopping: Sharpe degraded {eval_degradation_count} times. Best: {best_sharpe:.3f}")
                    break

        if eval_degradation_count >= early_stop_patience and global_step > warmup_steps:
            break

    # Save final model
    agent.save(os.path.join(CHECKPOINT_DIR, "final_agent.pth"))

    # Save training history
    import json
    with open(os.path.join(RESULTS_DIR, "training_history.json"), "w") as f:
        json.dump(training_history, f, indent=2)

    print(f"\nTraining complete. Best Sharpe: {best_sharpe:.3f}")
    print(f"Checkpoints saved to {CHECKPOINT_DIR}/")

    return agent, training_history


def finetune(
    base_model_path: str = os.path.join(CHECKPOINT_DIR, "best_agent.pth"),
    timesteps_per_symbol: int = 200_000,
    reward_mode: str = "log_return",
    eval_interval: int = 25_000,
    rollout_length: int = 336,
):
    """Fine-tune the base multi-asset agent on each symbol individually.

    Loads the best agent from multi-asset training, then trains a separate
    copy on each symbol. Saves per-symbol checkpoints.

    Args:
        base_model_path: Path to the multi-asset trained agent.
        timesteps_per_symbol: Training steps per symbol.
        reward_mode: Reward function type.
        eval_interval: Steps between evaluations.
        rollout_length: Steps per rollout.
    """
    from config import SYMBOLS

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    for symbol_full in SYMBOLS:
        short = symbol_full.replace("/USDT", "")
        print(f"\n{'#'*60}")
        print(f"  Fine-tuning on {symbol_full} — {timesteps_per_symbol} steps")
        print(f"{'#'*60}")

        # Prepare single-symbol data
        df_train, df_val, scaler, clip_bounds = prepare_rl_data(short)
        train_risk = _make_training_risk_config()
        train_env = make_env(df_train, scaler, clip_bounds, reward_mode, noise_std=0.02, risk_config=train_risk)
        val_env = make_env(df_val, scaler, clip_bounds, reward_mode, noise_std=0.0, randomize_start=False, risk_config=train_risk)

        # Load base agent (fresh copy each symbol)
        config = PPOConfig()
        # Lower learning rates for fine-tuning
        config.lr_policy = 1e-4
        config.lr_value = 3e-4
        config.lr_backbone = 1e-5
        # Start with moderate entropy to explore
        config.entropy_coeff_start = 0.03
        config.entropy_coeff_end = 0.010
        config.entropy_anneal_steps = timesteps_per_symbol // 2  # anneal over first half

        agent = PPOAgent(config=config)
        agent.load(base_model_path)

        best_sharpe = -np.inf
        eval_degradation_count = 0
        global_step = 0

        obs, _ = train_env.reset()

        while global_step < timesteps_per_symbol:
            # Collect rollout
            episode_rewards = []
            episode_actions = []
            for _ in range(rollout_length):
                action, log_prob, value = agent.select_action(obs)
                next_obs, reward, terminated, truncated, info = train_env.step(action)
                done = terminated or truncated

                agent.store_transition(obs, action, log_prob, reward, value, done)
                episode_rewards.append(reward)
                episode_actions.append(info["action_taken"])

                if done:
                    next_obs, _ = train_env.reset()

                obs = next_obs
                global_step += 1

                if global_step >= timesteps_per_symbol:
                    break

            # PPO update
            metrics = agent.update(obs)

            # Log
            if episode_actions:
                from collections import Counter
                action_dist = Counter(episode_actions)
                avg_reward = np.mean(episode_rewards)
                act_short = " ".join(f"{a}:{action_dist.get(a,0)}" for a in range(N_ACTIONS))
                pct = global_step / timesteps_per_symbol * 100
                print(
                    f"    [{pct:5.1f}%] step {global_step:>7d} | "
                    f"avgR: {avg_reward:+.5f} | "
                    f"PLoss: {metrics.get('policy_loss', 0):+.4f} | "
                    f"Ent: {metrics.get('entropy', 0):.3f} | "
                    f"EntC: {agent.entropy_coeff:.4f} | "
                    f"Act: [{act_short}]"
                )

            # Periodic evaluation
            if global_step % eval_interval < rollout_length:
                eval_metrics = evaluate_agent(agent, val_env, n_episodes=3)
                print(
                    f"  ** EVAL {short} step {global_step:>7d} | "
                    f"Return: {eval_metrics['avg_return']:+.4f} | "
                    f"Sharpe: {eval_metrics['avg_sharpe']:+.3f}"
                )

                if eval_metrics["avg_sharpe"] > best_sharpe:
                    best_sharpe = eval_metrics["avg_sharpe"]
                    save_path = os.path.join(CHECKPOINT_DIR, f"best_agent_{short}.pth")
                    agent.save(save_path)
                    eval_degradation_count = 0
                else:
                    eval_degradation_count += 1

                if eval_degradation_count >= 5:
                    print(f"  Early stopping {short}: Sharpe degraded 5 times. Best: {best_sharpe:.3f}")
                    break

        print(f"  {short} fine-tuning complete. Best Sharpe: {best_sharpe:.3f}")

    print(f"\nAll fine-tuning complete. Checkpoints saved to {CHECKPOINT_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RL trading agent")
    parser.add_argument("--symbol", type=str, default=None, help="Symbol to train on (e.g. BTC). None = all.")
    parser.add_argument("--timesteps", type=int, default=2_000_000, help="Total training timesteps.")
    parser.add_argument("--reward", type=str, default="log_return", choices=["dsr", "sortino", "log_return"], help="Reward function.")
    parser.add_argument("--pretrained", type=str, default=None, help="Path to pretrained CNN1D checkpoint.")
    parser.add_argument("--no-curriculum", action="store_true", help="Disable curriculum learning.")
    parser.add_argument("--eval-interval", type=int, default=50_000, help="Steps between evaluations.")
    parser.add_argument("--rollout-length", type=int, default=336, help="Steps per rollout.")
    parser.add_argument("--finetune", action="store_true", help="Fine-tune base agent on each symbol individually.")
    parser.add_argument("--finetune-steps", type=int, default=200_000, help="Steps per symbol during fine-tuning.")
    parser.add_argument("--base-model", type=str, default="models/rl/checkpoints/best_agent.pth", help="Base model for fine-tuning.")

    args = parser.parse_args()

    if args.finetune:
        finetune(
            base_model_path=args.base_model,
            timesteps_per_symbol=args.finetune_steps,
            reward_mode=args.reward,
            eval_interval=args.eval_interval,
            rollout_length=args.rollout_length,
        )
    else:
        train(
            symbol=args.symbol,
            total_timesteps=args.timesteps,
            reward_mode=args.reward,
            pretrained_backbone=args.pretrained,
            curriculum=not args.no_curriculum,
            eval_interval=args.eval_interval,
            rollout_length=args.rollout_length,
        )
