# Tâche — Chargement JSON native XGBoost

Statut : TODO
Ordre : 067
Workstream : WS-XGB-5
Milestone : MX-2
Gate lié : G-XGB-Ready

## Contexte

La méthode `save()` de `XGBoostRegModel` est implémentée (tâche #066) et persiste le modèle au format JSON natif. Cette tâche implémente `load()` pour restaurer un modèle depuis un fichier JSON, avec validation du round-trip `save()` → `load()` → `predict()` identique.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-5.2)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§7.1, §7.3)
- Code : `ai_trading/models/xgboost.py` (`XGBoostRegModel.load`)

Dépendances :
- Tâche 066 — WS-XGB-5.1 save JSON (doit être DONE)

## Objectif

Implémenter la méthode `load()` de `XGBoostRegModel` :
1. Résoudre le chemin avec `_resolve_path(path)` (réutilise la méthode créée en #066)
2. Vérifier l'existence du fichier, sinon `FileNotFoundError`
3. Instancier un `xgb.XGBRegressor()` vide
4. Charger : `self._model.load_model(str(resolved))`
5. Pas de fallback silencieux si le fichier est corrompu — l'erreur XGBoost remonte

## Règles attendues

- **Strict code** : `FileNotFoundError` si le fichier n'existe pas. Pas de fallback silencieux.
- **Round-trip** : `save()` → `load()` → `predict()` doit retourner des résultats identiques bit-exact à `predict()` avant `save()`.
- **Sécurité** : pas de pickle. Chargement JSON natif uniquement.

## Évolutions proposées

- Remplacer le stub `NotImplementedError` de `load()` dans `ai_trading/models/xgboost.py` par :
  ```python
  def load(self, path: Path) -> None:
      resolved = self._resolve_path(path)
      if not resolved.exists():
          raise FileNotFoundError(f"Model file not found: {resolved}")
      self._model = xgb.XGBRegressor()
      self._model.load_model(str(resolved))
  ```
- Ajouter des tests dans `tests/test_xgboost_model.py` :
  - `load()` restaure un modèle fonctionnel
  - Round-trip : `save()` → `load()` → `predict()` identique bit-exact
  - `FileNotFoundError` si le fichier n'existe pas
  - `predict()` fonctionne après `load()` sans `fit()` préalable
  - Résolution de chemin : directory et file path

## Critères d'acceptation

- [ ] `load()` restaure un modèle fonctionnel (capable de `predict()`)
- [ ] Round-trip : `save()` → `load()` → `predict()` retourne les mêmes résultats que `predict()` avant `save()` (bit-exact)
- [ ] `FileNotFoundError` si le fichier n'existe pas
- [ ] Résolution de chemin directory → `xgboost_model.json` appendé
- [ ] Résolution de chemin fichier → utilisé tel quel
- [ ] `predict()` fonctionne après `load()` sans erreur
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/067-xgb-load-json` depuis `Max6000i1`.

## Checklist de fin de tâche

- [ ] Branche `task/067-xgb-load-json` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-XGB-5] #067 RED: tests load XGBoostRegModel` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-XGB-5] #067 GREEN: load JSON natif XGBoostRegModel`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-5] #067 — Chargement JSON native XGBoost`.
