# Revue PR — [WS-12] #052 — Script de comparaison inter-stratégies (v2)

Branche : `task/052-compare-runs`
Tâche : `docs/tasks/M5/052__ws12_compare_runs.md`
Date : 2026-03-03
Itération : v2 (re-review après corrections v1)

## Verdict global : ✅ CLEAN

## Résumé

Re-review après le commit FIX `3de5059`. Les 3 items identifiés en v1 (W-1, W-2, M-1) sont tous correctement corrigés avec tests additionnels. Le scan automatisé complet, la lecture du diff FIX et l'exécution de la suite complète (1503 passed) ne révèlent aucun nouvel issue introduit par les corrections.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/052-compare-runs` | ✅ | `git branch --show-current` → `task/052-compare-runs` |
| Commit RED `[WS-12] #052 RED: tests comparaison inter-stratégies` | ✅ | hash `4af8ee0` — format conforme |
| Commit GREEN `[WS-12] #052 GREEN: script comparaison inter-stratégies` | ✅ | hash `25314a6` — format conforme |
| Commit FIX `[WS-12] #052 FIX: strict code .get()→[], buy_hold inclus §14.4, validation aggregate.trading.mean` | ✅ | hash `3de5059` — corrections post-review v1 |
| Commit RED = tests uniquement | ✅ | `git show --stat 4af8ee0` → `tests/test_compare_runs.py` (1 fichier) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 25314a6` → 5 fichiers (source, init, pyproject, tâche, tests) |
| Commit FIX = source + tests uniquement | ✅ | `git show --stat 3de5059` → 2 fichiers (`scripts/compare_runs.py`, `tests/test_compare_runs.py`) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (8/9 — item « Pull Request ouverte » non coché, attendu à ce stade) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_compare_runs.py -v --tb=short` | **26 passed**, 0 failed (+3 vs v1) |
| `pytest tests/ --tb=short -q` | **1503 passed**, 0 failed |
| `ruff check scripts/ tests/test_compare_runs.py` | **All checks passed** |

---

## Phase B — Code Review

### Vérification des corrections v1

#### W-1 : `.get()` silencieux → FIXED ✅

**Preuve** : `grep -n '\.get(' scripts/compare_runs.py` → **0 matches**.

Diff FIX L168-L173 : les 6 appels `.get("net_pnl")`, `.get("net_return")`, `.get("max_drawdown")`, `.get("sharpe")`, `.get("profit_factor")`, `.get("n_trades")` sont remplacés par des accès directs `trading_mean["net_pnl"]`, etc. Un `KeyError` explicite sera levé si une clé est absente — conforme §R1 (strict code).

#### W-2 : buy_hold exclu du §14.4 → FIXED ✅

**Preuve** : Diff FIX, `check_criterion_14_4` L214 :
```python
# §14.4 includes ALL baselines (go_nogo + contextual like buy_hold)
baselines = comparison[comparison["strategy_type"] == "baseline"]
```
Auparavant : `baselines = go_nogo[go_nogo["strategy_type"] == "baseline"]` (filtré sur go_nogo seul).

Le docstring a été mis à jour pour refléter le changement : *"Both go_nogo and contextual baselines are included."*

**Test additionnel** : `test_model_beats_only_buy_hold_returns_true` (L509-L537) — vérifie que si un modèle perd contre toutes les baselines go_nogo mais bat buy_hold, §14.4 retourne `True`. Test existant `test_buy_hold_included_in_criterion` (renommé depuis `test_contextual_buy_hold_excluded_from_criterion`) également mis à jour.

#### M-1 : validation `aggregate.trading.mean` manquante → FIXED ✅

**Preuve** : Diff FIX, `load_metrics` L98-L129 : validation complète ajoutée dans `load_metrics` :
- `aggregate` est un dict
- `aggregate` contient la clé `"trading"`
- `aggregate["trading"]` est un dict  
- `aggregate["trading"]` contient la clé `"mean"`
- `aggregate["trading"]["mean"]` est un dict

Chaque vérification lève un `ValueError` avec un message clair incluant le chemin du fichier.

