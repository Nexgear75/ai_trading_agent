# AGENTS.md — AI Trading Pipeline

## Projet
Pipeline commun AI Trading : comparaison rigoureuse de modèles ML/DL (XGBoost, CNN1D, GRU, LSTM, PatchTST, RL PPO) et baselines (no-trade, buy & hold, SMA) sur données OHLCV Binance avec protocole walk-forward, backtest unifié et métriques standardisées.

## Stack
- **Langage** : Python 3.11+
- **Tests** : pytest (config dans `pyproject.toml`)
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)
- **Données** : Parquet OHLCV (`data/raw/`)
- **Configs** : YAML versionnées (`configs/`)
- **Artefacts** : `runs/` (arborescence par run avec `manifest.json` + `metrics.json`)

## Documents de référence
- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2)
- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Tâches** : `docs/tasks/<milestone>/NNN__slug.md` (ex : `docs/tasks/M1/001__ws1_config_loader.md`)

## Règles non négociables

### TDD strict
1. **Pré-condition** : `pytest` GREEN avant de commencer toute tâche.
2. **RED** : écrire les tests d'abord, constater l'échec.
3. **Commit RED** : `git commit -m "[WS-X] #NNN RED: <résumé>"` (fichiers de tests uniquement).
4. **GREEN** : implémenter le minimum pour passer.
5. **Commit GREEN** : `git commit -m "[WS-X] #NNN GREEN: <résumé>"`
   Condition : tests GREEN + critères d'acceptation validés + checklist cochée.
6. Aucun commit intermédiaire sauf refactoring mineur (tests verts).
7. **Branche dédiée** : `task/NNN-short-slug` depuis `Max6000i1`. Jamais de commit direct sur `Max6000i1`.
8. **Pull Request obligatoire** vers `Max6000i1` après commit GREEN.

### Zéro ghost completion
Ne jamais marquer une tâche `DONE` ni cocher `[x]` sans code + tests + exécution vérifiée.

### Reproductibilité
Tout run doit être relançable à l'identique : seed globale (`reproducibility.global_seed`), hashes SHA-256 (données, config), `deterministic_torch`.

### Anti-fuite
Ne jamais introduire de look-ahead. Toutes les données doivent être point-in-time. Embargo respecté (`embargo_bars ≥ H`). Scaler fit sur train uniquement. Splits walk-forward séquentiels (train < val < test).

### Config-driven (pas de hardcoding)
Tout paramètre modifiable est lu depuis `configs/default.yaml`. Les formules de la spec (§6 features, §5 labels, §8 splits, §12 backtest) sont respectées. Tout choix implementation-defined (optimizer, LR, hyperparamètres modèles) est explicite dans la config YAML. Aucune valeur implicite cachée dans le code.

### Strict code (no fallbacks)
- Implementation code **MUST** be strict: **no silent fallback paths** and **no default values** and **no cast of value** that mask missing/invalid inputs/outputs.
- Prefer explicit validation + failure (raise/return error) over "best-effort" behavior.
- Avoid patterns like `or default`, `value if value else default`, broad `except` that continues, or optional params with implicit defaults.
- If an implementation choice is ambiguous or underspecified, **do nothing** (no guessing): update the spec first to remove ambiguity, then implement.

### Ambiguïté
Si specs ou tâche ambiguës → demander des clarifications avant d'implémenter.

## Structure des workstreams
- **WS-1** Fondations et configuration : config loader Pydantic v2, validation stricte, override CLI
- **WS-2** Ingestion des données et QA : OHLCV Binance (ccxt), QA checks, politique missing candles
- **WS-3** Feature engineering : 9 features MVP (logret, vol, RSI, EMA, volume), registre pluggable, warmup
- **WS-4** Construction des datasets et splitting : label `y_t`, sample builder `(N,L,F)`, adapter XGBoost, walk-forward splitter, embargo
- **WS-5** Normalisation / scaling : standard scaler, robust scaler, rolling z-score (post-MVP)
- **WS-6** Interface modèle et framework d'entraînement : BaseModel ABC, dummy model, training loop
- **WS-7** Calibration du seuil θ (Go/No-Go) : quantile grid, objectif `max_net_pnl_with_mdd_cap`
- **WS-8** Moteur de backtest : exécution trades long-only, cost model, equity curve, trade journal CSV
- **WS-9** Baselines : no-trade, buy & hold, SMA rule
- **WS-10** Métriques et agrégation inter-fold : prédiction (MSE, MAE, R², IC), trading (Sharpe, MDD, Win Rate, P&L net)
- **WS-11** Artefacts, manifest et schémas JSON : arborescence run, `manifest.json`, `metrics.json`
- **WS-12** Reproductibilité et orchestration : seed manager, orchestrateur, CLI entry point, Dockerfile
- **WS-13** Tests full-scale réseau (Bitcoin) : config dédiée `fullscale_btc.yaml`, test `make run-all` grandeur nature BTCUSDT 2017–2026, validation métriques sur données réelles

