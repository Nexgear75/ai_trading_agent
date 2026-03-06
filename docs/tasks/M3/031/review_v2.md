# Revue PR — [WS-7] #031 — Objectif d'optimisation et sélection du seuil θ (v2)

Branche : `task/031-theta-optimization`
Tâche : `docs/tasks/M3/031__ws7_theta_optimization.md`
Date : 2026-03-02
Itération : v2 (re-review après correction du MINEUR v1)

## Verdict global : ✅ CLEAN

## Résumé

Re-review après correction de l'item MINEUR v1. Le test `test_equity_independent_per_candidate` compare désormais les métriques (net_pnl, mdd, n_trades) d'un run multi-candidats vs des runs solo, prouvant l'absence de cross-contamination entre candidats. Le code source (`threshold.py`) est inchangé depuis v1. Aucun nouveau problème détecté. 0 BLOQUANT, 0 WARNING, 0 MINEUR.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/031-theta-optimization` | ✅ | `git branch --show-current` → `task/031-theta-optimization` |
| Commit RED présent | ✅ | `9afb4b1` — `[WS-7] #031 RED: tests objectif d'optimisation et sélection θ` — 1 fichier : `tests/test_theta_optimization.py` |
| Commit GREEN présent | ✅ | `88dc493` — `[WS-7] #031 GREEN: objectif d'optimisation et sélection θ` — 2 fichiers : `ai_trading/calibration/threshold.py`, `docs/tasks/M3/031__ws7_theta_optimization.md` |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline` : RED → GREEN consécutifs, pas de commit intermédiaire |
| Commits post-GREEN | ✅ | `0ea7106` (correction agents, fichiers `.github/agents/` uniquement — non lié au code métier), `5cf3786` (FIX : tests uniquement). Acceptables. |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ — `Statut : DONE` dans le fichier de tâche |
| Critères d'acceptation cochés | ✅ — 11/11 `[x]` |
| Checklist cochée | ✅ — 8/9 `[x]` (le 9e item « PR ouverte » est `[ ]`, normal car PR pas encore créée) |

#### Vérification des critères d'acceptation vs code/tests

| Critère | Preuve code/test |
|---|---|
| θ retenu respecte mdd ≤ mdd_cap ET n_trades ≥ min_trades | `threshold.py` L229 : `feasible = (mdd <= mdd_cap) and (n_trades >= min_trades)` ; tests `TestCalibrateThresholdConstraints` |
| θ retenu maximise net_pnl parmi faisables | `threshold.py` L238 : `sort(key=lambda d: (-d["net_pnl"], -d["quantile"]))` ; test `TestCalibrateThresholdBestPnl` |
| Ex-aequo → quantile le plus haut | Même sort key (`-d["quantile"]`) ; test `TestCalibrateThresholdTiebreaker` |
| Test : un seul θ faisable → sélection correcte | `TestCalibrateThresholdSingleFeasible` |
| Test : plusieurs θ faisables → meilleur net_pnl | `TestCalibrateThresholdBestPnl` |
| Equity réinitialisée E_0 pour chaque candidat | `threshold.py` L213-220 : appel frais `build_equity_curve(initial_equity=...)` par itération ; test `TestCalibrateThresholdEquityReset.test_equity_independent_per_candidate` (solo vs multi) |
| Anti-fuite : modifier y_hat_test → θ identique | `calibrate_threshold` n'accepte pas de paramètre test ; test `TestCalibrateThresholdAntiLeak` |
| Paramètres lus depuis config.thresholding | Test `TestCalibrateThresholdConfigDriven.test_config_keys_exist` vérifie `cfg.thresholding.objective`, `.mdd_cap`, `.min_trades` |
| Tests nominaux + erreurs + bords | 24 tests couvrant nominal (4), erreurs (5), bords (zero trades, no feasible, constant, details), anti-fuite, config-driven, equity reset |
| Suite de tests verte | 873 passed, 0 failed |
| ruff clean | All checks passed |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **873 passed**, 0 failed ✅ |
| `ruff check ai_trading/ tests/` | **All checks passed** ✅ |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (§R1) | `grep ' or \[\]\| or {}\| or ""\| or 0\b\| if .* else '` | 1 match L64 — faux positif (docstring : `"1 if y_hat[t] > theta, else 0"`) |
| Except trop large (§R1) | `grep 'except:$\|except Exception:'` | 0 occurrences ✅ |
| Print résiduel (§R7) | `grep 'print('` | 0 occurrences ✅ |
| Shift négatif (§R3) | `grep '.shift(-'` | 0 occurrences ✅ |
| Legacy random API (§R4) | `grep 'np.random.seed\|np.random.randn\|np.random.RandomState\|random.seed'` | 0 occurrences ✅ |
| TODO/FIXME (§R7) | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences ✅ |
| Chemins hardcodés (§R7) | `grep '/tmp\|/var/tmp\|C:\\'` tests | 0 occurrences ✅ |
| Imports absolus __init__ (§R7) | `grep 'from ai_trading\.'` calibration/__init__.py | 0 occurrences ✅ |
| Registration manuelle (§R7) | `grep 'register_model\|register_feature'` tests | 0 occurrences ✅ |
| Mutable defaults (§R6) | `grep 'def .*=\[\]\|def .*={}'` | 0 occurrences ✅ |
| open() sans context manager (§R6) | `grep '.read_text\|open('` src | 0 occurrences ✅ |
| Bool identity (§R6) | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences ✅ |
| noqa suppressions (§R7) | `grep 'noqa'` | 0 occurrences ✅ |
| isfinite validation (§R6) | `grep 'isfinite'` src | 1 match L47 : `math.isfinite(q)` — validation correcte des q_grid values ✅ |
| for range loop (§R9) | `grep 'for .* in range(.*):` src | 0 occurrences ✅ |
| numpy comprehension (§R9) | `grep 'np\.[a-z]*(.*for .* in '` src | 0 occurrences ✅ |
| Fixtures dupliquées (§R7) | `grep 'load_config.*configs/'` tests | 0 occurrences (utilise fixture partagée `default_config_path`) ✅ |

