# Revue PR — [WS-11] #044 — Arborescence du run (run_dir)

Branche : `task/044-run-dir`
Tâche : `docs/tasks/M5/044__ws11_run_dir.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation propre et bien structurée du module `run_dir.py` créant l'arborescence canonique des runs (§15.1). Le code est strict, config-driven, et les 19 tests couvrent les scénarios nominaux, erreurs et cas limites. Deux items mineurs empêchent le verdict CLEAN : checklist partiellement cochée dans le fichier de tâche et duplication de fixture dans les tests.

---

## Phase A — Compliance

### A1. Périmètre

| Métrique | Valeur |
|---|---|
| Branche | `task/044-run-dir` |
| Fichiers modifiés | 3 (1 source, 1 test, 1 tâche) |
| Source (`ai_trading/`) | `ai_trading/artifacts/run_dir.py` (131 lignes, nouveau) |
| Tests (`tests/`) | `tests/test_run_dir.py` (316 lignes, nouveau) |
| Docs | `docs/tasks/M5/044__ws11_run_dir.md` (mis à jour) |

### A2. Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `task/044-run-dir` |
| Commit RED présent | ✅ | `05b0392 [WS-11] #044 RED: tests arborescence run_dir` |
| Commit RED = tests uniquement | ✅ | `git show --stat 05b0392` → 1 fichier : `tests/test_run_dir.py` (317 insertions) |
| Commit GREEN présent | ✅ | `0b07758 [WS-11] #044 GREEN: arborescence run_dir` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 0b07758` → 3 fichiers : `ai_trading/artifacts/run_dir.py`, `docs/tasks/M5/044__ws11_run_dir.md`, `tests/test_run_dir.py` |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline` → exactement 2 commits |

### A3. Tâche

| Critère | Verdict | Détail |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en ligne 3 |
| Critères d'acceptation cochés | ✅ | 9/9 `[x]` |
| Checklist cochée | ❌ | 7/9 — les 2 derniers items (`Commit GREEN`, `Pull Request ouverte`) sont `[ ]` |

> **Remarque** : le commit GREEN existe (`0b07758`) mais la checkbox correspondante n'est pas cochée dans le fichier de tâche inclus dans ce même commit. La PR n'est pas encore ouverte, ce qui est normal à ce stade. → Item **MINEUR #1** ci-dessous.

### A4. CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1240 passed**, 0 failed |
| `pytest tests/test_run_dir.py -v` | **19 passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

✅ Phase A passée. Passage en Phase B.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

Toutes les commandes §GREP de `coding_rules.md` ont été exécutées sur `CHANGED_SRC=ai_trading/artifacts/run_dir.py` et `CHANGED_TEST=tests/test_run_dir.py`.

