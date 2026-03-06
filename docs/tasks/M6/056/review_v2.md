# Revue PR — [WS-13] #056 — Test full-scale make run-all BTCUSDT (v2)

Branche : `task/056-test-fullscale-run`
Tâche : `docs/tasks/M6/056__ws13_test_fullscale_run.md`
Date : 2026-03-03
Itération : v2 (suite à correction des 4 items mineurs de la v1)

## Verdict global : ✅ CLEAN

## Résumé

Suite à la v1 (REQUEST CHANGES, 4 mineurs), les 3 items actionnables ont été corrigés dans le commit FIX `54c8c9e` : variable morte `FULLSCALE_CONFIG` désormais utilisée, filtre `is_dir()` ajouté dans `test_at_least_one_fold`, et test equity curve aligné sur le nom réel du runner (`equity_curve.csv`). L'item M-2 (pyproject.toml dans le commit RED) est un commit passé non modifiable, reconnu et accepté. Le code est propre, conforme aux conventions, et la politique M6 (aucune fixture/mock/données synthétiques) est strictement respectée.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/056-*` | ✅ | `git branch --show-current` → `task/056-test-fullscale-run` |
| Commit RED présent | ✅ | `2113961 [WS-13] #056 RED: test fullscale make run-all BTCUSDT` |
| Commit GREEN présent | ✅ | `98be8df [WS-13] #056 GREEN: test fullscale make run-all BTCUSDT` |
| RED contient uniquement des tests | ⚠️ | `git show --stat 2113961` : `pyproject.toml` + `tests/test_fullscale_btc.py`. Voir observation historique ci-dessous. |
| GREEN contient tâche | ✅ | `git show --stat 98be8df` : `docs/tasks/M6/056__ws13_test_fullscale_run.md` uniquement |
| Pas de commits parasites RED↔GREEN | ✅ | 0 commit entre RED et GREEN |
| Commit FIX post-review | ✅ | `54c8c9e [WS-13] #056 FIX: remove dead var, add is_dir filter, fix equity_curve filename` — corrections v1, tests verts |

**Observation historique (non comptée)** : `pyproject.toml` est inclus dans le commit RED (2113961). Cette modification (enregistrement du marker `fullscale` et exclusion via `addopts`) est nécessaire pour que les tests RED soient fonctionnels (marker non enregistré → warning pytest). Commit passé non modifiable — accepté comme contexte historique.

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (10/11 — 1 non cochable = exécution réseau manuelle, annoté `[ ]` explicitement) |
| Checklist cochée | ✅ (8/9 — 1 non cochable = PR pas encore ouverte, normal) |

**Vérification croisée critères cochés ↔ code :**

| Critère coché | Preuve dans le code |
|---|---|
| `[x]` Marker `fullscale` enregistré | `pyproject.toml` L68-70 : `markers = ["fullscale: ..."]` |
| `[x]` `addopts` exclut fullscale | `pyproject.toml` L67 : `-m "not fullscale"` |
| `[x]` `test_fullscale_btc.py` existe | Fichier 194 lignes, `@pytest.mark.fullscale` L58 |
| `[x]` pytest standard exclut fullscale | `pytest --co` : `test_fullscale_btc.py` NON collecté (confirmé) |
| `[ ]` pytest -m fullscale GREEN | Correctement laissé non coché — réseau requis |
| `[x]` Artefacts attendus | Tests L97-162 : manifest.json, metrics.json, equity_curve.csv, config_snapshot.yaml |
| `[x]` ≥ 1 fold | Test L133, `fold_dirs = sorted(d for d in folds_dir.iterdir() if d.is_dir())` |
| `[x]` ≥ 70k lignes Parquet | Test L85, `MIN_PARQUET_ROWS = 70_000` L32 |
| `[x]` Scenarios nominaux + erreurs + bords | 11 tests couvrant tous les artefacts — cas erreurs non testables sans mocks (M6 policy) |
| `[x]` Suite standard verte | 1621 passed, 11 deselected, 0 failed |
| `[x]` ruff clean | `ruff check ai_trading/ tests/` → All checks passed |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1621 passed**, 11 deselected, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

✅ Phase A : PASS — on continue en Phase B.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

