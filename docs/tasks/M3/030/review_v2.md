# PR Review — [WS-7] #030 Grille de quantiles pour calibration θ

**Branche** : `task/030-quantile-grid`
**Date** : 2026-03-02
**Itération** : v2 (post-corrections v1)
**Verdict** : ✅ CLEAN

---

## Phase A — Compliance

### A1. Périmètre

Fichiers modifiés (3) :

| Fichier | Type |
|---|---|
| `ai_trading/calibration/threshold.py` | Source (nouveau — 71 lignes) |
| `tests/test_quantile_grid.py` | Tests (nouveau — 192 lignes) |
| `docs/tasks/M3/030__ws7_quantile_grid.md` | Tâche (mise à jour DONE) |

### A2. Structure branche & commits

| # | Critère | Résultat | Preuve |
|---|---------|---------|--------|
| 1 | Branche `task/030-quantile-grid` depuis `Max6000i1` | ✅ | `git log --oneline` |
| 2 | Commit RED : `[WS-7] #030 RED: tests grille de quantiles et apply_threshold` | ✅ | `115e148` |
| 3 | Commit GREEN : `[WS-7] #030 GREEN: grille de quantiles pour calibration θ` | ✅ | `eac4e77` |
| 4 | Commit RED contient uniquement tests | ✅ | `git show --stat 115e148` → `tests/test_quantile_grid.py` only |
| 5 | Commit GREEN contient impl + tâche | ✅ | `git show --stat eac4e77` → `threshold.py` + tâche + tests |
| 6 | Pas de commits parasites entre RED et GREEN | ✅ | 2 commits (RED + GREEN) + 1 FIX post-review |

### A3. Tâche associée

