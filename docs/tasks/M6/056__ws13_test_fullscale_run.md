# Tâche — Test full-scale `make run-all` sur données réelles BTCUSDT

Statut : TODO
Ordre : 056
Workstream : WS-13
Milestone : M6
Gate lié : M6

## Contexte
Le pipeline complet doit être validé sur données réelles BTCUSDT téléchargées depuis Binance (~73 000 bougies horaires, 2017–2026). Ce test d'intégration grandeur nature utilise un accès réseau réel (pas de fixtures ni mocks) et exécute `make run-all CONFIG=configs/fullscale_btc.yaml` via `subprocess`. Le test est marqué `@pytest.mark.fullscale` et skipped par défaut pour ne pas bloquer la suite de tests standard.

Références :
- Plan : `docs/plan/implementation.md` (WS-13.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§3, §17.3)
- Code : `ai_trading/pipeline/runner.py`, `Makefile`

Dépendances :
- Tâche 055 — Config fullscale_btc.yaml (doit être DONE)
- Milestone M5 complet (pipeline fonctionnel bout-en-bout)

## Objectif
Créer le fichier de test `tests/test_fullscale_btc.py` avec un test marqué `@pytest.mark.fullscale` qui exécute le pipeline complet sur données réelles et valide la production de tous les artefacts attendus.

## Règles attendues
- Accès réseau réel obligatoire : aucune fixture `tmp_path`, aucun mock de données. Les chemins réels de `configs/fullscale_btc.yaml` sont utilisés.
- Le marker `fullscale` doit être enregistré dans `pyproject.toml` et exclu des runs par défaut (`addopts` modifié pour ajouter `-m "not fullscale"`).
- Timeout de 600 secondes pour le test (le téléchargement initial peut être long).
- Le test ne doit jamais être exécuté dans la CI standard (uniquement sur demande explicite via `pytest -m fullscale`).

## Évolutions proposées
- Enregistrer le marker `fullscale` dans `pyproject.toml` (section `[tool.pytest.ini_options]`, clé `markers`).
- Modifier `addopts` dans `pyproject.toml` pour exclure les tests fullscale par défaut : `addopts = "-v --tb=short -m \"not fullscale\""`.
- Créer `tests/test_fullscale_btc.py` avec :
  - Un test `test_fullscale_run_all` marqué `@pytest.mark.fullscale` qui :
    1. Exécute `make run-all CONFIG=configs/fullscale_btc.yaml` via `subprocess.run`.
    2. Vérifie le code retour == 0.
    3. Vérifie que le fichier Parquet de données a ≥ 70 000 lignes.
    4. Vérifie que le run directory le plus récent contient `manifest.json` et `metrics.json`.
    5. Vérifie que `manifest.json` et `metrics.json` sont valides (JSON Schema).
    6. Vérifie qu'au moins 1 fold est complété.
    7. Vérifie la présence de `equity_curve_stitched.csv`.
    8. Vérifie la présence de `config_snapshot.yaml`.
    9. Vérifie que chaque fold contient `metrics.json` et `trades.csv`.

## Critères d'acceptation
- [ ] Marker `fullscale` enregistré dans `pyproject.toml`.
- [ ] `addopts` exclut les tests fullscale par défaut (`-m "not fullscale"`).
- [ ] `tests/test_fullscale_btc.py` existe avec test marqué `@pytest.mark.fullscale`.
- [ ] `pytest` standard (sans `-m fullscale`) n'exécute PAS les tests fullscale.
- [ ] `pytest -m fullscale tests/test_fullscale_btc.py -v --timeout=600` passe en GREEN avec accès réseau.
- [ ] Le run directory contient tous les artefacts attendus : `manifest.json`, `metrics.json`, `equity_curve_stitched.csv`, `config_snapshot.yaml`.
- [ ] Au moins 1 fold complété avec `metrics.json` et `trades.csv` par fold.
- [ ] Fichier Parquet de données contient ≥ 70 000 lignes.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests standard verte après implémentation (les tests fullscale ne sont pas exécutés par défaut).
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/056-test-fullscale-run` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/056-test-fullscale-run` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-13] #056 RED: test fullscale make run-all BTCUSDT`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-13] #056 GREEN: test fullscale make run-all BTCUSDT`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-13] #056 — Test full-scale make run-all BTCUSDT`.
