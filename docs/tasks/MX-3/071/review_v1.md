# Revue PR — [WS-XGB-7] #071 — Tests de reproductibilité XGBoost

Branche : `task/071-xgb-reproducibility`
Tâche : `docs/tasks/MX-3/071__ws_xgb7_reproducibility.md`
Date : 2026-03-03

## Verdict global : ✅ CLEAN

## Résumé

Ajout de 3 tests de reproductibilité XGBoost dans une classe `TestXGBoostReproducibility` + 2 helpers module-level. Aucun code source modifié — uniquement tests. Tests bien structurés, couverture complète des critères d'acceptation, scans GREP tous propres, 1774 tests GREEN, ruff clean.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/071-xgb-reproducibility` | ✅ | `git branch --show-current` → `task/071-xgb-reproducibility` |
| Commit RED présent | ✅ | `f67cbe3` — `[WS-XGB-7] #071 RED: tests reproductibilité XGBoost (métriques, SHA-256 trades, sérialisation round-trip)` |
| Commit GREEN présent | ✅ | `5a6f822` — `[WS-XGB-7] #071 GREEN: reproductibilité XGBoost validée` |
| Commit RED : tests uniquement | ✅ | `git show --stat f67cbe3` → `tests/test_xgboost_integration.py | 194 +++` (1 fichier, tests uniquement) |
| Commit GREEN : task update | ✅ | `git show --stat 5a6f822` → `docs/tasks/MX-3/071__ws_xgb7_reproducibility.md | 68 +++` (1 fichier, tâche uniquement — attendu pour une tâche tests-only) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ — `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (7/7) |
| Checklist cochée | ✅ (8/9 — seul `[ ] PR ouverte` non coché, attendu avant merge) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ --tb=short -q` | **1774 passed**, 12 deselected, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### Fichiers modifiés

| Fichier | Type | Lignes ajoutées |
|---|---|---|
| `tests/test_xgboost_integration.py` | Test | +194 |
| `docs/tasks/MX-3/071__ws_xgb7_reproducibility.md` | Tâche | +68 (nouveau fichier) |

Aucun fichier source (`ai_trading/`) modifié.

### B1 — Résultats du scan automatisé (GREP)

Scan exécuté sur `tests/test_xgboost_integration.py` (unique fichier `.py` modifié).

| Pattern recherché | Règle | Commande | Résultat |
|---|---|---|---|
| Fallbacks silencieux | §R1 | `grep 'or []\|or {}...'` | 0 occurrences (grep exécuté — N/A, pas de code source) |
| Except trop large | §R1 | `grep 'except:$\|except Exception:'` | 0 occurrences |
| Suppressions lint (noqa) | §R7 | `grep 'noqa'` | 0 occurrences |
| per-file-ignores | §R7 | `grep 'per-file-ignores' pyproject.toml` | Présent L52 (pré-existant, non modifié) |
| Print résiduel | §R7 | `grep 'print('` | 0 occurrences |
| Shift négatif | §R3 | `grep '.shift(-'` | 0 occurrences |
| Legacy random API | §R4 | `grep 'np.random.seed\|np.random.randn...'` | 0 occurrences |
| TODO/FIXME orphelins | §R7 | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences |
| Chemins hardcodés OS | §R7 | `grep '/tmp\|C:\\'` | 0 occurrences |
| Imports absolus `__init__` | §R7 | N/A — aucun `__init__.py` modifié | N/A |
| Registration manuelle tests | §R7 | `grep 'register_model\|register_feature'` | 0 occurrences |
| Mutable default arguments | §R6 | `grep 'def.*=[]\|def.*={}'` | 0 occurrences |
| Booléen par identité | §R6 | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences |
| open() sans context manager | §R6 | `grep 'open('` | 0 occurrences |
| Boucle for/range | §R9 | `grep 'for .* in range(.*):' ` | 0 occurrences |
| isfinite validation | §R6 | `grep 'isfinite'` | 0 occurrences (N/A — pas de validation de bornes dans les tests) |
| Fixtures dupliquées | §R7 | `grep 'load_config.*configs/'` | 0 occurrences |

### B2 — Annotations par fichier

#### `tests/test_xgboost_integration.py` (diff : +194 lignes)

**Helpers ajoutés (L548-579)** :

