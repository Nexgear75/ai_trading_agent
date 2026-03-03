# Tâche — Sauvegarde JSON native XGBoost

Statut : DONE
Ordre : 066
Workstream : WS-XGB-5
Milestone : MX-2
Gate lié : G-XGB-Ready

## Contexte

La méthode `fit()` de `XGBoostRegModel` est complète (tâches #062–#064). Cette tâche implémente `save()` pour persister le modèle entraîné au format JSON natif XGBoost. Le format pickle est interdit (non portable, risques de sécurité). La résolution du chemin suit le pattern `_resolve_path` utilisé par `DummyModel` et les baselines.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-5.1)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§7.1, §7.2)
- Code : `ai_trading/models/xgboost.py` (`XGBoostRegModel.save`)
- Code : `ai_trading/models/dummy.py` (`_resolve_path` — pattern de référence)

Dépendances :
- Tâche 064 — WS-XGB-3.3 fit artefacts (doit être DONE)

## Objectif

Implémenter la méthode `save()` de `XGBoostRegModel` :
1. Résoudre le chemin : si `path` est un répertoire, appender `xgboost_model.json` ; sinon utiliser `path` comme chemin fichier
2. Créer le répertoire parent si nécessaire : `resolved.parent.mkdir(parents=True, exist_ok=True)`
3. Sérialiser : `self._model.save_model(str(resolved))`
4. Lever `RuntimeError` si `self._model` n'est pas défini (pas de `fit()` préalable)

## Règles attendues

- **Strict code** : `RuntimeError` si le modèle n'est pas entraîné. Pas de fallback ni de sauvegarde partielle.
- **Sécurité** : format JSON natif XGBoost uniquement. Pickle interdit.
- **Pattern cohérent** : suivre le même pattern `_resolve_path` que `DummyModel` pour la résolution des chemins (directory → append filename, file → utiliser tel quel).

## Évolutions proposées

- Ajouter une constante `_MODEL_FILENAME = "xgboost_model.json"` dans `ai_trading/models/xgboost.py`
- Ajouter une méthode statique `_resolve_path(path: Path) -> Path` suivant le pattern de `DummyModel`
- Remplacer le stub `NotImplementedError` de `save()` par :
  ```python
  def save(self, path: Path) -> None:
      if self._model is None:
          raise RuntimeError("Model not fitted. Call fit() before save().")
      resolved = self._resolve_path(path)
      resolved.parent.mkdir(parents=True, exist_ok=True)
      self._model.save_model(str(resolved))
  ```
- Ajouter des tests dans `tests/test_xgboost_model.py` :
  - `save()` crée un fichier `xgboost_model.json` dans le répertoire spécifié
  - Le fichier créé est un JSON valide
  - `RuntimeError` si le modèle n'est pas entraîné
  - Résolution de chemin : directory → `xgboost_model.json` appendé
  - Résolution de chemin : file path → utilisé tel quel

## Critères d'acceptation

- [x] `save()` crée un fichier `xgboost_model.json` dans le répertoire spécifié
- [x] Le fichier créé est un JSON valide (parseable)
- [x] `RuntimeError` si le modèle n'est pas entraîné
- [x] Résolution de chemin directory → `xgboost_model.json` appendé
- [x] Résolution de chemin fichier → utilisé tel quel
- [x] Le répertoire parent est créé si nécessaire
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/066-xgb-save-json` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/066-xgb-save-json` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-5] #066 RED: tests save XGBoostRegModel` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-XGB-5] #066 GREEN: save JSON natif XGBoostRegModel`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-5] #066 — Sauvegarde JSON native XGBoost`.