| # | Critère | Résultat |
|---|---------|---------|
| 1 | Statut DONE | ✅ |
| 2 | Critères d'acceptation cochés `[x]` (11/11) | ✅ |
| 3 | Checklist cochée | ✅ (8/9 — seul l'item PR ouverte est `[ ]`, normal avant merge) |

### A4. Suite de validation

| # | Critère | Résultat |
|---|---------|---------|
| 1 | pytest GREEN | ✅ **846 passed**, 0 failed (dont 22 `test_quantile_grid.py`) |
| 2 | ruff clean | ✅ `All checks passed!` |

**Phase A : PASS** — passage en Phase B.

---

## Phase B — Code review adversariale

### B1. Scan automatisé (§GREP)

| Scan | Pattern | Résultat |
|------|---------|----------|
| §R1 — Fallbacks | `or []`, `or {}`, `or ""`, `or 0`, `if…else` | 0 occurrences src (1 faux positif : docstring L51 `else 0` — description, pas code) |
| §R1 — Except large | `except:`, `except Exception:` | 0 occurrences |
| §R7 — noqa | suppressions lint | 0 occurrences |
| §R7 — print() | print résiduel | 0 occurrences |
| §R3 — shift(-) | look-ahead | 0 occurrences |
| §R4 — legacy random | `np.random.seed` etc. | 0 occurrences |
| §R7 — TODO/FIXME | code mort | 0 occurrences |
| §R7 — chemins hardcodés | `/tmp`, `C:\` | 0 occurrences |
| §R7 — init imports abs | `from ai_trading.` dans `__init__.py` | 0 occurrences |
| §R7 — registration manuelle | `register_model`, `register_feature` | 0 occurrences (N/A — pas de registre ici) |
| §R6 — mutable defaults | `def f(x=[])`, `def f(x={})` | 0 occurrences |
| §R6 — open() | open sans context manager | 0 occurrences |
| §R6 — bool identity | `is True`, `is False` | 0 occurrences |
| §R6 — dict collision | assignation dict en boucle | 0 occurrences (dict comprehension L50, mais doublons maintenant rejetés par validation L40-41) |
| §R9 — for/range loop | boucle Python sur array numpy | 0 occurrences (boucle L42 est validation, pas calcul vectoriel) |

### B2. Lecture du diff — `ai_trading/calibration/threshold.py` (71 lignes)

**Type safety** : ✅ — `y_hat_val.ndim`, `y_hat_val.size`, `len(q_grid)`, bounds check sur chaque `q`, unicité `q_grid`.

**Edge cases** :
- `y_hat_val` vide → `ValueError` L37 ✅
- `q_grid` vide → `ValueError` L39 ✅
- `y_hat_val` non-1D → `ValueError` L34 ✅
- `q_grid` hors [0,1] → `ValueError` L44 ✅
- `q_grid` doublons → `ValueError` L40-41 ✅ (fix v1 — M-2)

**Return contract** :
- `compute_quantile_thresholds` : `dict[float, float]`, conversion explicite `float()` L50 ✅ (float64 pour métriques, §R5)
- `apply_threshold` : `NDArray[np.signedinteger]`, `astype(np.int32)` L70 ✅, même shape que input ✅

**Domaine des paramètres** :
- `theta: float` dans `apply_threshold` — aucune borne requise (tout theta est mathématiquement valide) ✅
- `q` dans `q_grid` — bornes [0, 1] validées L43-45 ✅

**Cohérence doc/code** :
- Docstrings précises et conformes au comportement ✅
- Spec §11.2 : `θ(q) = quantile_q(ŷ_val)` → implémenté par `np.quantile(y_hat_val, q)` ✅
- Spec §11.1 : `Go si ŷ_t > θ` → implémenté par `y_hat > theta` (strict >) ✅

**Resource cleanup** : N/A — pas d'I/O.
**Path handling** : N/A — pas de chemins.

RAS après lecture complète du diff (71 lignes).

### B2. Lecture du diff — `tests/test_quantile_grid.py` (192 lignes)

RAS après lecture complète du diff (192 lignes). Tests bien structurés, déterministes, données synthétiques, pas de réseau, seeds non requises (données `np.arange` déterministes). ID tâche `#030` dans docstring L1.

### B3. Tests

| # | Critère | Résultat | Preuve |
|---|---------|---------|--------|
| 1 | Convention nommage | ✅ | `test_quantile_grid.py`, `#030` en docstring L1 |
| 2 | Couverture critères d'acceptation (11/11) | ✅ | Mapping ci-dessous |
| 3 | Cas nominaux | ✅ | median, min, max, full grid, single element, identical, config integration |
| 4 | Cas d'erreurs | ✅ | empty y_hat, empty q_grid, 2D y_hat, q out of range (low/high), duplicates |
| 5 | Cas de bords | ✅ | single element, all identical, boundary theta==y_hat→0 |
| 6 | Boundary fuzzing compute | ✅ | q=0.0 (min), q=0.5 (median), q=1.0 (max), q<0, q>1 |
| 7 | Tests déterministes | ✅ | `np.arange` deterministic, pas de random |
| 8 | Données synthétiques | ✅ | `np.arange(100)`, `np.full(50, 7.7)`, `np.array([42.0])` |
| 9 | Pas de skip/xfail injustifié | ✅ | 0 skip/xfail |
| 10 | Portabilité chemins | ✅ | Pas de paths (scan B1: 0 `/tmp`) |
| 11 | Tests registre réalistes | N/A | Pas de registre dans ce module |
| 12 | Contrat ABC complet | N/A | Pas d'ABC dans ce module |

**Mapping critères d'acceptation → tests** :

| Critère | Test(s) |
|---------|---------|
| q=0.5 → médiane | `test_quantile_median` |
| q=0.0 → min | `test_quantile_min` |
| q=1.0 → max | `test_quantile_max` |
| Grille complète | `test_full_grid` |
| apply_threshold >θ→1, ≤θ→0 | `test_apply_threshold_positive`, `_negative`, `_mixed`, `_boundary` |
| apply_threshold même shape | `test_apply_threshold_same_shape` |
| Erreur si y_hat_val vide | `test_empty_y_hat_val_raises` |
| Paramètres depuis config | `test_q_grid_from_config`, `test_config_q_grid_values` |
| Tests nominaux+erreurs+bords | ✅ 22 tests couvrant les 3 catégories |
| Suite verte | ✅ 846 passed |
| ruff clean | ✅ All checks passed |

### B4. Audit — Règles non négociables

| Règle | Résultat | Preuve |
|-------|----------|--------|
| §R1 — Strict code | ✅ | Scan B1 (0 fallback, 0 except large) + validation explicite L34-45 avec `raise ValueError` |
| §R2 — Config-driven | ✅ | `q_grid` est paramètre de fonction, config integration testée L166-192 |
| §R3 — Anti-fuite | ✅ | Signature `y_hat_val` sémantiquement val-only, fonctions stateless, scan 0 `.shift(-` |
| §R4 — Reproductibilité | ✅ | `np.quantile` déterministe, scan 0 legacy random |
| §R5 — Float conventions | ✅ | `float()` return (float64 métriques), int32 pour signaux binaires |
| §R6 — Anti-patterns | ✅ | Scan 0 mutable defaults, 0 open, 0 bool identity. Dict comprehension L50 protégé par validation unicité L40-41 |
| §R7 — Qualité | ✅ | snake_case, imports propres, pas de print/TODO/noqa/code mort |
| §R8 — Intermodule | ✅ | `ThresholdingConfig.q_grid` existe dans `config.py` L153, noms cohérents avec config YAML L101 |
| §R9 — Finance | ✅ | `np.quantile` standard, nommage métier clair (theta, q_grid, signals) |
| §R10 — Indexing | ✅ | Pas d'indexation/slicing à risque, pas d'array bounds issues |

### B5. Qualité du code

| Critère | Résultat | Preuve |
|---------|----------|--------|
| Nommage snake_case | ✅ | `compute_quantile_thresholds`, `apply_threshold`, `y_hat_val`, `q_grid` |
| Pas de code mort/debug | ✅ | Scan B1: 0 print, 0 TODO |
| Imports propres / relatifs | ✅ | Scan B1: 0 `from ai_trading.` dans `__init__.py`, imports standard |
| DRY | ✅ | Pas de duplication |
| `.gitignore` couvre artefacts | ✅ | N/A — pas d'artefacts générés |
| Pas de fichiers temporaires | ✅ | Pas de fichiers `.pyc`, cache etc. dans la PR |

### B5-bis. Bonnes pratiques métier

| Critère | Résultat | Commentaire |
|---------|----------|-------------|
| Exactitude concepts financiers | ✅ | `np.quantile` correct pour grille de calibration |
| Nommage métier cohérent | ✅ | θ (theta), q_grid, signals — terminologie standard |
| Séparation responsabilités | ✅ | Module `calibration/threshold.py` encapsule uniquement le calcul de seuils |
| Invariants de domaine | ✅ | q ∈ [0,1] validé, y_hat non-vide validé |
| Cohérence unités/échelles | ✅ | Quantiles sans unité, signaux binaires {0,1} |
| Patterns calcul financier | ✅ | Vectorisé (`np.quantile`, comparaison broadcast), pas de boucle Python |

### B6. Conformité spec v1.0

| Critère | Résultat |
|---------|----------|
| Spécification §11.2 | ✅ `θ(q) = quantile_q(ŷ_val)` implémenté fidèlement |
| Plan WS-7.1 | ✅ Grille de quantiles conforme au plan |
| Formules doc vs code | ✅ Aucun off-by-one, strict `>` conforme |
| Pas d'exigence inventée | ✅ |

### B7. Cohérence intermodule

| Critère | Résultat | Commentaire |
|---------|----------|-------------|
| Signatures et types retour | ✅ | `dict[float, float]` et `NDArray[np.signedinteger]` cohérents |
| Clés de configuration | ✅ | `thresholding.q_grid` dans config.py L153 ↔ default.yaml L101 |
| Registres | N/A | Pas de registre |
| Conventions numériques | ✅ | float64 pour thresholds (métriques), int32 pour signaux |
| Imports croisés | ✅ | `numpy` + `ai_trading.config` (existant dans Max6000i1) |

---

## Vérification corrections v1

| Item v1 | Description | Résultat v2 |
|---------|-------------|-------------|
| M-1 | Checklist commit GREEN non cochée | ✅ Corrigé — `[x] **Commit GREEN**` dans la tâche (commit `2da36b7`) |
| M-2 | Pas de validation unicité `q_grid` | ✅ Corrigé — L40-41 `if len(q_grid) != len(set(q_grid)): raise ValueError(...)` + test `test_duplicate_q_grid_raises` (commit `2da36b7`) |

---

## Remarques

Aucune.

---

## Résumé

Code propre, concis et conforme à la spec §11.2. L'implémentation (71 lignes) couvre `compute_quantile_thresholds` et `apply_threshold` avec validation stricte de toutes les entrées. Les 22 tests couvrent exhaustivement les critères d'acceptation (nominaux, erreurs, bords, intégration config). Les deux points mineurs de la v1 (checklist tâche + validation unicité q_grid) sont correctement corrigés. Aucun nouveau problème identifié.