- `_deep_compare_metrics(obj1, obj2, path, atol)` — Comparaison récursive de structures JSON-like. Gère dict, list, int/float (avec `atol`), et fallback `==` pour str/None. Note : `isinstance(True, int)` est `True` en Python, donc les booléens passent par le chemin float ; fonctionnellement correct (comparaison numérique `abs(1.0 - 1.0) = 0.0 ≤ atol`), impact nul sur les métriques JSON.
  Sévérité : RAS

- `_sha256_file(path)` — Hash SHA-256 d'un fichier via `path.read_bytes()`. Correct, utilise `Path.read_bytes()` (pas de `open()` nu).
  Sévérité : RAS

**Classe `TestXGBoostReproducibility` (L585-734)** :

- **L595-598** `setup()` — Fixture `autouse=True` qui crée config + chemin YAML via helpers partagés (`_make_xgboost_config_dict`, `write_config`). Réutilise correctement les fixtures du module.
  Sévérité : RAS

- **L600-605** `_run_pipeline()` — Import local + appel `run_pipeline(config)`. Correct.
  Sévérité : RAS

- **L607-623** `_run_two()` — Exécute deux runs avec la même seed, output dirs séparés (`runs` vs `runs2`). Copie partielle du dict config (`dict()` + copie manuelle de `artifacts`). Suffisant puisque seul `artifacts.output_dir` est modifié.
  Sévérité : RAS

- **L627-645** `test_metrics_json_identical_across_two_runs()` — Deux runs, comparaison deep des `metrics.json` après suppression des champs non-déterministes (`run_id`, `timestamp`, `run_dir` via `.pop(key, None)`). L'usage de `.pop(key, None)` est approprié ici : suppression intentionnelle de métadonnées optionnelles pour la comparaison, pas un fallback silencieux. `atol=1e-7` conforme au critère d'acceptation.
  Sévérité : RAS

- **L649-671** `test_trades_csv_sha256_identical_across_two_runs()` — Deux runs, comparaison SHA-256 des `trades.csv` fold par fold. Assertions correctes : `len(folds) >= 1` vérifie qu'il y a des folds, `strict=True` dans `zip()` empêche les longueurs inégales, comparaison par hash. Conforme au critère SHA-256.
  Sévérité : RAS

- **L675-734** `test_serialization_roundtrip_predictions()` — Test unitaire de sérialisation : `fit()` → `predict()` → `save()` → `load()` → `predict()` → `assert_array_equal`. Utilise `np.random.default_rng(_SEED)` (pas de legacy random API). Données synthétiques float32 conformes aux conventions. Note : `model2._feature_names = [f"f{i}" for i in range(n_feat)]` (L727) accède à un attribut privé car `load()` ne restaure pas les feature names — c'est le comportement correct étant donné l'API existante, documenté par le commentaire inline `# Restore feature names (same convention as fit)`. La comparaison finale utilise `np.testing.assert_array_equal` (exact, pas `approx`), approprié pour du round-trip déterministe.
  Sévérité : RAS

RAS après lecture complète du diff (194 lignes).

#### `docs/tasks/MX-3/071__ws_xgb7_reproducibility.md`

Nouveau fichier de tâche, statut DONE, critères cochés. Conforme aux conventions.
Sévérité : RAS

### B3 — Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage tests | ✅ | Classe `TestXGBoostReproducibility` dans `test_xgboost_integration.py`, docstrings avec `#071` |
| Couverture des critères | ✅ | AC1 (classe) → classe ajoutée ; AC2 (metrics atol) → `test_metrics_json_identical…` ; AC3 (SHA-256) → `test_trades_csv_sha256…` ; AC4 (round-trip) → `test_serialization_roundtrip…` ; AC5 (seed) → `_SEED=42` + `np.random.default_rng` ; AC6 (tests green) → 1774 passed ; AC7 (ruff) → passed |
| Cas nominaux + erreurs + bords | ✅ | Cas nominal (2 runs identiques) couvert par les 3 tests. Pas de cas d'erreur attendu (tâche de validation de comportement existant). Bords : `len(folds) >= 1` vérifié |
| Boundary fuzzing | N/A | Pas de paramètres numériques d'entrée à fuzzer — tests de reproductibilité E2E |
| Déterministes | ✅ | `_SEED = 42`, `np.random.default_rng(_SEED)`, config `reproducibility.global_seed = 42` |
| Données synthétiques | ✅ | `build_ohlcv_df(n=500)` + `rng.standard_normal()` — aucune dépendance réseau |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé. Tous les chemins utilisent `tmp_path` |
| Tests registre réalistes | N/A | Pas de test de registre dans cette PR |
| Contrat ABC complet | N/A | Pas de nouveau module ABC dans cette PR |

