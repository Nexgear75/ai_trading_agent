# Revue PR — [WS-10] #041 — Métriques de trading

Branche : `task/041-trading-metrics`
Tâche : `docs/tasks/M4/041__ws10_trading_metrics.md`
Date : 2026-03-02
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Le module `metrics/trading.py` implémente correctement toutes les métriques de trading spécifiées (net_pnl, MDD, Sharpe, profit_factor, hit_rate, exposure, sharpe_per_trade) avec une bonne couverture de tests (cas nominaux, erreurs, bords). Les formules sont conformes à la spec §14.2 et Annexe E.2.5. Deux items mineurs empêchent le verdict CLEAN : la checklist de tâche incomplète et un test tautologique.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/041-*` | ✅ | `git branch --show-current` → `task/041-trading-metrics` |
| Commit RED présent | ✅ | `f3f6c16` — `[WS-10] #041 RED: trading metrics tests (...)` |
| Commit RED contient uniquement tests | ✅ | `git show --stat f3f6c16` → 1 fichier : `tests/test_trading_metrics.py` |
| Commit GREEN présent | ✅ | `dfa6347` — `[WS-10] #041 GREEN: trading metrics module (...)` |
| Commit GREEN contient impl + tâche | ✅ | `git show --stat dfa6347` → `ai_trading/metrics/trading.py`, `ai_trading/metrics/__init__.py`, `docs/tasks/M4/041__ws10_trading_metrics.md`, `tests/test_trading_metrics.py` (4 fichiers) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Diff montre `Statut : TODO` → `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (15/15) | Tous les critères passés de `[ ]` à `[x]` dans le diff |
| Checklist cochée | ⚠️ (7/9) | Items cochés: 7/9. **Deux items restent `[ ]`** : « Commit GREEN » et « Pull Request ouverte ». Le commit GREEN existe (dfa6347). |

→ **MINEUR #1** : Checklist de fin de tâche incomplète — voir section Remarques.

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1160 passed**, 0 failed, 0 errors ✅ |
| `ruff check ai_trading/ tests/` | **All checks passed** ✅ |

**Phase A : PASS** (pas de bloquant CI). On continue en Phase B.

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, etc.) | §R1 | 0 occurrences ✅ |
| Except trop large (`except:`, `except Exception:`) | §R1 | 0 occurrences ✅ |
| Print résiduel | §R7 | 0 occurrences ✅ |
| Shift négatif (`.shift(-`) | §R3 | 0 occurrences ✅ |
| Legacy random API | §R4 | 0 occurrences ✅ |
| TODO/FIXME orphelins | §R7 | 0 occurrences ✅ |
| Chemins hardcodés `/tmp` (tests) | §R7 | 0 occurrences ✅ |
| Imports absolus `__init__.py` | §R7 | 0 occurrences ✅ |
| Registration manuelle tests | §R7 | 0 occurrences (N/A — pas de registre) ✅ |
| Mutable default arguments | §R6 | 0 occurrences ✅ |
| `open()` sans context manager | §R6 | 0 occurrences (pas d'I/O fichier) ✅ |
| Comparaison booléenne par identité (`is True/False`) | §R6 | 0 occurrences ✅ |
| Dict collision silencieuse | §R6 | 0 occurrences ✅ |
| Boucle Python sur array numpy | §R9 | 0 occurrences ✅ |
| `isfinite` validation | §R6 | 2 occurrences : L62 (`sharpe_epsilon`), L80 (`timeframe_hours`) — validations correctes ✅ |
| Appels numpy dans compréhension | §R9 | 5 occurrences : `np.array([t["r_net"] for t in trades])` — **faux positif**, c'est `np.array()` d'une list comprehension (pattern standard, pas d'alternative vectorisée) ✅ |
| `noqa` | §R7 | 2 occurrences dans `__init__.py` : `F401` pour imports side-effect — **justifié** ✅ |
| Fixtures dupliquées | §R7 | 0 occurrences ✅ |

### Annotations par fichier (B2)

#### `ai_trading/metrics/trading.py` (365 lignes — fichier entier lu)

- **L62-68** `_validate_sharpe_epsilon` : checks `isfinite` puis `<= 0`. Correct — NaN/inf rejeté avant test de bornes. ✅

- **L80-83** `_validate_timeframe_hours` : checks `isfinite` et `<= 0`. Correct. ✅

- **L97-101** `compute_net_pnl` : `equity[-1] / equity[0] - 1.0`. Formule spec §14.2 : `E_T - E_0` avec `E_0 = 1.0` soit `E_T - 1`. L'implémentation normalise par `E_0` (`E_T/E_0 - 1`), ce qui est mathématiquement identique quand `E_0 = 1.0` et plus robuste pour `E_0 ≠ 1.0`. **Conforme**. ✅

- **L109-115** `compute_max_drawdown` : `running_peak = np.maximum.accumulate(equity)` puis `(running_peak - equity) / running_peak`. Vectorisé, conforme à la formule spec `max_t((peak_t - E_t) / peak_t)`. ✅

- **L142-147** `compute_sharpe` : `returns = equity[1:] / equity[:-1] - 1.0`, `mean(returns) / (std(ddof=0) + ε)`. Conforme spec. `ddof=0` (population std) est le standard pour Sharpe. ✅

- **L148-150** Sharpe annualisé : `sharpe * sqrt(365.25 * 24 / timeframe_hours)`. Conforme spec $\sqrt{K}$. ✅

- **L164-186** `compute_profit_factor` : gère les 4 cas spec E.2.5 (0 trades → None, only winners → None, only losers → 0.0, normal → ratio). Conforme. ✅

- **L175** Cas où tous les trades ont `r_net = 0` : `len(gains) == 0 and len(losses) == 0` → `None`. Cohérent — un trade breakeven n'est ni gagnant ni perdant. ✅

- **L258-262** `compute_exposure_time_frac` : `np.sum(in_trade) / len(in_trade)`. Simple et correct. ✅

- **L303-365** `compute_trading_metrics` : agrège toutes les métriques. Le cas `n_trades == 0` court-circuite avec les valeurs spec (sharpe=None, profit_factor=None, etc.). `net_pnl` et `max_drawdown` sont calculés normalement (pas hardcodés). Conforme. ✅

- **Note** — aucune validation de finitude sur les valeurs `r_net` des trades ni sur les valeurs `equity`. Si l'amont produit un NaN dans `r_net` ou `equity`, les métriques propagent silencieusement NaN. Toutefois, ces données proviennent de modules internes (`costs.apply_cost_model`, `engine.build_equity_curve`) qui valident déjà leurs sorties. Risque faible mais à noter.
  Sévérité : **pas d'item** (données internes, amont validé).

#### `ai_trading/metrics/__init__.py` (6 lignes — diff complet lu)

- Import relatif `from . import trading` ajouté. `# noqa: F401` justifié. ✅
- RAS après lecture complète du diff (6 lignes).

#### `tests/test_trading_metrics.py` (541 lignes — fichier entier lu)

- **L30-42** Helpers `_make_equity_curve` et `_make_trades` : synthétiques, pas de dépendance réseau, déterministes. ✅

- **L456** `TestFloat64Convention.test_all_float64` : `isinstance(val, float)` → vérifie correctement le type Python `float` (toujours 64-bit en CPython). **Cependant**, l'assertion L469 `assert np.finfo(np.float64).eps < 1e-15` est **tautologique** — elle vérifie une constante du type float64, pas la précision des valeurs réellement retournées. L'assertion est toujours vraie indépendamment du résultat de `compute_trading_metrics`.
  Sévérité : **MINEUR #2** — test qui ne prouve rien de plus que `isinstance`.
  Suggestion : supprimer la ligne tautologique ou la remplacer par une vérification sur les valeurs réelles (ex : `assert np.isclose(val, np.float64(val))`).

- **Coverage des critères d'acceptation** — mapping complet vérifié :

  | Critère d'acceptation | Test(s) couvrant |
  |---|---|
  | net_pnl/net_return corrects | `TestNetPnl` (5 tests : flat, gain, loss, non-unit E0, single candle) |
  | max_drawdown ∈ [0,1] | `TestMaxDrawdown` (6 tests : no dd, known, total, multiple, flat, single) |
  | sharpe sur grille complète | `TestSharpe` (7 tests : flat, positive, negative, includes zeros, annualized, single candle) |
  | profit_factor cas limites E.2.5 | `TestProfitFactor` (7 tests : normal, 0 trades, only winners, only losers, single win/loss, zero return) |
  | hit_rate | `TestHitRate` (5 tests : all win, all loss, mixed, 0 trades, zero return) |
  | n_trades | Vérifié dans `TestComputeTradingMetrics.test_nominal_aggregate` et `TestZeroTrades` |
  | avg/median trade return | `TestAvgTradeReturn` (2 tests), `TestMedianTradeReturn` (3 tests) |
  | exposure_time_frac | `TestExposureTimeFrac` (3 tests : no/full/partial exposure) |
  | sharpe_per_trade | `TestSharpePerTrade` (3 tests : nominal, 0 trades, single trade) |
  | n_trades == 0 all metrics | `TestZeroTrades.test_zero_trades_aggregate` — vérifie les 11 champs spec |
  | Sharpe annualisé | `TestSharpe.test_annualized` + `TestComputeTradingMetrics.test_annualized_sharpe_in_aggregate` |
  | Float64 | `TestFloat64Convention.test_all_float64` |
  | Cas erreurs/bords | `TestValidation` (7 tests : empty EC, missing columns, missing r_net, NaN/zero/neg epsilon, non-positive timeframe) |

- **Boundary fuzzing** :
  - `sharpe_epsilon` : testé pour NaN, 0.0, négatif → ✅
  - `timeframe_hours` : testé pour 0.0 → ✅
  - Single candle equity : testé (net_pnl, MDD, sharpe) → ✅
  - Single trade : testé (sharpe_per_trade) → ✅
  - 0 trades : testé pour toutes les fonctions → ✅

- **Boundary fuzzing — taux/proportions** : N/A — ce module ne manipule pas de taux de frais (fee_rate, slippage_rate). Les paramètres numériques validés sont `sharpe_epsilon` (> 0, isfinite) et `timeframe_hours` (> 0, isfinite). Pas de formule `(1 - p)` ou `(1 + p)`.

- **Seeds fixées** : N/A — pas de composante aléatoire dans les tests (données synthétiques déterministes). ✅

- **Portabilité chemins** : scan B1 confirme 0 `/tmp` hardcodé. Pas de paths dans les tests. ✅

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅ | Mapping complet ci-dessus — 15/15 critères couverts |
| Cas nominaux + erreurs + bords | ✅ | 12 classes de test, 48+ tests couvrant les 3 catégories |
| Boundary fuzzing | ✅ | epsilon=NaN/0/neg, timeframe=0, single candle, 0 trades, single trade |
| Déterministes | ✅ | Données synthétiques, pas d'aléa |
| Portabilité chemins | ✅ | Scan B1: 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre dans ce module |
| Contrat ABC complet | N/A | Pas d'ABC dans ce module |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) §R1 | ✅ | Scan B1: 0 fallback, 0 except large. Validation explicite + raise dans 5 validateurs. |
| Defensive indexing §R10 | ✅ | `equity[-1]` safe (EC validée non-vide L30). `equity[1:]/equity[:-1]` safe (guard L143 `len < 2 → None`). `running_peak = np.maximum.accumulate` safe car array non-vide. |
| Config-driven §R2 | ✅ | `sharpe_epsilon` et `sharpe_annualized` sont des paramètres explicites, lus depuis config par l'appelant. Valeurs présentes dans `configs/default.yaml` L209-210. |
| Anti-fuite §R3 | ✅ | Scan B1: 0 `.shift(-`. Module de métriques post-hoc (pas de look-ahead possible). |
| Reproductibilité §R4 | ✅ | Scan B1: 0 legacy random. Module déterministe (pas de composante aléatoire). |
| Float conventions §R5 | ✅ | Tous les calculs en `np.float64` explicite. Retours via `float()` (= float64 en CPython). |
| Anti-patterns Python §R6 | ✅ | Scan B1: 0 mutable defaults, 0 open sans context manager, 0 `is True/False`. `isfinite` utilisé pour epsilon et timeframe. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Tous les noms conformes (compute_net_pnl, compute_max_drawdown, etc.) |
| Pas de code mort/debug | ✅ | Scan B1: 0 print, 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | `__init__.py` utilise `from . import`. `trading.py` : 4 imports (math, numpy, pandas, __future__) — propres, ordonnés. |
| DRY | ✅ | Extraction des r_nets en `np.array` est répétée dans 5 fonctions mais chaque fonction est indépendante et publique — pas de duplication de logique métier. |
| `noqa` justifiés | ✅ | 2 `noqa: F401` dans `__init__.py` pour imports side-effect — standard. |

### Bonnes pratiques métier (B5-bis) §R9

| Critère | Verdict | Preuve |
|---|---|---|
| Exactitude concepts financiers | ✅ | MDD, Sharpe, profit factor, hit rate — formules canoniques conformes spec. |
| Nommage métier cohérent | ✅ | `net_pnl`, `max_drawdown`, `sharpe`, `profit_factor`, `hit_rate`, `exposure_time_frac` |
| Séparation responsabilités | ✅ | Module dédié aux métriques trading, pas de mélange avec backtest/features |
| Vectorisation numpy | ✅ | Scan B1: 0 boucle range(). Calculs vectorisés (np.maximum.accumulate, slicing). |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Preuve |
|---|---|---|
| §14.2 formules | ✅ | net_pnl=E_T/E_0-1, MDD=max((peak-E)/peak), Sharpe=mean(r)/std(r)+ε — conformes |
| Annexe E.2.5 profit_factor | ✅ | 4 cas (0 trades→null, only win→null, only loss→0.0, normal→ratio) conformes |
| Plan WS-10.2 | ✅ | Module, tests et tâche créés comme prévu |
| Formules doc vs code | ✅ | Aucun off-by-one détecté. Formules vérifiées ligne par ligne. |

### Cohérence intermodule (B7)

| Critère | Verdict | Preuve |
|---|---|---|
| Clé `r_net` dans trades | ✅ | Produite par `costs.py` L101, consommée par `engine.py` L139, cohérent avec `trading.py`. |
| Colonnes equity curve (`equity`, `in_trade`) | ✅ | Produites par `engine.build_equity_curve` (vérifié grep), consommées par `trading.py` avec validation. |
| Clés retour dict | ✅ | `net_pnl`, `net_return`, `max_drawdown`, `sharpe`, `profit_factor`, `hit_rate`, `n_trades`, `avg_trade_return`, `median_trade_return`, `exposure_time_frac`, `sharpe_per_trade` — conforme au schema `metrics.schema.json`. |
| Config keys | ✅ | `metrics.sharpe_epsilon`, `metrics.sharpe_annualized` présents dans `configs/default.yaml` L209-210. |
| Imports croisés | ✅ | `trading.py` n'importe aucun autre module du projet (standalone). |

---

## Remarques

1. **[MINEUR]** Checklist de fin de tâche incomplète.
   - Fichier : `docs/tasks/M4/041__ws10_trading_metrics.md`
   - Ligne(s) : dernières lignes de la checklist
   - Description : Les items « Commit GREEN » et « Pull Request ouverte » sont restés `[ ]` alors que le commit GREEN `dfa6347` existe. Inconsistance tâche ↔ état réel.
   - Suggestion : Cocher `[x]` sur l'item « Commit GREEN » (le commit existe). L'item « Pull Request ouverte » peut rester `[ ]` s'il est coché au moment de la création effective de la PR.

2. **[MINEUR]** Test float64 avec assertion tautologique.
   - Fichier : `tests/test_trading_metrics.py`
   - Ligne(s) : ~L469 dans `TestFloat64Convention.test_all_float64`
   - Description : L'assertion `assert np.finfo(np.float64).eps < 1e-15` vérifie une constante du type (`np.finfo(np.float64).eps ≈ 2.22e-16`) — elle est toujours vraie, indépendamment des valeurs retournées par `compute_trading_metrics`. Elle ne prouve pas que les métriques sont effectivement en float64.
   - Suggestion : Supprimer cette assertion tautologique. Le `isinstance(val, float)` au-dessus est suffisant (Python `float` = IEEE 754 double = float64).

---

## Résumé

| Sévérité | Nombre |
|---|---|
| BLOQUANT | 0 |
| WARNING | 0 |
| MINEUR | 2 |

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 2
- Rapport : `docs/tasks/M4/041/review_v1.md`
