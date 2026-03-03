# Revue PR — [WS-XGB-4] #065 — Prédiction XGBoost et cast float32

Branche : `task/065-xgb-predict`
Tâche : `docs/tasks/MX-2/065__ws_xgb4_predict.md`
Date : 2026-03-03
Itération : v2 (post-correction des 2 MINEURS de la v1)

## Verdict global : ✅ CLEAN

## Résumé

Implémentation de `predict()` dans `XGBoostRegModel` : validation stricte (RuntimeError si non fitté, ValueError si ndim ≠ 3, TypeError si dtype ≠ float32), aplatissement via `flatten_seq_to_tab`, prédiction et cast float32. Le commit FIX (`476e5d7`) corrige les 2 items MINEURS de la revue v1 : initialisation de `_feature_names` dans `__init__()` et ajout du test boundary N=0. Le code est conforme à la spec §6.1/§6.2 et au plan WS-XGB-4.1. 0 item identifié.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/065-xgb-predict` | ✅ | `git branch --show-current` → `task/065-xgb-predict` |
| Commit RED présent | ✅ | `6b02044` — `[WS-XGB-4] #065 RED: tests predict XGBoostRegModel` |
| Commit RED = tests uniquement | ✅ | `git show --stat 6b02044` → `tests/test_xgboost_model.py | 149 +++` (1 fichier) |
| Commit GREEN présent | ✅ | `48fb940` — `[WS-XGB-4] #065 GREEN: predict XGBoostRegModel` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 48fb940` → `ai_trading/models/xgboost.py`, `docs/tasks/MX-2/065__*.md`, `tests/test_xgboost_model.py` (3 fichiers) |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline Max6000i1...HEAD` → 3 commits : RED → GREEN → FIX (post-review v1, acceptable) |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Première ligne : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (11/11) | Tous `[x]` |
| Checklist cochée | ✅ (8/9) | 8 cochés ; 1 non coché = « Pull Request ouverte » (attendu — la PR n'est pas encore ouverte) |

#### Mapping critères d'acceptation → preuves

| # | Critère | Preuve code | Preuve test |
|---|---|---|---|
| 1 | shape (N,) dtype float32 | `xgboost.py` L165 `return y_hat.astype(np.float32)` | `test_predict_output_shape_n`, `test_predict_output_dtype_float32` |
| 2 | RuntimeError si pas fitté | `xgboost.py` L153-154 | `test_predict_raises_runtime_error_if_not_fitted` |
| 3 | ValueError si ndim ≠ 3 | `xgboost.py` L155-156 | `test_predict_raises_valueerror_if_x_2d`, `_1d`, `_4d` |
| 4 | TypeError si dtype ≠ float32 | `xgboost.py` L157-158 | `test_predict_raises_typeerror_if_x_float64`, `_int32` |
| 5 | Valeurs continues non bornées | `xgboost.py` L164 — appel direct `self._model.predict()` (XGBoost regression) | `test_predict_values_are_continuous` |
| 6 | Déterminisme | Pas d'état mutable dans predict | `test_predict_deterministic_same_result` |
| 7 | meta/ohlcv ignorés | `xgboost.py` L143-144 — paramètres acceptés, non utilisés | `test_predict_meta_ignored`, `_ohlcv_ignored`, `_meta_and_ohlcv_together` |
| 8 | Cast float64→float32 | `xgboost.py` L165 `.astype(np.float32)` | `test_predict_output_dtype_float32` |
| 9 | Tests nominaux + erreurs + bords | — | 17 tests dans `TestXGBoostRegModelPredict` |
| 10 | Suite verte | — | 65 passed, 0 failed |
| 11 | ruff clean | — | `All checks passed!` |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_xgboost_model.py -v --tb=short` | **65 passed**, 0 failed (2.13s) |
| `ruff check ai_trading/models/xgboost.py tests/test_xgboost_model.py` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux (`or []`, `or {}`, `or ""`, `if … else`) | `grep_search` xgboost.py | 0 occurrences (grep exécuté) |
| §R1 Except trop large (`except:`, `except Exception:`) | `grep_search` xgboost.py | 0 occurrences (grep exécuté) |
| §R7 Suppressions lint (`noqa`) | `grep_search` xgboost.py + test | 4 matches : 3× `N803` dans xgboost.py L33, L35, L143 (params `X_train`, `X_val`, `X` — imposés par spec/ABC), 1× `F811, F401` dans test L163 (import side-effect, pré-existant). Tous justifiés — inévitables. |
| §R7 per-file-ignores | `grep_search` pyproject.toml | `xgboost.py` absent des per-file-ignores (utilise inline `noqa` — acceptable). |
| §R7 Print résiduel (`print(`) | `grep_search` xgboost.py | 0 occurrences (grep exécuté) |
| §R3 Shift négatif (`.shift(-`) | `grep_search` xgboost.py | 0 occurrences (grep exécuté) |
| §R4 Legacy random API (`np.random.seed`, `randn`, `RandomState`, `random.seed`) | `grep_search` xgboost.py + test | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME/HACK/XXX | `grep_search` xgboost.py + test | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés (`/tmp`, `C:\`) | `grep_search` test | 0 occurrences (grep exécuté) |
| §R7 Imports absolus dans `__init__.py` | `grep_search` models/__init__.py | 1 match L3 — pré-existant, hors scope PR (`git diff` confirme : `__init__.py` non modifié) |
| §R7 Registration manuelle (`register_model`) | `grep_search` test | 1 match L59 — docstring commentaire, pas d'appel manuel. Faux positif. |
| §R6 Mutable defaults (`def …=[]`, `def …={}`) | `grep_search` xgboost.py | 0 occurrences (grep exécuté) |
| §R6 `open()` sans context manager | `grep_search` xgboost.py | 0 occurrences (grep exécuté) |
| §R6 Bool identity (`is True`, `is False`, `is np.bool_`) | `grep_search` xgboost.py + test | 0 occurrences (grep exécuté) |
| §R6 isfinite validation | `grep_search` xgboost.py | 0 occurrences — N/A pour predict (pas de validation de bornes numériques sur entrées float ; les données arrivent déjà validées par le pipeline amont) |
| §R9 Boucle Python sur array (`for … in range`) | `grep_search` xgboost.py | 1 match L105 : `[f"f{i}" for i in range(n_features)]` — list comprehension pour générer des noms de features. N'opère pas sur un array numpy, pas un hot path. Faux positif. |
| §R7 Fixture dupliquée (`load_config…configs/`) | `grep_search` test | 0 occurrences (grep exécuté) |
| §R6 Dict collision silencieuse | `grep_search` xgboost.py | 0 occurrences (grep exécuté) |
| §R9 Appels numpy dans compréhension | `grep_search` xgboost.py | 0 occurrences (grep exécuté) |

### Annotations par fichier (B2)

#### `ai_trading/models/xgboost.py`

Diff analysé : 3 hunks, ~25 lignes modifiées vs Max6000i1.

- **L29** `self._feature_names: list[str] | None = None` : Initialisation propre dans `__init__()` avec type annotation. Correction du MINEUR #1 de la v1. ✅ RAS.

- **L106** `self._feature_names = feature_names` : Stockage des feature_names dans `fit()` pour réutilisation dans `predict()`. Assignation avant utilisation dans `flatten_seq_to_tab`. ✅ RAS.

- **L148-165** (bloc predict complet) :
  - **L148-151** : Docstring conforme, référence `#065`.
  - **L153-154** : Guard `self._model is None` → `RuntimeError`. Conforme spec §6.1 + plan WS-XGB-4.1.
  - **L155-156** : `X.ndim != 3` → `ValueError`. Strict, pas de fallback.
  - **L157-158** : `X.dtype != np.float32` → `TypeError`. Strict, pas de fallback.
  - **L159-160** : Guard `X.shape[0] == 0` → retour `np.empty((0,), dtype=np.float32)`. Correction du MINEUR #2 de la v1. Comportement sûr — évite d'appeler XGBoost sur un array vide. Shape `(0,)` et dtype `float32` sont cohérents avec le contrat de retour.
  - **L161** : `x_tab, _ = flatten_seq_to_tab(X, self._feature_names)` — Appel conforme à la signature de `flatten_seq_to_tab(x_seq, feature_names)`. Si F(predict) ≠ F(fit), la validation dans `flatten_seq_to_tab` lèvera `ValueError` (pas de fallback silencieux).
  - **L164** : `y_hat = self._model.predict(x_tab)` — Appel XGBoost standard, retourne float64.
  - **L165** : `return y_hat.astype(np.float32)` — Cast explicite conforme spec §6.2.

- **Ordre de validation** : not-fitted → ndim → dtype → N=0 → flatten → predict → cast. L'ordre est logique : les checks les moins coûteux d'abord, la logique métier ensuite. ✅ RAS.

- **Cohérence variable naming** : `x_tab` (local, snake_case) vs `X` (paramètre imposé par ABC, `noqa: N803`). Cohérent avec le style de `fit()`. ✅ RAS.

RAS global après lecture complète du diff (25 lignes modified).

#### `tests/test_xgboost_model.py`

Diff analysé : suppressions (2 tests stub predict NotImplementedError) + ajouts (~160 lignes).

- **Suppressions L122-127, L140-146 (ancienne numérotation)** : Retrait des tests `test_predict_raises_not_implemented` et `test_predict_with_optional_params_raises_not_implemented` (remplacés par les vrais tests predict). Correct — les stubs ne sont plus pertinents.

- **L813-822** (`_RNG_PRED`, module-level data) : Données synthétiques avec `np.random.default_rng(65)`. Seed fixée, pas de dépendance réseau. Shapes (80, 10, 5), (25, 10, 5), (15, 10, 5) — cohérentes (même L, F). ✅

- **L825-837** (fixture `fitted_model`) : Utilise `default_config` (fixture conftest.py) et `tmp_path`. Pas de fixture dupliquée. Appel `model.fit(...)` avec tous les paramètres requis. ✅

- **L845-853** (`test_predict_raises_runtime_error_if_not_fitted`) : Crée un modèle non-fitté et vérifie `RuntimeError` avec `match="Model not fitted"`. ✅

- **L856-874** (tests ValueError 2D/1D/4D) : Trois dimensions non-3D testées. Bonne couverture des cas d'erreur ndim. ✅

- **L878-890** (tests TypeError float64/int32) : Deux dtypes incorrects testés avec `match="float32"`. ✅

- **L894-914** (tests nominaux shape/dtype/continuous/finite) :
  - `test_predict_returns_ndarray` : vérifie `isinstance(y_hat, np.ndarray)`.
  - `test_predict_output_shape_n` : vérifie `y_hat.shape == (N,)`.
  - `test_predict_output_dtype_float32` : vérifie `y_hat.dtype == np.float32`.
  - `test_predict_values_are_continuous` : vérifie que toutes les valeurs ne sont pas dans {0, 1}.
  - `test_predict_values_are_finite` : vérifie `np.all(np.isfinite(y_hat))`.
  ✅ Tous conformes.

- **L918-923** (`test_predict_deterministic_same_result`) : `assert_array_equal` sur deux appels identiques. Preuve correcte de déterminisme. ✅

- **L927-945** (meta/ohlcv ignorés) : 3 tests distincts (meta seul, ohlcv seul, les deux ensemble). Preuve `assert_array_equal` — résultat identique au cas sans. ✅

- **L949-956** (`test_predict_single_sample` — N=1) : Boundary N=1 testé avec seed séparée (`default_rng(6501)`). Vérifie shape `(1,)` et dtype. ✅

- **L960-966** (`test_predict_boundary_n_zero` — N=0) : Boundary N=0 testé. Correction du MINEUR #2 de la v1. Vérifie shape `(0,)` et dtype `float32`. ✅

RAS global après lecture complète du diff (~160 lignes added).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | Tests dans `tests/test_xgboost_model.py`, docstrings contiennent `#065` |
| Couverture critères d'acceptation | ✅ | 11/11 critères mappés (voir tableau Phase A) |
| Cas nominaux + erreurs + bords | ✅ | 17 tests : 6 erreurs, 7 nominaux, 2 boundary, 1 déterminisme, 3 meta/ohlcv ignored (total confirmé par nombre de méthodes `test_` dans `TestXGBoostRegModelPredict`) |
| Boundary fuzzing | ✅ | N=1 ✅, N=0 ✅ (ajouté en FIX) |
| Boundary — taux/proportions | ✅ N/A | `predict()` ne prend pas de paramètre taux/proportion |
| Déterministes | ✅ | Seeds fixées : `default_rng(65)`, `default_rng(6501)` |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` ; utilise `tmp_path` pytest |
| Tests registre réalistes | ✅ | `_reload_xgboost_module()` utilise `importlib.reload` (pré-existant, vérifié L55-65) |
| Contrat ABC complet | ✅ | Signature `predict(X, meta, ohlcv)` conforme à `BaseModel.predict` (L225-231 base.py) |
| Données synthétiques | ✅ | Toutes les données sont `np.random.default_rng(seed).standard_normal(...)` |
| Pas de tests désactivés | ✅ | Aucun `@pytest.mark.skip` ou `xfail` |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. Validation explicite + raise (RuntimeError, ValueError, TypeError). Le guard N=0 retourne un résultat explicite (pas un fallback silencieux). |
| §R10 Defensive indexing | ✅ | Pas d'indexation directe dans predict — délègue à `flatten_seq_to_tab` qui valide les dimensions. Le guard N=0 évite le edge case d'array vide dans XGBoost. |
| §R2 Config-driven | ✅ | Paramètres predict non config-dépendants (légitime — predict ne lit pas de config, c'est un appel purement fonctionnel). |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. predict() est purement forward (entrées → sorties, pas d'accès à des données futures). |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. predict() est déterministe (pas d'aléa interne). Tests : seeds fixées dans le fichier test. |
| §R5 Float conventions | ✅ | Entrée float32 (validée L157), sortie float32 (cast explicite L165). Conforme. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open(), 0 bool identity, 0 dict collision. Pas de désérialisation. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `x_tab`, `y_hat`, `_feature_names` — tout snake_case (sauf params spec `X` avec `noqa: N803`) |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO. Stubs save/load pré-existants (hors scope). |
| Imports propres / relatifs | ✅ | Imports dans xgboost.py : stdlib (Path, Any) → third-party (numpy, xgboost) → local (dataset, base). Pas de nouvel import ajouté par cette PR. |
| DRY | ✅ | Pas de duplication de logique entre fit() et predict(). L'aplatissement est délégué à `flatten_seq_to_tab`. |
| Suppressions lint justifiées | ✅ | 3× `noqa: N803` — params `X_train`, `X_val`, `X` imposés par spec/ABC (inévitable, pas renommables). |
| `__init__.py` à jour | ✅ | `ai_trading/models/__init__.py` importe déjà `xgboost` (L6-7, pré-existant). Pas de modification nécessaire. |
| Fichiers générés | ✅ | Aucun fichier généré dans la PR. |
| Variables mortes | ✅ | Toutes les variables assignées sont utilisées. `_` dans `x_tab, _ = flatten_seq_to_tab(...)` est une convention Python standard pour les valeurs ignorées. |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | predict() retourne des log-returns prédits — conforme spec §6.2. Pas de concept financier supplémentaire dans predict. |
| Nommage métier cohérent | ✅ | `y_hat` pour prédictions, `X` pour features — conventions standard ML/trading. |
| Séparation des responsabilités | ✅ | predict() fait uniquement de l'inférence. Aplatissement délégué à l'adapter. Pas de mélange de responsabilités. |
| Invariants de domaine | ✅ | Les prédictions sont des log-returns continus (non bornés, non arrondi). Conforme §6.2. |
| Cohérence des unités/échelles | ✅ | Entrée et sortie en float32, log-returns. Pas de mélange d'échelles. |
| Patterns de calcul financier | ✅ | Utilise XGBoost predict (optimisé en C), pas de boucle Python sur les données. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Preuve |
|---|---|---|
| Spec §6.1 — procédure predict | ✅ | 4 étapes spec (flatten → predict → cast → return) implémentées L161-165. Guard supplémentaire N=0 (L159-160) non spécifié mais défensif et correct. |
| Spec §6.2 — sortie et dtype | ✅ | Shape (N,), float32, log-returns continus. Conforme. |
| Spec §2.2 — meta/ohlcv ignorés | ✅ | Paramètres acceptés (`meta=None, ohlcv=None`) et non utilisés dans le corps. |
| Plan WS-XGB-4.1 | ✅ | Critères du plan tous couverts : RuntimeError not fitted, ValueError ndim, TypeError dtype, shape (N,) float32, déterminisme, meta/ohlcv ignorés. |
| Formules doc vs code | ✅ | Pas de formule mathématique spécifique dans predict — aplatissement délégué à l'adapter (conforme §3.1). Le pseudocode spec §6.1 montre `flatten_seq_to_tab(X)` — l'implémentation passe `(X, self._feature_names)` car la signature réelle de la fonction l'exige. Pas d'écart sémantique. |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signature vs BaseModel.predict | ✅ | `predict(self, X, meta=None, ohlcv=None) -> np.ndarray` — identique à l'ABC (base.py L225-231). |
| Signature vs DummyModel.predict | ✅ | Même interface. Vérifié via grep : `dummy.py` a la même signature. |
| Forwarding kwargs | ✅ | `meta` et `ohlcv` sont ignorés intentionnellement (spec §2.2). Pas de perte de contexte — XGBoost ne les utilise pas. |
| flatten_seq_to_tab signature | ✅ | Appel `flatten_seq_to_tab(X, self._feature_names)` conforme à la signature `(x_seq: np.ndarray, feature_names: list[str])` (dataset.py L162-164). |
| Feature names cohérence | ✅ | `_feature_names` générés dans `fit()` L105 (`[f"f{i}" for i in range(n_features)]`) et réutilisés dans `predict()` L161. Si F change entre fit et predict, `flatten_seq_to_tab` lèvera `ValueError`. |
| Dtypes cohérents | ✅ | Entrée float32, sortie float32 — cohérent avec le contrat ABC et le pipeline. |
| Imports croisés | ✅ | `flatten_seq_to_tab` importé depuis `ai_trading.data.dataset` — module existant sur Max6000i1. `BaseModel`, `register_model` depuis `ai_trading.models.base` — existants. |
| Defaults cohérents | ✅ | `meta=None, ohlcv=None` — identique à l'ABC. |

---

## Vérification des corrections v1

| Item v1 | Correction | Vérifié |
|---|---|---|
| MINEUR #1 : `_feature_names` non initialisé dans `__init__()` | `self._feature_names: list[str] \| None = None` ajouté L29 | ✅ (commit `476e5d7`) |
| MINEUR #2 : Boundary test N=0 manquant | `test_predict_boundary_n_zero` ajouté + guard `X.shape[0] == 0` dans predict L159-160 | ✅ (commit `476e5d7`) |

---

## Remarques

Aucune.

---

## Actions requises

Aucune.
