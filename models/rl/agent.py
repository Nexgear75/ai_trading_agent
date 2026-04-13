import numpy as np
import torch
import torch.nn as nn
from dataclasses import dataclass, field

from models.rl.networks import FeatureExtractor, PolicyNetwork, ValueNetwork


@dataclass
class PPOConfig:
    """PPO hyperparameters."""
    lr_policy: float = 3e-4
    lr_value: float = 1e-3
    lr_backbone: float = 3e-5
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    entropy_coeff: float = 0.10  # higher to prevent policy collapse
    value_coeff: float = 0.5
    max_grad_norm: float = 0.5
    n_epochs_per_update: int = 4
    minibatch_size: int = 256
    weight_decay: float = 1e-5


class RolloutBuffer:
    """Stores experience from a single rollout for PPO updates."""

    def __init__(self):
        self.market_obs = []
        self.portfolio_obs = []
        self.actions = []
        self.log_probs = []
        self.rewards = []
        self.values = []
        self.dones = []

    def add(
        self,
        market_obs: np.ndarray,
        portfolio_obs: np.ndarray,
        action: int,
        log_prob: float,
        reward: float,
        value: float,
        done: bool,
    ):
        self.market_obs.append(market_obs)
        self.portfolio_obs.append(portfolio_obs)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.values.append(value)
        self.dones.append(done)

    def clear(self):
        self.market_obs.clear()
        self.portfolio_obs.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.values.clear()
        self.dones.clear()

    def __len__(self):
        return len(self.rewards)

    def to_tensors(self, device: torch.device) -> dict:
        """Convert stored arrays to tensors."""
        return {
            "market_obs": torch.tensor(np.array(self.market_obs), dtype=torch.float32, device=device),
            "portfolio_obs": torch.tensor(np.array(self.portfolio_obs), dtype=torch.float32, device=device),
            "actions": torch.tensor(np.array(self.actions), dtype=torch.long, device=device),
            "log_probs": torch.tensor(np.array(self.log_probs), dtype=torch.float32, device=device),
            "rewards": torch.tensor(np.array(self.rewards), dtype=torch.float32, device=device),
            "values": torch.tensor(np.array(self.values), dtype=torch.float32, device=device),
            "dones": torch.tensor(np.array(self.dones), dtype=torch.float32, device=device),
        }


