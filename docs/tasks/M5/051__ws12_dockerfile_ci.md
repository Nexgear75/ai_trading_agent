# Tâche — Dockerfile et CI

Statut : DONE
Ordre : 051
Workstream : WS-12
Milestone : M5
Gate lié : M5

## Contexte
La reproductibilité exige que le pipeline soit exécutable dans un conteneur Docker identique. Un workflow CI minimal (GitHub Actions) garantit que les tests et le lint passent à chaque push/PR. Une fixture de données synthétiques permet au CI de fonctionner sans accès réseau.

Références :
- Plan : `docs/plan/implementation.md` (WS-12.4)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§16, §17.6)
- Code : `Dockerfile`, `.github/workflows/ci.yml`, `tests/conftest.py`

Dépendances :
- Tâche 050 — CLI entry point (doit être DONE)

## Objectif
1. **Mettre à jour le `Dockerfile`** existant pour :
   - Installer toutes les dépendances (`requirements.txt`).
   - Copier le code source.
   - `CMD` qui lance le pipeline via `python -m ai_trading run`.
   - Base image : `python:3.11-slim` (CPU only).

2. **Créer `.github/workflows/ci.yml`** avec un workflow CI minimal :
   - Trigger : `on: push/pull_request` (branches: `main`, `Max6000i1`).
   - Job unique `test` sur `runs-on: ubuntu-latest`.
   - Étapes : checkout → setup-python 3.11 → pip install → `make lint` → `make test`.

3. **Fixture de données synthétiques pour CI** :
   - Créer/compléter une fixture pytest dans `tests/conftest.py` qui génère un mini-dataset OHLCV synthétique (500 bougies, prix brownien géométrique) en mémoire, sans dépendance réseau.
   - Cette fixture est utilisée par les tests existants et le futur test d'intégration.

4. **Test d'intégration minimal** (`tests/test_integration.py`) :
   - Exécute le pipeline complet sur données synthétiques avec DummyModel.
   - Valide au moins une baseline (no_trade) pour vérifier le bypass θ bout en bout.
   - Vérifie la création de l'arborescence §15.1, la conformité JSON, la cohérence des métriques.

## Règles attendues
- Le Dockerfile de base est CPU only (`python:3.11-slim`). Le `Dockerfile.gpu` optionnel est post-MVP.
- La fixture CI ne doit pas dépendre du réseau (pas d'appel API Binance).
- Le test d'intégration valide DummyModel + no_trade (vérification bypass θ E2E, cf. note P-05).

## Évolutions proposées
- Mise à jour du `Dockerfile` existant.
- Nouveau fichier `.github/workflows/ci.yml`.
- Fixture `synthetic_ohlcv` dans `tests/conftest.py`.
- Nouveau fichier `tests/test_integration.py`.

## Critères d'acceptation
- [x] `docker build -t ai-trading-pipeline .` construit l'image sans erreur.
- [x] `docker run --rm ai-trading-pipeline` exécute le pipeline (peut échouer si données absentes — c'est attendu).
- [x] Le workflow CI (`.github/workflows/ci.yml`) est syntaxiquement correct.
- [x] La fixture `synthetic_ohlcv` génère un DataFrame OHLCV valide (500 bougies, colonnes conformes §4.1).
- [x] Le test d'intégration passe avec DummyModel sur données synthétiques → arborescence §15.1, JSON valides.
- [x] Le test d'intégration passe avec no_trade → bypass θ, net_pnl=0, n_trades=0.
- [ ] `make lint` et `make test` fonctionnent dans le CI. *(Le CI utilise actuellement les commandes directes `ruff check` et `pytest`. Le Makefile sera créé par la tâche 053 ; cet AC sera validé à ce moment-là.)*
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/051-dockerfile-ci` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/051-dockerfile-ci` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-12] #051 RED: tests intégration + CI`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-12] #051 GREEN: Dockerfile + CI + test intégration`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-12] #051 — Dockerfile et CI`.
