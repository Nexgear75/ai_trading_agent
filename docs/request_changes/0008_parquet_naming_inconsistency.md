# Request Changes — Incohérence de nommage des fichiers Parquet (fetch → qa → run)

Statut : DONE
Ordre : 0008

**Date** : 2026-03-03
**Périmètre** : Convention de nommage des fichiers Parquet bruts entre `ingestion.py`, `runner.py` et `__main__.py`.
**Détecté par** : Test e2e réseau `tests/test_e2e_network.py` (premier test exerçant la chaîne réelle `fetch → qa → run`).
**Verdict** : ✅ CLEAN (après corrections)

---

## Contexte

Le test e2e `test_e2e_network.py` est le premier à exercer le chemin complet `make run-all` (`fetch-data → qa → run`) avec téléchargement réel depuis Binance. Tous les tests d'intégration existants contournaient le problème en écrivant eux-mêmes le fichier Parquet sous le nom attendu par le runner.

---

## Remarques

### ~~1. [BLOQUANT] Convention de nommage Parquet incohérente entre modules~~ ✅ RÉSOLU

> **Résolu** : commit `877c754` — `[RC-0008] FIX B-1: Align Parquet naming to §17.4 ({symbol}_{tf}.parquet)` (Option A retenue)

**Description** : L'ingestion écrit le fichier sous `{symbol}_{tf}_{start}_{end}.parquet` mais le runner et le CLI QA cherchent `{symbol}_{tf}.parquet`. Le pipeline `make run-all` est donc **cassé** : le fichier téléchargé par `fetch` n'est jamais trouvé par `qa` ni `run`.

| Module | Fichier | Ligne | Convention utilisée |
|---|---|---|---|
| `ingestion.py` (`_parquet_path`) | `ai_trading/data/ingestion.py` | L245 | `BTCUSDT_1h_2024-01-01_2026-01-01.parquet` |
| `runner.py` (`_load_raw_ohlcv`) | `ai_trading/pipeline/runner.py` | L93 | `BTCUSDT_1h.parquet` |
| `__main__.py` (`_run_qa_command`) | `ai_trading/__main__.py` | L125 | `BTCUSDT_1h.parquet` |

**Contradiction dans la spec** :
- **§17.4** (texte normatif) : *« un fichier par symbole (ex: `BTCUSDT_1h.parquet`) »* → convention **sans dates**.
- **§15 manifest.json** (exemple illustratif) : *`"path": "data/raw/BTCUSDT_1h_2024-01-01_2026-01-01.parquet"`* → convention **avec dates**.

**Impact** : `make run-all` échoue systématiquement avec `FileNotFoundError`.

**Suggestion** : Unifier la convention de nommage. Deux options :

- **Option A** (alignement sur §17.4, changement minimal) : modifier `_parquet_path()` dans `ingestion.py` pour écrire `{symbol}_{tf}.parquet`. Le manifest enregistrera le chemin réel quel qu'il soit.
- **Option B** (alignement sur §15 manifest) : modifier `_load_raw_ohlcv()` dans `runner.py` et `_run_qa_command()` dans `__main__.py` pour utiliser la convention `{symbol}_{tf}_{start}_{end}.parquet`. Implique d'extraire la fonction `_parquet_path()` dans un module partagé.

**Recommandation** : Option A (§17.4 est le texte normatif, §15 est un exemple).

---

### ~~2. [WARNING] Tests d’intégration masquent le bug en écrivant le Parquet manuellement~~ ✅ RÉSOLU

> **Résolu** : la correction B-1 aligne ingestion sur la convention `{symbol}_{tf}.parquet` utilisée par les tests. Plus de divergence.

**Description** : Les tests `test_runner.py`, `test_integration.py` et `conftest.py` écrivent tous le fichier Parquet sous `{symbol}_1h.parquet` — exactement le nom attendu par le runner — sans passer par la fonction d'ingestion. Cela masque l'incohérence de nommage.

| Fichier | Ligne | Code |
|---|---|---|
| `tests/conftest.py` | L350 | `path = raw_dir / f"{symbol}_1h.parquet"` |
| `tests/test_runner.py` | L64 | `path = raw_dir / f"{symbol}_1h.parquet"` |
| `tests/test_runner.py` | L702 | `pq_path = raw_dir_2 / "BTCUSDT_1h.parquet"` |
| `tests/test_cli.py` | L343 | `parquet_path = raw_dir / "BTCUSDT_1h.parquet"` |

**Suggestion** : Après correction du bug #1, vérifier que tous ces helpers utilisent la même source de vérité pour le nommage (idéalement une fonction partagée importée depuis le module d'ingestion ou un module `paths`).

---

### ~~3. [MINEUR] Absence de test e2e réseau avant ce rapport~~ ✅ RÉSOLU

> **Résolu** : `tests/test_e2e_network.py` présent, marqué `@pytest.mark.network`.

**Description** : Aucun test ne validait le chemin réel `fetch → qa → run` avec accès réseau. Le marker `@pytest.mark.network` existait dans `pyproject.toml` mais aucun test ne l'utilisait.

**Suggestion** : Le fichier `tests/test_e2e_network.py` a été créé pour combler cette lacune. Il est marqué `@pytest.mark.network` et exclu du `pytest` par défaut. Lancer avec : `pytest -m network tests/test_e2e_network.py -v`.

---

## Résumé

| # | Sévérité | Description | Fichier(s) principal(aux) |
|---|---|---|---|
| 1 | **BLOQUANT** | Convention de nommage Parquet incohérente → `make run-all` cassé | `ingestion.py`, `runner.py`, `__main__.py` |
| 2 | **WARNING** | Tests d'intégration masquent le bug | `conftest.py`, `test_runner.py`, `test_cli.py` |
| 3 | **MINEUR** | Pas de test e2e réseau existant | `tests/` |