### Annotations par fichier (B2)

#### `ai_trading/calibration/threshold.py` (184 lignes ajoutées)

Diff inchangé depuis v1. Relecture complète confirmée :

- **L88-114** `compute_max_drawdown` : Implémentation vectorisée (`np.maximum.accumulate`, `np.where`). Formule conforme spec §14.2 : `MDD = max_t((peak_t - E_t) / peak_t)`. Guard `running_max > 0` évite division par zéro. Retourne `float`. **RAS.**
- **L117-163** `calibrate_threshold` signature + validation : 11 paramètres explicites, aucun default, aucun kwargs caché. Validation ndim, size, length match, q_grid vide, objective inconnu. Strict code conforme §R1. **RAS.**
- **L168-171** Appel `compute_quantile_thresholds` — délègue la validation des q values (duplicates, NaN, bornes). **RAS.**
- **L176-230** Boucle d'évaluation : chaque itération appelle `apply_threshold` → `execute_trades` → `apply_cost_model` → `build_equity_curve` frais. Aucune variable d'état partagée entre itérations. Equity réinitialisée par construction (appel frais `build_equity_curve(initial_equity=...)`). **RAS.**
- **L212-220** Cas zéro trades : `net_pnl=0.0`, `mdd=0.0`, `n_trades=0`. Pas de division par zéro, pas d'appel `build_equity_curve` avec liste vide. **RAS.**
- **L229** Condition feasible : `(mdd <= mdd_cap) and (n_trades >= min_trades)`. Conforme spec §11.3. **RAS.**
- **L238** Sort : `key=lambda d: (-d["net_pnl"], -d["quantile"])`. Maximise net_pnl, tiebreaker = plus haut quantile. Conforme spec. **RAS.**
- **L243-258** Retour structuré : 7 clés documentées. Cas no-feasible retourne `None` pour theta/quantile/metrics. **RAS.**
- **Type safety B2§1** : `y_hat_val` validé ndim=1 et size>0. `q_grid` validé non-vide. `objective` validé dans frozenset. `len(y_hat_val) != len(ohlcv_val)` vérifié. **RAS.**
- **Edge cases B2§2** : entrées vides/mismatch → ValueError. Zero trades → handled. No feasible → None return. **RAS.**
- **Domain bounds B2§3** : `fee_rate_per_side` et `slippage_rate_per_side` sont validés dans `apply_cost_model` (module amont, tâche #027). `position_fraction` validé dans `build_equity_curve` (module amont, tâche #029). `mdd_cap` et `min_trades` sont des contraintes de filtrage, pas des multiplicateurs — pas de risque domaine. **RAS.**
- **Return contract B2§5** : dict always returned with same keys. **RAS.**
- **Resource cleanup B2§6** : no file I/O, no connections. **RAS.**
- **Doc/code B2§7** : docstring matches behavior. **RAS.**

#### `tests/test_theta_optimization.py` (24 tests, 33 lignes modifiées dans FIX)

FIX commit diff vérifié (`git diff 0ea7106..5cf3786`). Modifications limitées à la classe `TestCalibrateThresholdEquityReset` :

- **L283-320 (FIX)** `test_equity_independent_per_candidate` : le test exécute `calibrate_threshold` avec `q_grid=[0.3, 0.5, 0.7]` (multi), puis exécute chaque q en solo (`q_grid=[q]`). Compare `net_pnl`, `mdd`, `n_trades` via `pytest.approx` pour floats et `==` pour int. Prouve que les métriques d'un candidat sont identiques qu'il soit évalué seul ou avec d'autres → **indépendance réelle vérifiée**. Correction conforme à la suggestion v1. **RAS.**

Reste du fichier inchangé depuis v1 :
- Seeds déterministes : `default_rng(42)`, `default_rng(123)`. ✅
- Données synthétiques (pas réseau). ✅
- Fixture `default_config_path` partagée (conftest.py). ✅
- Pas de `@pytest.mark.skip` / `xfail`. ✅
- Pas de chemin `/tmp` hardcodé. ✅
- Couverture : nominal (single feasible, best pnl, tiebreaker), erreurs (empty, mismatch, invalid objective, 2D, empty q_grid), bords (no feasible, zero trades, constant predictions, details keys/count), anti-fuite, config-driven, equity reset. ✅

### B3 — Vérification tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_theta_optimization.py`, `#031` dans docstrings |
| Couverture critères acceptation | ✅ | 11/11 critères couverts (tableau Phase A ci-dessus) |
| Cas nominaux + erreurs + bords | ✅ | 24 tests : 4 nominal, 5 erreurs, 15 bords/anti-fuite/config/details |
| Boundary fuzzing | ✅ | Zero trades (all predictions below θ), no feasible (impossible constraints), constant predictions, single q_grid, length mismatch |
| Pas de test désactivé | ✅ | 0 skip/xfail |
| Tests déterministes | ✅ | `default_rng(42)`, `default_rng(123)` |
| Données synthétiques | ✅ | `_make_ohlcv`, `_make_y_hat_val` helpers |
| Portabilité chemins | ✅ | 0 `/tmp` hardcodé |

### B4 — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code | ✅ | Scan B1 : 0 fallback, 0 except large. Validation explicite + raise. |
| §R2 Config-driven | ✅ | `calibrate_threshold` reçoit tous params en arguments. Config YAML contient `thresholding.objective`, `.mdd_cap`, `.min_trades`, `.q_grid`. Test `test_config_keys_exist`. |
| §R3 Anti-fuite | ✅ | θ calibré uniquement sur val (pas de param test dans signature). Scan B1 : 0 `.shift(-`. Test `test_theta_invariant_to_test_data`. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random API. Tests déterministes (seeds). |
| §R5 Float conventions | ✅ | `equity_array = equity_df["equity"].to_numpy(dtype=np.float64)` — float64 pour métriques. |
| §R6 Anti-patterns | ✅ | Scan B1 : 0 mutable default, 0 open() sans context, 0 bool identity. `math.isfinite(q)` valide NaN/inf sur q_grid. |
| §R10 Defensive indexing | ✅ | `equity.size == 0` check. `equity[-1]` safe car size>0 garanti (enriched_trades non vide). |

### B5 — Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| snake_case | ✅ | Nommage conforme |
| Pas de code mort | ✅ | Scan B1 : 0 TODO/FIXME |
| Pas de print() | ✅ | Scan B1 : 0 occurrences |
| Imports propres | ✅ | ruff clean, pas de noqa |
| DRY | ✅ | Pas de duplication de formules |
| `__init__.py` à jour | ✅ | `ai_trading/calibration/__init__.py` — pas d'import nécessaire |

### B6 — Cohérence avec les specs

| Critère | Verdict | Preuve |
|---|---|---|
| Conforme spec §11.3 | ✅ | Maximise P&L net sous contraintes MDD ≤ mdd_cap, n_trades ≥ min_trades. Tiebreaker : quantile le plus haut. Config defaults (mdd_cap=0.25, min_trades=20) conformes aux exemples spec. |
| Conforme plan WS-7.2 | ✅ | Boucle d'optimisation, retour structuré, traçabilité details |
| Formules doc vs code | ✅ | MDD spec §14.2 : `(peak - E) / peak` → code L109. Sort tiebreaker spec : highest quantile → code L238. |

### B7 — Cohérence intermodule

| Critère | Verdict | Preuve |
|---|---|---|
| Signatures amont | ✅ | `execute_trades(signals, ohlcv, horizon, execution_mode)`, `apply_cost_model(trades, fee_rate_per_side, slippage_rate_per_side)`, `build_equity_curve(trades, ohlcv, initial_equity, position_fraction)` — tous les params transmis. |
| Imports existants | ✅ | `from ai_trading.backtest.costs import apply_cost_model`, `from ai_trading.backtest.engine import build_equity_curve, execute_trades` — modules existants dans Max6000i1. |
| Forwarding kwargs | ✅ | Tous les paramètres reçus par `calibrate_threshold` sont transmis aux sous-appels correspondants. |

---

## Vérification v1 → v2

| Item v1 | Sévérité | Statut v2 | Preuve |
|---|---|---|---|
| 1. `test_equity_independent_per_candidate` ne vérifiait que la structure, pas l'indépendance réelle | MINEUR | ✅ CORRIGÉ | Commit `5cf3786` : test compare maintenant metrics solo vs multi via `pytest.approx`. Diff vérifié. |

## Remarques

Aucune remarque. Tous les items de la v1 sont corrigés, aucun nouveau problème détecté.

## Résumé

Implémentation solide de `calibrate_threshold` et `compute_max_drawdown`, conforme à la spec §11.3. Code vectorisé, strict, config-driven, anti-fuite par design. 24 tests couvrent nominaux, erreurs, bords, anti-fuite, config-driven et indépendance equity (corrigé en v2). 873 tests GREEN, ruff clean. Aucun item ouvert.
