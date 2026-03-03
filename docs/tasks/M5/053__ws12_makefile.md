# Tâche — Makefile (pilotage du pipeline)

Statut : TODO
Ordre : 053
Workstream : WS-12
Milestone : M5
Gate lié : M5

## Contexte
Le Makefile est l'interface utilisateur principale du pipeline (§17.3). Il expose les cibles de build, exécution, test, lint, Docker, et toutes les cibles de gate (milestone et intra-milestone). Les variables `CONFIG`, `MODEL`, `SEED` sont surchargeables. Le Makefile implémente les dépendances inter-gates.

Références :
- Plan : `docs/plan/implementation.md` (WS-12.6)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§17.3)
- Code : `Makefile`

Dépendances :
- Tâche 051 — Dockerfile et CI (doit être DONE)

## Objectif
Créer le `Makefile` à la racine du projet avec les cibles suivantes :

### Cibles principales
- `install` : `pip install -r requirements.txt`
- `fetch-data` : `python -m ai_trading fetch --config $(CONFIG)`
- `qa` : `python -m ai_trading qa --config $(CONFIG)`
- `run` : `python -m ai_trading run --config $(CONFIG)` (+ surcharges `MODEL`, `SEED` si définis)
- `run-all` : enchaîne `fetch-data → qa → run`

### Utilitaires
- `test` : `pytest tests/ -v`
- `lint` : `ruff check ai_trading/ tests/` (+ mypy si configuré)
- `docker-build` : `docker build -t ai-trading-pipeline .`
- `docker-run` : `docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/runs:/app/runs ai-trading-pipeline`
- `clean` : supprime les artefacts temporaires (pas les données)
- `help` : affiche la liste des cibles via grep sur les commentaires `##`

### Cibles de gate milestone
- `gate-m1` à `gate-m5` : exécutent les vérifications automatisables et génèrent `reports/gate_report_M<N>.json`

### Cibles de gate intra-milestone
- `gate-features` : pytest ciblé features + couverture ≥ 90%
- `gate-split` : pytest ciblé dataset/splitter + couverture ≥ 90%
- `gate-backtest` : pytest ciblé backtest + couverture ≥ 90%
- `gate-doc` : pytest ciblé training/calibration + couverture ≥ 90%
- `gate-perf` : benchmarks post-MVP (non bloquant)

### Variables surchargeables
- `CONFIG` (défaut : `configs/default.yaml`)
- `MODEL` (surcharge de `strategy.name`)
- `SEED` (surcharge de `reproducibility.global_seed`)

### Dépendances inter-gates
GM1 → G-Features → G-Split → GM2 → G-Doc → GM3 → G-Backtest → GM4 → GM5

## Règles attendues
- Les surcharges `MODEL` et `SEED` sont passées en override CLI `--set` au script Python.
- La cible `help` utilise le pattern grep sur les commentaires `##`.
- Chaque cible de gate génère un fichier `reports/gate_report_<ID>.json`.
- Les dépendances inter-gates sont respectées dans le Makefile.

## Évolutions proposées
- Fichier `Makefile` unique à la racine.
- Répertoire `reports/` créé automatiquement par les cibles de gate.
- Convention de commentaires `##` pour l'aide inline.

## Critères d'acceptation
- [ ] `make help` affiche la liste des cibles disponibles.
- [ ] `make install` installe les dépendances de `requirements.txt`.
- [ ] `make test` lance `pytest tests/ -v`.
- [ ] `make lint` lance `ruff check ai_trading/ tests/`.
- [ ] `make run CONFIG=configs/default.yaml` lance le pipeline.
- [ ] `make fetch-data` déclenche l'ingestion.
- [ ] `make run-all` enchaîne fetch → qa → run.
- [ ] `make docker-build` et `make docker-run` fonctionnent.
- [ ] Les variables `CONFIG`, `MODEL`, `SEED` sont surchargeables.
- [ ] `make gate-m1` à `make gate-m5` exécutent les vérifications et génèrent les rapports JSON.
- [ ] `make gate-features`, `make gate-split`, `make gate-backtest`, `make gate-doc` fonctionnent.
- [ ] Les dépendances inter-gates sont respectées (`gate-features` échoue si `gate-m1` n'est pas GO, etc.).
- [ ] Tests couvrent les scénarios nominaux (vérification syntaxique du Makefile, cibles help).
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/053-makefile` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/053-makefile` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-12] #053 RED: tests Makefile`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-12] #053 GREEN: Makefile`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-12] #053 — Makefile (pilotage du pipeline)`.