Fichiers scannés : `tests/test_fullscale_btc.py` (seul fichier `.py` modifié — aucun fichier source `ai_trading/` modifié).

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, etc.) | §R1 | 0 occurrences (grep exécuté) |
| Except trop large | §R1 | 0 occurrences (grep exécuté) |
| `noqa` | §R7 | 0 occurrences (grep exécuté) |
| `per-file-ignores` (pyproject.toml) | §R7 | L51 existant — aucune entrée ajoutée par cette PR |
| Print résiduel | §R7 | 0 occurrences (grep exécuté) |
| `.shift(-` (look-ahead) | §R3 | 0 occurrences (grep exécuté) |
| Legacy random API | §R4 | 0 occurrences (grep exécuté) |
| TODO/FIXME/HACK/XXX | §R7 | 0 occurrences (grep exécuté) |
| Chemins hardcodés `/tmp`, `C:\` | §R7 | 0 occurrences (grep exécuté) |
| Imports absolus `__init__` | §R7 | N/A — aucun `__init__.py` modifié |
| Registration manuelle tests | §R7 | 0 occurrences (grep exécuté) |
| Mutable default arguments | §R6 | 0 occurrences (grep exécuté) |
| `open()` sans context manager | §R6 | 1 match L51 — `with open(path, encoding="utf-8") as f:` ✅ |
| Comparaison booléenne identité | §R6 | 0 occurrences (grep exécuté) |
| Boucle `for range()` | §R9 | 0 occurrences (grep exécuté) |
| `isfinite` | §R6 | 0 occurrences — N/A, pas de validation numérique |
| Numpy compréhension | §R9 | 0 occurrences (grep exécuté) |
| Fixtures dupliquées | §R7 | 0 occurrences (grep exécuté) |
| **M6** tmp_path/mock/monkeypatch | M6 | 1 match L8 — docstring uniquement (faux positif) ✅ |
| **M6** `@pytest.fixture` | M6 | 0 occurrences ✅ |

### B2. Annotations par fichier

#### `tests/test_fullscale_btc.py` (194 lignes — diff complet lu)

- **L16-22** Imports : `json`, `subprocess`, `Path`, `jsonschema`, `pandas`, `pytest`. Ordre stdlib → third-party correct. Aucun import inutilisé.
  Sévérité : RAS

- **L24-32** Constantes module-level : `PROJECT_ROOT`, `FULLSCALE_CONFIG`, `PARQUET_PATH`, `RUNS_DIR`, `MANIFEST_SCHEMA_PATH`, `METRICS_SCHEMA_PATH`, `MIN_PARQUET_ROWS`. Toutes utilisées dans le code.
  Sévérité : RAS — **v1 item M-1 FIXÉ** : `FULLSCALE_CONFIG` maintenant utilisé L71 via `config_rel`.

- **L35-46** `_find_latest_run_dir(pattern="*_dummy")` : glob sur `RUNS_DIR`, tri lexicographique (correct pour le format `YYYYMMDD_HHMMSS`), erreur explicite `FileNotFoundError` si vide. Pattern `*_dummy` cohérent avec `fullscale_btc.yaml` L97 (`name: dummy`).
  Sévérité : RAS

- **L49-55** `_load_json(path)` : `with open(...)` (context manager ✅), validation `isinstance(data, dict)` après désérialisation (§R6 ✅), `raise TypeError` explicite.
  Sévérité : RAS

- **L68-82** `test_make_run_all_succeeds` : `subprocess.run` avec liste d'arguments (pas d'injection shell ✅), `timeout=600` conforme à la tâche, `cwd=str(PROJECT_ROOT)` correct. `FULLSCALE_CONFIG` utilisé via `config_rel = FULLSCALE_CONFIG.relative_to(PROJECT_ROOT)`.
  Sévérité : RAS — **v1 item M-1 FIXÉ**.

- **L85-90** `test_parquet_has_enough_rows` : vérifie `PARQUET_PATH.is_file()` puis `len(df) >= 70_000`. Correct.
  Sévérité : RAS

- **L97-107** `test_run_dir_has_manifest_json` / `test_run_dir_has_metrics_json` : vérifient la présence de `manifest.json` et `metrics.json` dans le run dir. Noms conformes au runner (`runner.py` L619-620).
  Sévérité : RAS

- **L113-123** `test_manifest_json_valid_schema` / `test_metrics_json_valid_schema` : chargent JSON + schéma, `jsonschema.validate()`. Correct.
  Sévérité : RAS

- **L133-140** `test_at_least_one_fold` : `folds_dir.iterdir()` avec filtre `if d.is_dir()`.
  Sévérité : RAS — **v1 item M-3 FIXÉ** : filtre `is_dir()` ajouté.

- **L147-150** `test_equity_curve_exists` : teste strictement `equity_curve.csv` (conforme au runner L571 : `stitched.to_csv(run_dir / "equity_curve.csv")`). AC également mis à jour.
  Sévérité : RAS — **v1 item M-4 FIXÉ**.

- **L157-162** `test_config_snapshot_exists` : vérifie `config_snapshot.yaml`. Correct.
  Sévérité : RAS

- **L168-182** `test_each_fold_has_metrics` : vérifie `metrics_fold.json` ou `metrics.json` par fold. Le runner écrit `metrics_fold.json` (L260 `metrics_builder.py`). La double vérification est documentée dans la docstring L169. Design de test robuste.
  Sévérité : RAS

- **L184-194** `test_each_fold_has_trades_csv` : vérifie `trades.csv` par fold. Conforme au runner (L446 `runner.py`). Filtre `is_dir()` appliqué.
  Sévérité : RAS

#### `pyproject.toml` (diff 6 lignes)

- **L67** `addopts = "-v --tb=short -m \"not fullscale\""` : correctement échappé, exclut fullscale par défaut. Vérifié par `pytest --co` : `test_fullscale_btc.py` non collecté.
  Sévérité : RAS

- **L68-70** `markers = ["fullscale: ..."]` : marker enregistré. Conforme.
  Sévérité : RAS

#### `docs/tasks/M6/056__ws13_test_fullscale_run.md`

- Passage `TODO` → `DONE`, `[ ]` → `[x]` cohérent avec le code produit. `equity_curve_stitched.csv` → `equity_curve.csv` dans l'AC et la description (aligné sur le runner). 1 critère réseau `[ ]` avec annotation. 1 item PR `[ ]`.
  Sévérité : RAS

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_fullscale_btc.py`, docstring `Task #056` L3 |
| Couverture des critères | ✅ | 11 tests × 9 points AC (mapping B2 ci-dessus) |
| Cas nominaux | ✅ | 11 tests validant tous les artefacts |
| Cas erreurs/bords | N/A | Test fullscale M6 — pas de mocks autorisés, cas erreurs non testables |
| Déterministes | ✅ | Assertions sur fichiers, pas d'aléatoire |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé. `Path(__file__).resolve().parent.parent` |
| Tests registre réalistes | N/A | Pas de registre impliqué |
| Contrat ABC complet | N/A | Pas d'ABC impliqué |
| M6 Policy | ✅ | Scan B1 : 0 fixture, 0 mock, 0 tmp_path, 0 conftest data |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. Helpers lèvent `FileNotFoundError`/`TypeError`. |
| §R10 Defensive indexing | ✅ | Pas d'indexation array dangereuse. `result.stdout[-2000:]` safe en Python (retourne chaîne complète si < 2000 chars). |
| §R2 Config-driven | ✅ | Constantes en tête de fichier. `MIN_PARQUET_ROWS = 70_000` conforme à l'AC. Pas de valeur magique inline. |
| §R3 Anti-fuite | N/A | Pas de manipulation de données temporelles. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Tests déterministes. |
| §R5 Float conventions | N/A | Pas de manipulation de tenseurs ou métriques. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, `open()` avec `with`, 0 `is True/False`, 0 dict collision. Validation type après `json.load()` (L53). |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case, noms descriptifs (`_find_latest_run_dir`, `_load_json`) |
| Pas de code mort/debug | ✅ | Toutes les constantes utilisées ; 0 print ; 0 TODO. **v1 item M-1 FIXÉ.** |
| Imports propres / relatifs | ✅ | Ordre stdlib → third-party correct. 0 import inutilisé. |
| DRY | ✅ | Pas de duplication significative. |
| Variables mortes | ✅ | Toutes les variables assignées sont référencées. |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | N/A | Test d'intégration, pas de calcul financier |
| Nommage métier | ✅ | `equity_curve`, `folds`, `trades` — termes cohérents |
| Séparation responsabilités | ✅ | Test dédié à la validation d'artefacts post-exécution |
| Invariants de domaine | N/A | |
| Cohérence unités/échelles | N/A | |
| Patterns calcul financier | N/A | |

