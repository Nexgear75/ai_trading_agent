# PR Review — [WS-7] #030 Grille de quantiles pour calibration θ

**Branche** : `task/030-quantile-grid`
**Date** : 2026-03-02
**Itération** : v1
**Verdict** : REQUEST CHANGES

---

## Phase A — Compliance

### A1. Périmètre

Fichiers modifiés (3) :

| Fichier | Type |
|---|---|
| `ai_trading/calibration/threshold.py` | Source (nouveau) |
| `tests/test_quantile_grid.py` | Tests (nouveau) |
| `docs/tasks/M3/030__ws7_quantile_grid.md` | Tâche (mise à jour) |

### A2. Structure branche & commits

| # | Critère | Résultat |
|---|---------|---------|
| 1 | Branche `task/030-quantile-grid` depuis `Max6000i1` | ✅ |
| 2 | Commit RED : `[WS-7] #030 RED: tests grille de quantiles et apply_threshold` | ✅ `115e148` |
| 3 | Commit GREEN : `[WS-7] #030 GREEN: grille de quantiles pour calibration θ` | ✅ `eac4e77` |
| 4 | Commit RED contient uniquement tests | ✅ `tests/test_quantile_grid.py` |
| 5 | Commit GREEN contient impl + tâche | ✅ `threshold.py` + tâche + tests |
| 6 | Pas de commits parasites entre RED et GREEN | ✅ 2 commits exactement |

### A3. Tâche associée

| # | Critère | Résultat |
|---|---------|---------|
| 1 | Statut DONE | ✅ |
| 2 | Critères d'acceptation cochés `[x]` (11/11) | ✅ |
| 3 | Checklist cochée | ⚠️ 2 items non cochés (voir Remarque 1) |

### A4. Suite de validation

| # | Critère | Résultat |
|---|---------|---------|
| 1 | pytest GREEN | ✅ 845 passed, 0 failed (dont 21 pour `test_quantile_grid.py`) |
| 2 | ruff clean | ✅ `All checks passed!` |

**Phase A : PASS** — passage en Phase B.

---

## Phase B — Code review adversariale

### B1. Scan automatisé (§GREP)

| Scan | Pattern | Résultat |
|------|---------|----------|
| §R1 — Fallbacks | `or []`, `or {}`, `or ""`, `or 0`, `if…else` | 0 occurrences src (1 faux positif docstring L49 : `else 0` dans description) |
| §R1 — Except large | `except:`, `except Exception:` | 0 occurrences |
| §R7 — noqa | suppressions lint | 0 occurrences |
| §R7 — print() | print résiduel | 0 occurrences |
| §R3 — shift(-) | look-ahead | 0 occurrences |
| §R4 — legacy random | `np.random.seed` etc. | 0 occurrences |
| §R7 — TODO/FIXME | code mort | 0 occurrences |
| §R7 — chemins hardcodés | `/tmp`, `C:\` | 0 occurrences |
| §R6 — mutable defaults | `def f(x=[])` | 0 occurrences |
| §R6 — open() | open sans context manager | 0 occurrences |
| §R6 — bool identity | `is True`, `is False` | 0 occurrences |
| §R6 — dict collision | assignation dict en boucle | 0 occurrences (dict comprehension L42, analysé manuellement → voir Remarque 2) |
| §R9 — for/range loop | boucle Python sur array | 0 occurrences (loop L36 est validation, pas calcul) |
| §R7 — init imports abs | `from ai_trading.` dans `__init__.py` | 0 occurrences |

### B2. Lecture du diff — `ai_trading/calibration/threshold.py` (68 lignes)

**Type safety** : ✅ — `y_hat_val.ndim`, `y_hat_val.size`, `len(q_grid)` et bounds check sur chaque `q`.

**Edge cases** :
- `y_hat_val` vide → `ValueError` ✅
- `q_grid` vide → `ValueError` ✅
- `y_hat_val` non-1D → `ValueError` ✅
- `q_grid` hors [0,1] → `ValueError` ✅
- `q_grid` avec doublons → pas de validation, collision silencieuse possible dans le dict (voir Remarque 2)

**Return contract** :
- `compute_quantile_thresholds` : `dict[float, float]`, conversion explicite `float()` ✅ (float64 pour métriques, §R5)
- `apply_threshold` : `NDArray[np.signedinteger]`, `astype(np.int32)` ✅, même shape que input ✅

**Domaine des paramètres** :
- `theta: float` dans `apply_threshold` — aucune borne requise (tout theta est valide mathématiquement) ✅
- `q` dans `q_grid` — bornes [0, 1] validées ✅

**Cohérence doc/code** :
- Docstrings précises et conformes au comportement ✅
- Spec §11.2 : `θ(q) = quantile_q(ŷ_val)` → implémenté par `np.quantile(y_hat_val, q)` ✅
- Spec §11.1 : `Go si ŷ_t > θ` → implémenté par `y_hat > theta` (strict >) ✅

**Resource cleanup** : N/A — pas d'I/O.

**Path handling** : N/A — pas de chemins.

### B2. Lecture du diff — `tests/test_quantile_grid.py` (178 lignes)

RAS après lecture complète du diff (178 lignes). Tests bien structurés, déterministes, données synthétiques, pas de réseau, seeds non requises (données `np.arange` déterministes).

### B3. Tests

| # | Critère | Résultat |
|---|---------|---------|
| 1 | Convention nommage `test_quantile_grid.py`, `#030` en docstring | ✅ |
| 2 | Couverture critères d'acceptation | ✅ 11/11 critères couverts |
| 3 | Cas nominaux | ✅ (median, min, max, full grid, config integration) |
| 4 | Cas d'erreurs | ✅ (empty y_hat, empty q_grid, 2D, q out of range) |
| 5 | Cas de bords | ✅ (single element, all identical, boundary theta==y_hat) |
| 6 | Boundary fuzzing compute | ✅ q=0.0 (min), q=0.5, q=1.0 (max), q<0, q>1 |
| 7 | Tests déterministes | ✅ (`np.arange`, pas de random) |
| 8 | Données synthétiques | ✅ |
| 9 | Pas de skip/xfail injustifié | ✅ |
| 10 | Portabilité chemins | ✅ (pas de `tmp_path` nécessaire, pas de paths) |

