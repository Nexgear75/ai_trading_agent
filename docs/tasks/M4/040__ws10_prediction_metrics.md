# Tâche — Métriques de prédiction

Statut : DONE
Ordre : 040
Workstream : WS-10
Milestone : M4
Gate lié : M4

## Contexte
Les métriques de prédiction évaluent la qualité des prédictions brutes des modèles supervisés (`output_type == "regression"`) sur la période test de chaque fold. Pour les baselines et le RL (`output_type == "signal"`), ces métriques valent `null` (les signaux binaires ne sont pas comparables à des rendements).

Références :
- Plan : `docs/plan/implementation.md` (WS-10.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§14.1)
- Code : `ai_trading/metrics/prediction.py` (à créer)

Dépendances :
- Tâche 036 — Validation du gate G-Backtest (doit être DONE)

## Objectif
Implémenter le module `metrics/prediction.py` calculant MAE, RMSE, Directional Accuracy et Spearman IC (optionnel) sur les vecteurs `y_true` et `y_hat`.

## Règles attendues
- **MAE** : `mean(|y - ŷ|)`.
- **RMSE** : `sqrt(mean((y - ŷ)²))`.
- **Directional Accuracy (DA)** : `mean(𝟙[sign(y) == sign(ŷ)])` sur les samples éligibles.
  - Samples avec `y_t == 0` exactement → **exclus**.
  - Samples avec `ŷ == 0` exactement → **exclus**.
  - Si tous les samples éligibles sont exclus → `DA = None` (null).
- **Spearman IC** (optionnel) : `corr_spearman(y, ŷ)`.
- **Modèles `output_type == "signal"`** : toutes les métriques → `None` (null).
- **Float conventions** : métriques calculées en float64.
- **Strict code** : pas de fallback, validation explicite des entrées.

## Évolutions proposées
- Créer `ai_trading/metrics/prediction.py` avec des fonctions pures : `compute_mae(y_true, y_hat)`, `compute_rmse(y_true, y_hat)`, `compute_directional_accuracy(y_true, y_hat)`, `compute_spearman_ic(y_true, y_hat)`, et une fonction agrégée `compute_prediction_metrics(y_true, y_hat, output_type)`.
- Mettre à jour `ai_trading/metrics/__init__.py`.
- Créer `tests/test_prediction_metrics.py`.

## Critères d'acceptation
- [x] `compute_mae` : test numérique sur vecteurs connus → résultat exact.
- [x] `compute_rmse` : test numérique sur vecteurs connus → résultat exact.
- [x] `compute_directional_accuracy` : DA ∈ [0, 1] sur données normales.
- [x] DA exclut les samples avec `y_true == 0` ou `y_hat == 0`.
- [x] DA retourne `None` si tous les samples sont exclus.
- [x] `compute_spearman_ic` : test numérique sur vecteurs connus.
- [x] `compute_prediction_metrics` avec `output_type == "signal"` → toutes les métriques `None`.
- [x] `compute_prediction_metrics` avec `output_type == "regression"` → métriques calculées.
- [x] Métriques en float64.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/040-prediction-metrics` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/040-prediction-metrics` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-10] #040 RED: tests for prediction metrics (MAE, RMSE, DA, Spearman IC)`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-10] #040 GREEN: prediction metrics (MAE, RMSE, DA, Spearman IC)`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-10] #040 — Métriques de prédiction`.
