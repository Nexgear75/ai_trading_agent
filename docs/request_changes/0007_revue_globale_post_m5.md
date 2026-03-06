# Request Changes — Revue globale post-M5 (branche Max6000i1)

Statut : DONE
Ordre : 0007

**Date** : 2025-07-18
**Périmètre** : Audit complet de tous les fichiers source (`ai_trading/`, 51 fichiers), tests (`tests/`, 48 fichiers), configs et scripts de la branche `Max6000i1`. Couvre conformité spec, plan, formules, inter-modules, conventions, anti-fuite, DRY.
**Résultat** : 1579 tests GREEN, ruff clean
**Verdict** : ✅ CLEAN (après corrections)

---

## Résultats d'exécution

| Check | Résultat |
|---|---|
| `pytest tests/` | **1579 passed** / 0 failed (20.64s) |
| `ruff check ai_trading/ tests/ scripts/` | **All checks passed** |
| `print()` résiduel | Aucun |
| `TODO`/`FIXME`/`HACK`/`XXX` orphelin | Aucun |
| `.shift(-n)` (look-ahead) | Aucun |
| Broad `except:` | Aucun |
| `except Exception:` | Aucun |
| Legacy random API (`np.random.seed`) | 2 occ. dans `utils/seed.py` — documentées (`# noqa: NPY002`), nécessaires pour le seed manager global |
| `or default` / fallback patterns | Aucun (hits uniquement dans docstrings) |
| `value if value else default` | Aucun |

---

## BLOQUANTS (0)

Aucun bloquant identifié.

---

## WARNINGS (2)

### ~~W-1. `trades.csv` non exporté par le runner~~ ✅ RÉSOLU

> **Résolu** : commit `fbbcb66` — `[RC-0007] FIX W-1: Wire trades.csv export in runner (§12.6, §15.1)`. Ajout de `save_trades` dans config, enrichissement y_true/y_hat, appel `export_trade_journal()` dans le runner, tests d'intégration ajoutés.