### B4 — Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code | ✅ | Scan B1 : 0 fallback, 0 except large. Pas de code source modifié |
| §R10 Defensive indexing | ✅ | Lecture diff : aucun slicing problématique dans le test code |
| §R2 Config-driven | ✅ | Config construite via `_make_xgboost_config_dict`, tous les paramètres depuis la config |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Pas de code source modifié |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. `np.random.default_rng(_SEED)` utilisé |
| §R5 Float conventions | ✅ | Tenseurs : `astype(np.float32)` (L689-698). Métriques : comparaison float64 naturellement via JSON |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 `open()` nu, 0 `is True/False`, 0 booléen par identité |

### B5 — Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `_deep_compare_metrics`, `_sha256_file`, `_run_two`, `_run_pipeline` |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 TODO/FIXME |
| Imports propres | ✅ | `import hashlib` ajouté (utilisé), aucun import inutilisé |
| DRY | ✅ | `_run_two()` factorise la logique des tests 1 et 2. Helpers `_deep_compare_metrics` et `_sha256_file` extraits au module level |
| Pas de fichiers générés | ✅ | `git diff --name-only` : uniquement test + tâche |

### B5-bis — Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | N/A | Pas de calcul financier dans ces tests |
| Nommage métier | ✅ | `metrics`, `trades`, `fold`, `predictions` — vocabulaire conforme |
| Séparation responsabilités | ✅ | Tests de reproductibilité séparés dans leur propre classe |
| Invariants de domaine | N/A | Pas de validation d'invariant financier |
| Cohérence unités/échelles | N/A | Pas de calcul d'échelle |
| Patterns calcul financier | N/A | Pas de calcul numérique financier |

### B6 — Conformité spec v1.0

| Critère | Verdict |
|---|---|
| Spécification pipeline (§16 reproductibilité) | ✅ — seed fixée, déterminisme vérifié, SHA-256 sur artefacts |
| Spécification modèle XGBoost (§9) | ✅ — `tree_method=hist` + `random_state` dans la config |
| Plan d'implémentation (WS-XGB-7.3) | ✅ — tests de reproductibilité pipeline comme prévu |
| Formules doc vs code | N/A — pas de formule mathématique dans cette tâche |

### B7 — Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `XGBoostRegModel.fit()`, `.predict()`, `.save()`, `.load()` appelés avec les bons paramètres |
| Noms de colonnes DataFrame | N/A | Pas de manipulation directe de DataFrame |
| Clés de configuration | ✅ | Config dict cohérente avec `_make_xgboost_config_dict` existant |
| Registres et conventions | N/A | Pas d'interaction registre |
| Structures données partagées | ✅ | Même structure config réutilisée entre les 3 classes de test |
| Conventions numériques | ✅ | float32 pour tenseurs, feature names `[f"f{i}"]` conforme à `fit()` |
| Imports croisés | ✅ | `XGBoostRegModel`, `load_config`, `run_pipeline`, `flatten_seq_to_tab` — tous existants dans Max6000i1 |
| Forwarding kwargs | N/A | Pas de forwarding dans les tests |

---

## Remarques

Aucun item identifié.

## Observations (informatives, hors grille)

1. **TDD characterisation tests** : les tests de reproductibilité valident un comportement déjà implémenté — le RED commit contenait des tests probablement déjà GREEN. C'est le comportement attendu pour des tests de caractérisation ajoutés à un pipeline existant.

2. **`model2._feature_names` (L727)** : accès direct à un attribut privé car `load()` ne sérialise pas les feature names. Correctement documenté par le commentaire inline. Le design gap est dans `save()`/`load()` (pré-existant, hors scope de cette tâche).

3. **Complémentarité avec test existant** : `TestXGBoostE2E.test_deterministic_across_two_runs` (#069) teste aussi le déterminisme mais de façon moins rigoureuse (même output dir, comparaison partielle via `pytest.approx`). Les nouveaux tests sont plus exhaustifs (output dirs séparés, deep comparison field-by-field, SHA-256 byte-exact).

---

## Actions requises

Aucune.
