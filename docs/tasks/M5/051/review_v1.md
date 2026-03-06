# Revue PR — [WS-12] #051 — Dockerfile et CI

Branche : `task/051-dockerfile-ci`
Tâche : `docs/tasks/M5/051__ws12_dockerfile_ci.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

La branche livre un Dockerfile mis à jour, un workflow CI GitHub Actions, une fixture `synthetic_ohlcv` (GBM 500 bougies) et un test d'intégration E2E couvrant DummyModel + no_trade baseline. La structure TDD (RED → GREEN) est respectée. Cependant, le critère d'acceptation « `make lint` et `make test` fonctionnent dans le CI » est coché `[x]` alors qu'aucun Makefile n'existe — le CI exécute les commandes directement. Un item WARNING est donc relevé.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention `task/NNN-short-slug` | ✅ | `task/051-dockerfile-ci` |
| Commit RED présent | ✅ | `7affe9c [WS-12] #051 RED: tests intégration pipeline + fixture synthetic_ohlcv` — 2 fichiers tests uniquement (`tests/conftest.py`, `tests/test_integration.py`) |
| Commit GREEN présent | ✅ | `9dbee59 [WS-12] #051 GREEN: Dockerfile + CI workflow + test intégration + fixture synthetic_ohlcv` — 3 fichiers (`.github/workflows/ci.yml`, `Dockerfile`, tâche) |
| Commit RED contient uniquement tests | ✅ | `git show --stat 7affe9c` : `tests/conftest.py` (+45), `tests/test_integration.py` (+399) |
| Commit GREEN contient implémentation + tâche | ✅ | `git show --stat 9dbee59` : `ci.yml` (+39), `Dockerfile` (+1/-1), tâche (+19/-19) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` : 2 commits exactement |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ⚠️ 10/10 cochés mais voir WARNING #1 ci-dessous |
| Checklist cochée | ✅ 8/9 cochés (PR non encore ouverte = attendu) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1475 passed**, 0 failed (17.70s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

**Phase A : PASS** — on continue en Phase B.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

> `CHANGED_SRC` = vide (aucun fichier `ai_trading/` modifié).
> Scans exécutés sur `tests/conftest.py tests/test_integration.py`.

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep 'or []\|or {}...'` | 0 occurrences |
| §R1 Except trop large | `grep 'except:$\|except Exception:'` | 0 occurrences |
| §R7 noqa | `grep 'noqa'` | 0 occurrences |
| §R7 Print résiduel | `grep 'print('` | 0 occurrences |
| §R3 Shift négatif | `grep '.shift(-'` | 0 occurrences |
| §R4 Legacy random API | `grep 'np.random.seed\|...'` | 0 occurrences |
| §R7 TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences |
| §R7 Chemins hardcodés | `grep '/tmp\|C:\\'` | 0 occurrences |
| §R7 Imports absolus `__init__` | Aucun `__init__.py` modifié | N/A |
| §R7 Registration manuelle tests | `grep 'register_model\|register_feature'` | 1 match — faux positif (docstring existante dans conftest.py L275, non modifiée par cette branche) |
| §R6 Mutable defaults | `grep 'def.*=[]\|def.*={}'` | 0 occurrences |
| §R6 open() sans context | `grep 'open('` | 1 match — `conftest.py:39` avec `with open(...)` ✅ (context manager, existant) |
| §R6 Booléen par identité | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences |
| §R9 Boucle Python sur array | `grep 'for .* in range(.*):' ` | 0 occurrences |
| §R6 isfinite | `grep 'isfinite'` | 0 occurrences (pas de validation numérique dans ce diff — N/A) |
| §R9 numpy répétés compréhension | `grep 'np\.[a-z]*(.*for'` | 0 occurrences |
| §R7 Fixtures dupliquées | `grep 'load_config.*configs/'` | 0 occurrences |
| §R7 per-file-ignores | pyproject.toml L51 | Existant, non modifié par cette PR |

### Annotations par fichier (B2)

#### `Dockerfile`

- **Diff** : 1 ligne modifiée — CMD passe de `["python", "-m", "ai_trading", "--config", "configs/default.yaml"]` à `["python", "-m", "ai_trading", "run"]`.
  - Cohérence avec `__main__.py` vérifié : le sous-commande `run` existe et est le défaut. ✅
  - Base image `python:3.11-slim` (CPU only) conforme à la tâche. ✅
  - `COPY requirements.txt .` + `pip install` + `COPY . .` présents. ✅
  - RAS après lecture complète du diff (1 ligne modifiée).

#### `.github/workflows/ci.yml`