**Fichiers** : `ai_trading/pipeline/runner.py`, `ai_trading/backtest/journal.py`
**Sévérité** : WARNING — le spec §12.6 et §15.1 imposent la production d'un fichier `trades.csv` par fold dans l'arborescence canonique du run. Le module `journal.py` implémente `export_trade_journal()` (tâche #035) mais cette fonction n'est **jamais appelée** par le runner (`pipeline/runner.py`). Les trades enrichis (`enriched_trades`) sont calculés par le runner et passés aux métriques, mais ne sont pas persistés.

De plus, le runner ne positionne pas les champs `y_true`/`y_hat` sur chaque trade dict, champs requis par `export_trade_journal()`. Le câblage est donc incomplet.

L'arborescence spec §15.1 liste :
```
folds/fold_00/
├── trades.csv          ← ABSENT
├── preds_val.csv       ✅
├── preds_test.csv      ✅
├── equity_curve.csv    ✅
├── metrics_fold.json   ✅
└── model_artifacts/    ✅
```

Il n'existe pas non plus de flag `artifacts.save_trades` dans la config (contrairement à `save_equity_curve`, `save_predictions`, `save_model`).

**Action** :
1. Ajouter un paramètre `save_trades: bool` dans `ArtifactsConfig` et `configs/default.yaml` (valeur par défaut `true`).
2. Dans le runner, enrichir chaque trade dict avec `y_true`/`y_hat` après le backtest.
3. Appeler `export_trade_journal()` dans la boucle per-fold du runner si `config.artifacts.save_trades` est `true`.
4. Ajouter un test d'intégration vérifiant la présence de `trades.csv` dans le run_dir.

### ~~W-2. `global_seed >= 1` dans le code vs `>= 0` dans le plan~~ ✅ RÉSOLU

> **Résolu** : commit `7166733` — `[RC-0007] FIX W-2: Align plan global_seed >= 1 (matches code)`. Plan aligné sur le code (Option 1 retenue).

**Fichiers** : `ai_trading/config.py` (L303), `ai_trading/utils/seed.py` (L41-43)
**Sévérité** : WARNING — le plan WS-1.3 spécifie `reproducibility.global_seed >= 0`, mais le code enforce `global_seed >= 1` via `Field(ge=1)` dans config.py et une validation explicite `seed < 1 → ValueError` dans seed.py. La valeur seed=0 est rejetée par les deux modules.

La spec §16.1 ne donne pas de borne explicite (elle dit uniquement que le seed global est fixé en configuration). L'implémentation est raisonnable (seed=0 est rarement utile) mais diverge du plan.

**Action** :
1. Aligner le plan WS-1.3 sur le code : changer « `global_seed >= 0` » en « `global_seed >= 1` » dans `docs/plan/implementation.md`.
2. Ou bien, si seed=0 doit être supporté, modifier config.py (`Field(ge=0)`) et seed.py pour accepter 0.
3. Recommandation : aligner le plan sur le code (option 1), car seed=0 est un cas dégénéré.

---

## MINEURS (3)

### ~~M-1. Facteur d’annualisation Sharpe : 365.25 vs 365~~ ✅ RÉSOLU

> **Résolu** : commit `a0f49a3` — `[RC-0007] FIX M-1: Document 365.25 annualization choice`. Commentaire inline ajouté.

**Fichiers** : `ai_trading/metrics/trading.py` (L163)
**Sévérité** : MINEUR — la spec §14.2 donne l'exemple K = 24 × 365 pour 1h (=8760). Le code utilise K = 365.25 × 24 / timeframe_hours (=8766 pour 1h). La différence (0.07%) est négligeable et le flag `sharpe_annualized` est `false` par défaut dans le MVP, donc aucun impact en pratique. La valeur 365.25 est techniquement plus précise (année julienne).

**Action** : Documenter le choix 365.25 dans un commentaire inline ou accepter l'écart comme implementation-defined.

### ~~M-2. Module `data/timeframes.py` sans tâche explicite dans le plan~~ ✅ RÉSOLU

> **Résolu** : Noté comme helper d'infrastructure légitime. Aucune action code nécessaire.

**Fichiers** : `ai_trading/data/timeframes.py`
**Sévérité** : MINEUR — ce module fournit le mapping `TIMEFRAME_DELTA` (single source of truth pour la conversion timeframe → timedelta). Il est utilisé par `qa.py`, `missing.py`, `splitter.py`, et `runner.py`. Il n'est rattaché à aucune tâche explicite ni WS dans le plan, mais est un helper d'infrastructure légitime (extrait lors du refactoring). Pas de bug, juste un manque de traçabilité plan → code.

**Action** : Aucune action nécessaire. Documenter l'existence de ce module dans la section conventions si une mise à jour du plan est prévue.

### ~~M-3. Helpers OHLCV dupliqués dans `conftest.py` : `make_ohlcv_random` vs `make_calibration_ohlcv`~~ ✅ RÉSOLU

> **Résolu** : Refactoring optionnel, non prioritaire. Accepté en l'état.

**Fichiers** : `tests/conftest.py` (L81, L120)
**Sévérité** : MINEUR — `make_ohlcv_random` et `make_calibration_ohlcv` génèrent tous deux des DataFrames OHLCV synthétiques avec des paramètres légèrement différents. La logique de construction est similaire (random walk sur close, puis open/high/low/volume). Les deux coexistent dans conftest.py avec des signatures et des propriétés subtilment différentes (calibration garantit des prix > 50, high/low décalés de ±0.5). Cela reste du test code et n'impacte pas le runtime.

**Action** : Envisager un refactoring optionnel pour unifier les builders OHLCV de test en un seul helper paramétrable. Non prioritaire.

---

## Conformité formules métier (§6c)

| ID | Section spec | Formule | Fichier code | Verdict |
|---|---|---|---|---|
| F-1 | §5.2 | $y_t = \log(C_{t+H} / O_{t+1})$ | `data/labels.py` | ✅ Conforme |
| F-2 | §6.2 | $\text{logret}_k(t) = \log(C_t / C_{t-k})$ | `features/log_returns.py` | ✅ Conforme |
| F-3 | §6.2 | $\text{logvol}(t) = \log(V_t + \varepsilon)$ | `features/volume.py` | ✅ Conforme |
| F-4 | §6.2 | $\text{dlogvol}(t) = \text{logvol}(t) - \text{logvol}(t-1)$ | `features/volume.py` | ✅ Conforme |
| F-5 | §6.3 | RSI Wilder (SMA init + récursif $\alpha = 1/n$) | `features/rsi.py` | ✅ Conforme |
| F-6 | §6.4 | $\text{EMA\_ratio} = \text{EMA}_{fast} / \text{EMA}_{slow} - 1$ | `features/ema.py` | ✅ Conforme |
| F-7 | §6.5 | $\text{vol}_w(t) = \text{std}(\text{logret}_1[t\text{-}w\text{+}1:t], \text{ddof=0})$ | `features/volatility.py` | ✅ Conforme |
| F-8 | §8.2 | $\text{embargo\_bars} \geq H$ | `data/splitter.py`, `config.py` | ✅ Conforme |
| F-9 | §9.1 | $x' = (x - \mu) / (\sigma + \varepsilon)$ | `data/scaler.py` | ✅ Conforme |
| F-10 | §9.2 | Robust : $(x - \text{median}) / (\text{IQR} + \varepsilon)$ + clip | `data/scaler.py` | ✅ Conforme |
| F-11 | §11.2 | Grille quantiles sur val, objectif max\_net\_pnl\_with\_mdd\_cap | `calibration/threshold.py` | ✅ Conforme |
| F-12 | §12.3 | $M_{net} = (1-f)^2 \cdot \frac{C_{t+H}(1-s)}{O_{t+1}(1+s)}$, $r_{net} = M_{net} - 1$ | `backtest/costs.py` | ✅ Conforme |
| F-13 | §12.4 | $E_{exit} = E_{entry} \cdot (1 + w \cdot r_{net})$ | `backtest/engine.py` | ✅ Conforme |
| F-14 | §14.2 | $\text{Sharpe} = \frac{\text{mean}(r_t)}{\text{std}(r_t) + \varepsilon}$ | `metrics/trading.py` | ✅ Conforme |

**Écarts détaillés** : Aucun écart formel. La seule divergence mineure est la constante d'annualisation (365.25 vs 365, cf. M-1), sans impact MVP.

---

## Conformité spec section-par-section (§6b)

| Section spec | Module code | Implémenté | Conforme | Remarques |
|---|---|---|---|---|
| §4.1 Source/format | `data/ingestion.py` | ✅ | ✅ | Colonnes canoniques, Parquet, SHA-256, retry/backoff |
| §4.2 QA checks | `data/qa.py` | ✅ | ✅ | Régularité temporelle, doublons, OHLC cohérence, volume nul |
| §4.3 Missing candles | `data/missing.py` | ✅ | ✅ | Masque de validité, pas d'interpolation (MVP) |
| §5.2 Label trade | `data/labels.py` | ✅ | ✅ | $\log(C_{t+H}/O_{t+1})$ exacte |
| §5.3 Label close-to-close | `data/labels.py` | ✅ | ✅ | $\log(C_{t+H}/C_t)$ implémenté, sélectionné par config |
| §6.2 Features logret | `features/log_returns.py` | ✅ | ✅ | k ∈ {1, 2, 4} paramétrable |
| §6.2 Features volume | `features/volume.py` | ✅ | ✅ | logvol + dlogvol, epsilon configurable |
| §6.3 RSI Wilder | `features/rsi.py` | ✅ | ✅ | SMA init, lissage récursif, cas limites |
| §6.4 EMA ratio | `features/ema.py` | ✅ | ✅ | SMA init, α = 2/(n+1), ratio - 1 |
| §6.5 Volatilité | `features/volatility.py` | ✅ | ✅ | Fenêtres 24/72 fixes, ddof config, logret interne |
| §6.6 Warm-up | `features/warmup.py` | ✅ | ✅ | min_warmup ≥ max(min_periods) enforced |
| §7.1 Dataset (N,L,F) | `data/dataset.py` | ✅ | ✅ | Sliding window, float32, shape (N,L,F) |
| §7.2 Adapter XGBoost | `data/dataset.py` | ✅ | ✅ | flatten_seq_to_tab (N, L×F) |
| §8.1–8.2 Walk-forward | `data/splitter.py` | ✅ | ✅ | Embargo, purge, disjonction, date-based |
| §8.3 Périodes par fold | `data/splitter.py` | ✅ | ✅ | train/val/test bornes dans FoldSpec |
| §8.4 Contraintes | `data/splitter.py`, `config.py` | ✅ | ✅ | step ≥ test, embargo ≥ H, disjonction |
| §9.1 Standard scaler | `data/scaler.py` | ✅ | ✅ | (x-μ)/(σ+ε), fit train only |
| §9.2 Robust scaler | `data/scaler.py` | ✅ | ✅ | Median/IQR + clip |
| §9.3 Rolling z-score | `data/scaler.py`, `config.py` | ✅ | ✅ | Rejeté en config (non MVP), implémentation absente — conforme |
| §10.1 Interface modèle | `models/base.py` | ✅ | ✅ | fit/predict/save/load ABC |
| §10.2 Conventions I/O | `models/base.py` | ✅ | ✅ | output_type (regression/signal), execution_mode |
| §10.3 Early stopping | `training/trainer.py` | ✅ | ✅ | Orchestré par le trainer, délégué au modèle |
| §10.4 Déterminisme | `utils/seed.py` | ✅ | ✅ | Seeds numpy/random/torch |
| §11.1–11.3 Calibration θ | `calibration/threshold.py` | ✅ | ✅ | Grille quantiles, objectif MDD cap, fallback E.2.2 |
| §11.4 Baselines bypass | `calibration/threshold.py` | ✅ | ✅ | output_type == "signal" → θ = -∞ |
| §11.5 RL bypass | `calibration/threshold.py` | ✅ | ✅ | Même bypass via output_type |
| §12.1 Règles Go/No-Go | `backtest/engine.py` | ✅ | ✅ | execute_trades, one_at_a_time, long_only |
| §12.2 Coûts | `backtest/costs.py` | ✅ | ✅ | Per-side multiplicative |
| §12.3 Rendement net | `backtest/costs.py` | ✅ | ✅ | M_net = (1-f)² × (exit_eff/entry_eff) |
| §12.4 Equity curve | `backtest/engine.py` | ✅ | ✅ | E × (1 + w × r_net) |
| §12.5 Buy & hold | `baselines/buy_hold.py`, `backtest/engine.py` | ✅ | ✅ | execution_mode = single_trade |
| §12.6 Journal trades | `backtest/journal.py` | ✅ | ⚠️ | Module implémenté mais **non câblé** dans le runner (cf. W-1) |
| §13.1 No-trade | `baselines/no_trade.py` | ✅ | ✅ | predict → zeros |
| §13.2 Buy & hold | `baselines/buy_hold.py` | ✅ | ✅ | predict → ones, single_trade |
| §13.3 SMA rule | `baselines/sma_rule.py` | ✅ | ✅ | SMA fast/slow, backward-looking, config params |
| §14.1 Métriques prédiction | `metrics/prediction.py` | ✅ | ✅ | MAE, RMSE, DA (excl. y=0), Spearman IC |
| §14.2 Métriques trading | `metrics/trading.py` | ✅ | ✅ | Sharpe, MDD, PF, hit_rate, net_pnl, exposure |
| §14.3 Agrégation | `metrics/aggregation.py` | ✅ | ✅ | mean/std par fold, stitch equity |
| §14.4 Acceptance criteria | `metrics/aggregation.py` | ✅ | ✅ | check_acceptance_criteria (advisory notes) |
| §15.1 Arborescence run | `artifacts/run_dir.py` | ✅ | ✅ | Canonique, folds/fold_XX/model_artifacts |
| §15.2 manifest.json | `artifacts/manifest.py` | ✅ | ✅ | Toutes les sections requises |
| §15.3 metrics.json | `artifacts/metrics_builder.py` | ✅ | ✅ | Per-fold + aggregate |
| §15.4 JSON Schema | `artifacts/validation.py` | ✅ | ✅ | Draft 2020-12, jsonschema |
| §16.1 Seeds | `utils/seed.py` | ✅ | ✅ | random, numpy, torch, PYTHONHASHSEED |
| §16.2 Journalisation | `utils/logging.py`, runner | ✅ | ✅ | Two-phase logging, text/json |
| §16.3 Feature version | `config.py`, `features/pipeline.py` | ✅ | ✅ | feature_version tracée |

---

## Conformité plan → code (§6bis)

| WS | Tâches DONE | Module(s) code | Code présent | Tests présents | Remarques |
|---|---|---|---|---|---|
| WS-1 | #001, #002, #003 | `config.py`, `__init__.py`, `utils/logging.py` | ✅ | ✅ `test_config.py`, `test_config_validation.py`, `test_project_structure.py` | Complet |
| WS-2 | #004, #005, #006 | `data/ingestion.py`, `data/qa.py`, `data/missing.py` | ✅ | ✅ `test_ingestion.py`, `test_qa.py`, `test_missing.py` | Complet |
| WS-3 | #007–#014, #023 | `features/registry.py`, `features/log_returns.py`, `features/volatility.py`, `features/rsi.py`, `features/ema.py`, `features/volume.py`, `features/pipeline.py`, `features/warmup.py` | ✅ | ✅ 8 test files | Complet, 9 features enregistrées |
| WS-4 | #015–#020 | `data/labels.py`, `data/dataset.py`, `data/splitter.py` | ✅ | ✅ `test_label_target.py`, `test_sample_builder.py`, `test_adapter_xgboost.py`, `test_metadata.py`, `test_splitter.py` | Complet |
| WS-5 | #021, #022 | `data/scaler.py` | ✅ | ✅ `test_standard_scaler.py`, `test_robust_scaler.py` | Complet |
| WS-6 | #024, #025, #028, #034 | `models/base.py`, `models/dummy.py`, `training/trainer.py` | ✅ | ✅ `test_base_model.py`, `test_dummy_model.py`, `test_fold_trainer.py`, `test_gate_doc.py` | Complet |
| WS-7 | #030–#033 | `calibration/threshold.py` | ✅ | ✅ `test_quantile_grid.py`, `test_theta_optimization.py`, `test_theta_bypass.py` | Complet |
| WS-8 | #026, #027, #029, #035, #036 | `backtest/engine.py`, `backtest/costs.py`, `backtest/journal.py` | ✅ | ✅ `test_trade_execution.py`, `test_cost_model.py`, `test_equity_curve.py`, `test_trade_journal.py`, `test_gate_backtest.py` | Module journal non câblé dans runner (W-1) |
| WS-9 | #037, #038, #039 | `baselines/no_trade.py`, `baselines/buy_hold.py`, `baselines/sma_rule.py`, `baselines/_base.py` | ✅ | ✅ `test_baseline_no_trade.py`, `test_baseline_buy_hold.py`, `test_baseline_sma_rule.py` | Complet |
| WS-10 | #040, #041, #042 | `metrics/prediction.py`, `metrics/trading.py`, `metrics/aggregation.py` | ✅ | ✅ `test_prediction_metrics.py`, `test_trading_metrics.py`, `test_aggregation.py` | Complet |
| WS-11 | #044–#047 | `artifacts/run_dir.py`, `artifacts/manifest.py`, `artifacts/metrics_builder.py`, `artifacts/validation.py` | ✅ | ✅ Tests intégrés dans les test files correspondants | Complet |
| WS-12 | #048–#054 | `utils/seed.py`, `pipeline/runner.py`, `__main__.py`, `Dockerfile`, `scripts/`, `Makefile` | ✅ | ✅ `test_gate_m4.py`, `test_gate_doc.py` | Complet pour le scope plan |

**Anomalies plan ↔ code** :
- **Tâches DONE sans code** : Aucune.
- **Code sans tâche** : `data/timeframes.py` — module utilitaire de mapping timeframe→timedelta, non rattaché à une tâche explicite. Helper d'infrastructure légitime (cf. M-2).
- **Critères d'acceptation non vérifiables** : Aucun identifié.
- **Modules attendus par le plan** : Tous présents et conformes aux noms listés dans AGENTS.md.

---

## Anti-fuite

| Module | Check | Verdict |
|---|---|---|
| `features/log_returns.py` | backward-looking only (`close.shift(k)` avec k > 0) | ✅ |
| `features/volume.py` | backward-looking only (`logvol.shift(1)`) | ✅ |
| `features/rsi.py` | SMA init + forward recursion (pas de `.shift(-n)`) | ✅ |
| `features/ema.py` | SMA init + forward recursion | ✅ |
| `features/volatility.py` | `.rolling(window=w).std()` backward-only | ✅ |
| `features/warmup.py` | Masque invalidation des premières bougies | ✅ |
| `data/labels.py` | Accès `close[t+H]` et `open[t+1]` — pointin-time depuis perspective décision à `t` | ✅ |
| `data/splitter.py` | Embargo cutoff strict : `train_end < test_start - embargo_bars × Δ` | ✅ |
| `data/scaler.py` | `fit(X_train)` uniquement, `transform()` séparé | ✅ |
| `training/trainer.py` | Scaler fit sur X_train, transform X_val/X_test séparément | ✅ |
| `calibration/threshold.py` | θ calibré sur val (y_hat_val + ohlcv_val), jamais sur test | ✅ |
| `backtest/engine.py` | Signaux à t → trade entry at t+1, exit at t+H | ✅ |
| `baselines/sma_rule.py` | `rolling().mean()` backward-looking, NaN → No-Go | ✅ |
| `pipeline/runner.py` | Workflow séquentiel : features → labels → samples → split → scale → train → calibrate → backtest | ✅ |

---

## Interfaces inter-modules

### Contrat de données (producteur → consommateur)

| Interface | Producteur | Consommateur | Conforme |
|---|---|---|---|
| OHLCV DataFrame | `ingestion.py` (timestamp_utc col) → `runner.py` (DatetimeIndex conversion) | `features/pipeline.py`, `labels.py`, `baselines/sma_rule.py` | ✅ |
| Features DataFrame | `features/pipeline.py` | `dataset.py` (build_samples) | ✅ |
| Labels array | `data/labels.py` → `(T,)` float64 | `dataset.py` (build_samples) | ✅ |
| Samples (N,L,F) | `dataset.py` → float32 | `splitter.py` (indexing), `trainer.py` | ✅ |
| FoldSpec | `splitter.py` | `runner.py` (indices extraction) | ✅ |
| Scaler | `scaler.py` (create_scaler factory) | `trainer.py` (fit/transform) | ✅ |
| Model I/O | `base.py` ABC | `dummy.py`, `baselines/*.py` | ✅ |
| Trades list[dict] | `engine.py` → `costs.py` → enriched | `trading.py` (metrics), `engine.py` (equity) | ✅ |
| Equity curve DataFrame | `engine.py` | `trading.py`, `aggregation.py` (stitch) | ✅ |
| Config Pydantic | `config.py` → PipelineConfig | Tous les modules | ✅ |

### Contrat de registre

| Registre | Expected keys | Actual keys | Conforme |
|---|---|---|---|
| FEATURE_REGISTRY | 9 features MVP | logret_1, logret_2, logret_4, vol_24, vol_72, logvol, dlogvol, rsi_14, ema_ratio_12_26 | ✅ |
| MODEL_REGISTRY | dummy + 3 baselines (MVP) | dummy, no_trade, buy_hold, sma_rule | ✅ |
| VALID_STRATEGIES | 10 stratégies | dummy, xgboost_reg, cnn1d_reg, gru_reg, lstm_reg, patchtst_reg, rl_ppo, no_trade, buy_hold, sma_rule | ✅ |

### Chaîne d'appel pipeline (runner.py)

```
1. set_global_seed()
2. _load_raw_ohlcv() → raw_df
3. run_qa_checks(raw_df)
4. _prepare_ohlcv_indexed(raw_df) → ohlcv (DatetimeIndex)
5. compute_features(ohlcv, config) → features_df
6. compute_labels(ohlcv, config.label) → y, label_mask
7. compute_valid_mask(timestamps, timeframe, L, H) → valid_mask
8. apply_warmup(features_df, valid_mask & label_mask, ...) → final_mask
9. build_samples(features_df, y, final_mask, config.window) → x_seq, y_out, timestamps
10. WalkForwardSplitter.split(timestamps) → folds
11. apply_purge(fold, ...) per fold → purged_folds
12. create_run_dir(config, strategy, n_folds) → run_dir
13. Per fold:
    a. FoldTrainer.train_fold() → y_hat_val, y_hat_test
    b. calibrate_threshold(y_hat_val, ohlcv_val, ...) → theta
    c. apply_threshold(y_hat_test, theta) → signals
    d. execute_trades(signals, ohlcv_test, ...) → trades
    e. apply_cost_model(trades, ...) → enriched_trades
    f. build_equity_curve(enriched_trades, ohlcv_test, ...) → equity_df
    g. compute_prediction_metrics() + compute_trading_metrics()
14. aggregate_fold_metrics() → aggregate
15. build_metrics() + write_metrics()
16. stitch_equity_curves() (if save_equity_curve)
17. build_manifest() + write_manifest()
18. validate_manifest() + validate_metrics()
```

La chaîne est complète et cohérente. Le seul maillon manquant est l'export de `trades.csv` entre les étapes 13e et 13f (cf. W-1).

---

## Résumé des actions

| # | Sévérité | Action | Fichier(s) |
|---|---|---|---|
| W-1 | WARNING | Câbler `export_trade_journal()` dans le runner, ajouter `save_trades` à la config | `pipeline/runner.py`, `config.py`, `configs/default.yaml` |
| W-2 | WARNING | Aligner plan et code sur la borne de `global_seed` (≥ 1) | `docs/plan/implementation.md` |
| M-1 | MINEUR | Documenter le choix 365.25 vs 365 pour le Sharpe annualisé | `metrics/trading.py` |
| M-2 | MINEUR | `data/timeframes.py` non rattaché à une tâche du plan | Documentation |
| M-3 | MINEUR | Helpers OHLCV dupliqués dans conftest.py | `tests/conftest.py` |

---

## Synthèse

Le codebase post-M5 est dans un excellent état. Les 1579 tests passent, ruff est propre, et les 14 formules métier vérifiées sont toutes conformes à la spécification. L'architecture inter-modules est cohérente et le pipeline end-to-end est correctement câblé. Les règles non négociables (strict code, config-driven, anti-fuite, reproductibilité) sont respectées sans exception.

Les deux warnings identifiés sont des lacunes de câblage (`trades.csv` non exporté par le runner) et d'alignement documentation/code (`global_seed` bounds). Aucun bloquant n'a été trouvé. La branche est dans un état sain pour passer le gate M5, sous réserve de résolution des 2 warnings.
