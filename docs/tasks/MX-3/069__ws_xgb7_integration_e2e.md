# Tâche — Test d'intégration E2E XGBoost dans le pipeline

Statut : DONE
Ordre : 069
Workstream : WS-XGB-7
Milestone : MX-3
Gate lié : G-XGB-Integration

## Contexte

Le gate G-XGB-Ready (tâche #068) a validé le modèle XGBoost en isolation (fit, predict, save, load, déterminisme). Il faut maintenant valider son fonctionnement dans le pipeline complet : features → splits → scaling → fit → predict → calibration θ → backtest → métriques → artefacts.

Le pipeline commun (`ai_trading/pipeline/runner.py`) supporte déjà `"xgboost_reg"` via `MODEL_REGISTRY`, `VALID_STRATEGIES` et `STRATEGY_FRAMEWORK_MAP`. Aucune modification du code source n'est attendue — seul un fichier de test d'intégration est à créer.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-7.1)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§8.1–§8.4, §12.2)
- Spécification pipeline : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§10, §11, §12, §14, §15)
- Code : `ai_trading/pipeline/runner.py`, `ai_trading/models/xgboost.py`
- Tests existants : `tests/test_runner.py` (modèle dummy), `tests/test_xgboost_model.py` (unitaires)

Dépendances :
- Tâche 068 — Gate G-XGB-Ready (doit être DONE)

## Objectif

Créer `tests/test_xgboost_integration.py` avec un test d'intégration E2E qui exécute un pipeline complet avec `strategy.name: "xgboost_reg"` sur données synthétiques (~500 bougies). Le test valide la chaîne complète sans crash et vérifie la conformité des artefacts produits.

## Règles attendues

- **Données synthétiques** : fixture CI avec ~500 bougies OHLCV générées par RNG (pas de réseau).
- **Config-driven** : config de test dérivée de `default.yaml` avec `strategy.name: "xgboost_reg"`, paramètres XGBoost réduits pour la performance des tests CI (`n_estimators: 10`, `max_depth: 3`).
- **Anti-fuite** : le test ne vérifie pas l'anti-fuite (tâche #070). Il vérifie uniquement le bon fonctionnement E2E.
- **Reproductibilité** : seed fixée, le test est déterministe.
- **Isolation** : le test utilise `tmp_path` pour les artefacts, aucune dépendance à `data/raw/`.

## Évolutions proposées

- Créer `tests/test_xgboost_integration.py` avec une classe `TestXGBoostE2E`.
- Fixture : générer un DataFrame OHLCV synthétique (~500 bougies, 1h), écrire un fichier Parquet temporaire.
- Fixture config : surcharger `default.yaml` avec `strategy.name: "xgboost_reg"`, `models.xgboost.n_estimators: 10`, `models.xgboost.max_depth: 3`, `walk_forward.n_folds: 2` pour la vitesse.
- Test principal : exécuter `run_pipeline()` (ou l'orchestrateur) et vérifier :
  1. Run sans crash.
  2. `manifest.json` existe et est valide (JSON Schema).
  3. `strategy.name == "xgboost_reg"` dans le manifest.
  4. `strategy.framework == "xgboost"` dans le manifest.
  5. `metrics.json` existe et est valide (JSON Schema).
  6. Métriques de prédiction non nulles (MAE > 0, RMSE > 0, DA ∈ [0,1]).
  7. Métriques de trading présentes.
  8. Au moins 1 fold complété.
  9. Fichier `xgboost_model.json` présent dans chaque fold.
  10. Fichier `trades.csv` présent dans chaque fold.

## Critères d'acceptation

- [x] `tests/test_xgboost_integration.py` créé avec classe `TestXGBoostE2E`.
- [x] Run E2E XGBoost sans crash sur données synthétiques (~500 bougies).
- [x] `manifest.json` valide JSON Schema, `strategy.name == "xgboost_reg"`, `strategy.framework == "xgboost"`.
- [x] `metrics.json` valide JSON Schema, métriques de prédiction non nulles.
- [x] Métriques de trading présentes et cohérentes.
- [x] Au moins 1 fold complété.
- [x] Fichier modèle XGBoost présent dans `model_artifacts/` de chaque fold (sauvé via `trainer.save(run_dir / "model")`).
- [x] Config de test avec `n_estimators: 10`, `max_depth: 3` pour performance CI.
- [x] Seed fixée, test déterministe.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/069-xgb-integration-e2e` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/069-xgb-integration-e2e` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-7] #069 RED: tests intégration E2E XGBoost` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-XGB-7] #069 GREEN: intégration E2E XGBoost validée`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-7] #069 — Intégration E2E XGBoost`.