### B6. Conformité spec / plan

| Critère | Verdict |
|---|---|
| Conforme spec §3, §17.3 | ✅ — test fullscale sur données BTCUSDT réelles |
| Conforme plan WS-13.2 | ✅ — marker fullscale, exclusion par défaut, `make run-all` |
| Formules doc vs code | N/A — pas de formule mathématique |

### B7. Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types | N/A | Pas de code source `ai_trading/` modifié |
| Noms artefacts | ✅ | `equity_curve.csv` (runner L571), `manifest.json` (manifest.py L193), `metrics.json` (metrics_builder.py L239), `metrics_fold.json` (metrics_builder.py L260), `trades.csv` (runner L446) — tous vérifiés |
| Clés de configuration | N/A | Config lue via `make` en subprocess |
| Registres | N/A | |
| Conventions numériques | N/A | |
| Imports croisés | ✅ | Imports : `json`, `subprocess`, `Path`, `jsonschema`, `pandas`, `pytest` — tous disponibles |

---

## Suivi v1 → v2

| Item v1 | Sévérité | Statut v2 | Preuve |
|---|---|---|---|
| M-1 : Variable morte `FULLSCALE_CONFIG` | MINEUR | ✅ FIXÉ | L26 définie, L71 utilisée via `config_rel = FULLSCALE_CONFIG.relative_to(PROJECT_ROOT)` |
| M-2 : `pyproject.toml` dans commit RED | MINEUR | Accepté | Commit passé non modifiable. Nécessaire pour que le marker `fullscale` soit enregistré pendant la phase RED. |
| M-3 : Filtre `is_dir()` manquant | MINEUR | ✅ FIXÉ | L139 : `sorted(d for d in folds_dir.iterdir() if d.is_dir())` |
| M-4 : equity_curve filename tolérant | MINEUR | ✅ FIXÉ | L147-150 : test strict `equity_curve.csv`, AC mis à jour |

---

## Remarques

Aucun item identifié en v2.

---

## Résumé

Les 3 items actionnables de la v1 ont été correctement corrigés dans le commit FIX. Le code est propre, respecte la politique M6 (0 fixture, 0 mock, 0 donnée synthétique), et tous les noms d'artefacts sont alignés avec le runner. Suite de tests standard verte (1621 passed, 0 failed), ruff clean. Aucun nouvel item identifié.