## Milestones
- **M1** Fondations (WS-1, WS-2) : config chargeable, données brutes téléchargées et QA passé
- **M2** Feature & Data Pipeline (WS-3, WS-4, WS-5) : features → datasets `(N,L,F)` → splits → scaler
- **M3** Training Framework (WS-6, WS-7) : interface modèle, boucle d'entraînement, calibration θ
- **M4** Evaluation Engine (WS-8, WS-9, WS-10) : backtest, baselines, métriques
- **M5** Production Readiness (WS-11, WS-12) : artefacts, orchestrateur, run reproductible bout-en-bout
- **M6** Full-Scale Integration Tests (WS-13) : test grandeur nature `make run-all` sur BTCUSDT réel depuis 2017, config dédiée, sans fixtures

## Priorisation
M1 → M2 → M3 → M4 → M5 → M6 (séquentiel, chaque milestone dépend du précédent).

## Skills

Les skills `.github/skills/*/SKILL.md` fournissent des workflows spécialisés invocables par Copilot.

| Skill | Déclencheur | Description |
|---|---|---|
| `implementing-task` | « implémente la tâche #NNN » | Orchestre 4 agents workers : TDD-Implementer (RED→GREEN), TDD-Reviewer (revue), TDD-Fixer (corrections), PR-Review-Fixer (corrections post-review GitHub). Boucle B+C jusqu'à 5× max, puis Post-PR en passe unique. |
| `implementing-request-change` | « implémente les request changes 0001 », « corrige les bloquants » | Corrections issues d'un rapport request_changes, par sévérité |
| `pr-reviewer` | « review la PR », « vérifie avant merge » | Revue systématique de PR |
| `task-creator` | « crée les tâches pour WS-X » | Génération de tâches structurées depuis spec/plan |
| `gate-validator` | « valide le gate M2 » | Audit Go/No-Go des gates M1–M5, G-* |
| `global-review` | « revue globale », « audit du code », « revue de la branche » | Revue complète de branche : cohérence inter-modules, conformité spec, qualité |
| `test-adherence` | « vérifie l'adhérence des tests », « tests vs spec », « matrice couverture » | Audit croisé tests ↔ spec ↔ tâches : formules, critères, anti-patterns |
| `plan-coherence` | « revue du plan », « cohérence du plan », « audit plan » | Orchestre 2 agents workers : Plan-Corrector (corrections), Plan-Analyzer (ré-analyse). Itère jusqu'à convergence. |
| `spec-coherence` | « vérifie la cohérence de la spec », « audit de la spécification » | Audit de cohérence intrinsèque d'une spécification : terminologie, formules, références, paramètres, flux I/O, glossaire, addenda. Rapport structuré. |
| `markdown-redaction` | « rédige un document Markdown » | Conventions GFM, mode Corporate FR, templates |

## Custom Agents (workers)

Les agents `.github/agents/*.agent.md` sont des workers invocables comme subagents par les skills orchestrateurs. Ils ne sont pas visibles directement dans le dropdown Copilot (`user-invocable: false`).

> **Modèle** : par défaut, chaque agent hérite du modèle sélectionné dans la session principale. Pour forcer un modèle spécifique, décommenter la ligne `model:` dans le frontmatter de l'agent (ex : `model: ['Claude Opus 4.6 (copilot)']`).

| Agent | Fichier | Utilisé par | Rôle |
|---|---|---|---|
| `TDD-Implementer` | `.github/agents/tdd-implementer.agent.md` | `implementing-task` | Implémentation TDD RED→GREEN |
| `TDD-Reviewer` | `.github/agents/tdd-reviewer.agent.md` | `implementing-task` | Revue de branche (audit complet) |
| `TDD-Fixer` | `.github/agents/tdd-fixer.agent.md` | `implementing-task` | Corrections post-revue |
| `PR-Review-Fixer` | `.github/agents/pr-review-fixer.agent.md` | `implementing-task` | Corrections post-review GitHub automatique |
| `Plan-Corrector` | `.github/agents/plan-corrector.agent.md` | `plan-coherence` | Correction d'une incohérence plan |
| `Plan-Analyzer` | `.github/agents/plan-analyzer.agent.md` | `plan-coherence` | Analyse de cohérence complète (Phase A itérative) |

## Instructions automatiques

Les fichiers `.github/instructions/*.instructions.md` sont injectés automatiquement par VS Code Copilot selon le pattern `applyTo` défini dans leur front matter.

| Instruction | Pattern | Description |
|---|---|---|
| `PULL_REQUEST_REVIEW.instructions.md` | `**` (tous fichiers) | Grille d'audit complète pour les revues de PR |

## Conventions de code
- Nommage : snake_case (modules, fonctions, variables).
- Modules attendus : config, ingestion, qa, features, registry, dataset, splitter, scaler, base (model), dummy, trainer, threshold, engine, baselines, prediction (metrics), trading (metrics), aggregation, manifest, metrics_builder, run_dir, seed, runner.
- Tests : structurés par module sous `tests/` (ex. `test_config.py`, `test_features.py`). Identifiant tâche `#NNN` dans les docstrings, pas dans les noms de fichiers.
- Configs : un fichier YAML par configuration de run dans `configs/`.
- Langue : anglais pour le code et les tests, français pour la documentation et les tâches.
- Linter : `ruff check ai_trading/ tests/` avant commit.

## Discipline de contexte
- Lire **ciblé** : utiliser grep/recherche et ne charger que les sections pertinentes de la spec.
- Ne pas charger le document de spécification par défaut : le lire **uniquement si nécessaire**.
- Préférer **exécuter** une commande plutôt que décrire longuement.
