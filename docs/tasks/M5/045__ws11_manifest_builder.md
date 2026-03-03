# Tâche — Manifest builder

Statut : DONE
Ordre : 045
Workstream : WS-11
Milestone : M5
Gate lié : M5

## Contexte
Le fichier `manifest.json` est le registre du run. Il documente l'identité du run, la configuration, le dataset, les splits, la stratégie, les coûts, l'environnement d'exécution et la liste des artefacts générés. Ce module le construit et le sérialise conformément au schéma Annexe A.

Références :
- Plan : `docs/plan/implementation.md` (WS-11.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§15.2, Annexe A, Annexe C.1, Annexe E.2.1)
- Schéma : `docs/specifications/manifest.schema.json`
- Exemple : `docs/specifications/example_manifest.json`
- Code : `ai_trading/artifacts/manifest.py`

Dépendances :
- Tâche 044 — Arborescence run_dir (doit être DONE)
- Tâche 019 — Walk-forward splitter (doit être DONE, pour les bornes de splits)
- Tâche 004 — Ingestion OHLCV (doit être DONE, pour SHA-256 des fichiers raw)

## Objectif
Implémenter le module `ai_trading/artifacts/manifest.py` qui construit le `manifest.json` à partir de :
- La config (fully resolved).
- Les métadonnées dataset (SHA-256 des fichiers raw parquet, n_rows).
- Les splits (bornes par fold — la période `train` correspond à `train_only`, excluant la portion val, cf. E.2.1).
- La stratégie (name, type, framework dérivé automatiquement, hyperparams, thresholding).
- Les coûts.
- L'environnement (python_version, platform, packages).
- Le commit Git courant (`git rev-parse HEAD` ; valeur `"unknown"` si hors dépôt Git — exception documentée au strict-no-fallback, loggée au WARNING).
- La version du pipeline (`ai_trading.__version__`).
- La liste des artefacts et leurs chemins relatifs.
- Le champ conditionnel `artifacts.files.pipeline_log` si `config.logging.file != null`.

## Règles attendues
- Strict code : toutes les données d'entrée (config, splits, dataset info) sont requises — pas de valeurs par défaut silencieuses.
- Le champ `strategy.framework` est dérivé automatiquement par l'orchestrateur (mapping interne), pas lu depuis la config YAML.
- La période `train` de chaque fold exclut la période `val` (bornes disjointes, cf. E.2.1).
- Le commit Git `"unknown"` est une exception documentée : loggée explicitement au WARNING, jamais silencieuse.
- Le JSON produit doit être valide contre `manifest.schema.json` (Draft 2020-12).

## Évolutions proposées
- Fonction `build_manifest(run_id, config, dataset_info, splits_info, strategy_info, costs_info, environment_info, artifacts_info, git_commit, pipeline_version) -> dict`.
- Fonction `write_manifest(manifest_data, run_dir)` pour écrire le fichier JSON.
- Fonction `get_git_commit() -> str` pour obtenir le hash Git courant.
- Mapping interne `STRATEGY_FRAMEWORK_MAP` pour dériver `strategy.framework` à partir de `strategy.name`.

## Critères d'acceptation
- [x] Le module `ai_trading/artifacts/manifest.py` existe et est importable.
- [x] Le JSON produit est valide contre `manifest.schema.json` (test via `jsonschema.validate()`).
- [x] La période `train` de chaque fold exclut la période `val` (bornes disjointes).
- [x] Le champ `git_commit` est présent et contient un hash hexadécimal valide ou `"unknown"`.
- [x] Le champ `pipeline_version` est présent et correspond à `ai_trading.__version__`.
- [x] Si `config.logging.file != null`, le champ `artifacts.files.pipeline_log` est présent dans le manifest.
- [x] Le champ `strategy.framework` est correctement dérivé pour chaque stratégie MVP (dummy, no_trade, buy_hold, sma_rule).
- [x] Tests couvrent les scénarios nominaux + erreurs + bords (git absent, pipeline_log conditionnel).
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/045-manifest-builder` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/045-manifest-builder` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-11] #045 RED: tests manifest builder`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-11] #045 GREEN: manifest builder`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-11] #045 — Manifest builder`.