**Tests additionnels** :
- `test_load_missing_aggregate_trading_mean_raises` : JSON avec `"aggregate": {}` → `ValueError` match `"trading"`
- `test_load_missing_trading_mean_raises` : JSON avec `"aggregate": {"trading": {}}` → `ValueError` match `"mean"`

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep -n ' or \[\]\| or {}\| or ""\| or 0\b\| if .* else '` | 0 matches |
| §R1 — Except trop large | `grep -n 'except:$\|except Exception:'` | 0 matches |
| §R1 — `.get()` silencieux | `grep -n '\.get('` | **0 matches** (corrigé depuis v1) |
| §R7 — Suppressions lint (`noqa`) | `grep -rn 'noqa'` | 0 matches |
| §R7 — Print résiduel | `grep -n 'print('` | 4 matches (L317, L332, L334, L336) — **faux positifs** : `print()` dans `main()` CLI entry point |
| §R3 — Shift négatif | `grep -n '\.shift(-'` | 0 matches |
| §R4 — Legacy random API | `grep -rn 'np\.random\.seed\|...'` | 0 matches |
| §R7 — TODO/FIXME orphelins | `grep -rn 'TODO\|FIXME\|...'` | 0 matches |
| §R7 — Chemins hardcodés OS (tests) | `grep -rn '/tmp\|C:\\'` tests/ | 0 matches |
| §R6 — Mutable default arguments | `grep -rn 'def .*=\[\]\|def .*={}'` | 0 matches |
| §R6 — `open()` sans context manager | `grep -rn '.read_text\|open('` | 1 match: L71 `p.read_text(encoding="utf-8")` — **faux positif** accepté |
| §R6 — Comparaison booléenne identité | `grep -rn 'is True\|is False'` tests/ | 5 matches — **faux positifs** : `check_criterion_14_4()` retourne `bool` natif |
| §R9 — Boucle Python sur array | `grep -n 'for .* in range'` | 0 matches |

### Annotations par diff FIX (B2)

#### `scripts/compare_runs.py` — diff FIX (52 insertions, 15 suppressions)

RAS après lecture complète du diff FIX. Les 3 modifications sont chirurgicales et correctes :
1. Ajout validation `aggregate.trading.mean` dans `load_metrics` (26 lignes) — logique correcte, messages d'erreur clairs.
2. Remplacement 6× `.get()` → `[]` dans `compare_strategies` — strict code conforme.
3. Modification `baselines` dans `check_criterion_14_4` pour inclure toutes les baselines — conforme §14.4.

Aucun nouveau pattern suspect introduit.

#### `tests/test_compare_runs.py` — diff FIX (71 insertions, 2 suppressions)

RAS après lecture complète du diff FIX. 3 tests ajoutés/modifiés :
1. `test_load_missing_aggregate_trading_mean_raises` — nouveau, couvre `aggregate: {}`.
2. `test_load_missing_trading_mean_raises` — nouveau, couvre `aggregate.trading: {}`.
3. `test_buy_hold_included_in_criterion` — renommé, docstring mis à jour.
4. `test_model_beats_only_buy_hold_returns_true` — nouveau, couvre le cas critique buy_hold seul.

Tous les tests utilisent `tmp_path`, données synthétiques, assertions précises.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_compare_runs.py`, docstrings avec `#052` |
| Couverture des critères d'acceptation | ✅ | 26 tests couvrent les 9 critères |
| Cas nominaux + erreurs + bords | ✅ | `TestLoadMetrics` (8 tests), `TestCompareStrategies` (6 tests), `TestCheckCriterion144` (7 tests), `TestOutputFiles` (2 tests), `TestCLI` (3 tests) |
| Déterministes | ✅ | Pas d'aléatoire |
| Données synthétiques | ✅ | `_make_metrics()` helper |
| Portabilité chemins | ✅ | `tmp_path` partout, 0 `/tmp` hardcodé |
| Tests registre réalistes | N/A | |
| Contrat ABC complet | N/A | |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | 0 `.get()`, 0 `or []`, 0 except large. Validation explicite dans `load_metrics`. |
| §R10 Defensive indexing | ✅ | Pas d'indexation array/slice. |
| §R2 Config-driven | ✅ | Script standalone post-MVP, paramètres via CLI. |
| §R3 Anti-fuite | ✅ | N/A — pas de calcul temporel. |
| §R4 Reproductibilité | ✅ | N/A — pas d'aléatoire. |
| §R5 Float conventions | ✅ | N/A — pas de tenseurs. |
| §R6 Anti-patterns Python | ✅ | Scans B1 tous clean. |
| §R7 Qualité du code | ✅ | snake_case, 0 TODO, imports propres, DRY. |
| §R8 Cohérence intermodule | ✅ | Module standalone dans `scripts/`, pas d'import `ai_trading/`. |
| §R9 Bonnes pratiques métier | ✅ | Comparaison P&L/MDD conforme aux concepts financiers. |

### Conformité spec v1.0

| Critère | Verdict |
|---|---|
| §13.4 — Séparation Go/No-Go vs contextuelle | ✅ — Colonne `comparison_type`, Markdown en deux sections. |
| §14.4 — Critère d'acceptation | ✅ — buy_hold désormais inclus. Test `test_model_beats_only_buy_hold_returns_true` le prouve. |
| Plan WS-12.5 | ✅ — Script CLI standalone post-MVP. |

---

## Remarques

Aucune.

## Résumé

Les 3 items de la v1 (W-1 `.get()` silencieux, W-2 buy_hold exclu de §14.4, M-1 validation `aggregate.trading.mean`) sont tous correctement corrigés avec tests additionnels couvrant chaque fix. Le scan automatisé B1, la lecture complète du diff FIX et l'exécution de la suite complète (1503 passed, ruff clean) ne révèlent aucun nouveau problème. Le code est conforme aux règles du projet et à la spécification.

---

RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : `docs/tasks/M5/052/review_v2.md`