- **L9-13** Triggers `push` et `pull_request` sur branches `[main, Max6000i1]` : conforme à la tâche. ✅
- **L17** `runs-on: ubuntu-latest` : conforme. ✅
- **L21** `actions/checkout@v4` : version récente. ✅
- **L23-25** `actions/setup-python@v5` avec `python-version: "3.11"` : conforme. ✅
- **L28-32** Install : `pip install -r requirements.txt`, `-r requirements-dev.txt`, `-e .` : couvre toutes les dépendances. ✅
- **L35** Lint : `ruff check ai_trading/ tests/` — commande directe, **pas `make lint`**. ⚠️ Voir WARNING #1.
- **L38** Test : `pytest tests/ -v` — commande directe, **pas `make test`**. ⚠️ Voir WARNING #1.
- Syntaxe YAML correcte (pas d'erreur d'indentation, aucun champ manquant).
  - RAS après lecture complète du diff (39 lignes).

#### `tests/conftest.py`

- **L293-337** Fixture `synthetic_ohlcv` :
  - Seed fixée `seed = 42` via `np.random.default_rng(seed)` — conforme §R4. ✅
  - 500 bougies, GBM correct : `S(t+1) = S(t) * exp((mu - σ²/2)dt + σ√dt·Z)`. ✅
  - Colonnes conformes §4.1 : `timestamp_utc`, `open`, `high`, `low`, `close`, `volume`. ✅
  - Timestamps UTC-aware (`tz="UTC"`). ✅
  - `high = max(open, close) * (1 + U[0.0005, 0.005])` → toujours ≥ open et close. ✅
  - `low = min(open, close) * (1 - U[0.0005, 0.005])` → toujours ≤ open et close. ✅
  - `volume = rng.uniform(100.0, 10000.0, n)` → strictement positif. ✅
  - Pas de dépendance réseau. ✅
  - RAS après lecture complète du diff (45 lignes ajoutées).

#### `tests/test_integration.py`

- **L24-30** Helper `_write_parquet` : crée le répertoire `raw_dir` avec `mkdir(parents=True, exist_ok=True)`. ✅
- **L33-196** Helper `_make_integration_config` :
  - Crée `output_dir` avec `mkdir(parents=True, exist_ok=True)`. ✅
  - Config YAML complète avec toutes les clés attendues par le modèle Pydantic. ✅
  - `position_fraction: 1.0` — valeur limite mais valide (fraction du capital investie). ✅
  - Utilise `yaml.dump` → sérialisation propre. ✅
  - Utilise `Path.write_text()` — pas de `open()` nu. ✅
- **L204-258** `TestSyntheticOhlcvFixture` (9 tests) :
  - Couvre row count, colonnes, UTC, contiguïté, prix > 0, volume > 0, high ≥ low, déterminisme, pas de NaN. ✅
- **L265-319** `TestIntegrationDummy` (5 tests) :
  - Pipeline complet DummyModel → arborescence §15.1, manifest/metrics JSON valides, métriques non-null. ✅
  - Import `from ai_trading.pipeline.runner import run_pipeline` vérifié : existe dans `__main__.py`. ✅
  - Import `from ai_trading.artifacts.validation import validate_manifest, validate_metrics` : existence vérifiée. ✅
- **L326-399** `TestIntegrationNoTrade` (5 tests) :
  - no_trade → `n_trades=0`, `net_pnl=0`, θ bypass (`method='none'`, `theta=None`). ✅
  - Arborescence §15.1 + JSON schema valide pour baseline. ✅
  - Chaque test utilise `tmp_path` (pas de chemins hardcodés). ✅
  - Docstrings avec `#051`. ✅
  - RAS après lecture complète du diff (399 lignes ajoutées).

#### `docs/tasks/M5/051__ws12_dockerfile_ci.md`

- Statut passé de `TODO` à `DONE`. ✅
- Tous les `[ ]` → `[x]` pour les AC et la checklist. ✅
- Seul item non coché : « Pull Request ouverte vers Max6000i1 » — attendu à ce stade.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères AC | ✅ | AC1 (docker build) → non testable en pytest, AC3 (CI syntax) → vérifié par lecture, AC4 (fixture 500 candles) → `TestSyntheticOhlcvFixture`, AC5 (DummyModel arbo+JSON) → `TestIntegrationDummy`, AC6 (no_trade bypass) → `TestIntegrationNoTrade` |
| Cas nominaux | ✅ | DummyModel + no_trade pipeline E2E |
| Cas erreurs + bords | ⚠️ | Fixture validation couvre des bords (positive, NaN, high≥low, déterminisme). Pas de tests d'erreur (config invalide, données manquantes, etc.) — voir MINEUR #1 |
| Déterministes | ✅ | seed=42 dans fixture, `test_deterministic` vérifie reproductibilité |
| Portabilité chemins | ✅ | Scan B1: 0 `/tmp`, tous les tests utilisent `tmp_path` |
| Tests registre réalistes | N/A | Pas de test de registre dans cette PR |
| Contrat ABC complet | N/A | Pas d'ABC dans cette PR |
| Données synthétiques | ✅ | Fixture GBM, aucune dépendance réseau |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1: 0 fallback, 0 except large |
| §R10 Defensive indexing | ✅ | Pas d'indexing complexe dans le diff |
| §R2 Config-driven | ✅ | Config YAML complète dans le helper, pas de hardcoding hors test fixtures |
| §R3 Anti-fuite | N/A | Pas de code pipeline modifié |
| §R4 Reproductibilité | ✅ | Scan B1: 0 legacy random, seed=42 via `default_rng` |
| §R5 Float conventions | N/A | Pas de code numérique modifié |
| §R6 Anti-patterns Python | ✅ | Scan B1: 0 mutable default, open avec context manager, 0 identité booléenne |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case partout, noms descriptifs |
| Pas de code mort/debug | ✅ | Scan B1: 0 print, 0 TODO |
| Imports propres / relatifs | ✅ | Scan B1: pas d'`__init__.py` modifié, imports standard |
| DRY | ✅ | Helper `_make_integration_config` factorisé entre les classes de test |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | ✅ | GBM correctement implémenté : `exp((μ - σ²/2)dt + σ√dt·Z)` |
| Nommage métier cohérent | ✅ | `ohlcv`, `close`, `high`, `low`, `volume` — standard |
| Séparation des responsabilités | ✅ | Fixture séparée dans conftest, tests d'intégration dédiés |
| Invariants de domaine | ✅ | Prix > 0, volume > 0, high ≥ low vérifiés |
| Cohérence des unités | ✅ | Timestamps UTC, prices en quote currency |
| Patterns calcul financier | ✅ | `np.log`, `np.exp`, `np.cumsum` — vectorisé |

