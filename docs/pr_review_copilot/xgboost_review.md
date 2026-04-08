# PR Review — Add XGBoost model

**Branche** : `xgboost`
**Date** : 8 avril 2026
**Verdict** : REQUEST CHANGES

## Grille d'audit

### Structure branche & commits
- [ ] Branche `task/NNN-short-slug` depuis `Max6000i1`.
  > Branche nommée `xgboost` (pas de préfixe `task/NNN`), créée depuis `main`.
- [ ] Commit RED : `[WS-X] #NNN RED: <résumé>` (tests uniquement).
  > Pas de commit RED (aucun test écrit avant l'implémentation).
- [ ] Commit GREEN : `[WS-X] #NNN GREEN: <résumé>` (implémentation + tâche).
  > Commit unique, pas de convention RED/GREEN.
- [ ] Pas de commits parasites entre RED et GREEN.
  > N/A — un seul commit.

### Tâche associée
- [ ] `docs/tasks/NNN__slug.md` : statut DONE.
  > Aucune tâche associée dans docs/tasks/.
- [ ] Critères d'acceptation cochés `[x]`.
  > N/A.
- [ ] Checklist cochée `[x]`.
  > N/A.

### Tests
- [ ] Convention de nommage (`test_config.py`, `test_features.py`, etc.).
  > **Aucun test écrit.** Pas de `tests/test_xgboost*.py`.
- [ ] Couverture des critères d'acceptation.
  > N/A — pas de tests.
- [ ] Cas nominaux + erreurs + bords.
  > N/A.
- [ ] `pytest` GREEN, 0 échec.
  > N/A.
- [x] `ruff check ai_trading/ tests/` clean.
  > **Non** — 3 erreurs ruff (voir remarques 1 et 2).
- [N/A] Données synthétiques (pas réseau).
- [N/A] Tests déterministes (seeds fixées).

### Strict code (no fallbacks)
- [x] Aucun `or default`, `value if value else default`.
- [x] Aucun `except` trop large.
- [x] Validation explicite + `raise`.
  > Les validations de timeframe sont déléguées à `get_timeframe_config` qui raise. OK.

### Config-driven
- [ ] Paramètres dans `configs/default.yaml`, pas hardcodés.
  > Hyperparamètres XGBoost (`n_estimators=1000`, `max_depth=6`, `learning_rate=0.05`, `early_stopping_rounds=50`) hardcodés en defaults de `train()`. Les autres modèles ont le même pattern, mais la spec demande config-driven. Voir remarque 5.
- [x] Formules conformes à la spec.
  > Forward return et fenêtres identiques au CNN.

### Anti-fuite (look-ahead)
- [x] Données point-in-time.
- [N/A] Embargo `embargo_bars >= H` (§8.2).
- [x] Scaler fit sur train uniquement.
- [x] Splits train < val < test.
  > Split temporel chronologique, pas de shuffle. OK.
- [x] Features backward-looking.
- [N/A] θ calibré sur val, pas test.

### Reproductibilité
- [x] Seeds fixées et tracées.
  > `random_state=42` dans XGBRegressor. OK.
- [N/A] Hashes SHA-256 si applicable.

### Float conventions
- [N/A] Float32 pour tenseurs X_seq, y.
  > XGBoost utilise ses propres types internes. N/A.
- [x] Float64 pour métriques.
  > `compute_metrics` utilise numpy float64 par défaut. OK.

### Qualité
- [x] snake_case.
- [ ] Pas de print(), code mort, TODO orphelin.
  > `print()` utilisé partout (cohérent avec les autres modèles existants). Voir remarque 6.
- [ ] Imports propres.
  > `import numpy as np` inutilisé dans `evaluation.py`. Voir remarque 1.
- [ ] DRY : pas de duplication de logique.
  > Duplication significative de `data_preparator.py` (≈70% copié du CNN). Voir remarque 3.
  > `_get_checkpoint_paths` dupliqué dans 6 fichiers à travers le projet. Voir remarque 4.

## Remarques

1. **[BLOQUANT] ruff F401 — import inutilisé**
   - Fichier : `models/xgboost/evaluation.py`
   - Ligne(s) : 12
   - `import numpy as np` importé mais jamais utilisé.
   - Suggestion : Supprimer la ligne `import numpy as np`.

2. **[BLOQUANT] ruff F541 — f-strings sans placeholder**
   - Fichier : `models/xgboost/training.py` ligne 47, `models/xgboost/evaluation.py` ligne 74
   - `f"  ENTRAÎNEMENT XGBOOST"` et `f"  ÉVALUATION XGBOOST"` — f-strings sans substitution.
   - Suggestion : Retirer le préfixe `f` sur ces deux lignes.

3. **[WARNING] DRY — data_preparator.py duplique ~70% du CNN**
   - Fichier : `models/xgboost/data_preparator.py`
   - Ligne(s) : 10–103
   - Le chargement des données, calcul des forward returns, construction des fenêtres par symbole, clipping et scaling sont quasi-identiques au CNN `data_preparator.py`. La seule différence est le flatten 3D→2D et l'absence de conversion PyTorch.
   - Suggestion : Extraire la logique commune (load → windows → clip → scale) dans un helper partagé (ex : `utils/data_preparation.py`) et ne garder dans chaque `data_preparator.py` que la partie spécifique au modèle (reshape, tensor conversion).

4. **[WARNING] DRY — `_get_checkpoint_paths` dupliqué 6 fois**
   - Fichiers : `models/{cnn,cnn_bilstm_am,xgboost}/{training,evaluation}.py`
   - Même pattern copié/collé avec seulement le nom de dossier qui change.
   - Suggestion : Centraliser dans un helper (ex : `utils/paths.py`) avec signature `get_checkpoint_paths(model_name: str, timeframe: str)`.

5. **[WARNING] Config-driven — hyperparamètres hardcodés**
   - Fichier : `models/xgboost/training.py`
   - Ligne(s) : 25–31
   - `n_estimators=1000`, `max_depth=6`, `learning_rate=0.05` sont des defaults inline. Les modèles CNN ont des configs dans `config.py` (`get_cnn_config`), mais XGBoost n'a pas d'équivalent `get_xgboost_config(timeframe)`.
   - Suggestion : Ajouter un `XGBOOST_CONFIGS` dans `config.py` avec des profils par timeframe (comme `CNN_CONFIGS`), et une fonction `get_xgboost_config(timeframe)`.

6. **[MINEUR] Utilisation de `print()` au lieu de logging**
   - Fichiers : tous les fichiers XGBoost
   - Cohérent avec le reste du projet (CNN, CNN_BiLSTM_AM), mais en termes de qualité, `logging` serait préférable. Non bloquant car c'est le pattern existant.

7. **[BLOQUANT] Aucun test**
   - Aucun fichier `tests/test_xgboost*.py` n'existe.
   - Suggestion : Ajouter des tests couvrant au minimum :
     - `data_preparator.prepare_data` : shapes des arrays, clipping fit sur train only, pas de NaN
     - `training.train` : modèle entraîné sauvegardé, fichiers checkpoint créés
     - `evaluation.evaluate` : métriques retournées, graphiques générés
     - `evaluation.load_model` : charge un modèle sauvegardé sans erreur

8. **[MINEUR] Pas de vérification NaN dans data_preparator**
   - Fichier : `models/xgboost/data_preparator.py`
   - Le CNN `data_preparator` a un check NaN (lignes 70-72) qui a été omis dans la version XGBoost.
   - Suggestion : Ajouter le même check NaN après la concaténation des fenêtres.

## Résumé

L'implémentation réutilise correctement le pipeline de features existant (anti-fuite, scaling train-only, split temporel). Cependant, la PR ne peut pas être mergée en l'état : 3 erreurs ruff, aucun test, et une duplication significative avec le CNN `data_preparator`. Les hyperparamètres devraient aussi être centralisés dans `config.py` pour rester cohérent avec les conventions du projet.
