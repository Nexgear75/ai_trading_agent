# Review v1 — Task #029 Equity Curve

**Branche** : `task/029-equity-curve`
**Date** : 2 mars 2026
**Verdict** : CLEAN

## Phase A — Compliance

### Branch & Commits
- [x] Branch `task/029-equity-curve` from `Max6000i1`
- [x] RED commit: `[WS-8] #029 RED: tests courbe d'équité` — tests only (`tests/test_equity_curve.py`)
- [x] GREEN commit: `[WS-8] #029 GREEN: courbe d'équité` — implementation (`ai_trading/backtest/engine.py`) + task file + minor test adjustments (1 unused variable removed, 1 assertion method adjusted — 2 insertions, 3 deletions)
- [x] No parasitic commits (exactly 2 commits: RED then GREEN)

### Task
- [x] Status: DONE
- [x] All 14 acceptance criteria checked `[x]`
- [x] Checklist checked `[x]` (commit GREEN and PR items unchecked — expected: procedural post-commit markers)

### Tests & Lint
- [x] pytest GREEN: **824 passed** in 7.25s, 0 failures
- [x] ruff check clean: All checks passed
- [x] Deterministic tests: synthetic data, `np.random.default_rng(42)`

## Phase B — Code Review

### §R1 Strict code
- Validation explicite à l'entrée de `build_equity_curve` : `ohlcv` non vide, `initial_equity > 0`, `position_fraction ∈ (0, 1]`.
- Validation des trades : clés requises (`entry_time`, `exit_time`, `r_net`), timestamps présents dans l'index ohlcv.
- Erreurs levées via `raise ValueError` avec messages descriptifs.
- Aucun fallback silencieux, aucun `except` trop large.
- ✅ Conforme.

### §R2 Config-driven
- `initial_equity` et `position_fraction` sont des paramètres de fonction, lus depuis `config.backtest.initial_equity` et `config.backtest.position_fraction` dans la config Pydantic (`config.py:182-183`).
- Valeurs YAML dans `configs/default.yaml:124-125` : `initial_equity: 1.0`, `position_fraction: 1.0`.
- Validation Pydantic : `Field(gt=0)` et `Field(gt=0, le=1)` — cohérent avec la validation dans `build_equity_curve`.
- Aucune valeur magique hardcodée.
- ✅ Conforme.

### §R3 Anti-fuite
- Pas de look-ahead : la courbe d'équité est construite candle par candle en forward-only (`for t in range(n)`).
- L'equity est mise à jour uniquement aux bougies de sortie (événements passés).
- Pas de `.shift(-n)`.
- ✅ Conforme.

### §R4 Reproductibilité
- Pas de composante aléatoire dans le code source.
- Tests utilisent `np.random.default_rng(42)` (API moderne, seed fixée).
- ✅ Conforme.

### §R5 Float conventions
- Equity array : `np.float64` (`np.full(n, np.nan, dtype=np.float64)`) — correct pour les métriques.
- `in_trade` : `np.zeros(n, dtype=bool)` — type approprié.
- ✅ Conforme.

### §R6 Anti-patterns Python/numpy/pandas
- Pas de mutable default arguments.
- Pas de `open()` sans context manager (`save_equity_curve_csv` utilise `DataFrame.to_csv()`).
- Pas de comparaison float avec `==` dans le code source.
- Tests utilisent `pytest.approx` et `np.testing.assert_allclose` correctement.
- ✅ Conforme.

### §R7 Qualité du code
- snake_case cohérent dans tout le code.
- Pas de `print()`, code mort, TODO, FIXME.
- Pas de `# noqa`.
- Imports propres : `from __future__ import annotations`, `pathlib.Path`, `numpy`, `pandas`.
- Pas de chemins hardcodés dans les tests ; `tmp_path` utilisé pour les CSV.
- ✅ Conforme.

### §R8 Cohérence intermodule
- `build_equity_curve` consomme les trades enrichis de `apply_cost_model` (keys `entry_time`, `exit_time`, `r_net`) — vérifié dans `costs.py:73-80`.
- Pydantic `BacktestConfig` (`config.py:182-183`) : `initial_equity: float = Field(gt=0)`, `position_fraction: float = Field(gt=0, le=1)` — domaines cohérents avec la validation dans `build_equity_curve`.
- `__init__.py` du package backtest inchangé (docstring mise à jour dans un commit précédent, mentionne déjà "equity curve").
- ✅ Conforme.

