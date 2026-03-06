# Revue PR — [WS-11] #044 — Arborescence du run (run_dir)

Branche : `task/044-run-dir`
Tâche : `docs/tasks/M5/044__ws11_run_dir.md`
Date : 2026-03-03
Itération : v2 (suite corrections v1)

## Verdict global : ✅ CLEAN

## Résumé

Les deux items MINEUR de la revue v1 ont été correctement corrigés dans le commit FIX `75f45df` : la checkbox « Commit GREEN » est cochée dans le fichier de tâche, et le helper `_load_default_config()` a été supprimé au profit d'une fixture partagée `default_config` factorisée dans `conftest.py`. Le code source `run_dir.py` est inchangé depuis v1 et reste conforme. La suite complète (1240 tests) passe, ruff est clean, et tous les scans §GREP sont négatifs.

---

## Phase A — Compliance

### A1. Périmètre

| Métrique | Valeur |
|---|---|
| Branche | `task/044-run-dir` |
| Fichiers modifiés vs `Max6000i1` | 5 |
| Source (`ai_trading/`) | `ai_trading/artifacts/run_dir.py` (131 lignes, nouveau) |
| Tests (`tests/`) | `tests/test_run_dir.py` (nouveau), `tests/conftest.py` (modifié), `tests/test_quantile_grid.py` (modifié) |
| Docs | `docs/tasks/M5/044__ws11_run_dir.md` (mis à jour) |

### A2. Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `task/044-run-dir` |
| Commit RED présent | ✅ | `05b0392 [WS-11] #044 RED: tests arborescence run_dir` |
| Commit RED = tests uniquement | ✅ | `git show --stat 05b0392` → 1 fichier : `tests/test_run_dir.py` (317 insertions) |
| Commit GREEN présent | ✅ | `0b07758 [WS-11] #044 GREEN: arborescence run_dir` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 0b07758` → 3 fichiers : `ai_trading/artifacts/run_dir.py`, `docs/tasks/M5/044__ws11_run_dir.md`, `tests/test_run_dir.py` |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline` → RED, GREEN, puis FIX (post-review) |
| Commit FIX post-review | ✅ | `75f45df [WS-11] #044 FIX: check Commit GREEN checkbox, factorize _load_default_config into conftest default_config fixture` — corrige les 2 items MINEUR de v1 |

### A3. Tâche

| Critère | Verdict | Détail |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en ligne 3 |
| Critères d'acceptation cochés | ✅ | 9/9 `[x]` |
| Checklist cochée | ✅ | 8/9 `[x]` — seul `Pull Request ouverte` reste `[ ]`, ce qui est normal à ce stade pré-PR |

#### Vérification des critères d'acceptation

| Critère | Code / Test preuve |
|---|---|
| Module importable | `test_format_matches_spec` (importe le module) |
| `create_run_dir` crée l'arborescence §15.1 | `run_dir.py` L96-126 + `test_creates_run_directory`, `test_folds_subdirectories_created`, `test_model_artifacts_per_fold` |
| `generate_run_id` format conforme | `run_dir.py` L25-52 + `test_format_matches_spec`, `test_uses_utc_time` |
| `save_config_snapshot` écrit YAML | `run_dir.py` L55-78 + `test_writes_yaml_file`, `test_content_is_valid_yaml`, `test_snapshot_preserves_config_values` |
| Nombre de folds = paramètre | `run_dir.py` L124 + `test_folds_subdirectories_created` (n=4), `test_single_fold` (n=1) |
| Erreur si output_dir inexistant | `run_dir.py` L115-117 + `test_output_dir_not_existing_raises` |
| Tests nominaux + erreurs + bords | 19 tests couvrant les 3 catégories |
| Suite verte | 1240 passed |
| ruff clean | All checks passed |

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

Toutes les commandes §GREP de `coding_rules.md` exécutées sur les fichiers modifiés.

