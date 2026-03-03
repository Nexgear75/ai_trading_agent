# Tâche — Artefacts d'entraînement XGBoost

Statut : DONE
Ordre : 064
Workstream : WS-XGB-3
Milestone : MX-2
Gate lié : G-XGB-Ready

## Contexte

La méthode `fit()` de `XGBoostRegModel` est fonctionnelle avec early stopping (tâches #062, #063). Cette tâche complète `fit()` en lui faisant retourner le dictionnaire d'artefacts d'entraînement conformément au contrat `BaseModel.fit() -> dict` et à la spec modèle §5.3.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-3.3)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§5.3)
- Code : `ai_trading/models/xgboost.py` (`XGBoostRegModel.fit`)

Dépendances :
- Tâche 063 — WS-XGB-3.2 early stopping (doit être DONE)

## Objectif

Compléter le retour de `fit()` avec un dictionnaire contenant au minimum :
1. `"best_iteration"` (int, 0-indexed) — round du meilleur modèle
2. `"best_score"` (float) — RMSE de validation au `best_iteration`
3. `"n_features_in"` (int) — nombre de features tabulaires ($L \cdot F$)

## Règles attendues

- **Contrat BaseModel** : `fit()` doit retourner un `dict` (pas `None`, pas `{}`).
- **Types stricts** : les valeurs du dict doivent avoir les types corrects (int, float, int).
- **Spec §5.3** : les 3 clés minimales sont obligatoires. L'enrichissement post-MVP (ex : `evals_result`) est optionnel.

## Évolutions proposées

- Modifier le `return` de `fit()` dans `ai_trading/models/xgboost.py` pour retourner :
  ```python
  return {
      "best_iteration": self._model.best_iteration,
      "best_score": self._model.best_score,
      "n_features_in": X_tab_train.shape[1],
  }
  ```
- Ajouter des tests dans `tests/test_xgboost_model.py` :
  - `fit()` retourne un dict (pas `None`)
  - Le dict contient les 3 clés : `"best_iteration"`, `"best_score"`, `"n_features_in"`
  - `"best_iteration"` est un int
  - `"best_score"` est un float fini
  - `"n_features_in"` est un int égal à $L \times F$

## Critères d'acceptation

- [x] `fit()` retourne un dict contenant `"best_iteration"`, `"best_score"`, `"n_features_in"`
- [x] `"best_iteration"` est un `int` ≥ 0
- [x] `"best_score"` est un `float` fini (pas NaN, pas Inf)
- [x] `"n_features_in"` est un `int` égal à $L \times F$ (vérifiable avec L=10, F=5 → 50)
- [x] Tests couvrent les scénarios nominaux + vérification des types
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/064-xgb-fit-artifacts` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/064-xgb-fit-artifacts` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-3] #064 RED: tests artefacts fit XGBoostRegModel` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-XGB-3] #064 GREEN: artefacts d'entraînement XGBoostRegModel`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-3] #064 — Artefacts d'entraînement XGBoost`.
