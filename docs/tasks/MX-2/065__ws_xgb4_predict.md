# Tâche — Prédiction XGBoost et cast float32

Statut : DONE
Ordre : 065
Workstream : WS-XGB-4
Milestone : MX-2
Gate lié : G-XGB-Ready

## Contexte

La méthode `fit()` de `XGBoostRegModel` est complète (tâches #062–#064). Cette tâche implémente `predict()` : validation stricte des entrées, aplatissement, prédiction via le régresseur entraîné, et cast explicite en float32.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-4.1)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§6.1, §6.2)
- Code : `ai_trading/models/xgboost.py` (`XGBoostRegModel.predict`)
- Code : `ai_trading/data/dataset.py` (`flatten_seq_to_tab`)

Dépendances :
- Tâche 064 — WS-XGB-3.3 fit artefacts (doit être DONE)

## Objectif

Implémenter la méthode `predict()` de `XGBoostRegModel` :
1. Vérifier que `self._model` est défini, sinon `RuntimeError("Model not fitted. Call fit() before predict().")`
2. Validation stricte : `X.ndim == 3` → sinon `ValueError` ; `X.dtype == np.float32` → sinon `TypeError`
3. Aplatissement via `flatten_seq_to_tab(X, feature_names)` (feature_names récupérés depuis le fit)
4. Prédiction : `y_hat = self._model.predict(X_tab)`
5. Cast explicite en float32 : `y_hat.astype(np.float32)` (XGBoost retourne du float64)
6. Les paramètres `meta` et `ohlcv` sont ignorés (conformément à la spec §2.2)

## Règles attendues

- **Strict code** : `RuntimeError` si pas de fit préalable. `ValueError` si shape invalide. `TypeError` si dtype invalide. Pas de fallback.
- **Float32** : cast explicite obligatoire (XGBoost retourne float64 internement).
- **Déterminisme** : appels multiples de `predict()` avec les mêmes données → résultats identiques (pas d'état mutable).
- **Spec §6.2** : les valeurs sont des log-returns continus (non bornés).

## Évolutions proposées

- Remplacer le stub `NotImplementedError` de `predict()` dans `ai_trading/models/xgboost.py` par :
  ```python
  def predict(self, X, meta=None, ohlcv=None):
      if self._model is None:
          raise RuntimeError("Model not fitted. Call fit() before predict().")
      if X.ndim != 3:
          raise ValueError(f"X must be 3D (N, L, F), got {X.ndim}D.")
      if X.dtype != np.float32:
          raise TypeError(f"X.dtype must be float32, got {X.dtype}.")
      X_tab, _ = flatten_seq_to_tab(X, self._feature_names)
      y_hat = self._model.predict(X_tab)
      return y_hat.astype(np.float32)
  ```
- Stocker `self._feature_names` lors de `fit()` pour le réutiliser dans `predict()`
- Ajouter des tests dans `tests/test_xgboost_model.py` :
  - `predict()` retourne shape $(N,)$ dtype float32
  - `RuntimeError` si `fit()` non appelé
  - `ValueError` si `X.ndim != 3`
  - `TypeError` si `X.dtype != float32`
  - Appels multiples → résultats identiques
  - `meta` et `ohlcv` sont ignorés (pas d'effet)

## Critères d'acceptation

- [x] `predict()` retourne un array numpy de shape $(N,)$ et dtype `float32`
- [x] `RuntimeError` si `fit()` n'a pas été appelé
- [x] `ValueError` si `X.ndim != 3`
- [x] `TypeError` si `X.dtype != float32`
- [x] Les valeurs retournées sont des floats continus (non bornés)
- [x] Appels multiples de `predict()` avec les mêmes données → résultats identiques
- [x] `meta` et `ohlcv` sont ignorés sans erreur
- [x] Cast explicite float64 → float32 vérifié
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/065-xgb-predict` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/065-xgb-predict` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-4] #065 RED: tests predict XGBoostRegModel` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-XGB-4] #065 GREEN: predict XGBoostRegModel`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-4] #065 — Prédiction XGBoost et cast float32`.