### §R9 Bonnes pratiques métier
- Formule conforme : `E_exit = E_entry × (1 + w × r_net)` → implémentée comme `current_equity * (1 + position_fraction * r_net)`.
- Produit cumulatif : `E_final = E_0 × Π(1 + w × r_net_i)` — vérifié par parcours séquentiel forward.
- Pas de mark-to-market intra-trade : equity constante entre entrée et sortie.
- `in_trade` correctement marqué : True de l'entrée à la sortie (inclusive), False ailleurs.
- Nommage métier clair : `equity`, `in_trade`, `position_fraction`, `initial_equity`.
- ✅ Conforme.

### §R10 Defensive indexing
- `range(entry_pos, exit_pos + 1)` pour marquer `in_trade` — bornes correctes (entry et exit inclusifs).
- `ts_to_idx` lookup garantit que les positions sont valides (validation explicite au préalable).
- Pas de slicing négatif risqué.
- ✅ Conforme.

### Numerical example verification
- `E_before=1.0`, `w=1.0`, `f=0.001`, `s=0.0003`, `Open=100`, `Close=102`
- `p_entry_eff = 100 × 1.0003 = 100.03`
- `p_exit_eff = 102 × 0.9997 = 101.9694`
- `fee_factor² = 0.999² = 0.998001`
- `m_net = 0.998001 × (101.9694 / 100.03) ≈ 1.01738`
- `r_net ≈ 0.01738`, `E_exit ≈ 1.01738 ≈ 1.0174` ✓
- Test vérifie `r_net ≈ 0.0174` à `abs=5e-4` et `E_exit = 1.0 + r_net` à `abs=1e-8`.
- ✅ Conforme.

### Acceptance criteria traceability

| Critère | Test(s) |
|---------|---------|
| E_0 = initial_equity | `TestSingleTrade::test_equity_starts_at_initial` |
| Equity constante hors position | `test_equity_constant_before_trade`, `test_equity_constant_after_trade` |
| Equity constante intra-trade | `test_equity_constant_during_trade`, `TestNoMarkToMarket` |
| E_exit = E_entry × (1 + w × r_net) | `test_equity_updated_at_exit` |
| E_final = E_0 × Π(...) | `TestMultiTrade::test_cumulative_equity` |
| in_trade correct | `TestInTradeColumn` (2 tests) |
| CSV (time_utc, equity, in_trade) | `TestCsvRoundtrip` (2 tests) |
| w < 1.0 | `TestPositionFraction` (2 tests) |
| Numerical example | `TestNumericalExample::test_spec_numerical` |
| single_trade mode | `TestSingleTradeMode::test_single_trade_equity` |
| Drawdown intra-trade → equity constante | `TestNoMarkToMarket::test_equity_constant_intra_trade_volatile` |
| Nominaux + erreurs + bords | `TestValidation` (9 tests) + `TestNoTrades` (2) + `TestTradeAtLastCandle` (1) + `TestOutputShape` (3) |

### §GREP Results

```
§R1 — Fallbacks silencieux:         0 occurrences (grep exécuté)
§R1 — Except trop large:            0 occurrences (grep exécuté)
§R7 — Suppressions lint (noqa):     0 occurrences (grep exécuté)
§R7 — Print résiduel:               0 occurrences (grep exécuté)
§R3 — Shift négatif:                0 occurrences (grep exécuté)
§R4 — Legacy random API:            0 occurrences (grep exécuté)
§R7 — TODO/FIXME:                   0 occurrences (grep exécuté)
§R7 — Chemins hardcodés (tests):    0 occurrences (grep exécuté)
§R7 — Imports absolus __init__.py:  N/A (aucun __init__.py modifié)
§R7 — Registration manuelle tests:  0 occurrences (grep exécuté)
§R6 — Mutable default arguments:    0 occurrences (grep exécuté)
§R6 — open() sans context manager:  0 occurrences (grep exécuté)
§R7 — per-file-ignores:             Aucune entrée ajoutée
```

## Items

Aucun.

## Summary

Implémentation propre et conforme de la courbe d'équité (§12.4). Le code suit la formule `E_exit = E_entry × (1 + w × r_net)` avec parcours forward candle par candle, sans mark-to-market intra-trade. Les validations sont explicites et strictes (initial_equity > 0, position_fraction ∈ (0, 1], clés et timestamps des trades). La suite de 29 tests couvre exhaustivement tous les critères d'acceptation : cas nominaux (single/multi-trade, w < 1), exemple numérique spec, in_trade column, CSV roundtrip, mode single_trade, no mark-to-market, et 9 tests de validation d'erreurs. Zéro finding.
