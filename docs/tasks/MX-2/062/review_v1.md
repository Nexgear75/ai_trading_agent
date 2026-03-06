# Revue PR — [WS-XGB-3] #062 — Instanciation régresseur et fit de base

Branche : `task/062-xgb-fit-base`
Tâche : `docs/tasks/MX-2/062__ws_xgb3_fit_base.md`
Date : 2026-03-03

## Verdict global : ✅ APPROVE

## Résumé

L'implémentation de `fit()` dans `XGBoostRegModel` est correcte, conforme à la spec §5.1 et config-driven. Le code valide strictement les entrées (shape 3D, dtype float32, shape compatibility), aplatit via l'adapter `flatten_seq_to_tab`, instancie le `XGBRegressor` avec les 7 hyperparamètres config + 4 paramètres imposés, et appelle `fit()` avec `eval_set`. Les 26 tests couvrent tous les critères d'acceptation. Deux observations mineures sont signalées (y dtype non validé, pas de test boundary N=0) mais ni l'une ni l'autre ne sont des exigences des critères d'acceptation de la tâche.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Branche `task/NNN-short-slug` | ✅ | `task/062-xgb-fit-base` — `git log --oneline` |
| Commit RED au format `[WS-X] #NNN RED: <résumé>` | ✅ | `0abae39 [WS-XGB-3] #062 RED: tests fit base XGBoostRegModel` |
| Commit GREEN au format `[WS-X] #NNN GREEN: <résumé>` | ✅ | `f418ac9 [WS-XGB-3] #062 GREEN: implémentation fit base XGBoostRegModel` |
| Commit RED contient uniquement tests | ✅ | `git show --stat 0abae39` → `tests/test_xgboost_model.py | 281 ++++` (1 fichier modifié) |
| Commit GREEN contient implémentation + tâche | ✅ | `git show --stat f418ac9` → `ai_trading/models/xgboost.py` + `docs/tasks/MX-2/062__ws_xgb3_fit_base.md` (2 fichiers) |
| Pas de commits parasites entre RED et GREEN | ✅ | Exactement 2 commits sur la branche : RED puis GREEN |

### Tâche associée

| Critère | Verdict | Preuve |
|---|---|---|
| Tâche modifiée dans la PR | ✅ | `git diff --name-only Max6000i1...HEAD` inclut `docs/tasks/MX-2/062__ws_xgb3_fit_base.md` |
| Statut DONE | ✅ | Lecture du fichier : `Statut : DONE` |
| Critères d'acceptation cochés `[x]` | ✅ | 14 critères, tous cochés `[x]` — vérifiés individuellement ci-dessous (§B3) |
| Checklist cochée `[x]` | ✅ | 9 items de checklist, 8 cochés `[x]`. Seul « Pull Request ouverte » est `[ ]` — cohérent (PR pas encore ouverte au moment du commit) |

### CI / Validation

| Critère | Verdict | Preuve |
|---|---|---|
| pytest GREEN | ✅ | `1691 passed, 12 deselected in 22.94s` (full suite), `26 passed in 0.97s` (fichier seul) |
| ruff clean | ✅ | `ruff check ai_trading/ tests/` → `All checks passed!` |

**Phase A : PASS** — poursuite en Phase B.

---

## Phase B — Code review adversariale

### B1. Scan automatisé (GREP)

