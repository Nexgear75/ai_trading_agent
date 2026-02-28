# Tâche — Validation stricte de la configuration

Statut : TODO
Ordre : 003
Workstream : WS-1
Milestone : M1
Gate lié : M1

## Contexte
La configuration YAML doit être validée de manière stricte pour rejeter immédiatement toute incohérence : bornes numériques, contraintes croisées, règles MVP imposées par la spec. Un rejet explicite (`raise`) est obligatoire pour chaque violation.

Références :
- Plan : `docs/plan/implementation.md` (WS-1.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (Annexe E.2.6, §8.1, §12.1, §13.3, Annexe E.2.3, §17.5)
- Code : `ai_trading/config.py` (à enrichir)
- Config : `configs/default.yaml`

Dépendances :
- Tâche 002 — Config loader Pydantic v2 (doit être DONE)

## Objectif
Ajouter une validation stricte et exhaustive à la configuration Pydantic v2 :
1. Bornes numériques via `Field()`.
2. Contraintes croisées via `@model_validator(mode="after")`.
3. Mapping statique `VALID_STRATEGIES` pour cohérence `strategy_type` ↔ `strategy.name`.
4. Règles MVP non négociables (backtest, symbole unique, etc.).

## Règles attendues
- Strict code : chaque violation lève une erreur explicite avec un message clair. Pas de fallback, pas de correction silencieuse.
- Anti-fuite : `embargo_bars >= label.horizon_H_bars` (garantit l'absence de fuite entre train/val et test).
- Config-driven : tous les seuils de validation sont documentés ici et dans le code, pas de magic numbers.

## Évolutions proposées

### Bornes numériques (via Pydantic `Field`)
- `label.horizon_H_bars >= 1`
- `window.L >= 2`
- `window.min_warmup >= 1`
- `splits.train_days >= 1`, `splits.test_days >= 1`, `splits.step_days >= 1`
- `splits.val_frac_in_train ∈ (0, 0.5]` (strictement positif)
- `splits.min_samples_train >= 1`, `splits.min_samples_test >= 1`
- `splits.embargo_bars >= 0`
- `costs.fee_rate_per_side >= 0`, `costs.slippage_rate_per_side >= 0`
- `thresholding.q_grid` : chaque valeur ∈ `[0, 1]` et triée croissante
- `thresholding.mdd_cap ∈ (0, 1]`
- `thresholding.min_trades >= 0`
- `backtest.initial_equity > 0`
- `backtest.position_fraction ∈ (0, 1]`
- `models.*.dropout ∈ [0, 1)`
- `models.*.num_layers >= 1` (GRU, LSTM, PatchTST)
- `models.patchtst.n_heads` divise `models.patchtst.d_model`
- `models.patchtst.stride <= models.patchtst.patch_size`
- `baselines.sma.fast >= 2`
- `training.batch_size >= 1`
- `scaling.rolling_window >= 2` (si `scaling.method == rolling_zscore`)
- `reproducibility.global_seed >= 0`
- `reproducibility.deterministic_torch` (booléen)
- `metrics.sharpe_epsilon > 0`
- `metrics.sharpe_annualized` (booléen)
- `artifacts.output_dir` (chaîne non vide)

### Contraintes croisées (`@model_validator`)
- **Warmup-features** : `min_warmup >= max(rsi_period, ema_slow, max(vol_windows))`
- **Warmup-window** : `min_warmup >= window.L`
- **Embargo-horizon** : `embargo_bars >= label.horizon_H_bars`
- **Walk-forward** : `step_days >= test_days` (pas de chevauchement test inter-folds)
- **MVP backtest** : `backtest.mode == "one_at_a_time"` et `backtest.direction == "long_only"`
- **Symbole unique** : `len(symbols) == 1`
- **SMA (si applicable)** : si `strategy.name == "sma_rule"` → `sma.fast < sma.slow <= min_warmup`
- **Strategy cohérence** : `strategy.name` dans `VALID_STRATEGIES`, `strategy_type` correspond au mapping
- **Scaling MVP** : `scaling.method = rolling_zscore` → erreur (non implémenté)
- **Warning val_days** : si `floor(train_days * val_frac_in_train) < 7` → warning

### Mapping statique `VALID_STRATEGIES`
```python
VALID_STRATEGIES = {
    "xgboost_reg": "model",
    "cnn1d_reg": "model",
    "gru_reg": "model",
    "lstm_reg": "model",
    "patchtst_reg": "model",
    "rl_ppo": "model",
    "no_trade": "baseline",
    "buy_hold": "baseline",
    "sma_rule": "baseline",
}
```

## Critères d'acceptation
- [ ] Config valide (`configs/default.yaml`) passe la validation sans erreur
- [ ] `backtest.mode != "one_at_a_time"` → erreur explicite
- [ ] `backtest.direction != "long_only"` → erreur explicite
- [ ] `min_warmup < max(rsi_period, ema_slow, max(vol_windows))` → erreur
- [ ] `min_warmup < window.L` → erreur
- [ ] `embargo_bars < label.horizon_H_bars` → erreur (ex: `embargo_bars=2, H=4` → rejet)
- [ ] `strategy_type = "baseline"` avec `strategy.name = "xgboost_reg"` → erreur
- [ ] `strategy_type = "model"` avec `strategy.name = "no_trade"` → erreur
- [ ] `strategy.name` absent de `VALID_STRATEGIES` → erreur
- [ ] `step_days < test_days` → erreur
- [ ] `horizon_H_bars=0` → erreur, `window.L=1` → erreur, `position_fraction=0` → erreur
- [ ] `dropout=1.0` → erreur, `q_grid` non triée → erreur, `mdd_cap=0` → erreur
- [ ] `min_trades=-1` → erreur, `num_layers=0` → erreur
- [ ] `n_heads` ne divise pas `d_model` → erreur, `stride > patch_size` → erreur
- [ ] `sma.fast=1` → erreur, `batch_size=0` → erreur
- [ ] `global_seed=-1` → erreur, `sharpe_epsilon=0` → erreur, `output_dir=""` → erreur
- [ ] Clé YAML inconnue (ex: `dataset.foo: bar`) → erreur Pydantic `extra fields not permitted`
- [ ] `scaling.method = "rolling_zscore"` → erreur (non implémenté MVP)
- [ ] `len(symbols) > 1` → erreur (MVP mono-symbole)
- [ ] Warning émis si `val_days < 7`
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/003-config-validation` depuis `main`.

## Checklist de fin de tâche
- [ ] Branche `task/003-config-validation` créée depuis `main`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-1] #003 RED: tests validation stricte configuration`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-1] #003 GREEN: validation stricte configuration`.
- [ ] **Pull Request ouverte** vers `main` : `[WS-1] #003 — Validation stricte de la configuration`.
