# Tâche — Validation Pydantic du bloc models.xgboost

Statut : DONE
Ordre : 061
Workstream : WS-XGB-6
Milestone : MX-1
Gate lié : G-XGB-Ready

## Contexte

Le modèle Pydantic `XGBoostModelConfig` existe déjà dans `ai_trading/config.py` avec les 7 champs requis (`max_depth`, `n_estimators`, `learning_rate`, `subsample`, `colsample_bytree`, `reg_alpha`, `reg_lambda`), mais **sans contraintes de validation** (pas de `Field(gt=0)`, `Field(le=1)`, etc.). La spec modèle XGBoost §11.1 impose des contraintes strictes sur chaque champ. Le fichier `configs/default.yaml` contient déjà les valeurs MVP. Cette tâche ajoute les contraintes Pydantic manquantes et les tests associés.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-6.1)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§11.1, §11.2)
- Code : `ai_trading/config.py` (`XGBoostModelConfig`)
- Config : `configs/default.yaml` (bloc `models.xgboost`)

Dépendances :
- Tâche 001 — WS-1 config loader (doit être DONE) ✅
- Tâche 002 — WS-1 config validation (doit être DONE) ✅

## Objectif

Ajouter les contraintes de validation Pydantic à `XGBoostModelConfig` conformément à la spec §11.1, et tester exhaustivement les rejets sur valeurs invalides.

## Règles attendues

- **Config-driven** : les contraintes reproduisent exactement la spec §11.1, pas de contrainte inventée.
- **Strict code** : validation explicite via `Field(...)`, pas de `@validator` contournant silencieusement.
- **Pas de valeur par défaut** : les champs restent obligatoires (pas de `= None` ni de `default=...`).

## Évolutions proposées

- Modifier `XGBoostModelConfig` dans `ai_trading/config.py` :
  - `max_depth: int = Field(gt=0)` — entier strictement positif
  - `n_estimators: int = Field(gt=0)` — entier strictement positif
  - `learning_rate: float = Field(gt=0, le=1)` — float dans ]0, 1]
  - `subsample: float = Field(gt=0, le=1)` — float dans ]0, 1]
  - `colsample_bytree: float = Field(gt=0, le=1)` — float dans ]0, 1]
  - `reg_alpha: float = Field(ge=0)` — float ≥ 0
  - `reg_lambda: float = Field(ge=0)` — float ≥ 0
- Ajouter des tests dans `tests/test_config_validation.py` (ou un fichier dédié `tests/test_xgboost_config.py`) pour chaque contrainte :
  - `max_depth=0` → rejet
  - `max_depth=-1` → rejet
  - `n_estimators=0` → rejet
  - `learning_rate=0` → rejet
  - `learning_rate=1.5` → rejet
  - `learning_rate=1.0` → accepté (borne incluse)
  - `subsample=0` → rejet
  - `subsample=1.1` → rejet
  - `subsample=1.0` → accepté (borne incluse)
  - `colsample_bytree=0` → rejet
  - `colsample_bytree=1.1` → rejet
  - `reg_alpha=-0.1` → rejet
  - `reg_alpha=0.0` → accepté (borne incluse)
  - `reg_lambda=-0.1` → rejet
  - `reg_lambda=0.0` → accepté (borne incluse)
- Vérifier que `configs/default.yaml` passe la validation avec les nouvelles contraintes (les valeurs MVP : max_depth=5, n_estimators=500, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, reg_alpha=0.0, reg_lambda=1.0)
- Vérifier l'interaction avec les paramètres pipeline partagés (§11.2) :
  - `training.early_stopping_patience` → utilisé comme `early_stopping_rounds` (vérifié dans WS-XGB-3)
  - `reproducibility.global_seed` → utilisé comme `random_state` (vérifié dans WS-XGB-3)

## Critères d'acceptation

- [x] `XGBoostModelConfig` a des contraintes `Field(...)` sur les 7 champs
- [x] `max_depth` : `Field(gt=0)` — rejet de 0 et négatifs
- [x] `n_estimators` : `Field(gt=0)` — rejet de 0 et négatifs
- [x] `learning_rate` : `Field(gt=0, le=1)` — rejet de 0 et > 1
- [x] `subsample` : `Field(gt=0, le=1)` — rejet de 0 et > 1
- [x] `colsample_bytree` : `Field(gt=0, le=1)` — rejet de 0 et > 1
- [x] `reg_alpha` : `Field(ge=0)` — rejet de négatifs
- [x] `reg_lambda` : `Field(ge=0)` — rejet de négatifs
- [x] `configs/default.yaml` parsé sans erreur avec les nouvelles contraintes
- [x] Tests couvrent les scénarios nominaux + erreurs + valeurs limites
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/061-xgb-config-pydantic-validation` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/061-xgb-config-pydantic-validation` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-6] #061 RED: tests validation Pydantic XGBoostModelConfig` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-XGB-6] #061 GREEN: validation Pydantic XGBoostModelConfig`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-6] #061 — Validation Pydantic XGBoostModelConfig`.
