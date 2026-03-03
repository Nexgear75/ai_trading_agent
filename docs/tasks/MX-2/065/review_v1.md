# Revue PR — [WS-XGB-4] #065 — Prédiction XGBoost et cast float32

Branche : `task/065-xgb-predict`
Tâche : `docs/tasks/MX-2/065__ws_xgb4_predict.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation de `predict()` dans `XGBoostRegModel` : validation stricte (RuntimeError si non fitté, ValueError si ndim ≠ 3, TypeError si dtype ≠ float32), aplatissement via `flatten_seq_to_tab`, prédiction et cast float32. Le code est propre, conforme à la spec §6.1/§6.2, et les 16 tests predict couvrent bien les critères d'acceptation. Deux items MINEUR empêchent le verdict CLEAN.

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
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Première ligne : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (11/11) | Tous `[x]` |
| Checklist cochée | ✅ (8/9) | 8 cochés ; 1 non coché = « Pull Request ouverte » (attendu — la PR n'est pas encore ouverte) |

#### Mapping critères d'acceptation → preuves

| # | Critère | Preuve code | Preuve test |
|---|---|---|---|
| 1 | shape (N,) dtype float32 | `xgboost.py` L157 `return y_hat.astype(np.float32)` | `test_predict_output_shape_n`, `test_predict_output_dtype_float32` |
| 2 | RuntimeError si pas fitté | `xgboost.py` L148-149 | `test_predict_raises_runtime_error_if_not_fitted` |
| 3 | ValueError si ndim ≠ 3 | `xgboost.py` L150-151 | `test_predict_raises_valueerror_if_x_2d`, `_1d`, `_4d` |
| 4 | TypeError si dtype ≠ float32 | `xgboost.py` L152-153 | `test_predict_raises_typeerror_if_x_float64`, `_int32` |
| 5 | Valeurs continues non bornées | `xgboost.py` L156 — appel direct `self._model.predict()` (XGBoost regression) | `test_predict_values_are_continuous` |
| 6 | Déterminisme | Pas d'état mutable dans predict | `test_predict_deterministic_same_result` |
| 7 | meta/ohlcv ignorés | `xgboost.py` L143-144 — paramètres acceptés, non utilisés | `test_predict_meta_ignored`, `_ohlcv_ignored`, `_meta_and_ohlcv_together` |
| 8 | Cast float64→float32 | `xgboost.py` L157 `.astype(np.float32)` | `test_predict_output_dtype_float32` |
| 9 | Tests nominaux + erreurs + bords | — | 16 tests dans `TestXGBoostRegModelPredict` |
| 10 | Suite verte | — | 64 passed, 0 failed |
| 11 | ruff clean | — | `All checks passed!` |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_xgboost_model.py -v --tb=short` | **64 passed**, 0 failed (1.96s) |
| `ruff check ai_trading/models/xgboost.py tests/test_xgboost_model.py` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep 'or []\|or {}...' xgboost.py` | 0 occurrences (grep exécuté) |
| §R1 Except trop large | `grep 'except:$\|except Exception:' xgboost.py` | 0 occurrences (grep exécuté) |
| §R7 Suppressions lint (`noqa`) | `grep 'noqa' xgboost.py tests/test_xgboost_model.py` | 4 matches : 3× `N803` dans xgboost.py (params `X_train`, `X_val`, `X` — imposés par spec/ABC), 1× `F811, F401` dans test (import side-effect, pré-existant). Tous justifiés. |
| §R7 Print résiduel | `grep 'print(' xgboost.py` | 0 occurrences (grep exécuté) |
| §R3 Shift négatif | `grep '.shift(-' xgboost.py` | 0 occurrences (grep exécuté) |
| §R4 Legacy random API | `grep 'np.random.seed\|...' xgboost.py tests/` | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX' xgboost.py tests/` | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés `/tmp` | `grep '/tmp\|C:\\' tests/` | 0 occurrences (grep exécuté) |
| §R7 Imports absolus `__init__` | `grep 'from ai_trading\.' __init__.py` | 1 match `ai_trading/models/__init__.py:3` — **pré-existant**, hors scope PR |
| §R7 Registration manuelle tests | `grep 'register_model' tests/` | 1 match — commentaire docstring, pas d'appel manuel. Faux positif. |
| §R6 Mutable defaults | `grep 'def .*=[]' xgboost.py tests/` | 0 occurrences (grep exécuté) |
| §R6 open() sans context manager | `grep 'open(' xgboost.py` | 0 occurrences (grep exécuté) |
| §R6 Bool identity | `grep 'is True\|is False' xgboost.py tests/` | 0 occurrences (grep exécuté) |
| §R6 isfinite validation | `grep 'isfinite' xgboost.py` | 0 occurrences — N/A pour predict (pas de validation de bornes numériques sur les entrées float) |
| §R9 Boucle Python sur array | `grep 'for .* in range' xgboost.py` | 0 occurrences (grep exécuté) |
| §R7 Fixture dupliquée | `grep 'load_config.*configs/' tests/` | 0 occurrences (grep exécuté) |
| §R6 Dict collision | `grep '\[.*\] = ' xgboost.py` | 0 occurrences (grep exécuté) |
| §R7 per-file-ignores | `grep 'per-file-ignores' pyproject.toml` | `xgboost.py` absent des per-file-ignores (utilise inline `noqa` — acceptable) |

