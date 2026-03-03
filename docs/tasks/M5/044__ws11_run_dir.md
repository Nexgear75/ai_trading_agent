# Tâche — Arborescence du run (run_dir)

Statut : DONE
Ordre : 044
Workstream : WS-11
Milestone : M5
Gate lié : M5

## Contexte
Le pipeline doit produire une arborescence de sortie canonique pour chaque run, conforme à §15.1. Ce module crée la structure de répertoires et fournit les fonctions utilitaires pour y écrire les artefacts.

Références :
- Plan : `docs/plan/implementation.md` (WS-11.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§15.1)
- Code : `ai_trading/artifacts/run_dir.py`

Dépendances :
- Tâche 002 — Config loader (doit être DONE, pour `artifacts.output_dir`)

## Objectif
Implémenter le module `ai_trading/artifacts/run_dir.py` qui crée l'arborescence canonique d'un run :

```
runs/<run_id>/
├── manifest.json
├── metrics.json
├── config_snapshot.yaml
├── folds/
│   ├── fold_00/
│   │   ├── preds_val.csv
│   │   ├── preds_test.csv
│   │   ├── trades.csv
│   │   ├── equity_curve.csv
│   │   ├── metrics_fold.json
│   │   └── model_artifacts/
│   ├── fold_01/
│   │   └── ...
│   └── ...
├── equity_curve.csv          (optionnel, stitched global)
└── pipeline.log              (si logging.file configuré)
```

Le `run_id` suit la convention `YYYYMMDD_HHMMSS_<strategy>`.

## Règles attendues
- Config-driven : le répertoire racine est lu depuis `config.artifacts.output_dir` (pas de chemin hardcodé).
- Strict code : si le répertoire parent n'existe pas, lever une erreur explicite (pas de `mkdir -p` silencieux sur le parent).
- Le `run_id` est généré de manière déterministe à partir de la date UTC courante et du nom de stratégie.
- Le fichier `config_snapshot.yaml` est la config **fully resolved** (après merge defaults + custom + overrides CLI).
- La génération de `report.html` / `report.pdf` est reportée post-MVP.

## Évolutions proposées
- Fonction `create_run_dir(config, strategy_name, n_folds) -> Path` qui crée toute l'arborescence et retourne le chemin du `run_dir`.
- Fonction `generate_run_id(strategy_name) -> str` pour le format `YYYYMMDD_HHMMSS_<strategy>`.
- Fonction `save_config_snapshot(run_dir, config)` pour écrire le `config_snapshot.yaml`.
- Chaque sous-répertoire `folds/fold_XX/model_artifacts/` est créé.

## Critères d'acceptation
- [x] Le module `ai_trading/artifacts/run_dir.py` existe et est importable.
- [x] `create_run_dir` crée l'arborescence conforme à §15.1 (répertoires `folds/fold_XX/`, `model_artifacts/`).
- [x] `generate_run_id` retourne un identifiant conforme au format `YYYYMMDD_HHMMSS_<strategy>`.
- [x] `save_config_snapshot` écrit le fichier YAML correctly resolved dans le `run_dir`.
- [x] Le nombre de sous-répertoires fold correspond au paramètre `n_folds`.
- [x] Erreur explicite si `output_dir` n'est pas un répertoire existant (ou créable).
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/044-run-dir` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/044-run-dir` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-11] #044 RED: tests arborescence run_dir`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-11] #044 GREEN: arborescence run_dir`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-11] #044 — Arborescence du run (run_dir)`.
