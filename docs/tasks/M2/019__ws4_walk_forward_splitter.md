# Tâche — Walk-forward splitter

Statut : DONE
Ordre : 019
Workstream : WS-4
Milestone : M2
Gate lié : G-Split

## Contexte
Le splitter walk-forward découpe les samples en folds train/val/test avec des bornes calculées en dates UTC. C'est le composant central du protocole d'évaluation : il garantit la causalité temporelle et la disjonction des ensembles.

Références :
- Plan : `docs/plan/implementation.md` (WS-4.5, schéma temporel, exemple numérique, conventions des bornes)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§8.1, §8.3, Annexe E.2.1)
- Config : `configs/default.yaml` (section `splits.*`)
- Code : `ai_trading/data/splitter.py` (à créer), `ai_trading/data/timeframes.py` (helper existant)

Dépendances :
- Tâche 016 — Sample builder (doit être DONE)

## Objectif
Implémenter le rolling walk-forward splitter dans `ai_trading/data/splitter.py` :
1. Calculer les bornes temporelles en dates UTC pour chaque fold k.
2. Extraire la validation comme sous-intervalle temporal final du train (`val_frac_in_train`).
3. Appliquer la politique de troncation (fold dont `test_end > dataset.end` → supprimé).
4. Appliquer le filtrage par samples minimum (`min_samples_train`, `min_samples_test`).
5. Assertion : aucun fold valide → `ValueError`.
6. Logger les compteurs de folds (`n_folds_theoretical`, `n_folds_valid`, `n_folds_excluded`).
7. Retourner un itérateur de folds avec indices/masques + bornes UTC + compteurs.

## Règles attendues
- **Config-driven** : tous les paramètres (`train_days`, `test_days`, `step_days`, `val_frac_in_train`, `embargo_bars`, `min_samples_train`, `min_samples_test`) lus depuis `config.splits`.
- **Anti-fuite** : aucun timestamp test ne doit apparaître dans train/val d'un même fold.
- **Strict code** : 0 folds valides → `ValueError("No valid folds: dataset too short for the given split parameters")`.
- **Strict code** : fold avec `N_train < min_samples_train` ou `N_test < min_samples_test` → exclu avec warning loggé.
- **Convention des bornes** : `dataset.start` inclusif, `dataset.end` exclusif. Bornes de fold inclusives (premier et dernier timestamp).

## Évolutions proposées
- Créer `ai_trading/data/splitter.py` avec :
  - `WalkForwardSplitter(config)` — classe ou fonction.
  - `split(timestamps) -> list[FoldInfo]` — retourne les folds avec indices train/val/test + bornes UTC + compteurs N.
  - Utiliser `parse_timeframe()` de `ai_trading/data/timeframes.py` pour convertir le timeframe en timedelta.
- Chaque `FoldInfo` contient : `train_indices`, `val_indices`, `test_indices`, bornes UTC (`train_start`, `train_only_end`, `val_start`, `train_val_end`, `test_start`, `test_end`), compteurs (`n_train`, `n_val`, `n_test`).
- Calcul des bornes conformément à l'exemple numérique du plan :
  - `train_start[k] = dataset.start + k * step_days`
  - `train_val_end[k] = train_start[k] + train_days - Δ`
  - `val_days = floor(train_days * val_frac_in_train)`
  - `val_start[k] = train_start[k] + (train_days - val_days)`
  - `test_start[k] = train_start[k] + train_days + embargo_bars * Δ`
  - `test_end[k] = test_start[k] + test_days - Δ`

## Critères d'acceptation
- [x] Folds disjoints : aucun timestamp de décision commun entre train/val/test d'un même fold.
- [x] Nombre de folds : `n_folds_valid <= n_folds_max` et `n_folds_valid >= 1` (borne supérieure théorique).
- [x] Bornes UTC correctes conformément à l'exemple numérique du plan (fold k=0, paramètres MVP).
- [x] `val_days = floor(train_days * val_frac_in_train)` calculé correctement.
- [x] Test de troncation : fold dont `test_end > dataset.end` est exclu.
- [x] Test de bord : période totale non multiple exact de `step_days` → formule correcte.
- [x] Test dates : bornes de split en dates UTC, un gap de données ne décale pas les bornes.
- [x] Test `min_samples` : fold avec trop peu de samples → exclu avec warning.
- [x] Test 0 folds valides → `ValueError`.
- [x] Test `parse_timeframe` : `"1h"` → `timedelta(hours=1)`, `"4h"` → `timedelta(hours=4)`, `"invalid"` → `ValueError`.
- [x] Compteurs loggés : `n_folds_theoretical == n_folds_valid + n_folds_excluded`.
- [x] Tous les paramètres lus depuis la config.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/019-walk-forward-splitter` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/019-walk-forward-splitter` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-4] #019 RED: tests walk-forward splitter`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-4] #019 GREEN: walk-forward splitter`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-4] #019 — Walk-forward splitter`.
