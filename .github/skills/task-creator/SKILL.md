---
name: task-creator
description: Analyse la spécification AI Trading Pipeline v1.0 et le plan d'implémentation pour générer des tâches d'implémentation structurées. À utiliser quand l'utilisateur demande de créer des tâches pour un WS, un milestone ou un chapitre de spec.
argument-hint: "[scope: WS-X/M1..M5/chapitre] [nb_taches]"
---

# Agent Skill — Task Creator (AI Trading Pipeline)

## Objectif
Générer des fichiers de tâches clairs, actionnables et traçables à partir des documents de cadrage du projet AI Trading Pipeline.

## Contexte repo (chemins réels)

- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2)
- **Plan de réalisation** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Répertoire des tâches** : `docs/tasks/<milestone>/` (ex : `docs/tasks/M1/`, `docs/tasks/M2/`, etc. — à créer si absent)
- **Configs** : `configs/default.yaml`
- **Code source** : `ai_trading/`
- **Tests** : `tests/`
- **Langue** : français pour docs/tâches, anglais pour code/tests
- **Mode de travail** : TDD strict (RED → GREEN)

## Rôle de l'agent

Tu dois :
- détecter les écarts entre spécification, plan, et tâches existantes ;
- proposer des tâches atomiques (une intention technique claire par fichier) ;
- garder l'alignement avec les workstreams WS-1..WS-12, milestones M1..M5 et gates (M1..M5, G-Features, G-Split, G-Backtest, G-Doc, G-Leak, G-Perf) ;
- éviter les tâches vagues, non testables, ou non traçables.

## Workflow de génération

1. **Analyser la spec**
   - Lire les sections pertinentes de `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`.
   - Extraire les exigences normatives, formules, interfaces, artefacts attendus, et règles anti-fuite.

2. **Lire le plan d'implémentation**
   - Prioriser via `docs/plan/implementation.md` (WS, milestones, dépendances, critères d'acceptation).
   - Respecter les gates intra-milestone et milestone.

3. **Auditer les tâches existantes**
   - Lister `docs/tasks/` et ses sous-répertoires par milestone (`M1/`, `M2/`, …).
   - Identifier : numérotation max, doublons, trous de couverture (spec/plan non adressés), dépendances.

4. **Générer les tâches manquantes**
   - Créer uniquement des tâches nécessaires, ordonnées et testables.
   - Ajouter les références précises (fichier + section).

## Format des fichiers de tâche

```markdown
# Tâche — [Titre descriptif en français]

Statut : TODO
Ordre : [NNN]
Workstream : [WS-1|WS-2|...|WS-12]
Milestone : [M1|M2|M3|M4|M5]
Gate lié : [M1..M5|G-Features|G-Split|G-Backtest|G-Doc|N/A]

## Contexte
[Explication brève du contexte et pourquoi cette tâche existe]

Références :
- Plan : `docs/plan/implementation.md` (section ciblée, ex: WS-3.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§X.Y)
- Code : `ai_trading/[chemin/pertinent]` (si applicable)

Dépendances :
- Tâche NNN — [titre] (doit être DONE)

## Objectif
[Énoncé clair de ce qui doit être accompli]

## Règles attendues
- [Règle clé 1 avec justification : strict code, anti-fuite, config-driven, etc.]
- [Règle clé 2]

## Évolutions proposées
- [Changement proposé 1]
- [Changement proposé 2]

## Critères d'acceptation
- [ ] [Critère vérifiable 1]
- [ ] [Critère vérifiable 2]
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/NNN-short-slug` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/NNN-short-slug` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-X] #NNN RED: <résumé>` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-X] #NNN GREEN: <résumé>`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-X] #NNN — <titre>`.
```

## Convention de nommage

Répertoire : `docs/tasks/<milestone>/` — un sous-répertoire par milestone (`M1`, `M2`, `M3`, `M4`, `M5`).

Fichiers : `NNN__short_slug.md`

- `NNN` : numéro séquentiel sur 3 chiffres (001, 002, ...), **global** à tout le projet (pas par milestone)
- `__` : séparateur fixe
- `short_slug` : minuscule, underscores, orienté action

Exemples :
- `docs/tasks/M1/001__ws1_config_loader.md`
- `docs/tasks/M1/002__ws1_config_validation.md`
- `docs/tasks/M2/003__ws2_ingestion_ohlcv.md`
- `docs/tasks/M2/010__ws3_feature_pipeline.md`

## Principes clés

### 1) Alignement plan/spec
Chaque tâche doit indiquer son lien avec :
- un workstream (WS-1..WS-12),
- un milestone (M1..M5),
- et un point de spécification (§X.Y).

### 2) Tâches testables
Les critères d'acceptation doivent être mesurables et vérifiables (pas d'énoncés vagues).

### 3) Commits TDD obligatoires
Deux commits par tâche :
1. **Commit RED** : `[WS-X] #NNN RED: <résumé>` (tests uniquement, échouant)
2. **Commit GREEN** : `[WS-X] #NNN GREEN: <résumé>` (implémentation + tâche mise à jour)

### 4) Branche et PR
- Branche : `task/NNN-short-slug` depuis `Max6000i1`
- PR vers `Max6000i1` : `[WS-X] #NNN — <titre>`

### 5) Dépendances explicites
Si une tâche dépend d'une autre, la dépendance est écrite dans `Contexte > Dépendances`.

### 6) Granularité
Une tâche = un résultat livrable principal. Si trop large, découper.

### 7) Priorisation
Respecter M1 → M2 → M3 → M4 → M5 et les gates intra-milestone.

## Valeurs de statut

- `TODO` — non commencée
- `IN_PROGRESS` — en cours
- `DONE` — terminée, critères validés

## Référentiel rapide (AI Trading Pipeline)

Sujets typiquement à couvrir en tâches :

**M1 — Fondations (WS-1, WS-2)** :
- Config loader Pydantic v2, validation stricte, override CLI
- Ingestion OHLCV Binance (ccxt), QA checks, politique missing candles

**M2 — Feature & Data Pipeline (WS-3, WS-4, WS-5)** :
- 9 features MVP (logret, vol, RSI, EMA, volume), registre pluggable, warmup
- Label y_t, sample builder (N,L,F), adapter XGBoost, walk-forward splitter, embargo
- Standard scaler, robust scaler (fit on train only)

**M3 — Training Framework (WS-6, WS-7)** :
- BaseModel ABC, dummy model, registre MODEL_REGISTRY
- Training loop (fold trainer), early stopping
- Calibration θ (quantile grid, objectif max_net_pnl_with_mdd_cap), bypass RL/baselines

**M4 — Evaluation Engine (WS-8, WS-9, WS-10)** :
- Moteur backtest (one_at_a_time, long_only), cost model, equity curve, trade journal
- Baselines (no-trade, buy & hold, SMA rule)
- Métriques prédiction + trading, agrégation inter-fold

**M5 — Production Readiness (WS-11, WS-12)** :
- Arborescence run, manifest builder, metrics builder, validation JSON Schema
- Seed manager, orchestrateur, CLI, Dockerfile, Makefile

## Limites
- Ne pas inventer d'exigences hors documents source.
- Signaler explicitement toute ambiguïté ou section absente.
- Si `docs/tasks/<milestone>/` n'existe pas, le créer avant génération des tâches.
