# Tâche — Data loader : découverte et validation des runs

Statut : TODO
Ordre : 074
Workstream : WS-D-1
Milestone : MD-1
Gate lié : N/A

## Contexte
Le module `data_loader.py` est le cœur du chargement de données du dashboard. Il factorise la logique existante de `scripts/compare_runs.py` et fournit les fonctions de découverte, validation et chargement des artefacts JSON/YAML de chaque run.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (WS-D-1.2)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§4.1, §4.2, §4.3)
- Code : `scripts/dashboard/data_loader.py` (à implémenter), `scripts/compare_runs.py` (logique à factoriser)

Dépendances :
- Tâche 073 — Structure projet et dépendances dashboard (doit être DONE)

## Objectif
Implémenter dans `data_loader.py` les fonctions de découverte des runs valides, de chargement et validation de `metrics.json`, `manifest.json` et `config_snapshot.yaml`, en factorisant la logique de `scripts/compare_runs.py`.

## Règles attendues
- **DRY** : factoriser `load_metrics()` et la validation des clés depuis `scripts/compare_runs.py` — pas de duplication de logique (spec §10.2).
- **Strict code** : validation explicite des clés requises (`run_id`, `strategy`, `aggregate`) avec `raise` si manquantes — pas de fallback silencieux.
- **Dégradation contrôlée** : les runs invalides (JSON cassé, clés manquantes) sont signalés (logging) mais ne bloquent pas le chargement des autres runs (spec §4.3).
- Exclusion des runs `strategy.name == "dummy"` (spec §4.3).

## Évolutions proposées
- Implémenter `discover_runs(runs_dir: Path) -> list[dict]` : scan de `runs/`, filtrage par présence de `metrics.json` valide, exclusion dummy.
- Implémenter `load_run_manifest(run_dir: Path) -> dict` : chargement et validation de `manifest.json`.
- Implémenter `load_run_metrics(run_dir: Path) -> dict` : chargement et validation de `metrics.json` (clés requises : `run_id`, `strategy`, `aggregate`).
- Implémenter `load_config_snapshot(run_dir: Path) -> dict` : chargement de `config_snapshot.yaml`.
- Refactoriser `scripts/compare_runs.py` pour importer depuis `data_loader.py` (ou module commun).

## Critères d'acceptation
- [ ] `discover_runs()` découvre les runs valides et exclut les runs dummy.
- [ ] `load_run_metrics()` valide les clés `run_id`, `strategy`, `aggregate` et lève une exception si manquantes.
- [ ] `load_run_manifest()` charge et retourne le contenu de `manifest.json`.
- [ ] `load_config_snapshot()` charge et retourne le contenu de `config_snapshot.yaml`.
- [ ] Runs invalides (JSON cassé, fichier absent) signalés par logging sans bloquer les autres.
- [ ] Logique DRY avec `scripts/compare_runs.py` (pas de duplication).
- [ ] Tests unitaires : run valide, run invalide (JSON cassé), run dummy exclu, répertoire vide, `metrics.json` manquant.
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/074-wsd1-data-loader-discovery` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/074-wsd1-data-loader-discovery` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-D-1] #074 RED: tests data loader découverte et validation runs` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-D-1] #074 GREEN: data loader découverte et validation runs`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-1] #074 — Data loader découverte et validation runs`.
