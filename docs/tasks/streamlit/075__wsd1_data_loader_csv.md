# Tâche — Data loader : chargement des CSV (equity, trades, prédictions)

Statut : TODO
Ordre : 075
Workstream : WS-D-1
Milestone : MD-1
Gate lié : N/A

## Contexte
Le dashboard exploite plusieurs fichiers CSV produits par le pipeline : equity curves (stitchée et par fold), trades (par fold, concaténés), prédictions (par fold et split), et métriques par fold. Ces fichiers sont optionnels — le dashboard doit fonctionner en mode dégradé si certains sont absents.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (WS-D-1.3)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§4.2, §6.3, §6.5, §6.6, §8.2, §8.3)
- Code : `scripts/dashboard/data_loader.py` (extension)

Dépendances :
- Tâche 074 — Data loader découverte et validation runs (doit être DONE)

## Objectif
Étendre `data_loader.py` avec les fonctions de chargement des fichiers CSV conditionnels : equity curves (stitchée et par fold), trades (concaténation multi-fold avec colonne `fold` et colonne calculée `costs`), prédictions (val/test), et métriques par fold (`metrics_fold.json`).

## Règles attendues
- **Dégradation gracieuse** : retourner `None` pour chaque fichier absent — pas d'exception (spec §4.2).
- **Strict code** : validation des colonnes attendues après chargement — `raise` si colonnes obligatoires manquantes sur un fichier existant.
- Colonne `fold` déduite du chemin lors de la concaténation des trades (spec §6.6).
- Colonne calculée `costs = fees_paid + slippage_paid` (spec §6.6).

## Évolutions proposées
- Implémenter `load_equity_curve(run_dir: Path) -> pd.DataFrame | None` : chargement de `equity_curve.csv` stitché. Colonnes : `time_utc`, `equity`, `in_trade`, `fold`.
- Implémenter `load_fold_equity_curve(fold_dir: Path) -> pd.DataFrame | None` : chargement de `folds/fold_XX/equity_curve.csv`. Colonnes : `time_utc`, `equity`, `in_trade`.
- Implémenter `load_trades(run_dir: Path) -> pd.DataFrame | None` : concaténation de tous les `folds/fold_XX/trades.csv` avec ajout colonne `fold`. Colonnes source : `entry_time_utc`, `exit_time_utc`, `entry_price`, `exit_price`, `entry_price_eff`, `exit_price_eff`, `f`, `s`, `fees_paid`, `slippage_paid`, `y_true`, `y_hat`, `gross_return`, `net_return`. Colonne calculée : `costs`.
- Implémenter `load_fold_trades(fold_dir: Path) -> pd.DataFrame | None` : chargement d'un `trades.csv` spécifique.
- Implémenter `load_predictions(fold_dir: Path, split: str) -> pd.DataFrame | None` : chargement de `preds_val.csv` ou `preds_test.csv`. Colonnes : `timestamp`, `y_true`, `y_hat`.
- Implémenter `load_fold_metrics(fold_dir: Path) -> dict | None` : chargement optionnel de `metrics_fold.json`. Retourne `None` si absent.

## Critères d'acceptation
- [ ] Chargement correct de chaque type de CSV avec les bons types de colonnes.
- [ ] Colonne `fold` ajoutée automatiquement lors de la concaténation des trades.
- [ ] Colonne `costs` calculée (`fees_paid + slippage_paid`).
- [ ] Retour `None` si fichier absent (pas d'exception).
- [ ] Validation des colonnes obligatoires sur fichier existant (exception si manquantes).
- [ ] Tests unitaires avec fixtures CSV synthétiques : fichier valide, fichier absent, colonnes manquantes, concaténation multi-fold.
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/075-wsd1-data-loader-csv` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/075-wsd1-data-loader-csv` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-D-1] #075 RED: tests data loader chargement CSV` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-D-1] #075 GREEN: data loader chargement CSV`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-1] #075 — Data loader chargement CSV`.
