# Tâche — Ingestion OHLCV Binance

Statut : DONE
Ordre : 004
Workstream : WS-2
Milestone : M1
Gate lié : M1

## Contexte
Le pipeline doit disposer de données OHLCV brutes téléchargées depuis Binance. L'ingestion est une étape préalable et séparée (§17.4) du pipeline de modélisation : les données sont téléchargées une seule fois puis réutilisées offline pour tous les runs.

Références :
- Plan : `docs/plan/implementation.md` (WS-2.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§4.1, §17.4)
- Code : `ai_trading/data/ingestion.py` (à créer)
- Config : `configs/default.yaml` (sections `dataset`)

Dépendances :
- Tâche 002 — Config loader Pydantic v2 (doit être DONE)

## Objectif
Implémenter un module `ai_trading/data/ingestion.py` qui télécharge les données OHLCV via l'API Binance (ccxt) pour le symbole, timeframe et période configurés, et les stocke en Parquet.

## Règles attendues
- Config-driven : symbole, timeframe, période et répertoire sont lus depuis `config.dataset`.
- Strict code : erreur explicite si l'exchange n'est pas supporté, si le symbole n'existe pas, ou si la connexion échoue après les retries.
- Convention de bornes : `dataset.start` inclus, `dataset.end` exclusif (`[start, end[`).
- Anti-fuite : les timestamps sont en UTC, triés par ordre croissant.
- Reproductibilité : le SHA-256 du fichier Parquet est calculé pour traçabilité.

## Évolutions proposées
- Créer `ai_trading/data/ingestion.py` avec une fonction `fetch_ohlcv(config: PipelineConfig) -> Path`.
- Création automatique du répertoire : `os.makedirs(config.dataset.raw_dir, exist_ok=True)`.
- Pagination : boucle sur `fetch_ohlcv()` avec paramètre `since` incrémenté (~1000 bougies par appel).
- Retry : backoff exponentiel en cas d'erreur réseau ou rate-limit 429 (max 3 retries).
- Cache locale / mode idempotent : si le fichier Parquet existe déjà et couvre la période, ne pas re-télécharger ; sinon, téléchargement incrémental des bougies manquantes.
- Colonnes canoniques : `timestamp_utc, open, high, low, close, volume, symbol`.
- Tri croissant par `timestamp_utc`.
- Calcul et retour du SHA-256 du fichier Parquet.
- Nom du fichier Parquet : `{symbol}_{timeframe}_{start}_{end}.parquet` dans `config.dataset.raw_dir`.

## Critères d'acceptation
- [x] Fichier Parquet généré avec les colonnes canoniques (`timestamp_utc, open, high, low, close, volume, symbol`)
- [x] Colonnes typées correctement : `timestamp_utc` en datetime64[ns, UTC], prix et volume en float64
- [x] Tri croissant par `timestamp_utc` vérifié par test
- [x] SHA-256 stable sur relance (mode idempotent)
- [x] Pagination correcte : toute la période demandée est couverte
- [x] Retry avec backoff exponentiel fonctionnel (testé via mock)
- [x] Cache locale : pas de re-téléchargement si le fichier couvre déjà la période
- [x] Erreur explicite si le symbole ou l'exchange n'existe pas
- [x] Convention de bornes `[start, end[` respectée
- [x] Tests unitaires avec mocks ccxt (pas d'accès réseau dans les tests)
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/004-ingestion-ohlcv` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/004-ingestion-ohlcv` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-2] #004 RED: tests ingestion OHLCV Binance`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-2] #004 GREEN: ingestion OHLCV Binance`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-2] #004 — Ingestion OHLCV Binance`.