### B4. Audit — Règles non négociables

| Règle | Résultat | Preuve |
|-------|----------|--------|
| §R1 — Strict code | ✅ | Scan B1 + validation explicite L30-40 avec `raise ValueError` |
| §R2 — Config-driven | ✅ | `q_grid` paramètre de fonction, test config integration L166-178 |
| §R3 — Anti-fuite | ✅ | Signature `y_hat_val` sémantiquement val-only, stateless, scan 0 `.shift(-` |
| §R4 — Reproductibilité | ✅ | `np.quantile` déterministe, scan 0 legacy random |
| §R5 — Float conventions | ✅ | `float()` return (float64), int32 pour signaux |
| §R6 — Anti-patterns | ⚠️ | Dict comprehension L42 avec `q` comme clé — doublons possibles (Remarque 2) |
| §R7 — Qualité | ✅ | snake_case, imports propres, pas de print/TODO/noqa |
| §R8 — Intermodule | ✅ | `ThresholdingConfig.q_grid` existe dans `config.py` L153, noms cohérents |
| §R9 — Finance | ✅ | `np.quantile` standard, nommage métier clair |
| §R10 — Indexing | ✅ | Pas d'indexation/slicing à risque |

---

## Remarques

1. **[MINEUR]** Checklist de tâche incomplète
   - Fichier : `docs/tasks/M3/030__ws7_quantile_grid.md`
   - Ligne(s) : avant-dernière et dernière de la checklist
   - Description : Les items `Commit GREEN` et `Pull Request ouverte` sont `[ ]` alors que le commit GREEN existe (`eac4e77`).
   - Suggestion : Cocher `[x]` pour le commit GREEN. L'item PR ouverte sera coché après création de la PR.

2. **[MINEUR]** Pas de validation d'unicité de `q_grid` dans `compute_quantile_thresholds`
   - Fichier : `ai_trading/calibration/threshold.py`
   - Ligne(s) : 36-42
   - Description : Le dict comprehension `{q: float(np.quantile(y_hat_val, q)) for q in q_grid}` produirait une collision silencieuse si `q_grid` contenait des doublons (ex: `[0.5, 0.5]` → dict à 1 entrée au lieu de 2). Le validateur Pydantic (`_validate_q_grid`) ne rejette pas les doublons non plus (seul le tri est vérifié). Risque faible car les valeurs seraient identiques, mais le contrat retour (`len(result) == len(q_grid)`) serait violé.
   - Suggestion : Ajouter dans la validation de `compute_quantile_thresholds` :
     ```python
     if len(q_grid) != len(set(q_grid)):
         raise ValueError("q_grid must not contain duplicate values")
     ```
     Et/ou ajouter la même validation dans `ThresholdingConfig._validate_q_grid`.

---

## Résumé

Code propre, concis et conforme à la spec §11.2. L'implémentation est correcte, les tests sont complets et bien structurés (21 tests, couverture des critères d'acceptation, cas de bords). Deux points mineurs identifiés : checklist de tâche incomplète et absence de validation d'unicité sur `q_grid`.