| Règle | Pattern recherché | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `or []`, `or {}`, `or ""`, `or 0`, `if ... else` | 0 occurrences ✅ |
| §R1 Except trop large | `except:$`, `except Exception:` | 0 occurrences ✅ |
| §R7 Suppressions lint | `noqa` | 0 occurrences ✅ |
| §R7 `per-file-ignores` | dans `pyproject.toml` | 1 match (pré-existant, hors scope PR) ✅ |
| §R7 Print résiduel | `print(` dans SRC | 0 occurrences ✅ |
| §R3 Shift négatif | `.shift(-` | 0 occurrences ✅ |
| §R4 Legacy random API | `np.random.seed`, `np.random.randn`, etc. | 0 occurrences ✅ |
| §R7 TODO/FIXME | `TODO`, `FIXME`, `HACK`, `XXX` | 0 occurrences ✅ |
| §R7 Chemins hardcodés tests | `/tmp`, `/var/tmp`, `C:\` | 0 occurrences ✅ |
| §R7 Imports absolus `__init__` | `from ai_trading.` dans `__init__.py` | 0 occurrences (fichier non modifié) ✅ |
| §R7 Registration manuelle tests | `register_model`, `register_feature` | 0 occurrences ✅ |
| §R6 Mutable defaults | `def ...=[]`, `def ...={}` | 0 occurrences ✅ |
| §R6 `open()` sans context manager | `open(`, `.read_text` dans SRC | 0 occurrences — `write_text` est un raccourci `Path` accepté ✅ |
| §R6 open() dans tests | `open(` | 2 occurrences (L105, L125) — toutes avec `with` ✅ |
| §R6 Comparaison bool identité | `is np.bool_`, `is True`, `is False` | 0 occurrences ✅ |
| §R6 Dict collision silencieuse | `[...] = ...` en boucle | 0 occurrences ✅ |
| §R9 Boucle Python range | `for ... in range(...)` | 1 match (L124) — faux positif : boucle `mkdir`, pas de numpy ✅ |
| §R6 `isfinite` check | `isfinite`, `math.isfinite`, `np.isfinite` | 0 occurrences — N/A, pas de validation float dans ce module ✅ |
| §R9 numpy comprehension | `np.xxx(...for ... in ...)` | 0 occurrences ✅ |
| §R7 Fixtures dupliquées | `load_config.*configs/` dans tests | 0 occurrences (helper `_load_default_config` utilise un chemin construit, pas le pattern grep exact) — voir analyse manuelle item MINEUR #2 |

### B2. Annotations par fichier

#### `ai_trading/artifacts/run_dir.py` (131 lignes — fichier entièrement nouveau)

- **L48** `if not strategy_name:` — Validation correcte. Rejette `""`, `None` (si passé malgré le type hint). ✅
- **L50-51** `datetime.now(UTC)` + `strftime("%Y%m%d_%H%M%S")` — Utilise UTC conformément à la spec. Format conforme `YYYYMMDD_HHMMSS`. ✅
- **L52** `f"{timestamp}_{strategy_name}"` — Format conforme. Le `strategy_name` n'est pas validé comme composant de chemin sûr (pas de `/` ni `\`), mais le risque est mitigé par la validation Pydantic en amont (`VALID_STRATEGIES` dans `config.py` L28-38 ne contient que des identifiants simples). Acceptable. RAS.
- **L67-70** `if not run_dir.is_dir(): raise FileNotFoundError(...)` — Validation stricte. ✅
- **L73** `config.model_dump()` — Sérialisation Pydantic v2 correcte, produit un dict Python pur. ✅
- **L74-77** `snapshot_path.write_text(yaml.dump(...), encoding="utf-8")` — Écriture atomique par `write_text`. ✅
- **L88** `if n_folds < 1: raise ValueError(...)` — Validation stricte. ✅
- **L92-94** `Path(config.artifacts.output_dir)` + `if not output_dir.is_dir()` — Config-driven. Le `output_dir` est lu depuis la config, pas hardcodé. `Path()` peut être relatif au CWD — cohérent avec le design config. ✅
- **L98** `run_dir.mkdir(parents=True, exist_ok=True)` — L'`output_dir` est validé comme existant en L93. Le `parents=True` est techniquement superflu (un seul niveau de profondeur sous `output_dir`) mais inoffensif. ✅
- **L102-103** `folds_dir / f"fold_{i:02d}" / "model_artifacts"` + `mkdir(parents=True, exist_ok=True)` — Crée `folds/fold_XX/model_artifacts/` en une seule passe. Conforme §15.1. ✅
- **L107** `save_config_snapshot(run_dir, config)` — Appelé après la création de l'arborescence. ✅

**Bilan** : RAS après lecture complète du diff (131 lignes). Code strict, bien structuré.

#### `tests/test_run_dir.py` (316 lignes — fichier entièrement nouveau)

- **L21-23** `_load_default_config()` — Helper local qui duplique la logique de `conftest.py::default_config_path` + `load_config`. Utilisé par `TestSaveConfigSnapshot` (3 tests). Les tests `TestCreateRunDir` utilisent correctement les fixtures partagées (`default_yaml_data`, `tmp_yaml`). → **MINEUR #2** ci-dessous.
- **L41-49** `test_format_matches_spec` — Vérifie le format regex `YYYYMMDD_HHMMSS_<strategy>`. ✅
- **L51-62** `test_uses_utc_time` — Mock de `datetime.now(UTC)` avec valeur fixe, vérifie le résultat exact. Déterministe. ✅
- **L64-69** `test_different_strategy_names` — Vérifie que le nom de stratégie apparaît dans le run_id. ✅
- **L71-79** `test_empty_strategy_raises` — Vérifie le rejet de la chaîne vide. ✅
- **L89-99** `test_writes_yaml_file` — Vérifie la création du fichier `config_snapshot.yaml`. ✅
- **L101-115** `test_content_is_valid_yaml` — Vérifie que le contenu est du YAML valide avec les sections attendues. ✅
- **L117-132** `test_snapshot_preserves_config_values` — Vérifie que les valeurs sont préservées. ✅
- **L134-143** `test_run_dir_not_existing_raises` — Vérifie le rejet d'un répertoire inexistant. ✅
- **L153-166** `test_creates_run_directory` — Cas nominal. ✅
- **L168-180** `test_run_dir_under_output_dir` — Vérifie que le run_dir est enfant de output_dir. ✅
- **L182-196** `test_folds_subdirectories_created` — Vérifie les répertoires `fold_00..fold_03` pour `n_folds=4`. ✅
- **L198-213** `test_model_artifacts_per_fold` — Vérifie `model_artifacts/` dans chaque fold. ✅
- **L215-226** `test_config_snapshot_created` — Vérifie que `config_snapshot.yaml` existe dans le run_dir. ✅
- **L228-239** `test_returns_path_object` — Vérifie le type de retour `Path`. ✅
- **L241-253** `test_output_dir_not_existing_raises` — Cas d'erreur : output_dir inexistant. ✅
- **L255-268** `test_n_folds_zero_raises` — Cas limite : `n_folds=0`. ✅
- **L270-283** `test_n_folds_negative_raises` — Cas limite : `n_folds=-1`. ✅
- **L285-299** `test_single_fold` — Cas limite : `n_folds=1`. Vérifie exactement 1 fold. ✅
- **L301-316** `test_run_id_in_directory_name` — Vérifie que le nom du répertoire suit le format run_id. ✅

**Bilan** : 19 tests couvrant nominal + erreurs + cas limites. Aucun test désactivé, tous déterministes, données synthétiques, chemins portables (`tmp_path`).

### B3. Vérification des tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage fichier | ✅ | `test_run_dir.py` |
| ID tâche `#044` dans docstrings | ✅ | Toutes les docstrings contiennent `#044` |
| Couverture critères d'acceptation | ✅ | 9/9 couverts (voir mapping ci-dessous) |
| Cas nominaux | ✅ | 10 tests nominaux |
| Cas d'erreur | ✅ | 4 tests (empty strategy, missing run_dir, missing output_dir, n_folds invalid) |
| Cas de bords | ✅ | `n_folds=0`, `n_folds=-1`, `n_folds=1` |
| Boundary : `n_folds=0` | ✅ | `test_n_folds_zero_raises` |
| Boundary : `n_folds=1` | ✅ | `test_single_fold` |
| Boundary : `n_folds < 0` | ✅ | `test_n_folds_negative_raises` |
| Pas de `@pytest.mark.skip` / `xfail` | ✅ | grep confirmé : 0 occurrences |
| Tests déterministes | ✅ | UTC mocké, `tmp_path` partout |
| Données synthétiques | ✅ | Aucune dépendance réseau |
| Portabilité chemins | ✅ | `tmp_path` uniquement, 0 chemin hardcodé |

**Mapping critères → tests** :

| Critère d'acceptation | Test(s) |
|---|---|
| Module importable | `test_format_matches_spec` (importe le module) |
| `create_run_dir` crée l'arborescence §15.1 | `test_creates_run_directory`, `test_folds_subdirectories_created`, `test_model_artifacts_per_fold` |
| `generate_run_id` format conforme | `test_format_matches_spec`, `test_uses_utc_time` |
| `save_config_snapshot` écrit YAML | `test_writes_yaml_file`, `test_content_is_valid_yaml`, `test_snapshot_preserves_config_values` |
| Nombre de folds = paramètre | `test_folds_subdirectories_created` (n=4), `test_single_fold` (n=1) |
| Erreur si `output_dir` inexistant | `test_output_dir_not_existing_raises` |
| Tests nominaux + erreurs + bords | 19 tests couvrant les 3 catégories |
| Suite verte | 1240 passed, 0 failed |
| ruff clean | All checks passed |

### B4. Audit du code — Règles non négociables

#### B4a. §R1 — Strict code (no fallbacks)
- [x] 0 fallback silencieux (grep exécuté).
- [x] 0 `except` trop large (grep exécuté).
- [x] Validation explicite : `generate_run_id` → `ValueError` si empty, `save_config_snapshot` → `FileNotFoundError` si dir absent, `create_run_dir` → `ValueError` si `n_folds < 1`, `FileNotFoundError` si `output_dir` absent.

#### B4a-bis. §R10 — Defensive indexing / slicing
- [x] N/A — aucune opération d'indexing/slicing sur des arrays.

#### B4b. §R2 — Config-driven
- [x] `output_dir` lu depuis `config.artifacts.output_dir` (L92).
- [x] Aucune valeur magique hardcodée (le format `fold_%02d` est une convention de nommage, pas un paramètre configurable — conforme §15.1).

#### B4c. §R3 — Anti-fuite
- [x] N/A — module d'arborescence, pas de données temporelles.

#### B4d. §R4 — Reproductibilité
- [x] N/A — pas d'aléatoire (la date UTC est déterministe pour un instant donné).

#### B4e. §R5 — Float conventions
- [x] N/A — pas de calcul flottant.

#### B4f. §R6 — Anti-patterns
- [x] 0 mutable default (grep exécuté).
- [x] `write_text` utilisé au lieu de `open()` dans le source (raccourci `Path` accepté).
- [x] `open()` dans les tests utilise `with` (L105, L125).
- [x] N/A pour comparaison float, NaN/inf, dict collision.
- [x] `Path(config.artifacts.output_dir)` : le `output_dir` est un `str` de la config → `Path()` correct.

### B5. Qualité du code

- [x] snake_case cohérent.
- [x] Pas de code mort, commenté ou TODO orphelin.
- [x] Pas de `print()` résiduel.
- [x] Imports propres : stdlib → third-party (`yaml`) → local (`ai_trading.config`).
- [x] Pas de variables mortes.
- [x] Pas de fichiers générés dans la PR.
- [x] `__init__.py` de `artifacts/` : pas modifié — contient juste un docstring, pas d'import nécessaire (les callers importent directement `from ai_trading.artifacts.run_dir import ...`). ✅

### B5-bis. §R9 — Bonnes pratiques métier
- [x] N/A — module utilitaire (pas de calcul financier).

### B6. Cohérence avec les specs

- [x] Arborescence conforme à §15.1 : `<output_dir>/<run_id>/folds/fold_XX/model_artifacts/` + `config_snapshot.yaml`. Les fichiers supplémentaires de §15.1 (`manifest.json`, `metrics.json`, `preds_*.csv`, etc.) seront créés par d'autres tâches (WS-11.2+) — correct scoping.
- [x] Format `run_id` conforme : `YYYYMMDD_HHMMSS_<strategy>` (spec : `runs/20260227_120000_xgboost_reg`).
- [x] Config snapshot = config fully resolved (`model_dump()` de Pydantic v2).
- [x] Pas d'exigence inventée hors spec.

### B7. §R8 — Cohérence intermodule

- [x] `PipelineConfig` importé depuis `ai_trading.config` — symbole existant dans `Max6000i1`, attribut `artifacts.output_dir` existant (L309 de `config.py`).
- [x] `load_config` utilisé dans les tests — fonction existante.
- [x] Pas d'imports croisés vers des modules non mergés.
- [x] Pas de divergence de signatures ou types.

---

## Remarques

1. **[MINEUR]** Checklist de tâche incomplète
   - Fichier : `docs/tasks/M5/044__ws11_run_dir.md`
   - Ligne(s) : avant-dernière et dernière lignes de la checklist
   - Description : Les items `Commit GREEN` et `Pull Request ouverte` sont `[ ]` alors que le commit GREEN existe (`0b07758`). Le premier devrait être coché dans le commit ; le second est attendu non coché à ce stade pré-PR.
   - Suggestion : Cocher `[x]` pour `Commit GREEN` dans le fichier de tâche. L'item `Pull Request ouverte` peut rester `[ ]` jusqu'à l'ouverture effective.

2. **[MINEUR]** Duplication de fixture dans les tests
   - Fichier : `tests/test_run_dir.py`
   - Ligne(s) : 21-23
   - Description : Le helper `_load_default_config()` duplique la logique des fixtures conftest (`default_config_path` + `load_config`). Les tests `TestSaveConfigSnapshot` l'utilisent alors que `TestCreateRunDir` utilise correctement les fixtures partagées.
   - Suggestion : Remplacer `_load_default_config()` par l'utilisation des fixtures `default_config_path` + `load_config(str(default_config_path))` dans `TestSaveConfigSnapshot`, ou simplement utiliser `default_yaml_data` + `tmp_yaml` comme le fait `TestCreateRunDir`.

---

## Résumé

Implémentation solide et concise (131 lignes de source, 19 tests) qui crée correctement l'arborescence canonique §15.1. Le code respecte les règles strict-code, config-driven, et toutes les validations sont explicites. Deux items mineurs à corriger avant merge : checklist du fichier de tâche à compléter, et duplication de fixture dans les tests à factoriser via les fixtures conftest existantes.

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 2
- Rapport : `docs/tasks/M5/044/review_v1.md`