| Scan | Résultat | Classification |
|---|---|---|
| §R1 — Fallbacks silencieux (`or []`, `or {}`, `or ""`, `if...else`) | 0 occurrences (grep exécuté) | ✅ |
| §R1 — Except trop large (`except:`, `except Exception:`) | 0 occurrences (grep exécuté) | ✅ |
| §R7 — `noqa` | 4 matches : `N803` sur `X_train`, `X_val`, `X` (paramètres ABC imposés) + `F811/F401` dans test import side-effect | Faux positifs — tous justifiés par l'interface ABC ou le pattern de test |
| §R7 — `print()` résiduel | 0 occurrences (grep exécuté) | ✅ |
| §R3 — `.shift(-` (look-ahead) | 0 occurrences (grep exécuté) | ✅ |
| §R4 — Legacy random API | 0 occurrences (grep exécuté) | ✅ |
| §R7 — TODO/FIXME/HACK/XXX | 0 occurrences (grep exécuté) | ✅ |
| §R7 — Chemins hardcodés (`/tmp`, `C:\`) dans tests | 0 occurrences (grep exécuté) | ✅ |
| §R7 — Imports absolus dans `__init__.py` | N/A — aucun `__init__.py` modifié | ✅ |
| §R7 — Registration manuelle dans tests | 1 match : `_reload_xgboost_module()` (commentaire docstring mentionnant `@register_model`) | Faux positif — les tests utilisent `importlib.reload()` (pattern correct) |
| §R6 — Mutable default arguments | 0 occurrences (grep exécuté) | ✅ |
| §R6 — `open()` sans context manager | 0 occurrences (grep exécuté) | ✅ |
| §R6 — Comparaison booléenne par identité | 0 occurrences (grep exécuté) | ✅ |
| §R6 — Dict collision silencieuse | 0 occurrences (grep exécuté) | ✅ |
| §R9 — Boucle Python sur array numpy | 0 occurrences (grep exécuté) | ✅ |
| §R6 — `isfinite` checks | 0 occurrences (grep exécuté) | Note : pas de paramètres float en entrée publique nécessitant un check NaN (les entrées sont des arrays numpy, pas des scalaires) |
| §R9 — Appels numpy dans compréhension | 0 occurrences (grep exécuté) | ✅ |
| §R7 — Fixtures dupliquées (`load_config.*configs/`) | 0 occurrences (grep exécuté) | ✅ — tests utilisent `default_config` de `conftest.py` |
| §R7 — `per-file-ignores` dans `pyproject.toml` | 1 match (ligne 52) — préexistant, pas modifié par cette PR | ✅ |

### B2. Lecture du diff ligne par ligne

#### `ai_trading/models/xgboost.py` (68 lignes ajoutées, 2 supprimées)

**Observations :**

1. **Validation des entrées (L49-L78)** : 6 checks stricts couvrant ndim (X_train, X_val), shape[0] match (train, val), et dtype (X_train, X_val). Messages d'erreur informatifs avec f-string. ✅
2. **Aplatissement (L80-L83)** : `feature_names` générés comme `f0, f1, ...` — noms génériques acceptables car les column names sont discardés (`_`). L'adapter `flatten_seq_to_tab` effectue sa propre validation 3D, redondante mais inoffensive. ✅
3. **Instanciation XGBRegressor (L86-L100)** : 7 hyperparamètres lus depuis `config.models.xgboost.*`, 4 paramètres imposés (`objective`, `tree_method`, `booster`, `verbosity`), `random_state` depuis `config.reproducibility.global_seed`, `early_stopping_rounds` depuis `config.training.early_stopping_patience`. Strictement conforme à la spec §5.1 pseudo-code et §4.4 tableau récapitulatif. ✅
4. **Fit (L103-L107)** : `eval_set=[(x_tab_val, y_val)]` — uniquement données val, pas de test. `verbose=False`. Conforme §5.1. ✅
5. **Return (L109)** : `return {}` — provisoire, documenté dans la tâche (artefacts en tâche #064). Spec §5.1 attend `best_iteration`, `best_score`, `n_features_in` mais c'est hors scope de cette tâche. ✅
6. **Type safety** : `config.models.xgboost` et `config.reproducibility.global_seed` sont lus depuis Pydantic v2 qui garantit les types. ✅
7. **Edge cases** : `X_train` avec N=0 n'est pas bloqué explicitement, mais XGBoost le gère en interne (pas un bug, comportement délégué au framework). ✅
8. **Return contract** : retourne toujours un `dict` (vide). ✅
9. **Resource cleanup** : pas de fichiers ouverts, pas de ressources à libérer. ✅
10. **Cohérence doc/code** : la docstring décrit correctement le flux (validation → flatten → instantiate → fit). ✅

RAS après lecture complète du diff (68 lignes d'ajout net).

#### `tests/test_xgboost_model.py` (248 lignes ajoutées, 33 supprimées)

**Observations :**

1. **Suppression du test `test_fit_raises_not_implemented`** : logique — `fit()` n'est plus un stub. ✅
2. **Suppression du test `test_fit_with_optional_params_raises_not_implemented`** : idem. ✅
3. **Données synthétiques** : `_RNG_FIT = np.random.default_rng(62)` — seed fixée, modern API. Tailles (N=100, L=10, F=5) conformes au critère d'acceptation. ✅
4. **`_make_xgb_model()`** : factory directe sans registry → pas de dépendance au side-effect reload. ✅
5. **14 tests fit()** couvrant : shape errors (2D, 1D pour X_train ; 2D pour X_val), shape mismatch (train, val), dtype errors (float64 pour X_train, X_val), nominal (no error, isinstance XGBRegressor, returns dict), config-driven (7 hyperparams, random_state, imposed params, early_stopping). ✅
6. **Tous les tests utilisent `default_config`** de `conftest.py` (pas de fixture dupliquée). ✅
7. **Tous les tests utilisent `tmp_path`** (pas de chemin hardcodé). ✅
8. **`pytest.raises` avec `match`** pour chaque validation → vérifie le bon message d'erreur. ✅
9. **Données déterministes** : pas d'aléa non seedé. ✅

RAS après lecture complète du diff (248 lignes d'ajout).

### B3. Vérification des tests — Critères d'acceptation

| Critère d'acceptation | Test correspondant | Preuve |
|---|---|---|
| `fit()` sans erreur sur (N=100, L=10, F=5) | `test_fit_nominal_no_error` | L303 : données `_N_FIT=100, _L_FIT=10, _F_FIT=5` |
| `self._model` est `XGBRegressor` après `fit()` | `test_fit_model_is_xgbregressor` | L316 : `assert isinstance(model._model, xgb.XGBRegressor)` |
| `ValueError` si `X_train.ndim != 3` | `test_fit_raises_valueerror_x_train_not_3d` + `test_fit_raises_valueerror_x_train_1d` | L200 (2D), L213 (1D) |
| `ValueError` si `X_val.ndim != 3` | `test_fit_raises_valueerror_x_val_not_3d` | L225 |
| `ValueError` si `X_train.shape[0] != y_train.shape[0]` | `test_fit_raises_valueerror_x_train_y_train_shape_mismatch` | L237 : `y_bad = _Y_TRAIN_FIT[:50]` |
| `ValueError` si `X_val.shape[0] != y_val.shape[0]` | `test_fit_raises_valueerror_x_val_y_val_shape_mismatch` | L252 : `y_val_bad = _Y_VAL_FIT[:10]` |
| `TypeError` si `X_train.dtype != float32` | `test_fit_raises_typeerror_x_train_not_float32` | L266 : `x_f64 = ...astype(np.float64)` |
| `TypeError` si `X_val.dtype != float32` | `test_fit_raises_typeerror_x_val_not_float32` | L279 |
| 7 hyperparamètres config-driven | `test_fit_hyperparams_from_config` | L338-L344 : assertions une par une vs `default_config.models.xgboost.*` |
| `random_state` = `global_seed` | `test_fit_random_state_from_config` | L356 |
| Paramètres imposés | `test_fit_imposed_params` | L367-L370 : `objective`, `tree_method`, `booster`, `verbosity` |
| Tests nominaux + erreurs + bords | ✅ | 8 tests erreur, 3 tests nominaux, 3 tests config-driven |
| pytest GREEN | ✅ | `26 passed in 0.97s` |
| ruff clean | ✅ | `All checks passed!` |

### B4. Audit — Règles non négociables

#### B4a. Strict code (no fallbacks) — §R1
- ✅ Aucun fallback silencieux (scan B1 : 0 occurrences).
- ✅ Aucun except trop large (scan B1 : 0 occurrences).
- ✅ Validation explicite avec `raise ValueError` / `raise TypeError` pour toutes les entrées.

#### B4a-bis. Defensive indexing / slicing — §R10
- ✅ Pas d'indexing/slicing complexe. L'accès `X_train.shape[0]`, `X_train.shape[2]` est safe sur arrays 3D (validés avant).

#### B4b. Config-driven — §R2
- ✅ Les 7 hyperparamètres sont lus depuis `config.models.xgboost.*` (diff L87-L93).
- ✅ `random_state` depuis `config.reproducibility.global_seed` (diff L97).
- ✅ `early_stopping_rounds` depuis `config.training.early_stopping_patience` (diff L98).
- ✅ Aucune valeur magique pour les hyperparamètres configurables.
- ✅ Les 4 valeurs imposées (`objective`, `tree_method`, `booster`, `verbosity`) sont bien imposées par la spec §4.4 (non configurables).

#### B4c. Anti-fuite — §R3
- ✅ `eval_set` contient uniquement les données val, pas de test.
- ✅ Pas de `.shift(-` (scan B1 : 0 occurrences).
- ✅ L'adapter `flatten_seq_to_tab` est une fonction pure (pas d'état, pas de leak).

#### B4d. Reproductibilité — §R4
- ✅ `random_state = config.reproducibility.global_seed`.
- ✅ Pas de legacy random API (scan B1 : 0 occurrences).
- ✅ Seeds fixées dans les tests (`np.random.default_rng(62)`).

#### B4e. Float conventions — §R5
- ✅ `X_train` et `X_val` validés float32.
- ✅ `flatten_seq_to_tab` préserve le dtype (spec §3.3, code vérifié dans dataset.py).

#### B4f. Anti-patterns Python — §R6
- ✅ Aucun mutable default (scan B1 : 0 occurrences).
- ✅ Aucun `open()` sans context manager (scan B1 : 0 occurrences).
- ✅ Aucune comparaison booléenne par identité (scan B1 : 0 occurrences).
- ✅ f-strings utilisées pour les messages d'erreur.

### B5. Qualité du code — §R7
- ✅ snake_case cohérent (sauf `X_train`, `X_val`, `X` imposés par ABC — noqa N803 justifié).
- ✅ Pas de code mort, commenté, TODO, FIXME (scan B1 : 0 occurrences).
- ✅ Pas de `print()` (scan B1 : 0 occurrences).
- ✅ Imports propres : `xgboost as xgb` + `flatten_seq_to_tab`, pas d'import inutilisé.
- ✅ Pas de fixture dupliquée (tests utilisent `default_config` et `tmp_path` de conftest/pytest).
- ✅ Tests utilisent `importlib.reload` pour le registre (pattern correct).

### B5-bis. Bonnes pratiques métier — §R9
- ✅ Pas de boucle Python sur array (scan B1 : 0 occurrences).
- ✅ Séparation des responsabilités : `fit()` délègue l'aplatissement à l'adapter, l'instanciation et le training au framework XGBoost.

### B6. Cohérence avec les specs

| Point | Verdict | Preuve |
|---|---|---|
| Conforme à spec §5.1 (procédure fit) | ✅ | Ordre : validation → aplatissement → instanciation → fit → return. Correspond au pseudo-code §5.1. |
| Conforme à spec §4.1 (framework) | ✅ | `xgboost.XGBRegressor`, `tree_method="hist"`, `booster="gbtree"`. |
| Conforme à spec §4.2 (objective) | ✅ | `objective="reg:squarederror"` — imposé, non configurable. |
| Conforme à spec §4.3-§4.4 (7 hyperparamètres) | ✅ | `max_depth`, `n_estimators`, `learning_rate`, `subsample`, `colsample_bytree`, `reg_alpha`, `reg_lambda` — tous depuis config. |
| Conforme à spec §5.2 (early stopping) | ✅ | `early_stopping_rounds = config.training.early_stopping_patience`. |
| Conforme au plan WS-XGB-3.1 | ✅ | Toutes les étapes du plan sont implémentées. |
| Pas d'exigence inventée | ✅ | Tout est tracé vers la spec ou le plan. |

### B7. Cohérence intermodule — §R8

| Point | Verdict | Preuve |
|---|---|---|
| Signature `fit()` conforme à `BaseModel` ABC | ✅ | Même signature exacte (vérifié `base.py` L183-L228). |
| `flatten_seq_to_tab` appelé correctement | ✅ | `(X_train, feature_names)` → retourne `(x_tab, column_names)` — conforme à `dataset.py` L162. |
| `config.models.xgboost.*` existe dans Pydantic model | ✅ | Task #061 a validé `XGBoostModelConfig` — config keys correspondent. |
| Pas de dépendance non mergée | ✅ | Imports : `xgboost`, `flatten_seq_to_tab`, `BaseModel`, `register_model` — tous disponibles sur `Max6000i1`. |

---

## Remarques

1. [WARNING] Pas de validation `y_train.dtype` / `y_val.dtype` float32
   - Fichier : `ai_trading/models/xgboost.py`
   - Ligne(s) : après L78 (après les checks dtype de X)
   - Contexte : La section « Règles attendues » de la tâche mentionne « y_train, y_val en float32 » et la spec §2.2 indique dtype float32 pour y. Cependant, les critères d'acceptation de la tâche ne listent PAS de validation y dtype. L'implémentation est conforme aux critères tels que définis, mais la validation est incomplète par rapport à la règle §R1 (validation aux frontières). XGBoost gère la conversion silencieusement, mais le principe strict code voudrait un `raise TypeError` pour y non-float32.
   - Suggestion : Ajouter la validation y dtype dans une tâche ultérieure ou enrichir les critères d'acceptation.

2. [MINEUR] Pas de test boundary N=0 / N=1
   - Fichier : `tests/test_xgboost_model.py`
   - Ligne(s) : classe `TestXGBoostRegModelFit`
   - Contexte : Le boundary fuzzing mental (§B3) recommande de tester `param=0` et `param=1`. Aucun test ne vérifie le comportement avec N_train=0 ou N_train=1 échantillons. Le comportement est délégué à XGBoost (qui échoue ou s'exécute selon les cas), donc pas de bug, mais la couverture boundary est incomplète.
   - Suggestion : Ajouter un test avec N=1 minimal dans une tâche ultérieure pour documenter le comportement.

---

## Résumé

Implémentation propre et conforme suivant rigoureusement le processus TDD (RED puis GREEN, 2 commits, branche dédiée). Le code est strictement config-driven, sans fallback, sans look-ahead, avec validation explicite des entrées. Les 14 critères d'acceptation sont couverts par 14+ tests vérifiables. Deux observations mineures (y dtype non validé, pas de test N=0/1) ne bloquent pas l'approbation car elles sont hors scope des critères définis pour cette tâche.