def compute_gae(
    rewards: torch.Tensor,
    values: torch.Tensor,
    dones: torch.Tensor,
    next_value: float,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute Generalized Advantage Estimation.

    Args:
        rewards: (T,) step rewards.
        values: (T,) value estimates.
        dones: (T,) episode termination flags.
        next_value: V(s_{T+1}) bootstrap value.
        gamma: Discount factor.
        gae_lambda: GAE lambda.

    Returns:
        (advantages, returns) both shape (T,).
    """
    T = len(rewards)
    advantages = torch.zeros(T, device=rewards.device)
    gae = 0.0

    for t in reversed(range(T)):
        if t == T - 1:
            next_val = next_value
        else:
            next_val = values[t + 1].item()

        next_non_terminal = 1.0 - dones[t].item()
        delta = rewards[t].item() + gamma * next_val * next_non_terminal - values[t].item()
        gae = delta + gamma * gae_lambda * next_non_terminal * gae
        advantages[t] = gae

    returns = advantages + values
    return advantages, returns


class PPOAgent:
    """Proximal Policy Optimization agent for trading.

    Manages the policy network, value network, shared backbone,
    rollout buffer, and PPO update logic.
    """

    def __init__(
        self,
        config: PPOConfig | None = None,
        pretrained_backbone_path: str | None = None,
        device: str | None = None,
    ):
        self.config = config or PPOConfig()

        if device:
            self.device = torch.device(device)
        elif torch.cuda.is_available():
            self.device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = torch.device("mps")
        else:
            self.device = torch.device("cpu")

        # Build networks with SEPARATE backbones
        # Sharing a backbone caused value loss (~50k) to dominate and
        # prevent policy learning. Separate backbones let each learn independently.
        if pretrained_backbone_path:
            self.policy_backbone = FeatureExtractor.from_pretrained_cnn(pretrained_backbone_path)
            self.value_backbone = FeatureExtractor.from_pretrained_cnn(pretrained_backbone_path)
        else:
            self.policy_backbone = FeatureExtractor()
            self.value_backbone = FeatureExtractor()

        self.policy = PolicyNetwork(self.policy_backbone)
        self.value = ValueNetwork(self.value_backbone)

        self.policy.to(self.device)
        self.value.to(self.device)

        # Separate optimizers so value updates can't affect policy backbone
        self.policy_optimizer = torch.optim.Adam([
            {"params": self.policy_backbone.parameters(), "lr": self.config.lr_backbone},
            {"params": self.policy.policy_head.parameters(), "lr": self.config.lr_policy},
        ], weight_decay=self.config.weight_decay)

        self.value_optimizer = torch.optim.Adam([
            {"params": self.value_backbone.parameters(), "lr": self.config.lr_backbone},
            {"params": self.value.value_head.parameters(), "lr": self.config.lr_value},
        ], weight_decay=self.config.weight_decay)

        # Cosine annealing LR schedulers
        self.policy_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.policy_optimizer, T_max=2000, eta_min=1e-6
        )
        self.value_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.value_optimizer, T_max=2000, eta_min=1e-6
        )

        self.buffer = RolloutBuffer()

        # Training stats
        self.total_steps = 0
        self.update_count = 0

    @torch.no_grad()
    def select_action(self, obs: dict, deterministic: bool = False) -> tuple[int, float, float]:
        """Select an action given an observation.

        Args:
            obs: Dict with "market" and "portfolio" arrays.
            deterministic: If True, use argmax policy (and eval mode to disable dropout).

        Returns:
            (action, log_prob, value_estimate)
        """
        market = torch.tensor(obs["market"], dtype=torch.float32, device=self.device).unsqueeze(0)
        portfolio = torch.tensor(obs["portfolio"], dtype=torch.float32, device=self.device).unsqueeze(0)

        action, log_prob = self.policy.get_action(market, portfolio, deterministic=deterministic)
        value = self.value(market, portfolio)

        return action.item(), log_prob.item(), value.item()

    @torch.no_grad()
    def estimate_value(self, obs: dict) -> float:
        """Estimate the value of a state (for GAE bootstrap)."""
        market = torch.tensor(obs["market"], dtype=torch.float32, device=self.device).unsqueeze(0)
        portfolio = torch.tensor(obs["portfolio"], dtype=torch.float32, device=self.device).unsqueeze(0)
        return self.value(market, portfolio).item()

    def store_transition(self, obs: dict, action: int, log_prob: float, reward: float, value: float, done: bool):
        """Store a transition in the rollout buffer."""
        self.buffer.add(
            market_obs=obs["market"],
            portfolio_obs=obs["portfolio"],
            action=action,
            log_prob=log_prob,
            reward=reward,
            value=value,
            done=done,
        )
        self.total_steps += 1

    def update(self, next_obs: dict) -> dict:
        """Run PPO update on collected rollout data.

        Args:
            next_obs: The observation after the last step (for bootstrapping).

        Returns:
            Dict with training metrics (policy_loss, value_loss, entropy, etc.)
        """
        if len(self.buffer) == 0:
            return {}

        # Bootstrap value for the last state
        next_value = self.estimate_value(next_obs)

        # Convert buffer to tensors
        data = self.buffer.to_tensors(self.device)

        # Compute GAE
        advantages, returns = compute_gae(
            data["rewards"], data["values"], data["dones"],
            next_value, self.config.gamma, self.config.gae_lambda,
        )

        # Normalize advantages
        if len(advantages) > 1:
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # PPO epochs
        T = len(self.buffer)
        indices = np.arange(T)
        total_policy_loss = 0.0
        total_value_loss = 0.0
        total_entropy = 0.0
        n_updates = 0

        self.policy.train()
        self.value.train()

        for _ in range(self.config.n_epochs_per_update):
            np.random.shuffle(indices)

            for start in range(0, T, self.config.minibatch_size):
                end = min(start + self.config.minibatch_size, T)
                mb_idx = indices[start:end]

                mb_market = data["market_obs"][mb_idx]
                mb_portfolio = data["portfolio_obs"][mb_idx]
                mb_actions = data["actions"][mb_idx]
                mb_old_log_probs = data["log_probs"][mb_idx]
                mb_advantages = advantages[mb_idx]
                mb_returns = returns[mb_idx]

                # --- Policy update ---
                dist = self.policy(mb_market, mb_portfolio)
                new_log_probs = dist.log_prob(mb_actions)
                entropy = dist.entropy().mean()

                ratio = torch.exp(new_log_probs - mb_old_log_probs)
                surr1 = ratio * mb_advantages
                surr2 = torch.clamp(ratio, 1.0 - self.config.clip_epsilon, 1.0 + self.config.clip_epsilon) * mb_advantages
                policy_loss = -torch.min(surr1, surr2).mean() - self.config.entropy_coeff * entropy

                self.policy_optimizer.zero_grad()
                policy_loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), self.config.max_grad_norm)
                self.policy_optimizer.step()

                new_values = self.value(mb_market, mb_portfolio)
                value_loss = nn.functional.huber_loss(new_values, mb_returns)

                self.value_optimizer.zero_grad()
                value_loss.backward()
                nn.utils.clip_grad_norm_(self.value.parameters(), self.config.max_grad_norm)
                self.value_optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += entropy.item()
                n_updates += 1

        self.buffer.clear()
        self.update_count += 1

        self.policy_scheduler.step()
        self.value_scheduler.step()

        return {
            "policy_loss": total_policy_loss / max(n_updates, 1),
            "value_loss": total_value_loss / max(n_updates, 1),
            "entropy": total_entropy / max(n_updates, 1),
            "n_updates": n_updates,
        }

    def freeze_backbone(self):
        """Freeze the policy CNN backbone (curriculum phase 1)."""
        for param in self.policy_backbone.parameters():
            param.requires_grad = False

    def unfreeze_backbone(self):
        """Unfreeze the policy CNN backbone (curriculum phase 2+)."""
        for param in self.policy_backbone.parameters():
            param.requires_grad = True

    def save(self, path: str, verbose: bool = True):
        """Save agent state to disk."""
        torch.save({
            "policy": self.policy.state_dict(),
            "value": self.value.state_dict(),
            "policy_optimizer": self.policy_optimizer.state_dict(),
            "value_optimizer": self.value_optimizer.state_dict(),
            "policy_scheduler": self.policy_scheduler.state_dict(),
            "value_scheduler": self.value_scheduler.state_dict(),
            "total_steps": self.total_steps,
            "update_count": self.update_count,
            "config": self.config,
        }, path)
        if verbose:
            print(f"Agent saved to {path}")

    def load(self, path: str, verbose: bool = True):
        """Load agent state from disk."""
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.policy.load_state_dict(checkpoint["policy"])
        self.value.load_state_dict(checkpoint["value"])
        self.policy_optimizer.load_state_dict(checkpoint["policy_optimizer"])
        self.value_optimizer.load_state_dict(checkpoint["value_optimizer"])
        if "policy_scheduler" in checkpoint:
            self.policy_scheduler.load_state_dict(checkpoint["policy_scheduler"])
            self.value_scheduler.load_state_dict(checkpoint["value_scheduler"])
        self.total_steps = checkpoint["total_steps"]
        self.update_count = checkpoint["update_count"]
        if verbose:
            print(f"Agent loaded from {path} (step {self.total_steps})")
