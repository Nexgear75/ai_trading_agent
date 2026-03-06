# Revue PR — [WS-10] #040 — Métriques de prédiction

**Branche** : `task/040-prediction-metrics`
**Tâche** : `docs/tasks/M4/040__ws10_prediction_metrics.md`
**Date** : 2026-03-02
**Itération** : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation des métriques de prédiction (MAE, RMSE, DA, Spearman IC) est fonctionnellement correcte, bien structurée et conforme à la spec §14.1. Le processus TDD est respecté (RED puis GREEN), les 1106 tests passent, ruff est clean. Cependant, la constante `_VALID_OUTPUT_TYPES` est dupliquée entre `prediction.py` et `models/base.py` (**BLOQUANT** DRY §R7 — même problème déjà corrigé dans task #033 pour `threshold.py`). De plus, certains tests de bords manquent (entrées 2-D, constant `y_hat` dans Spearman IC).

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/040-prediction-metrics` | ✅ | `git branch --show-current` → `task/040-prediction-metrics` |
| Commit RED présent | ✅ | `4d90243` — `[WS-10] #040 RED: tests for prediction metrics (MAE, RMSE, DA, Spearman IC)` |
| Commit GREEN présent | ✅ | `b617eea` — `[WS-10] #040 GREEN: prediction metrics (MAE, RMSE, DA, Spearman IC)` |
| Commit RED = tests uniquement | ✅ | `git show --stat 4d90243` → 1 fichier: `tests/test_prediction_metrics.py` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat b617eea` → `ai_trading/metrics/__init__.py`, `ai_trading/metrics/prediction.py`, `docs/tasks/M4/040__ws10_prediction_metrics.md`, `tests/test_prediction_metrics.py` |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en tête du fichier |
| Critères d'acceptation cochés | ✅ (12/12) | Tous les critères `[x]` |
| Checklist cochée | ⚠️ (8/10) | 2 items non cochés : « Commit GREEN » et « Pull Request ouverte » — le commit GREEN existe (`b617eea`) mais la case n'est pas cochée dans le fichier de tâche |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1106 passed**, 0 failed ✅ |
| `ruff check ai_trading/ tests/` | **All checks passed** ✅ |

**Phase A : PASS** — processus TDD respecté, CI verte.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| Pattern recherché (§) | Commande | Résultat |
|---|---|---|
| R1 — Fallbacks silencieux | `grep -n 'or \[\]\|or {}\|or ""\|or 0\b\|if .* else '` sur SRC | 0 occurrences (grep exécuté, exit 1) |
| R1 — Except trop large | `grep -n 'except:$\|except Exception:'` sur SRC | 0 occurrences (grep exécuté, exit 1) |
| R7 — noqa | `grep -rn 'noqa'` sur CHANGED | 1 match : `ai_trading/metrics/__init__.py:3: # noqa: F401` — **Faux positif** : import pour side-effect, justifié |
| R7 — per-file-ignores | `grep -n 'per-file-ignores' pyproject.toml` | L51 : section existante mais non modifiée par cette PR |
| R7 — Print résiduel | `grep -n 'print('` sur SRC | 0 occurrences (grep exécuté, exit 1) |
| R3 — Shift négatif | `grep -n '.shift(-'` sur SRC | 0 occurrences (grep exécuté, exit 1) |
| R4 — Legacy random API | `grep -rn 'np.random.seed\|...'` sur CHANGED | 0 occurrences (grep exécuté, exit 1) |
| R7 — TODO/FIXME | `grep -rn 'TODO\|FIXME\|HACK\|XXX'` sur CHANGED | 0 occurrences (grep exécuté, exit 1) |
| R7 — Chemins hardcodés tests | `grep -n '/tmp\|/var/tmp\|C:\\'` sur TEST | 0 occurrences (grep exécuté, exit 1) |
| R7 — Imports absolus `__init__` | `grep -n 'from ai_trading\.'` sur `__init__.py` | 0 occurrences (grep exécuté, exit 1) — import relatif `from . import prediction` ✅ |
| R7 — Registration manuelle tests | `grep -n 'register_model\|register_feature'` sur TEST | 0 occurrences (grep exécuté, exit 1) — N/A ce module |
| R6 — Mutable defaults | `grep -n 'def .*=\[\]\|def .*={}'` sur CHANGED | 0 occurrences (grep exécuté, exit 1) |
| R6 — open() sans context | `grep -n '.read_text\|open('` sur SRC | 0 occurrences (grep exécuté, exit 1) — pas d'I/O |
| R6 — Bool identity | `grep -rn 'is np.bool_\|is True\|is False'` sur CHANGED | 0 occurrences (grep exécuté, exit 1) |
| R6 — isfinite | `grep -n 'isfinite'` sur SRC | 3 matches : L49 `np.isfinite(y_true)`, L51 `np.isfinite(y_hat)`, L143 `math.isfinite(ic)` — ✅ validation NaN/inf correcte |
| R9 — for range() sur array | `grep -n 'for .* in range(.*):` sur SRC | 0 occurrences (grep exécuté, exit 1) — tout vectorisé |
| R9 — np comprehension | `grep -n 'np\.[a-z]*(.*for .* in '` sur SRC | 0 occurrences (grep exécuté, exit 1) |
| R6 — Dict collision | `grep -n '\[.*\] = .*'` sur SRC (hors def/#/""") | 0 occurrences (grep exécuté, exit 1) |
| R7 — Fixtures dupliquées | `grep -n 'load_config.*configs/'` sur TEST | 0 occurrences (grep exécuté, exit 1) — pas de config dans ces tests |

### B2. Annotations par fichier

#### `ai_trading/metrics/prediction.py` (198 lignes de diff, fichier nouveau)

- **L13-14** `_VALID_OUTPUT_TYPES = frozenset({"regression", "signal"})` : **DRY violation** — cette constante est identique à `VALID_OUTPUT_TYPES` définie dans `ai_trading/models/base.py` L51. Ce même problème exact a été identifié comme **BLOQUANT** dans la review v1 de la tâche #033 (voir `docs/tasks/M3/033/review_v1.md` remarque #1) et a été corrigé dans `threshold.py` en important depuis `ai_trading.models.base`. Le module `prediction.py` devrait faire de même.
  Sévérité : **BLOQUANT**
  Suggestion : remplacer la définition locale par `from ai_trading.models.base import VALID_OUTPUT_TYPES` et utiliser `VALID_OUTPUT_TYPES` au lieu de `_VALID_OUTPUT_TYPES`. Pas de risque de cycle d'import (`metrics.prediction` n'est pas importé par `models.base`).

- **L34** `def _validate_vectors(y_true, y_hat, *, min_length=1)` : la validation ne vérifie pas que les arrays sont de type numérique (pas de check `dtype`). Si des arrays de strings ou d'objets sont passés, `np.isfinite` pourrait lever une TypeError non descriptive. **RAS** (les entrées viennent de modules internes, frontière interne).

- **L60-73** `compute_mae` : implémentation `float(np.mean(np.abs(y_true - y_hat)))` — conforme à la spec §14.1 `MAE = mean(|y - ŷ|)`. Le `float()` wrapper garantit un Python float (64 bits). ✅

- **L76-89** `compute_rmse` : implémentation `float(np.sqrt(np.mean((y_true - y_hat) ** 2)))` — conforme à la spec §14.1 `RMSE = sqrt(mean((y - ŷ)²))`. ✅

- **L92-115** `compute_directional_accuracy` : implémentation avec exclusion de `y_true == 0` et `y_hat == 0`, retour None si aucun sample éligible. Conforme à la spec §14.1 convention DA. ✅

- **L109** `sign_match = np.sign(y_true[eligible]) == np.sign(y_hat[eligible])` : comparaison `==` sur les résultats de `np.sign` (valeurs entières -1, 0, +1). Pas de problème de float ici car `np.sign` renvoie des valeurs exactes. ✅

- **L119-148** `compute_spearman_ic` : utilise `scipy.stats.spearmanr`, vérifie min_length=2 (corrélation requiert ≥2 points), détecte inputs constants, et vérifie que le résultat est fini. Conforme spec §14.1. ✅

- **L141** `result.statistic` : accès à l'attribut `.statistic` de `SpearmanrResult`. Le `# type: ignore[union-attr]` est présent — acceptable car dépend de la version scipy. ✅

- **L153-192** `compute_prediction_metrics` : pour `output_type == "signal"`, retourne immédiatement dict all-None sans valider les vecteurs. Pour `output_type == "regression"`, appelle les 4 fonctions individuelles. Les clés du dict (`mae`, `rmse`, `directional_accuracy`, `spearman_ic`) correspondent exactement au schéma `example_metrics.json` de la spec. ✅

#### `ai_trading/metrics/__init__.py` (8 lignes de diff)

- **L3** `from . import prediction  # noqa: F401` : import relatif correct pour rendre le module accessible. `noqa: F401` justifié (import pour namespace). ✅

RAS après lecture complète du diff (8 lignes).

#### `tests/test_prediction_metrics.py` (401 lignes de diff)

- **L1-6** Docstring avec `#040` et `Spec §14.1` : convention respectée. ✅

- **L49-50** `TestComputeMAE` : couvre cas nominal (`test_known_values`), prédiction parfaite, élément unique, float64, vide, longueurs différentes, NaN, inf. Bon coverage. ✅

- **L95-139** `TestComputeRMSE` : mêmes catégories de tests que MAE. ✅

- **L145-212** `TestComputeDirectionalAccuracy` : couvre toutes directions égales, toutes mauvaises, mixtes, DA ∈ [0,1], exclusion y_true=0, exclusion y_hat=0, exclusion les deux=0, all excluded → None, all y_hat=0 → None, float64, vide, longueurs. Très bon coverage. ✅

- **L218-289** `TestComputeSpearmanIC` : corrélation parfaite positive/négative, valeurs connues vs scipy, float64, vide, single element, longueurs, constant y_true.
  **Manque** : pas de test pour `y_hat` constant (code L139: `if np.all(y_hat == y_hat[0]): raise ValueError`). Le test `test_constant_input_raises` ne vérifie que y_true constant.
  Sévérité : **MINEUR**
  Suggestion : ajouter un test `test_constant_y_hat_raises` avec y_hat constant et y_true variable.

- **Manque global** : aucun test ne passe un array 2-D à une des fonctions pour exercer la validation `ndim != 1` (code L34-37). La validation existe mais n'est jamais testée.
  Sévérité : **MINEUR**
  Suggestion : ajouter un test `test_2d_input_raises` dans au moins une classe (ex: `TestComputeMAE`).

- **L295-378** `TestComputePredictionMetrics` : couvre signal → all None, regression → computed, regression values match individual, dict keys, float64, invalid output_type, DA None propagation, signal ignores inputs. Bon coverage. ✅

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `tests/test_prediction_metrics.py`, `#040` dans docstring L3 |
| Couverture des critères d'acceptation | ✅ | 12/12 critères couverts (mapping ci-dessous) |
| Cas nominaux + erreurs + bords | ⚠️ | Manque 2-D input et constant y_hat (MINEUR) |
| Boundary fuzzing | ✅ | N=0 (empty), N=1 (single), N=2 (spearman min), valeurs extrêmes couvertes |
| Déterministes | ✅ | Pas d'aléatoire dans les tests — valeurs déterministes |
| Portabilité chemins | ✅ | Scan B1: 0 match `/tmp` |
| Tests registre réalistes | N/A | Pas de registre dans ce module |
| Contrat ABC complet | N/A | Pas d'ABC dans ce module |
| Données synthétiques | ✅ | Tous les vecteurs sont construits localement |

**Mapping critères d'acceptation → tests** :

| Critère | Test(s) |
|---|---|
| `compute_mae` test numérique | `TestComputeMAE::test_known_values` (L49) |
| `compute_rmse` test numérique | `TestComputeRMSE::test_known_values` (L99) |
| DA ∈ [0, 1] | `TestComputeDirectionalAccuracy::test_da_in_01_range` (L170) |
| DA exclut y_true==0, y_hat==0 | `test_excludes_y_true_zero` (L176), `test_excludes_y_hat_zero` (L183), `test_excludes_both_zero` (L190) |
| DA → None si all exclus | `test_all_excluded_returns_none` (L197), `test_all_y_hat_zero_returns_none` (L203) |
| Spearman IC numérique | `TestComputeSpearmanIC::test_known_values` (L238) |
| signal → all None | `TestComputePredictionMetrics::test_signal_returns_all_none` (L300) |
| regression → computed | `TestComputePredictionMetrics::test_regression_computes_all` (L308) |
| float64 | `test_float64_output` dans chaque classe |
| Nominaux + erreurs + bords | Classes with empty, mismatched, NaN, inf tests |
| Suite verte | 1106 passed |
| ruff clean | All checks passed |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1: 0 fallback, 0 except large. Validation explicite + raise dans `_validate_vectors` |
| §R10 Defensive indexing | ✅ | Pas d'indexation par expression calculée. `eligible` masque booléen safe |
| §R2 Config-driven | ✅ | Module de métriques pures sans paramètres configurables — pas de hardcoding de paramètres métier |
| §R3 Anti-fuite | ✅ | Scan B1: 0 `.shift(-`. Métriques post-hoc sur y_true/y_hat, pas de look-ahead possible |
| §R4 Reproductibilité | ✅ | Scan B1: 0 legacy random. Fonctions déterministes pures |
| §R5 Float conventions | ✅ | Toutes les métriques retournent `float(np.xxx(...))` → float64. Docstrings: `(1-D, float64)` |
| §R6 Anti-patterns Python | ✅ | Scan B1: 0 mutable default, 0 open, 0 bool identity. `isfinite` présent L49/L51/L143 |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Tous les noms conformes |
| Pas de code mort/debug | ✅ | Scan B1: 0 print, 0 TODO |
| Imports propres / relatifs | ✅ | `__init__.py` → import relatif `from . import prediction`. Imports src: `math`, `numpy`, `scipy.stats` — propres |
| DRY | ❌ | `_VALID_OUTPUT_TYPES` dupliquée (BLOQUANT #1) |
| noqa justifiés | ✅ | 1 seul `noqa: F401` dans `__init__.py` — import pour namespace, justifié |
| `__init__.py` à jour | ✅ | `from . import prediction` ajouté |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | ✅ | MAE, RMSE, DA, Spearman IC implémentés selon définitions standards |
| Nommage métier | ✅ | `directional_accuracy`, `spearman_ic`, `mae`, `rmse` — noms complets et clairs |
| Séparation des responsabilités | ✅ | Module dédié aux métriques de prédiction uniquement |
| Invariants de domaine | ✅ | DA ∈ [0,1], exclusion des samples à direction indéterminée |
| Cohérence unités/échelles | ✅ | Pas de mélange — tout en unités de y (rendements) |
| Patterns de calcul | ✅ | Tout vectorisé numpy, pas de boucle Python. Scan B1: 0 `for range` |

### B6. Conformité spec v1.0

| Critère | Verdict | Commentaire |
|---|---|---|
| Spécification §14.1 | ✅ | Formules MAE, RMSE, DA, Spearman IC conformes à la spec |
| Plan d'implémentation WS-10.1 | ✅ | Module créé selon le plan |
| Formules doc vs code | ✅ | Vérification croisée spec/code/tests — correspondance exacte |
| Convention DA (exclusion y=0, ŷ=0, all excluded → null) | ✅ | Conforme à la spec L820 |
| Clés dict métriques | ✅ | `mae`, `rmse`, `directional_accuracy`, `spearman_ic` — conformes à `example_metrics.json` |

### B7. Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | Fonctions pures, pas d'appel croisé entrant |
| Noms de colonnes DataFrame | N/A | Pas de DataFrame manipulé |
| Clés de configuration | N/A | Pas de clé config lue |
| Registres et conventions partagées | ❌ | `_VALID_OUTPUT_TYPES` dupliquée au lieu d'importer `VALID_OUTPUT_TYPES` depuis `models.base` — BLOQUANT #1 |
| Structures de données partagées | ⚠️ | Même problème que ci-dessus |
| Conventions numériques | ✅ | float64 pour toutes les métriques |
| Imports croisés | ✅ | Seuls imports: `math`, `numpy`, `scipy` — pas de dépendance interne |

---

## Remarques

1. **[BLOQUANT]** `_VALID_OUTPUT_TYPES` DRY violation — constante dupliquée
   - Fichier : `ai_trading/metrics/prediction.py`
   - Ligne(s) : 13-14
   - Suggestion : supprimer la définition locale `_VALID_OUTPUT_TYPES = frozenset({"regression", "signal"})` et remplacer par `from ai_trading.models.base import VALID_OUTPUT_TYPES`. Utiliser `VALID_OUTPUT_TYPES` aux L174 et L176. Pas de risque de cycle d'import (vérifié : `models.base` n'importe rien de `metrics`). Ce même problème a été identifié et corrigé dans task #033 pour `threshold.py` → pattern établi.

2. **[MINEUR]** Test manquant pour constant `y_hat` dans Spearman IC
   - Fichier : `tests/test_prediction_metrics.py`
   - Ligne(s) : ~296 (classe `TestComputeSpearmanIC`)
   - Suggestion : ajouter `test_constant_y_hat_raises` vérifiant que `compute_spearman_ic(np.array([1.0, 2.0, 3.0]), np.array([5.0, 5.0, 5.0]))` lève `ValueError`. Le code (L139) gère ce cas mais il n'est pas testé.

3. **[MINEUR]** Test manquant pour input 2-D
   - Fichier : `tests/test_prediction_metrics.py`
   - Ligne(s) : N/A (absent)
   - Suggestion : ajouter au moins un test `test_2d_input_raises` passant un array 2-D pour exercer la validation `ndim != 1` (code L34-37).

4. **[MINEUR]** Checklist tâche incomplète
   - Fichier : `docs/tasks/M4/040__ws10_prediction_metrics.md`
   - Ligne(s) : 62-63
   - Suggestion : cocher les items « Commit GREEN » et « Pull Request ouverte » une fois les actions effectuées.

---

## Résumé

| Sévérité | Nombre |
|---|---|
| BLOQUANT | 1 |
| WARNING | 0 |
| MINEUR | 3 |

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 1
- Warnings : 0
- Mineurs : 3
- Rapport : `docs/tasks/M4/040/review_v1.md`
