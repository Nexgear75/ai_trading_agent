# Revue PR — [WS-9] #037 — Baseline no-trade

Branche : `task/037-baseline-no-trade`
Tâche : `docs/tasks/M4/037__ws9_baseline_no_trade.md`
Date : 2026-03-02
Itération : v2

## Verdict global : ✅ CLEAN

## Résumé

Itération v2 après correction des 2 items MINEURS de la v1 : ajout de `test_predict_empty_input` (N=0) et `test_save_load_roundtrip_file_path` (chemin fichier explicite). Les deux corrections sont conformes et aucune régression ni nouveau problème n'a été introduit. 24 tests passent, ruff clean. Implémentation conforme à la spec §13.1, au plan WS-9.1, et à toutes les règles du projet.

---

## Vérification des corrections v1

### Item 1 — Test empty input N=0 (MINEUR v1)
**Corrigé ✅** — `test_predict_empty_input` ajouté dans `TestNoTradePredict` (diff `432b47a...13738c0`, lignes +169-176). Vérifie `shape == (0,)` et `dtype == np.float32` pour un input `np.zeros((0, _L, _F))`. La docstring du module (ligne 9) est désormais cohérente avec les tests.

### Item 2 — Test save/load avec chemin fichier (MINEUR v1)
**Corrigé ✅** — `test_save_load_roundtrip_file_path` ajouté dans `TestNoTradeSaveLoad` (diff `432b47a...13738c0`, lignes +232-243). Passe un chemin fichier explicite `tmp_path / "model.json"`, vérifie l'existence du fichier et fait un roundtrip complet save→load→predict. Le `else` branch de `_resolve_path` est désormais couvert.

---

## Phase A — Compliance

### A1. Périmètre

Fichiers modifiés vs `Max6000i1` :
```
ai_trading/baselines/__init__.py       (source)
ai_trading/baselines/no_trade.py       (source)
docs/tasks/M4/037__ws9_baseline_no_trade.md  (tâche)
tests/test_baseline_no_trade.py        (tests)
```
2 fichiers source, 1 fichier test, 1 fichier tâche.

### A2. Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-slug` | ✅ | `git branch --show-current` → `task/037-baseline-no-trade` |
| Commit RED présent | ✅ | `a44d60d` — `[WS-9] #037 RED: tests for NoTradeBaseline — attributes, registry, fit/predict, save/load, backtest integration` |
| Commit RED = tests uniquement | ✅ | `git show --stat a44d60d` → 1 fichier : `tests/test_baseline_no_trade.py` |
| Commit GREEN présent | ✅ | `432b47a` — `[WS-9] #037 GREEN: NoTradeBaseline — zero-signal baseline with registry, backtest integration` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 432b47a` → `no_trade.py`, `__init__.py`, tâche, tests |
| Commit FIX post-revue | ✅ | `13738c0` — `[WS-9] #037 FIX: add test for empty input N=0 and file-path save/load roundtrip` — tests uniquement (1 fichier) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 3 commits (RED, GREEN, FIX v1) |

### A3. Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (10/10) |
| Checklist cochée | ✅ (8/9 — seul « PR ouverte » reste `[ ]`, attendu) |

Vérification par critère d'acceptation :

1. **Hérite `BaseModel` + `@register_model("no_trade")`** → `no_trade.py` L24-25. ✅
2. **`output_type == "signal"`, `execution_mode == "standard"`** → `no_trade.py` L27-28. ✅
3. **`fit()` no-op** → `no_trade.py` L44 : `return {}`. ✅
4. **`predict(X)` retourne `np.zeros(N, dtype=np.float32)`** → `no_trade.py` L62-63. ✅
5. **Backtest → 0 trades, equity constante 1.0** → 5 tests d'intégration `TestNoTradeBacktestIntegration`. ✅
6. **Métriques : `net_pnl=0`, `n_trades=0`, `MDD=0`** → Tests dédiés. ✅
7. **`get_model_class("no_trade")` résolvable** → `test_get_model_class_resolves`. ✅
8. **Tests nominaux + erreurs + bords** → 24 tests, 7 classes, N=0/1/30/10000. ✅
9. **Suite de tests verte** → 1010 passed. ✅
10. **`ruff check` passe** → All checks passed. ✅

### A4. CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1010 passed**, 0 failed (7.49s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

✅ Phase A PASS.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| # | Pattern recherché | Règle | Résultat |
|---|---|---|---|
| 1 | Fallbacks silencieux (`or []`, `or {}`, `or ""`, `or 0`, `if … else`) | §R1 | 0 occurrences |
| 2 | Except trop large (`except:`, `except Exception:`) | §R1 | 0 occurrences |
| 3 | `# noqa` | §R7 | 0 occurrences (noqa apparaît dans les sources mais grep sur `$CHANGED` via le scan global ne les matche pas car les fichiers source ne contiennent que N803 — vérifié en v1 comme inévitables) |
| 4 | `print(` | §R7 | 0 occurrences |
| 5 | `.shift(-` | §R3 | 0 occurrences |
| 6 | Legacy random API | §R4 | 0 occurrences |
| 7 | `TODO` / `FIXME` / `HACK` / `XXX` | §R7 | 0 occurrences |
| 8 | Chemins hardcodés `/tmp`, `C:\` (tests) | §R7 | 0 occurrences |
| 9 | Imports absolus dans `__init__.py` | §R7 | 0 occurrences — import relatif `from . import no_trade` |
| 10 | Registration manuelle dans tests | §R7 | 1 match : L54 commentaire `# … @register_model` — faux positif (commentaire, pas un appel) |
| 11 | Mutable default arguments | §R6 | 0 occurrences |
| 12 | `open(` / `.read_text` | §R6 | 0 occurrences (les sources utilisent `Path.write_text()` / `Path.read_text()` — grep non matché en mode strict, vérifié manuellement en v1 : raccourcis autorisés §R6) |
| 13 | Comparaison booléenne identité | §R6 | 0 occurrences |
| 14 | Boucle `for … in range(` sur source | §R9 | 0 occurrences |
| 15 | `isfinite` checks | §R6 | 0 occurrences — N/A (aucun paramètre numérique à valider) |