### Conformité spec v1.0 (B6)

| Critère | Verdict |
|---|---|
| Spécification (§16 Dockerfile, §17.6 CI) | ✅ — Dockerfile CPU only `python:3.11-slim`, CMD appelle le pipeline |
| Plan d'implémentation (WS-12.4) | ✅ — Tous les livrables attendus présents |
| Formules doc vs code | ✅ — GBM conforme, pas de formule divergente |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `run_pipeline(config) → Path` conforme à l'usage dans `__main__.py` |
| Noms de colonnes DataFrame | ✅ | `timestamp_utc, open, high, low, close, volume` — conforme §4.1 |
| Clés de configuration | ✅ | Config YAML intégration contient toutes les sections attendues par `PipelineConfig` |
| Registres et conventions | N/A | Pas de registre impliqué |
| Structures de données partagées | ✅ | `validate_manifest`/`validate_metrics` appelés correctement |
| Conventions numériques | ✅ | float64 par défaut en fixture (numpy) |
| Imports croisés | ✅ | `ai_trading.config.load_config`, `ai_trading.pipeline.runner.run_pipeline`, `ai_trading.artifacts.validation` — tous vérifiés existants |

---

## Remarques

1. **[WARNING]** AC ghost completion : `make lint` et `make test` n'existent pas
   - Fichier : `docs/tasks/M5/051__ws12_dockerfile_ci.md`
   - Ligne(s) : AC #7 (`[x] make lint et make test fonctionnent dans le CI`)
   - Description : Le critère d'acceptation est coché `[x]` mais **aucun `Makefile` n'existe** dans le repository. Le workflow CI (`.github/workflows/ci.yml`) exécute `ruff check ai_trading/ tests/` et `pytest tests/ -v` directement, ce qui atteint le même objectif fonctionnel mais ne satisfait pas littéralement l'AC.
   - Suggestion : **Option A** (recommandé) — Créer un `Makefile` avec les targets `lint` et `test`, puis modifier le CI pour appeler `make lint` et `make test`. **Option B** — Modifier l'AC pour refléter la réalité : « `ruff check` et `pytest` fonctionnent dans le CI ».

2. **[MINEUR]** Pas de tests d'erreur dans `test_integration.py`
   - Fichier : `tests/test_integration.py`
   - Description : L'AC #8 « Tests couvrent les scénarios nominaux + erreurs + bords » est coché mais les tests d'intégration ne couvrent que des scénarios nominaux (DummyModel OK, no_trade OK) et des validations de fixture (bords). Aucun test d'erreur (ex : config invalide, données manquantes, symbole inexistant) n'est présent. Pour des tests d'intégration, c'est acceptable car les erreurs sont couvertes par les tests unitaires, mais l'AC est techniquement incomplète.
   - Suggestion : Ajouter 1-2 tests d'erreur (ex : `test_missing_parquet_raises`, `test_invalid_strategy_raises`) ou reformuler l'AC.

## Résumé

La branche est de bonne qualité : TDD proprement exécuté (RED → GREEN), fixture GBM correcte et déterministe, tests d'intégration E2E couvrant DummyModel et no_trade avec validation d'arborescence §15.1 et JSON schema. Le CI workflow est syntaxiquement correct et couvre lint + test. Le seul point notable est le WARNING sur l'AC « `make lint`/`make test` » qui est coché alors qu'aucun Makefile n'existe — c'est une ghost completion partielle qui nécessite soit la création d'un Makefile, soit la correction de l'AC.
