# Tâche — Fold trainer (orchestration fit/predict par fold)

Statut : TODO
Ordre : 028
Workstream : WS-6
Milestone : M3
Gate lié : G-Doc

## Contexte
Le trainer est l'orchestrateur d'entraînement par fold. Il enchaîne scaling → fit → predict → save sans contenir de logique spécifique au modèle. Il passe systématiquement `meta_train`, `meta_val` et `ohlcv` à tous les modèles (les supervisés les ignorent, le RL les utilise). L'early stopping est délégué au modèle via `fit()`. Le trainer est le seul responsable du scaling (l'orchestrateur WS-12.2 ne touche pas au scaling).

Références :
- Plan : `docs/plan/implementation.md` (WS-6.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§10.3)
- Code : `ai_trading/training/trainer.py` (à créer)

Dépendances :
- Tâche 025 — DummyModel (doit être DONE) — pour tester le workflow E2E
- Tâche 021 — WS-5 standard scaler (doit être DONE) — pour le scaling
- Tâche 016 — WS-4 sample builder (doit être DONE) — pour les données (N, L, F)

## Objectif
Implémenter le module `ai_trading/training/trainer.py` qui orchestre le workflow d'entraînement par fold : scaling des features, appel à `model.fit()`, prédictions val/test, et sauvegarde du modèle.

## Règles attendues
- **Anti-fuite** : scaler fit sur `X_train` uniquement, puis transform appliqué à train/val/test. Jamais de fit sur val ou test.
- **Strict code** : pas de fallback si le scaler ou le modèle échoue — propager l'erreur.
- **Config-driven** : `training.early_stopping_patience` lu depuis la config et transmis au modèle.
- **Séparation des responsabilités** : le trainer orchestre (scale → fit → predict → save), il ne fait PAS de boucle epoch — c'est le modèle qui gère.

## Évolutions proposées

### 1. Classe ou fonction `FoldTrainer` dans `ai_trading/training/trainer.py`
- **Scaling** (responsabilité exclusive du trainer) :
  1. `scaler.fit(X_train)` — fit uniquement sur train
  2. `X_train = scaler.transform(X_train)`
  3. `X_val = scaler.transform(X_val)`
  4. `X_test = scaler.transform(X_test)`
- **Fit** : `model.fit(X_train, y_train, X_val, y_val, config, run_dir, meta_train, meta_val, ohlcv)`
  - Passer systématiquement `meta_train`, `meta_val`, `ohlcv` (le modèle les ignore ou les utilise selon son type)
  - Patience configurable via `config.training.early_stopping_patience`
- **Predict** : `y_hat_val = model.predict(X_val)`, `y_hat_test = model.predict(X_test)`
  - Le trainer retourne `(y_hat_val, y_hat_test)` à l'appelant
  - Le trainer ne génère PAS les fichiers `preds_val.csv` / `preds_test.csv` (responsabilité de l'orchestrateur)
- **Save** : `model.save(run_dir / "model")`

### 2. Retour structuré
- Le trainer retourne un objet/dict contenant : `y_hat_val`, `y_hat_test`, `artifacts` (retour de `model.fit()`), `scaler` (pour traçabilité)

## Critères d'acceptation
- [ ] Le trainer orchestre correctement le workflow complet (scale → fit → predict → save) avec DummyModel sans crash
- [ ] Scaling : `scaler.fit()` appelé sur `X_train` uniquement — vérifiable par inspection ou mock
- [ ] Scaling : `scaler.transform()` appliqué à train, val et test
- [ ] `model.fit()` reçoit les bons arguments, y compris `meta_train`, `meta_val`, `ohlcv`
- [ ] Prédictions `y_hat_val` et `y_hat_test` retournées avec shapes correctes `(N_val,)` et `(N_test,)`
- [ ] Paramètre `patience` configurable et transmis au modèle via config
- [ ] `model.save()` appelé après le fit
- [ ] Anti-fuite : test vérifiant que le scaler n'est PAS fit sur val ou test (perturbation test)
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/028-fold-trainer` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/028-fold-trainer` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-6] #028 RED: tests fold trainer scale/fit/predict/save` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-6] #028 GREEN: fold trainer orchestration`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-6] #028 — Fold trainer (orchestration fit/predict par fold)`.