| Règle | Pattern recherché | Fichiers scannés | Résultat |
|---|---|---|---|
| §R1 Fallbacks silencieux | `or []`, `or {}`, `or ""`, `or 0`, `if ... else` | SRC | 0 occurrences ✅ |
| §R1 Except trop large | `except:$`, `except Exception:` | SRC | 0 occurrences ✅ |
| §R7 Suppressions lint | `noqa` | ALL | 0 occurrences ✅ |
| §R7 Print résiduel | `print(` | SRC | 0 occurrences ✅ |
| §R3 Shift négatif | `.shift(-` | SRC | 0 occurrences ✅ |
| §R4 Legacy random API | `np.random.seed`, `np.random.randn`, etc. | ALL | 0 occurrences ✅ |
| §R7 TODO/FIXME | `TODO`, `FIXME`, `HACK`, `XXX` | ALL | 0 occurrences ✅ |
| §R7 Chemins hardcodés tests | `/tmp`, `/var/tmp`, `C:\` | TESTS | 0 occurrences ✅ |
| §R7 Imports absolus `__init__` | `from ai_trading.` dans `__init__.py` | N/A | Aucun `__init__.py` modifié ✅ |
| §R7 Registration manuelle tests | `register_model`, `register_feature` | TESTS | 0 occurrences ✅ |
| §R6 Mutable defaults | `def ...=[]`, `def ...={}` | ALL | 0 occurrences ✅ |
| §R6 `open()` sans context manager | `.read_text`, `open(` | SRC | 0 occurrences — `write_text` est raccourci Path ✅ |
| §R6 `open()` dans tests | `open(` | TESTS | 2 matches (test_run_dir.py L95, L115) — tous avec `with` ✅ |
| §R6 Comparaison bool identité | `is np.bool_`, `is True`, `is False` | ALL | 0 occurrences ✅ |
| §R6 Dict collision silencieuse | `[...] = ...` en boucle | SRC | 0 occurrences ✅ |
| §R9 Boucle Python range | `for ... in range(...)` | SRC | 1 match (L124) — faux positif : boucle mkdir, pas numpy ✅ |
| §R6 isfinite check | `isfinite` | SRC | 0 occurrences — N/A, pas de float validation ✅ |
| §R9 numpy comprehension | `np.xxx(...for ... in ...)` | SRC | 0 occurrences ✅ |
| §R7 Fixtures dupliquées | `load_config.*configs/` | TESTS | 0 occurrences ✅ |

### B2. Annotations par fichier

#### `ai_trading/artifacts/run_dir.py` (131 lignes — inchangé depuis v1)

RAS. Le code source n'a pas été modifié entre v1 et v2. L'analyse v1 reste valide :
- Validation stricte aux frontières (L48, L67-70, L113-117)
- Config-driven : `output_dir` lu depuis config (L115)
- Arborescence conforme §15.1 (L121-126)
- `write_text` avec encoding UTF-8 (L76)
- Format run_id conforme `YYYYMMDD_HHMMSS_<strategy>` (L50-52)

#### `tests/conftest.py` (ajout fixture `default_config`)

- **L28-33** Nouvelle fixture `default_config` : charge la config par défaut via `load_config(str(default_config_path))`. Import lazy de `load_config` dans le body de la fixture — correct pour éviter les problèmes d'import circulaire. Dépend de la fixture `default_config_path` existante. ✅

#### `tests/test_quantile_grid.py` (suppression fixture locale + import inutilisé)

- **L12-13** Import `from ai_trading.config import load_config` supprimé — correct, plus utilisé après suppression de la fixture locale. ✅
- **L22-24** Trois lignes blanches consécutives après le fixture `y_hat_val` (artefact de la suppression). Ruff ne flag pas (2 lignes vides entre top-level est PEP 8 ; 3 est toléré). Non bloquant, cosmétique pur. RAS.

#### `tests/test_run_dir.py` (suppression helper, utilisation fixture conftest)

- **L15** `from ai_trading.config import load_config` reste importé — utilisé 11 fois dans `TestCreateRunDir`. ✅
- **L71, 84, 104, 121** `TestSaveConfigSnapshot` utilise désormais la fixture `default_config` au lieu de `_load_default_config()`. ✅
- **L14-16** Suppression du helper `_load_default_config()` et du bloc `# Helpers` — correctement nettoyé. ✅

#### `docs/tasks/M5/044__ws11_run_dir.md`

- Checkbox `Commit GREEN` passée de `[ ]` à `[x]`. ✅

### B3. Vérification des tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage fichier | ✅ | `test_run_dir.py` |
| ID tâche `#044` dans docstrings | ✅ | Toutes les 19 docstrings contiennent `#044` |
| Couverture critères d'acceptation | ✅ | 9/9 couverts (mapping dans Phase A3) |
| Cas nominaux | ✅ | 10 tests nominaux |
| Cas d'erreur | ✅ | 4 tests (empty strategy, missing run_dir, missing output_dir, n_folds invalid) |
| Cas de bords | ✅ | `n_folds=0`, `n_folds=-1`, `n_folds=1` |
| Boundary `n_folds=0` | ✅ | `test_n_folds_zero_raises` |
| Boundary `n_folds=1` | ✅ | `test_single_fold` |
| Boundary `n_folds < 0` | ✅ | `test_n_folds_negative_raises` |
| Pas de `skip` / `xfail` | ✅ | 0 occurrences (grep exécuté) |
| Tests déterministes | ✅ | UTC mocké, `tmp_path` partout |
| Données synthétiques | ✅ | Aucune dépendance réseau |
| Portabilité chemins | ✅ | `tmp_path` uniquement, 0 chemin hardcodé (grep exécuté) |
| Pas de registration manuelle | ✅ | N/A (pas de registre dans ce module) |
| Pas de fixture dupliquée | ✅ | `_load_default_config` supprimé, `default_config` factorisé dans conftest |

### B4. Audit du code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. Lecture diff : validation explicite + raise |
| §R10 Defensive indexing / slicing | ✅ | N/A — aucune opération d'indexing/slicing |
| §R2 Config-driven | ✅ | `output_dir` lu depuis `config.artifacts.output_dir` (L115). Format fold = convention spec §15.1 |
| §R3 Anti-fuite | ✅ | N/A — module utilitaire, pas de données temporelles. 0 `.shift(-` |
| §R4 Reproductibilité | ✅ | N/A — pas d'aléatoire. 0 legacy random API |
| §R5 Float conventions | ✅ | N/A — pas de calcul flottant |
| §R6 Anti-patterns Python | ✅ | 0 mutable default, `write_text` correct, `open()` tests avec `with`, pas de float ==, pas de dict collision |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `generate_run_id`, `save_config_snapshot`, `create_run_dir` |
| Pas de code mort/debug | ✅ | 0 `print()`, 0 TODO/FIXME (grep exécuté) |
| Imports propres / relatifs | ✅ | stdlib → third-party → local. 0 import absolu dans `__init__.py` |
| DRY | ✅ | Fixture `default_config` factorisée dans conftest (corrigé en v2) |
| Pas de `noqa` | ✅ | 0 occurrences |
| Pas de variables mortes | ✅ | Toutes les variables assignées sont utilisées |
| `__init__.py` à jour | ✅ | `ai_trading/artifacts/__init__.py` n'a pas besoin d'import (callers importent directement) |

### B5-bis. §R9 — Bonnes pratiques métier

N/A — module utilitaire (pas de calcul financier, pas d'indicateur technique).

### B6. Cohérence avec les specs

| Critère | Verdict | Commentaire |
|---|---|---|
| Arborescence §15.1 | ✅ | `<output_dir>/<run_id>/folds/fold_XX/model_artifacts/` + `config_snapshot.yaml`. Fichiers supplémentaires (manifest, metrics, preds, trades, equity_curve) correctement hors scope de cette tâche |
| Format run_id | ✅ | `YYYYMMDD_HHMMSS_<strategy>` conforme à l'exemple spec `runs/20260227_120000_xgboost_reg` |
| Config snapshot | ✅ | `model_dump()` Pydantic v2 = config fully resolved |
| Plan WS-11.1 | ✅ | Couverture correcte du scope WS-11.1 |
| Pas d'exigence inventée | ✅ | |

### B7. §R8 — Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `PipelineConfig` type correct, retour `Path` documenté |
| Clés de configuration | ✅ | `config.artifacts.output_dir` existe dans le modèle Pydantic |
| Imports croisés | ✅ | `ai_trading.config.PipelineConfig` et `load_config` existent dans `Max6000i1` |
| Conventions numériques | ✅ | N/A |
| Forwarding kwargs | ✅ | N/A |

---

## Vérification des corrections v1

| Item v1 | Sévérité | Correction appliquée | Verdict |
|---|---|---|---|
| #1 Checklist « Commit GREEN » non cochée | MINEUR | Checkbox `[x]` dans commit FIX `75f45df` | ✅ Corrigé |
| #2 Duplication fixture `_load_default_config()` | MINEUR | Helper supprimé, fixture `default_config` ajoutée dans `conftest.py`, `TestSaveConfigSnapshot` utilise la fixture, fixture locale supprimée de `test_quantile_grid.py` | ✅ Corrigé |

---

## Remarques

Aucune.

---

## Résumé

Les deux items MINEUR de la revue v1 sont corrigés. Le code source `run_dir.py` est inchangé et reste conforme. La factorisation de `default_config` dans `conftest.py` est propre et bénéficie à `test_run_dir.py` et `test_quantile_grid.py`. Suite complète verte (1240 tests), ruff clean, tous les scans GREP négatifs. Aucun item résiduel.

---

RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : `docs/tasks/M5/044/review_v2.md`