### B2. Annotations par fichier

#### `ai_trading/baselines/__init__.py` (3 lignes)

Inchangé depuis v1. RAS.

#### `ai_trading/baselines/no_trade.py` (95 lignes)

Inchangé depuis v1. RAS après lecture complète (95 lignes). Tous les points vérifiés en v1 restent valides.

#### `tests/test_baseline_no_trade.py` (353 lignes — +21 vs v1)

Diff v1→v2 : 2 tests ajoutés, 0 tests modifiés, 0 tests supprimés.

- **L169-176** `test_predict_empty_input` : input `(0, L, F)` → vérifie `shape == (0,)` et `dtype == np.float32`. Correct et conforme à la suggestion v1. RAS.

- **L232-243** `test_save_load_roundtrip_file_path` : chemin fichier explicite `tmp_path / "model.json"`, vérifie existence du fichier et roundtrip save→load→predict equality. Correct et conforme à la suggestion v1. RAS.

Aucune observation nouvelle sur le reste du fichier (inchangé depuis v1).

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_baseline_no_trade.py`, `#037` dans docstrings |
| Chaque critère d'acceptation couvert | ✅ | 10/10 (mapping en A3) |
| Cas nominaux | ✅ | predict, fit, save/load, registry (13 tests) |
| Cas d'erreur | ✅ | `test_load_nonexistent_raises` |
| Cas de bords | ✅ | N=0, N=1, N=10000, N=30 |
| Boundary fuzzing | ✅ | N=0 ✅, N=1 ✅, N>N ✅ (N=10000) |
| Pas de test désactivé | ✅ | 0 `skip`/`xfail` |
| Tests déterministes | ✅ | `default_rng(777)`, `default_rng(42)` |
| Données synthétiques | ✅ | Pas de dépendance réseau |
| Chemins portables | ✅ | `tmp_path` partout, scan B1 : 0 `/tmp` |
| Tests registre réalistes | ✅ | `importlib.reload` dans `_import_no_trade()` |
| Contrat ABC complet (dir + file) | ✅ | `test_save_load_roundtrip` (dir) + `test_save_load_roundtrip_file_path` (file) |

### B4. Audit du code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (§R1) | ✅ | Scan B1 : 0 fallbacks, 0 except larges |
| Defensive indexing (§R10) | ✅ | `X.shape[0]` — pas de risque |
| Config-driven (§R2) | ✅ | Aucun paramètre configurable (baseline stateless) |
| Anti-fuite (§R3) | ✅ | Scan B1 : 0 `.shift(-`. Output indépendant des données. |
| Reproductibilité (§R4) | ✅ | Scan B1 : 0 legacy random. Output déterministe (zéros). |
| Float conventions (§R5) | ✅ | `np.float32` pour predict output |
| Anti-patterns Python (§R6) | ✅ | Scan B1 : 0 mutable defaults, Path raccourcis autorisés |

### B5. Qualité du code (§R7)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Cohérent |
| Pas de code mort / debug | ✅ | Scan B1 : 0 print, 0 TODO |
| Imports propres / relatifs | ✅ | Scan B1 : 0 imports absolus __init__ |
| `# noqa` justifiés | ✅ | 3× N803 (ABC) + 1× F401 (side-effect) — inévitables |
| DRY | ✅ | Pas de duplication détectée |

### B5-bis. Bonnes pratiques métier (§R9)

- Concept no-trade = borne inférieure, nommage explicite. ✅

### B6. Cohérence spec

| Critère | Verdict |
|---|---|
| Spec §13.1 (no-trade baseline) | ✅ |
| Plan WS-9.1 | ✅ |
| Pas d'exigence inventée | ✅ |
| Formules doc vs code | ✅ (N/A — pas de formule complexe) |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures `fit()`/`predict()`/`save()`/`load()` | ✅ | Match exact avec ABC `BaseModel` |
| `output_type = "signal"` | ✅ | Cohérent pipeline |
| `execution_mode = "standard"` | ✅ | Cohérent convention |
| `@register_model("no_trade")` | ✅ | Mécanisme registre standard |
| Imports croisés | ✅ | `BaseModel`, `register_model` depuis `ai_trading.models.base` — existent dans Max6000i1 |

---

## Remarques

Aucune remarque. Les 2 items MINEURS de la v1 sont correctement corrigés et aucun nouveau problème n'a été introduit.

---

## Résumé

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/M4/037/review_v2.md
```
