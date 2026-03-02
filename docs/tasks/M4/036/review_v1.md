# Revue PR — [WS-8] #036 — Validation du gate G-Backtest

Branche : `task/036-gate-backtest`
Tâche : `docs/tasks/M4/036__gate_backtest.md`
Date : 2025-03-02

## Verdict global : ✅ APPROVE (CLEAN)

## Résumé

Gate G-Backtest ajoutant 24 tests répartis en 6 classes couvrant les 6 critères du gate. Aucun code d'implémentation ajouté — seuls un fichier de tests et la mise à jour de la tâche. Tous les critères sont satisfaits, les conventions respectées, aucun défaut détecté.

---

## Phase A — Compliance

### A1. Périmètre

Fichiers modifiés vs `Max6000i1` :
```
docs/tasks/M4/036__gate_backtest.md
tests/test_gate_backtest.py
```
- 0 fichiers source (`ai_trading/`)
- 1 fichier tests (`tests/`)
- 1 fichier doc/tâche

### A2. Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche | ✅ | `task/036-gate-backtest` — conforme |
| Commit RED présent | ✅ | `5cc0c0f` — `[WS-8] #036 RED: gate G-Backtest validation tests (6 criteria)` |
| Commit GREEN présent | ✅ | `e6cbaca` — `[WS-8] #036 GREEN: gate G-Backtest validation — 24 tests, 6 criteria pass` |
| RED contient uniquement tests | ✅ | `git show --stat 5cc0c0f` → `tests/test_gate_backtest.py | 525 +++` (1 fichier) |
| GREEN contient impl + tâche | ✅ | `git show --stat e6cbaca` → `docs/tasks/M4/036__gate_backtest.md | 36 +/-` (1 fichier — gate, pas d'impl nécessaire) |
| Pas de commits parasites | ✅ | `git log --oneline` → exactement 2 commits (RED + GREEN) |

### A3. Tâche associée

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Diff : `Statut : TODO` → `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (9/9) | Tous `[ ]` → `[x]` dans le diff |
| Checklist cochée | ✅ (8/9) | 8/9 cochés ; le 9e `[ ] Pull Request ouverte` est logiquement non encore coché |

**Vérification des critères cochés vs preuves :**

| Critère | Preuve (test(s) correspondant(s)) |
|---|---|
| C1 — Déterminisme | `TestDeterminism.test_trades_csv_sha256_identical` (L119), `test_equity_curve_identical` (L131) |
| C2 — Cohérence equity-trades | `TestEquityTradeCoherence.test_equity_final_matches_product_formula` (L160), `test_coherence_single_trade` (L175), `test_coherence_no_trades` (L188), `test_coherence_multiple_trades` (L199) |
| C3 — One-at-a-time | `TestOneAtATime.test_dense_signals_no_overlap` (L221), `test_consecutive_signals_skip_while_in_position` (L239), `test_no_overlap_with_alternating_signals` (L252) |
| C4 — Coûts | `TestCostsHandComputed.test_cost_formulas_match_hand_calculation` (L266, 4 cas paramétrés), `test_zero_cost_rates_no_drag` (L323), `test_costs_always_reduce_return` (L337) |
| C5 — trades.csv parseable | `TestTradesCSVConformity` (5 tests L360-L423) |
| C6 — Anti-fuite | `TestAntiLeak` (3 tests L432-L525) |
| Scénarios nominaux + erreurs + bords | ✅ Voir mapping détaillé B3 ci-dessous |
| Suite verte | ✅ 986 passed (ci-dessous) |
| ruff clean | ✅ (ci-dessous) |

### A4. CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **986 passed**, 0 failed (7.20s) |
| `ruff check ai_trading/ tests/` | **All checks passed!** |

**Phase A : PASS** — passage à la Phase B.

---

## Phase B — Code Review

### B1. Scan automatisé obligatoire (GREP)

| Pattern recherché (§) | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep -n ' or []\| or {}...' tests/test_gate_backtest.py` | 1 match L277 — analysé ci-dessous : **faux positif** |
| §R1 Except trop large | `grep -n 'except:$\|except Exception:' tests/test_gate_backtest.py` | 0 occurrences (grep exécuté) |
| §R7 noqa | `grep -rn 'noqa' tests/test_gate_backtest.py docs/tasks/M4/036__gate_backtest.md` | 0 occurrences (grep exécuté) |
| §R7 Print résiduel | `grep -n 'print(' tests/test_gate_backtest.py` | 0 occurrences (grep exécuté) |
| §R3 Shift négatif | `grep -n '.shift(-' tests/test_gate_backtest.py` | 0 occurrences (grep exécuté) |
| §R4 Legacy random API | `grep -rn 'np.random.seed...' tests/test_gate_backtest.py docs/tasks/M4/036__gate_backtest.md` | 0 occurrences (grep exécuté) |
| §R7 TODO/FIXME | `grep -rn 'TODO\|FIXME\|HACK\|XXX' ...` | 0 occurrences (grep exécuté) |
| §R7 Chemins hardcodés OS | `grep -n '/tmp\|C:\\' tests/test_gate_backtest.py` | 0 occurrences (grep exécuté) |
| §R7 Registration manuelle tests | `grep -n 'register_model\|register_feature' tests/test_gate_backtest.py` | 0 occurrences (grep exécuté) — N/A (gate test, pas de registre) |
| §R6 Mutable defaults | `grep -rn 'def .*=[]\|def .*={}' ...` | 0 occurrences (grep exécuté) |
| §R6 is True/False (numpy) | `grep -rn 'is np.bool_\|is True\|is False' ...` | 0 occurrences (grep exécuté) |
| §R7 Fixtures dupliquées | `grep -n 'load_config.*configs/' tests/test_gate_backtest.py` | 0 occurrences (grep exécuté) |
| §R9 for range (vectorisation) | `grep -n 'for .* in range(.*):' tests/test_gate_backtest.py` | 2 matches L251, L281 — analysés ci-dessous |

**Analyse des matches :**

- **L277** `signals = np.array([1 if i % 2 == 0 else 0 for i in range(n)], dtype=int)` : pattern `if...else` dans une list comprehension pour construire des données de test. **Faux positif** — pas un fallback silencieux, c'est de la construction de données.

- **L251, L281** `for i in range(1, len(trades)):` : itération sur des trades retournés par le engine để vérifier l'absence de chevauchement. C'est du code de test, pas du code source — les boucles sont sur des listes Python (pas des arrays numpy). **Faux positif** — pattern correct pour un test d'assertion.

### B2. Annotations par fichier (lecture ligne par ligne)

#### `tests/test_gate_backtest.py` (525 lignes)

Fichier lu intégralement. Observations :

- **L1-16** Docstring module : identifie la tâche `#036`, documente les 6 critères. ✅
- **L18-24** Imports : `hashlib`, `numpy`, `pandas`, `pytest`, et 3 imports du package `ai_trading.backtest`. Tous les modules importés existent dans `Max6000i1`. ✅
- **L30-47** Constantes `HORIZON=4`, `FEE=0.0005`, `SLIPPAGE=0.00025`, `INITIAL_EQUITY=1.0`, `POSITION_FRACTION=1.0`. Valeurs cohérentes pour des tests de gate. `EXPECTED_JOURNAL_COLUMNS` correspond exactement à `_COLUMN_ORDER` dans `journal.py`. ✅
- **L55-66** `_make_ohlcv()` : utilise `np.random.default_rng(seed)` — conforme §R4. Génère des prix synthétiques déterministes. `close = np.abs(close) + 50.0` garantit que les prix restent positifs. ✅
- **L69-73** `_make_sparse_signals()` : construit un vecteur de signaux binaires. Pas de fallback. ✅
- **L76-107** `_run_full_pipeline()` : orchestre execute_trades → apply_cost_model → build_equity_curve → export_trade_journal. Ajoute `y_true` et `y_hat` (requis par journal). Utilise `tmp_dir` (pytest `tmp_path`). ✅
- **L96-97** `t["y_true"] = np.log(exit_p / entry_p)` et `t["y_hat"] = t["y_true"] + 0.001` : dummy prediction pour le journal. Mathématiquement correct (log-return). ✅
- **L115-149** `TestDeterminism` (3 tests) : test SHA-256 identique, equity `atol=1e-10`, sanity check avec données différentes. Seeds fixées (99, 1, 2). ✅
- **L157-215** `TestEquityTradeCoherence` (4 tests) : formule `E_0 * Π(1 + w * r_net_i)`, trade unique, zéro trades (equity = E_0), multiples trades. Formule `E_final` conforme à `engine.py` L232. `atol=1e-8` conforme à la tâche. ✅
- **L221-282** `TestOneAtATime` (3 tests) : signaux denses all-ones, consécutifs (asserts `< n // 2` trades), alternants. Vérifie `signal_time >= prev exit_time` et `entry_time > prev exit_time`. ✅
- **L290-352** `TestCostsHandComputed` (6 tests dont 4 paramétrés) : calcul à la main conforme à §12.3 (`p_entry_eff = p_entry * (1 + s)`, `p_exit_eff = p_exit * (1 - s)`, `m_net = (1-f)² * (p_exit_eff / p_entry_eff)`, `r_net = m_net - 1`). 4 cas paramétrés (gain, loss, high-cost, break-even) ≥ 3 requis. Cas f=0/s=0, et assertion r_net < gross return. ✅
- **L361-423** `TestTradesCSVConformity` (5 tests) : colonnes conformes, row count, valeurs finies, f/s match config, empty trades → empty CSV. Re-lecture depuis disque pour valider la parseabilité. ✅
- **L432-525** `TestAntiLeak` (3 tests) : perturbation de prix futurs (après bar K), vérification que trades avant K sont identiques (timing ET prix). Test avec données OHLCV complètement différentes → mêmes signal_time/entry_time/exit_time. ✅

**Type safety** : les tests invoquent des fonctions internes du package avec des types corrects (ndarray, DataFrame, int, str). Pas de données désérialisées depuis l'extérieur. ✅

**Edge cases** : no-trade (0 signal), all-ones (dense), single trade, break-even prices, perturbation cross-boundary. Couverture satisfaisante. ✅

RAS — aucun défaut détecté après lecture complète des 525 lignes.

#### `docs/tasks/M4/036__gate_backtest.md`

Le diff se limite au passage `TODO → DONE` et au cochage des critères/checklist. RAS.

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | Fichier `test_gate_backtest.py`, classes `TestDeterminism`, `TestEquityTradeCoherence`, etc. ID `#036` dans docstrings. |
| Couverture des 6 critères | ✅ | Mapping 1:1 (voir A3 ci-dessus) — chaque critère a une classe dédiée |
| Cas nominaux + erreurs + bords | ✅ | Nominaux : pipeline complète, N trades, 1 trade. Erreurs : N/A (gate test, pas de validation d'erreurs — le SUT est déjà implémenté). Bords : 0 trades, dense signals, break-even, single trade. |
| Boundary fuzzing | ✅ | `signals = all-zeros` (0 trades), `signals = all-ones` (dense), `HORIZON=4` avec n=20/30/40/50/60/80, break-even `p_entry == p_exit`, `f=0, s=0`. |
| Boundary fuzzing taux | N/A | Pas de code source modifié — le cost model est testé ici avec des valeurs valides (gate = vérification, pas validation). Les tests de bornes de `fee_rate` et `slippage_rate` sont dans `test_cost_model.py`. |
| Déterministes | ✅ | Seeds fixées : 42, 99, 77, 55, 33, 11, 22, 44, 88, 10, 20, 777, 999, 1, 2 — aucun appel aléatoire sans seed. |
| Données synthétiques | ✅ | `_make_ohlcv()` génère des données localement, aucune dépendance réseau. |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé. Tous les chemins via `tmp_path` pytest. |
| Tests registre réalistes | N/A | Pas de test de registre dans ce fichier. |
| Contrat ABC complet | N/A | Pas de test d'ABC dans ce fichier. |
| Pas de skip/xfail | ✅ | Aucun `@pytest.mark.skip` ni `xfail` trouvé (vérifié par lecture). |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 match (faux positif L277 = list comprehension). Aucun except. |
| §R10 Defensive indexing | N/A | Pas de code source modifié — les tests accèdent via clés dict/DataFrame. |
| §R2 Config-driven | N/A | Pas de code source modifié. Les constantes de test (HORIZON, FEE) sont des valeurs de test, pas de hardcoding source. |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. TestAntiLeak vérifie explicitement l'absence de look-ahead dans le engine. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Toutes les seeds via `np.random.default_rng()`. |
| §R5 Float conventions | N/A | Pas de code source modifié. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 `is True/False`, 0 `open()` sans context manager dans tests. |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Tous les noms de fonctions/variables en snake_case. |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 `TODO`, 0 `FIXME`. |
| Imports propres / relatifs | ✅ | 7 imports : 1 stdlib (`hashlib`), 2 third-party (`numpy`, `pandas`), 1 pytest, 3 locaux. Ordre correct, pas d'import `*`. |
| DRY | ✅ | `_make_ohlcv()` et `_run_full_pipeline()` factorisent la logique répétitive. |
| ruff clean | ✅ | `All checks passed!` |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Log-return `np.log(exit_p / entry_p)`, equity formula, cost model formulas conformes. |
| Nommage métier | ✅ | `equity`, `entry_price_eff`, `r_net`, `gross_return`, `net_return`. |
| Séparation des responsabilités | ✅ | Tests uniquement — pas de logique métier. |
| Invariants de domaine | ✅ | Prix positifs (L63 `np.abs(close) + 50.0`), equity > 0 maintenu. |
| Cohérence des unités | ✅ | Log-returns pour y_true, multiplicative returns pour r_net — cohérent avec spec. |
| Patterns de calcul financier | ✅ | `np.log`, `np.cumsum`, vectorisé. |

### B6. Conformité spec v1.0

| Critère | Verdict | Preuve |
|---|---|---|
| Spécification §12 | ✅ | Formules coûts §12.3 vérifiées (L307-311 du test vs `costs.py`). Colonnes journal §12.6 (`_COLUMN_ORDER`) vérifiées (L37-47 du test vs `journal.py`). Equity §12.4 vérifiée (formule produit). |
| Plan d'implémentation | ✅ | Gate G-Backtest positionné après WS-8.4, conforme au plan. |
| Formules doc vs code | ✅ | `E_final = E_0 * Π(1 + w * r_net_i)` — test L170 vs engine L232. `m_net = (1-f)² * (p_exit_eff / p_entry_eff)` — test L309 vs costs L93. Pas d'off-by-one. |

### B7. Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `execute_trades(signals, ohlcv, horizon, mode)` — conforme à `engine.py`. `apply_cost_model(trades, f, s)` — conforme à `costs.py`. `build_equity_curve(trades, ohlcv, E0, w)` — conforme. `export_trade_journal(trades, path, f, s)` — conforme. |
| Noms de colonnes DataFrame | ✅ | `equity` dans equity_df, colonnes journal conformes à `_COLUMN_ORDER`. |
| Clés de configuration | N/A | Pas de lecture config — valeurs de test utilisées directement. |
| Registres et conventions | N/A | Pas de registre concerné. |
| Structures de données | ✅ | Dicts trades avec clés `signal_time`, `entry_time`, `exit_time`, `entry_price`, `exit_price`, `r_net`, `y_true`, `y_hat` — conformes aux modules amont. |
| Conventions numériques | ✅ | Float64 pour les prix et métriques — cohérent. |
| Imports croisés | ✅ | 3 imports de `ai_trading.backtest` : tous existent dans `Max6000i1`. |

---

## Remarques

Aucune remarque.

## Actions requises

Aucune action requise.

## Résumé

24 tests en 6 classes couvrant les 6 critères du gate G-Backtest. Code de test propre, déterministe, sans dépendance réseau, formules conformes à la spec §12. Tous les scans automatisés sont propres, les 986 tests passent, ruff est clean. Verdict : CLEAN.
