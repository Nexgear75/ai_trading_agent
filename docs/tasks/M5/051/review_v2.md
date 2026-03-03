# Revue PR — [WS-12] #051 — Dockerfile et CI

Branche : `task/051-dockerfile-ci`
Tâche : `docs/tasks/M5/051__ws12_dockerfile_ci.md`
Date : 2026-03-03
Itération : v2 (suite à corrections v1)

## Verdict global : ✅ CLEAN

## Résumé

La branche livre un Dockerfile mis à jour (CMD `run`), un workflow CI GitHub Actions, une fixture `synthetic_ohlcv` (GBM 500 bougies, seed=42) et un test d'intégration E2E couvrant DummyModel, no_trade baseline et 2 scénarios d'erreur. Les 2 items de la review v1 ont été corrigés dans le commit FIX : l'AC `make lint/test` est décochée avec mention de report à la tâche #053, et des tests d'erreur (`TestIntegrationErrors`) ont été ajoutés. Aucun item résiduel.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention `task/NNN-short-slug` | ✅ | `task/051-dockerfile-ci` (`git branch --show-current`) |
| Commit RED présent | ✅ | `7affe9c [WS-12] #051 RED: tests intégration pipeline + fixture synthetic_ohlcv` — 2 fichiers tests uniquement (`tests/conftest.py` +45, `tests/test_integration.py` +399) |
| Commit GREEN présent | ✅ | `9dbee59 [WS-12] #051 GREEN: Dockerfile + CI workflow + test intégration + fixture synthetic_ohlcv` — 3 fichiers (`.github/workflows/ci.yml` +39, `Dockerfile` +1/-1, tâche +19/-19) |
| Commit RED contient uniquement tests | ✅ | `git show --stat 7affe9c` : `tests/conftest.py`, `tests/test_integration.py` |
| Commit GREEN contient implémentation + tâche | ✅ | `git show --stat 9dbee59` : `ci.yml`, `Dockerfile`, tâche |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → 3 commits : RED, GREEN, FIX (corrections review v1 — acceptable post-GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ — 9/10 cochés, 1 explicitement décoché avec justification (AC `make lint/test` → reporté à #053) |
| Checklist cochée | ✅ — 8/9 cochés (PR non encore ouverte = attendu) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1477 passed**, 0 failed (17.88s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

**Phase A : PASS**

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

> `CHANGED_SRC` = vide (aucun fichier `ai_trading/` modifié).
> Scans exécutés sur `tests/conftest.py tests/test_integration.py`.

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep 'or []\|or {}\|or ""\|or 0\b'` | 0 occurrences (grep exécuté) |
| §R1 Except trop large | `grep 'except:'` | 0 occurrences (grep exécuté) |
| §R7 noqa | `grep 'noqa'` | 0 occurrences (grep exécuté) |
| §R7 Print résiduel | `grep 'print('` | 0 occurrences (grep exécuté) |
| §R3 Shift négatif | `grep '.shift(-'` | 0 occurrences (grep exécuté) |
| §R4 Legacy random API | `grep 'np.random.seed\|np.random.randn\|np.random.RandomState\|random.seed'` | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés | `grep '/tmp\|/var/tmp\|C:\\'` | 0 occurrences (grep exécuté) |
| §R7 Imports absolus `__init__` | Aucun `__init__.py` modifié | N/A |
| §R7 Registration manuelle tests | `grep 'register_model\|register_feature'` | 1 match — faux positif (docstring existante dans conftest.py L275, non modifiée par cette branche) |
| §R6 Mutable defaults | `grep 'def.*=[]\|def.*={}'` | 0 occurrences (grep exécuté) |
| §R6 open() sans context | `grep '.read_text\|open('` | Matches dans test_integration.py — tous `Path.read_text()` (acceptable §R6) ; conftest.py L39 `with open(...)` pré-existant ✅ |
| §R6 Booléen par identité | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| §R9 Boucle Python sur array | `grep 'for .* in range'` | Matches dans conftest.py L178-182, L242 — pré-existants, hors diff de cette branche |
| §R6 isfinite | `grep 'isfinite'` | 0 occurrences — N/A (pas de validation numérique dans le diff) |
| §R9 numpy répétés compréhension | `grep 'np\.[a-z]*(.*for'` | 0 occurrences (grep exécuté) |
| §R7 Fixtures dupliquées | `grep 'load_config.*configs/'` | 0 occurrences (grep exécuté) |
| §R7 per-file-ignores | pyproject.toml | Existant, non modifié par cette PR |

### Annotations par fichier (B2)

#### `Dockerfile`

- **Diff** : 1 ligne modifiée — CMD passe de `["python", "-m", "ai_trading", "--config", "configs/default.yaml"]` à `["python", "-m", "ai_trading", "run"]`.
  - Cohérence avec `__main__.py` : la sous-commande `run` existe. ✅
  - Base image `python:3.11-slim` (CPU only) conforme à la tâche. ✅
  - `COPY requirements.txt .` + `pip install` + `COPY . .` présents. ✅
  - RAS après lecture complète du diff (1 ligne modifiée).

#### `.github/workflows/ci.yml`

- **L9-13** Triggers `push` et `pull_request` sur branches `[main, Max6000i1]` : conforme à la tâche. ✅
- **L17** `runs-on: ubuntu-latest` : conforme. ✅
- **L21** `actions/checkout@v4` : version récente. ✅
- **L23-25** `actions/setup-python@v5` avec `python-version: "3.11"` : conforme. ✅
- **L28-32** Install : `pip install -r requirements.txt`, `-r requirements-dev.txt`, `-e .` : couvre toutes les dépendances. ✅
- **L35** Lint : `ruff check ai_trading/ tests/` — commande directe (pas `make lint`). L'AC correspondante est déchochée et reportée à #053. ✅
- **L38** Test : `pytest tests/ -v` — commande directe (pas `make test`). Idem décoché. ✅
- Syntaxe YAML correcte.
- RAS après lecture complète du diff (39 lignes).

#### `tests/conftest.py`

- **L293-337** Fixture `synthetic_ohlcv` :
  - Seed fixée `seed = 42` via `np.random.default_rng(seed)` — conforme §R4. ✅
  - 500 bougies, GBM correct : `S(t+1) = S(t) * exp((μ - σ²/2)dt + σ√dt·Z)`. ✅
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
  - `position_fraction: 1.0` — valeur limite mais valide. ✅
  - Utilise `yaml.dump` → sérialisation propre. ✅
  - Utilise `Path.write_text()` — pas de `open()` nu. ✅
- **L204-258** `TestSyntheticOhlcvFixture` (9 tests) :
  - Couvre row count, colonnes, UTC, contiguïté, prix > 0, volume > 0, high ≥ low, déterminisme, pas de NaN. ✅
- **L265-319** `TestIntegrationDummy` (5 tests) :
  - Pipeline complet DummyModel → arborescence §15.1, manifest/metrics JSON valides, métriques non-null. ✅
  - Imports `run_pipeline`, `validate_manifest`, `validate_metrics` : existants et fonctionnels. ✅
- **L326-399** `TestIntegrationNoTrade` (5 tests) :
  - no_trade → `n_trades=0`, `net_pnl=0`, θ bypass (`method='none'`, `theta=None`). ✅
  - Arborescence §15.1 + JSON schema valide pour baseline. ✅
- **L407-444** `TestIntegrationErrors` (2 tests) — **NOUVEAU (v2)** :
  - `test_missing_parquet_raises` : supprime le fichier parquet puis vérifie `FileNotFoundError` avec match spécifique. ✅
  - `test_invalid_strategy_name_raises` : patche le YAML avec un nom de stratégie invalide → `ValidationError` à `load_config`. ✅
- Tous les tests utilisent `tmp_path` (pas de chemins hardcodés). ✅
- Docstrings avec `#051`. ✅
- RAS après lecture complète (444 lignes).

#### `docs/tasks/M5/051__ws12_dockerfile_ci.md`

- Statut `DONE`. ✅
- 9/10 AC cochés, 1 explicitement décoché avec justification claire (report à #053). ✅
- Checklist : 8/9 cochés (PR non ouverte = attendu). ✅

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères AC | ✅ | AC1 (docker build) → non testable en pytest, AC3 (CI syntax) → vérifié par lecture, AC4 (fixture) → `TestSyntheticOhlcvFixture` (9 tests), AC5 (DummyModel E2E) → `TestIntegrationDummy` (5 tests), AC6 (no_trade bypass) → `TestIntegrationNoTrade` (5 tests), AC7 (make) → décoché/reporté, AC8 (erreurs) → `TestIntegrationErrors` (2 tests) |
| Cas nominaux | ✅ | DummyModel + no_trade pipeline E2E |
| Cas erreurs | ✅ | `test_missing_parquet_raises`, `test_invalid_strategy_name_raises` |
| Cas bords | ✅ | Fixture: prix positifs, NaN, high ≥ low, déterminisme |
| Déterministes | ✅ | seed=42 dans fixture, `test_deterministic` vérifie reproductibilité |
| Portabilité chemins | ✅ | Scan B1: 0 `/tmp`, tous `tmp_path` |
| Tests registre réalistes | N/A | Pas de test de registre dans cette PR |
| Contrat ABC complet | N/A | Pas d'ABC dans cette PR |
| Données synthétiques | ✅ | Fixture GBM, aucune dépendance réseau |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1: 0 fallback, 0 except large |
| §R10 Defensive indexing | ✅ | Pas d'indexing complexe dans le diff |
| §R2 Config-driven | ✅ | Config YAML complète dans le helper, pas de hardcoding hors fixtures |
| §R3 Anti-fuite | N/A | Pas de code pipeline modifié |
| §R4 Reproductibilité | ✅ | Scan B1: 0 legacy random, seed=42 via `default_rng` |
| §R5 Float conventions | N/A | Pas de code numérique modifié |
| §R6 Anti-patterns Python | ✅ | Scan B1: 0 mutable default, `Path.read_text()` OK, 0 identité booléenne |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case partout, noms descriptifs |
| Pas de code mort/debug | ✅ | Scan B1: 0 print, 0 TODO |
| Imports propres / relatifs | ✅ | Pas d'`__init__.py` modifié, imports standard |
| DRY | ✅ | Helper `_make_integration_config` factorisé entre les 4 classes de test |

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

## Suivi des items review v1

| # | Sévérité | Description | Résolution v2 |
|---|---|---|---|
| 1 | WARNING | AC `make lint/test` coché sans Makefile | ✅ AC décochée avec note de report à #053 (commit `06472fc`) |
| 2 | MINEUR | Pas de tests d'erreur dans `test_integration.py` | ✅ `TestIntegrationErrors` ajouté avec 2 tests (commit `06472fc`) |

---

## Remarques

Aucune remarque.

---

## Actions requises

Aucune.