### Annotations par fichier (B2)

#### `ai_trading/models/xgboost.py`

Diff analysé : 2 hunks, ~20 lignes modifiées.

- **L28** `self._model = None` : `__init__` initialise `self._model` mais pas `self._feature_names`. L'attribut `_feature_names` est créé pour la première fois dans `fit()` (L105). En pratique, le guard `self._model is None` dans `predict()` (L148) empêche l'accès à `_feature_names` avant `fit()`, mais l'absence d'initialisation dans `__init__` est une irrégularité pour les type-checkers et la lisibilité.
  Sévérité : **MINEUR**
  Suggestion : Ajouter `self._feature_names: list[str] | None = None` dans `__init__()`.

- **L148-157** (predict body) : Implémentation conforme à la spec §6.1. Vérification not-fitted → ndim → dtype → flatten → predict → cast. L'ordre de validation est logique et cohérent avec `fit()`. RAS.

- **L155** `x_tab, _ = flatten_seq_to_tab(X, self._feature_names)` : Si F(predict) ≠ F(fit), `flatten_seq_to_tab` lèvera `ValueError` (validation existante dans l'adapter). C'est un comportement correct (pas de fallback silencieux).

- **L156** `y_hat = self._model.predict(x_tab)` : XGBoost retourne float64. Cast explicite en L157. Conforme.

- **L157** `return y_hat.astype(np.float32)` : Cast explicite float64 → float32 conforme à la spec §6.2 et §3.3.

#### `tests/test_xgboost_model.py`

Diff analysé : suppressions (2 tests stub predict NotImplementedError) + ajouts (~150 lignes).

- **Suppressions L122-127, L140-146** : Retrait des tests `test_predict_raises_not_implemented` et `test_predict_with_optional_params_raises_not_implemented` (remplacés par les vrais tests predict). Correct.

- **L817-826** (`_RNG_PRED`, module-level data) : Données synthétiques avec `np.random.default_rng(65)`. Seed fixée, pas de dépendance réseau. ✅

- **L829-841** (fixture `fitted_model`) : Utilise `default_config` (fixture conftest.py) et `tmp_path`. Pas de fixture dupliquée. ✅

- **L849-857** (`test_predict_raises_runtime_error_if_not_fitted`) : Crée un modèle non-fitté et vérifie RuntimeError. ✅

- **L860-878** (tests ValueError 2D/1D/4D) : Trois dimensions non-3D testées. Bonne couverture des cas d'erreur ndim. ✅

- **L882-894** (tests TypeError float64/int32) : Deux dtypes incorrects testés. ✅

- **L898-918** (tests nominaux shape/dtype/continuous/finite) : Couvrent shape (N,), dtype float32, valeurs continues et finies. ✅

- **L922-927** (déterminisme) : `assert_array_equal` sur deux appels identiques. Preuve correcte. ✅

- **L931-949** (meta/ohlcv ignorés) : 3 tests distincts (meta seul, ohlcv seul, les deux ensemble). Preuve `assert_array_equal` — résultat identique. ✅

- **L953-960** (`test_predict_single_sample` — N=1) : Boundary N=1 testé. ✅

- **Boundary N=0 manquant** : Aucun test pour `predict(X=np.empty((0, L, F), dtype=np.float32))`. Per §B3 boundary fuzzing, N=0 devrait être testé pour predict (retourne array vide ? ou erreur ?). Le code actuel retournerait un array vide `(0,)` float32 (comportement correct via flatten + XGBoost predict), mais l'absence de test laisse ce comportement non documenté.
  Sévérité : **MINEUR**
  Suggestion : Ajouter `test_predict_boundary_n_zero` qui vérifie que predict retourne un array shape `(0,)` dtype float32 quand X est `(0, L, F)`.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | Tests dans `tests/test_xgboost_model.py`, docstrings contiennent `#065` |
| Couverture critères d'acceptation | ✅ | 11/11 critères mappés (voir tableau Phase A) |
| Cas nominaux + erreurs + bords | ✅ | 16 tests : 6 erreurs, 7 nominaux, 2 boundary, 1 déterminisme |
| Boundary fuzzing | ⚠️ | N=1 ✅, N=0 absent (voir MINEUR #2) |
| Déterministes | ✅ | Seeds fixées : `default_rng(65)`, `default_rng(6501)` |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` ; utilise `tmp_path` pytest |
| Tests registre réalistes | ✅ | `_reload_xgboost_module()` utilise `importlib.reload` (pré-existant) |
| Contrat ABC complet | ✅ | Signature predict(X, meta, ohlcv) conforme à `BaseModel.predict` |
| Données synthétiques | ✅ | Toutes les données sont `np.random.default_rng(seed).standard_normal(...)` |
| Pas de tests désactivés | ✅ | Aucun `@pytest.mark.skip` ou `xfail` |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. Validation explicite + raise (RuntimeError, ValueError, TypeError). |
| §R10 Defensive indexing | ✅ | Pas d'indexation directe dans predict — délègue à `flatten_seq_to_tab` qui valide les dimensions. |
| §R2 Config-driven | ✅ | Paramètres predict non config-dépendants (légitime — predict ne lit pas de config). |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. predict() est purement forward (données d'entrée → sorties). |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. predict() est déterministe (pas d'aléa). |
| §R5 Float conventions | ✅ | Entrée float32, sortie float32 (cast explicite L157). Conforme. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open(), 0 bool identity. Pas de désérialisation. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `x_tab`, `y_hat`, `_feature_names` — tout snake_case (sauf params spec `X`) |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO. Stubs save/load pré-existants (hors scope). |
| Imports propres / relatifs | ✅ | Imports dans xgboost.py : stdlib → third-party → local. Relatif dans test. |
| DRY | ✅ | Pas de duplication de logique. |
| Suppressions lint justifiées | ✅ | 3× `noqa: N803` — params imposés par spec/ABC (inévitable). |
| Fichiers générés | ✅ | Aucun fichier généré dans la PR. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Preuve |
|---|---|---|
| Spec §6.1 — procédure predict | ✅ | 4 étapes spec (flatten → predict → cast → return) exactement implémentées dans L154-157. |
| Spec §6.2 — sortie et dtype | ✅ | Shape (N,), float32, log-returns continus. Conforme. |
| Spec §2.2 — meta/ohlcv ignorés | ✅ | Paramètres acceptés (`meta=None, ohlcv=None`) et non utilisés. |
| Plan WS-XGB-4.1 | ✅ | predict() implémenté conformément au plan. |
| Formules doc vs code | ✅ | Pas de formule mathématique spécifique dans predict — aplatissement délégué à l'adapter (conforme §3.1). |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signature vs BaseModel.predict | ✅ | `predict(self, X, meta=None, ohlcv=None) -> np.ndarray` — identique à l'ABC. |
| Signature vs DummyModel.predict | ✅ | Même signature que `dummy.py` L46-57. |
| Forwarding kwargs | ✅ | `meta` et `ohlcv` sont ignorés intentionnellement (spec §2.2). Pas de perte de contexte. |
| flatten_seq_to_tab signature | ✅ | Appel `flatten_seq_to_tab(X, self._feature_names)` conforme à la signature `(x_seq, feature_names)`. |
| Dtypes cohérents | ✅ | Entrée float32, sortie float32 — cohérent avec le pipeline. |

---

## Remarques

1. **[MINEUR]** `self._feature_names` non initialisé dans `__init__()`.
   - Fichier : `ai_trading/models/xgboost.py`
   - Ligne(s) : 27-28
   - Description : L'attribut `_feature_names` est créé pour la première fois dans `fit()` (L105) mais n'est pas déclaré dans `__init__()`. Le guard `self._model is None` dans `predict()` protège fonctionnellement contre un `AttributeError`, mais l'absence d'initialisation dans `__init__` est une irrégularité pour les type-checkers et la lisibilité.
   - Suggestion : Ajouter `self._feature_names: list[str] | None = None` dans `__init__()` après `self._model = None`.

2. **[MINEUR]** Boundary test N=0 manquant pour `predict()`.
   - Fichier : `tests/test_xgboost_model.py`
   - Ligne(s) : après L960 (fin de `TestXGBoostRegModelPredict`)
   - Description : Par §B3 boundary fuzzing, le cas N=0 devrait être testé pour `predict()`. Le code retournerait correctement un array `(0,)` float32, mais ce comportement n'est pas documenté par un test.
   - Suggestion : Ajouter un test `test_predict_boundary_n_zero` vérifiant que `predict(X=np.empty((0, L, F), dtype=np.float32))` retourne un array shape `(0,)` dtype float32.

---

## Résumé

Implémentation solide et conforme à la spec §6.1/§6.2. Le code est strict (pas de fallbacks), correctement typé (float32 entry/exit), et les 16 tests predict couvrent bien les critères d'acceptation. Deux items MINEUR identifiés : initialisation manquante de `_feature_names` dans `__init__` et absence du test boundary N=0 pour predict.

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 2
- Rapport : docs/tasks/MX-2/065/review_v1.md
```
