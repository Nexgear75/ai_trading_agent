# Request Changes — Revue globale post-M3 (branche Max6000i1)

Statut : DONE
Ordre : 0005

**Date** : 2026-03-02
**Périmètre** : Audit complet de la branche `Max6000i1` — 35 modules source (`ai_trading/`), 33 fichiers de tests (`tests/`), config (`configs/default.yaml`), tâches M1/M2/M3.
**Résultat** : 917 tests GREEN, ruff clean
**Verdict** : ✅ CLEAN (après corrections)

---

## Résultats d'exécution

| Check | Résultat |
|---|---|
| `pytest tests/` | **917 passed** / 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |
| `print()` résiduel | Aucun |
| `TODO`/`FIXME` orphelin | Aucun |
| `.shift(-n)` (look-ahead) | Aucun |
| Broad `except` | Aucun |
| Legacy random API | Aucun |
| `or default` / fallback patterns | Aucun |
| `from X import *` | Aucun |

---

## BLOQUANTS (0)

Aucun bloquant identifié.

---

## WARNINGS (2)

### W-1. ~~Helpers OHLCV dupliqués dans les tests~~ ✅ RÉSOLU

> **Résolu** : commit `67d9961` — `[RC-0005] FIX W-1,W-2: consolidate duplicate test helpers into conftest.py`

**Fichiers** : `tests/test_equity_curve.py` (L24), `tests/test_qa.py` (L24), `tests/test_volume_features.py` (L23), `tests/test_ingestion.py` (L39)
**Sévérité** : WARNING — risque de dérive entre helpers identiques.

Plusieurs fichiers de tests définissent localement des fonctions `_make_ohlcv(...)` similaires à celles fournies dans `conftest.py` (`make_ohlcv_random`, `make_ohlcv_from_close`). Chaque helper a des nuances (colonne `symbol`, timezone, colonnes supplémentaires) qui justifient parfois leur existence, mais d'autres sont des variantes mineures qui pourraient converger.

Les fichiers `test_volatility.py`, `test_ema_ratio.py`, `test_rsi.py`, `test_feature_pipeline.py` utilisent correctement les helpers partagés de conftest.

**Action** :
1. Évaluer si les helpers locaux de `test_equity_curve.py`, `test_qa.py`, `test_volume_features.py` peuvent être remplacés par des variantes paramétrées dans `conftest.py`.
2. Si un helper local est justifié (ex. format ccxt brut pour `test_ingestion.py`), le documenter.

### W-2. ~~Fixtures de test dupliquées entre fichiers~~ ✅ RÉSOLU

> **Résolu** : commit `67d9961` — `[RC-0005] FIX W-1,W-2: consolidate duplicate test helpers into conftest.py`

**Fichiers** : `tests/test_sample_builder.py` (L19), `tests/test_warmup_validation.py` (L30), `tests/test_splitter.py` (L68)
**Sévérité** : WARNING — duplication de logique de construction.

- `_make_features_df()` apparaît dans `test_sample_builder.py` et `test_warmup_validation.py`.
- `_make_timestamps()` est définie localement dans `test_splitter.py` alors qu'une version existe dans `conftest.py`.
- `_make_labels()` et `_make_window_config()` dans `test_sample_builder.py` pourraient être partagées.

**Action** : Consolider les helpers récurrents dans `conftest.py` pour éviter la dérive et faciliter la maintenance.

---

## MINEURS (4)

### M-1. Modules baselines, metrics, artifacts et pipeline vides

**Fichiers** : `ai_trading/baselines/__init__.py`, `ai_trading/metrics/__init__.py`, `ai_trading/artifacts/__init__.py`, `ai_trading/pipeline/__init__.py`
**Sévérité** : MINEUR — attendu, ces modules sont prévus pour M4/M5.

Ces modules ne contiennent qu'un docstring. C'est normal à ce stade (M3 terminé, M4 non commencé). À compléter lors des WS-9, WS-10, WS-11, WS-12.

**Action** : Aucune action immédiate. Vérifier leur implémentation lors des gates M4 et M5.

### M-2. Docstring `__main__.py` placeholder

**Fichiers** : `ai_trading/__main__.py` (L1-L18)
**Sévérité** : MINEUR — le point d'entrée CLI est un stub.

Le module `__main__.py` log un message « Pipeline not yet implemented » et fait `sys.exit(0)`. C'est prévu pour WS-12.3.

**Action** : Aucune action immédiate. Sera complété par WS-12.3.

### M-3. ~~Nommage `_FEATURE_NAME` dans `rsi.py` et `ema.py`~~ ✅ RÉSOLU

> **Résolu** : commit `ddfb890` — `[RC-0005] FIX M-3: remove _FEATURE_NAME constants, use inline strings`

**Fichiers** : `ai_trading/features/rsi.py` (L25), `ai_trading/features/ema.py` (L19)
**Sévérité** : MINEUR — cohérence cosmétique.

Les modules `rsi.py` et `ema.py` définissent une constante `_FEATURE_NAME` pour le nom de la feature, tandis que `log_returns.py` et `volume.py` utilisent des chaînes littérales inline. Les deux approches fonctionnent mais la convention n'est pas uniforme.

**Action** : Harmoniser le pattern (constante ou inline) dans tous les modules de features lors d'un refactoring futur.

### M-4. ~~Schéma Robust Scaler — IQR vs quantiles configurables~~ ✅ RÉSOLU

> **Résolu** : commit `364e6a2` — `[RC-0005] FIX M-4: document configurable IQR vs traditional Q25-Q75`

**Fichiers** : `ai_trading/data/scaler.py` (L205-L280)
**Sévérité** : MINEUR — documentation.

Le `RobustScaler` utilise les quantiles configurables `robust_quantile_low` (0.005) et `robust_quantile_high` (0.995) pour la mise à l'échelle, ce qui diffère de l'IQR traditionnel (Q25-Q75). La spec §9.2 mentionne « IQR » mais donne comme exemple « 0.5% et 99.5% », ce qui est ambigu. L'implémentation est raisonnable et les quantiles sont configurables.

**Action** : Ajouter un commentaire dans `scaler.py` précisant que « IQR » est ici l'écart inter-quantile configurable (pas nécessairement Q25-Q75).

---

## Conformité formules métier (§6c)

| ID | Section spec | Formule | Fichier code | Verdict |
|---|---|---|---|---|
| F-1 | §5.2 | $y_t = \log(C_{t+H} / O_{t+1})$ | `data/labels.py` | ✅ |
| F-2 | §6.2 | $\text{logret}_k(t) = \log(C_t / C_{t-k})$ | `features/log_returns.py` | ✅ |
| F-3 | §6.2 | $\text{logvol}(t) = \log(V_t + \varepsilon)$ | `features/volume.py` | ✅ |
| F-4 | §6.2 | $\text{dlogvol}(t) = \text{logvol}(t) - \text{logvol}(t-1)$ | `features/volume.py` | ✅ |
| F-5 | §6.3 | RSI Wilder (SMA init + récursif $\alpha = 1/n$) | `features/rsi.py` | ✅ |
| F-6 | §6.4 | $\text{EMA\_ratio} = \text{EMA}_{fast} / \text{EMA}_{slow} - 1$ | `features/ema.py` | ✅ |
| F-7 | §6.5 | $\text{vol}_w(t) = \text{std}(\text{logret}_1[t-w+1:t], \text{ddof})$ | `features/volatility.py` | ✅ |
| F-8 | §8.2 | $\text{embargo\_bars} \geq H$ | `data/splitter.py` | ✅ |
| F-9 | §9.1 | $x' = (x - \mu) / (\sigma + \varepsilon)$ | `data/scaler.py` | ✅ |
| F-10 | §9.2 | Robust : $(x - \text{median}) / (\text{IQR} + \varepsilon)$ + clip | `data/scaler.py` | 🔍 |
| F-11 | §11.2 | Grille quantiles sur val predictions | `calibration/threshold.py` | ✅ |
| F-12 | §12.3 | $M_{net} = (1-f)^2 \cdot \frac{C_{t+H}(1-s)}{O_{t+1}(1+s)}$, $r_{net} = M_{net} - 1$ | `backtest/costs.py` | ✅ |
| F-13 | §12.4 | $E_{exit} = E_{entry} \cdot (1 + w \cdot r_{net})$ | `backtest/engine.py` | ✅ |
| F-14 | §14.2 | Sharpe = $\mu(r) / \sigma(r) \times \sqrt{N_{ann}}$ | `metrics/` | ⚠️ |

> Légende : ✅ Conforme — ❌ Divergent — ⚠️ Non encore implémenté — 🔍 Spec ambiguë

**Écarts détaillés** :
- F-10 : La spec §9.2 mentionne « IQR » (traditionnellement Q75-Q25) mais cite comme exemple « 0.5% et 99.5% ». Le code utilise les quantiles configurables (`robust_quantile_low`=0.005, `robust_quantile_high`=0.995) comme intervalle de référence. L'implémentation est raisonnable — la spec est ambiguë sur ce point.
- F-14 : Module `metrics/` non encore implémenté (prévu WS-10, M4). Métrique Sharpe non codée.

---

## Conformité spec section-par-section (§6b)

| Section spec | Module code | Implémenté | Conforme | Remarques |
|---|---|---|---|---|
| §4.1 Source/format | `data/ingestion.py` | ✅ | ✅ | Colonnes canoniques, tz-aware UTC, Parquet |
| §4.2 QA checks | `data/qa.py` | ✅ | ✅ | Duplicatas, NaN, OHLC cohérence, gaps, prix négatifs, zero-volume |
| §4.3 Missing candles | `data/missing.py` | ✅ | ✅ | Masque booléen, pas d'interpolation |
| §5.2 Label trade | `data/labels.py` | ✅ | ✅ | `log(C[t+H]/O[t+1])` exact |
| §5.3 Label close-to-close | `data/labels.py` | ✅ | ✅ | `log(C[t+H]/C[t])` implémenté |
| §6.2 Features MVP logret | `features/log_returns.py` | ✅ | ✅ | logret_1, logret_2, logret_4 |
| §6.2 Features logvol/dlogvol | `features/volume.py` | ✅ | ✅ | Epsilon configurable |
| §6.3 RSI Wilder | `features/rsi.py` | ✅ | ✅ | SMA init + Wilder smoothing |
| §6.4 EMA ratio | `features/ema.py` | ✅ | ✅ | SMA init, ratio - 1 |
| §6.5 Volatilité | `features/volatility.py` | ✅ | ✅ | Fenêtres fixes 24/72, ddof config |
| §6.6 Warm-up | `features/warmup.py` | ✅ | ✅ | min_warmup >= max(min_periods), NaN check |
| §7.1 Dataset (N,L,F) | `data/dataset.py` | ✅ | ✅ | float32, sliding window |
| §7.2 Adapter XGBoost | `data/dataset.py` | ✅ | ✅ | Flatten (N, L×F) |
| §7.3 Métadonnées | `data/dataset.py` | ✅ | ✅ | decision_time, entry/exit time/price |
| §8.1–§8.4 Splits | `data/splitter.py` | ✅ | ✅ | Walk-forward rolling, embargo, purge |
| §9.1 Standard scaler | `data/scaler.py` | ✅ | ✅ | (x-μ)/(σ+ε), fit train only |
| §9.2 Robust scaler | `data/scaler.py` | ✅ | 🔍 | IQR = quantile configurable (voir F-10) |
| §10.1–§10.2 Interface modèle | `models/base.py` | ✅ | ✅ | ABC avec fit/predict/save/load, output_type |
| §10.4 Déterminisme modèle | `models/dummy.py` | ✅ | ✅ | default_rng(seed) |
| §11.1–§11.3 Calibration θ | `calibration/threshold.py` | ✅ | ✅ | Quantile grid, max_net_pnl_with_mdd_cap, fallback E.2.2 |
| §11.4–§11.5 Bypass θ | `calibration/threshold.py` | ✅ | ✅ | Signal models → method="none" |
| §12.1 Trade execution | `backtest/engine.py` | ✅ | ✅ | Go/No-Go, one_at_a_time, long_only |
| §12.3 Coûts | `backtest/costs.py` | ✅ | ✅ | Per-side multiplicative, formule exacte |
| §12.4 Equity curve | `backtest/engine.py` | ✅ | ✅ | E × (1 + w × r_net) |
| §12.5 Buy & hold | `backtest/engine.py` | ✅ | ✅ | single_trade mode |
| §12.6 Journal trades | — | ⚠️ | — | Pas de trades.csv (WS-8.4 non implémenté) |
| §13.1–§13.3 Baselines | `baselines/` | ⚠️ | — | Module vide (prévu M4, WS-9) |
| §14.1–§14.3 Métriques | `metrics/` | ⚠️ | — | Module vide (prévu M4, WS-10) |
| §15.1–§15.4 Artefacts | `artifacts/` | ⚠️ | — | Module vide (prévu M5, WS-11) |
| §16.1–§16.3 Repro | `utils/`, config | ⚠️ | — | Seed manager non implémenté (prévu M5, WS-12) |

---

## Conformité plan → code (§6bis)

| WS | Tâches DONE | Module(s) code | Code présent | Tests présents | Remarques |
|---|---|---|---|---|---|
| WS-1 | #001, #002, #003 | `config.py`, `__init__.py`, `__main__.py` | ✅ | ✅ | `test_project_structure.py`, `test_config.py`, `test_config_validation.py` |
| WS-2 | #004, #005, #006 | `data/ingestion.py`, `data/qa.py`, `data/missing.py`, `data/timeframes.py` | ✅ | ✅ | `test_ingestion.py`, `test_qa.py`, `test_missing.py` |
| WS-3 | #007–#014, #023 | `features/registry.py`, `features/log_returns.py`, `features/volatility.py`, `features/rsi.py`, `features/ema.py`, `features/volume.py`, `features/pipeline.py`, `features/warmup.py` | ✅ | ✅ | 9 fichiers de tests correspondants |
| WS-4 | #015–#020 | `data/labels.py`, `data/dataset.py`, `data/splitter.py` | ✅ | ✅ | `test_label_target.py`, `test_sample_builder.py`, `test_adapter_xgboost.py`, `test_metadata.py`, `test_splitter.py` |
| WS-5 | #021, #022 | `data/scaler.py` | ✅ | ✅ | `test_standard_scaler.py`, `test_robust_scaler.py` |
| WS-6 | #024, #025, #028, #034 | `models/base.py`, `models/dummy.py`, `training/trainer.py` | ✅ | ✅ | `test_base_model.py`, `test_dummy_model.py`, `test_fold_trainer.py`, `test_gate_doc.py` |
| WS-7 | #030–#033 | `calibration/threshold.py` | ✅ | ✅ | `test_quantile_grid.py`, `test_theta_optimization.py`, `test_theta_bypass.py` |
| WS-8 | #026, #027, #029 | `backtest/engine.py`, `backtest/costs.py` | ✅ | ✅ | `test_trade_execution.py`, `test_cost_model.py`, `test_equity_curve.py` |
| WS-9 | — | `baselines/` | ⚠️ vide | — | Pas de tâches DONE (M4) |
| WS-10 | — | `metrics/` | ⚠️ vide | — | Pas de tâches DONE (M4) |
| WS-11 | — | `artifacts/` | ⚠️ vide | — | Pas de tâches DONE (M5) |
| WS-12 | — | `pipeline/`, `utils/` | ⚠️ partiel | — | Logging implémenté, orchestrateur non (M5) |

**Anomalies plan ↔ code** :
- Tâches DONE sans code : aucune.
- Code sans tâche : `data/timeframes.py` — module utilitaire partagé, factoring naturel des modules WS-2. Non problématique.
- Critères d'acceptation [x] non vérifiables : aucun identifié.
- Modules attendus tous présents pour M1–M3.

---

## Anti-fuite

| Module | Check | Verdict |
|---|---|---|
| `features/log_returns.py` | backward-looking only (`.shift(k)`, k > 0) | ✅ |
| `features/volume.py` | backward-looking only (`.shift(1)`) | ✅ |
| `features/rsi.py` | backward-looking only (SMA init + forward recursion) | ✅ |
| `features/ema.py` | backward-looking only (SMA init + forward recursion) | ✅ |
| `features/volatility.py` | backward-looking only (rolling window) | ✅ |
| `data/labels.py` | forward-looking intentionnel (label = futur, masqué) | ✅ |
| `data/splitter.py` | embargo_bars >= H, purge implémentée | ✅ |
| `data/scaler.py` | fit sur train uniquement, API claire | ✅ |
| `training/trainer.py` | scaler.fit(X_train), transform(X_val/X_test) | ✅ |
| `calibration/threshold.py` | θ calibré sur val, pas test | ✅ |
| `data/missing.py` | masque conservative, pas d'interpolation | ✅ |
| Recherche `.shift(-n)` dans tout `ai_trading/` | Aucune occurrence | ✅ |

---

## Audit inter-modules

### Contrat de données
- ✅ Les colonnes produites par ingestion (`timestamp_utc`, `open`, `high`, `low`, `close`, `volume`, `symbol`) correspondent aux colonnes attendues par QA et features.
- ✅ Les features produisent des `pd.Series` indexées par le même index que l'OHLCV.
- ✅ Le sample builder produit des tenseurs float32 `(N, L, F)` conformes à l'interface modèle.
- ✅ Le scaler attend et produit des arrays 3D `(N, L, F)` float32.
- ✅ Les types de données aux frontières sont cohérents (float64 pour métriques/labels, float32 pour tenseurs).

### Contrat de paramètres
- ✅ Toutes les clés config lues par les modules existent dans `configs/default.yaml`.
- ✅ Noms de paramètres cohérents entre config, code et spec.
- ✅ Paramètre `vol_windows` correctement verrouillé (misleading param documenté et validé en config).

### Contrat de registre (features)
- ✅ Les 9 features de `feature_list` sont toutes enregistrées dans `FEATURE_REGISTRY`.
- ✅ Les `required_params` de chaque feature correspondent à des clés existantes dans `features.params`.
- ✅ `min_periods` est cohérent avec le comportement réel de `compute()`.
- ✅ Le `__init_subclass__` enforce la déclaration explicite de `required_params`.

### Chaîne d'appel pipeline
- ✅ Ingestion → QA → Features → Dataset → Splits → Scaling → Training : interfaces compatibles.
- ✅ Le FoldTrainer orchestre correctement : `create_scaler().fit(X_train)` → `transform(X_*)` → `model.fit()` → `model.predict()`.
- ✅ La calibration θ appelle `execute_trades` → `apply_cost_model` → `build_equity_curve` correctement.

---

## Reproductibilité

| Aspect | Verdict | Détail |
|---|---|---|
| Seeds test | ✅ | Tous les tests utilisent `np.random.default_rng(seed)` |
| Seeds code | ✅ | `DummyModel` utilise `np.random.default_rng(self._seed)` |
| Legacy random API | ✅ | Aucune occurrence `np.random.seed()`, `np.random.randn()`, `np.random.RandomState()` |
| Seed manager (WS-12) | ⚠️ | Non encore implémenté (prévu M5) |
| SHA-256 hashes | ✅ | Implémenté dans `ingestion.py` pour les fichiers Parquet |

---

## Résumé des actions

| # | Sévérité | Action | Fichier(s) |
|---|---|---|---|
| W-1 | WARNING | Consolider les helpers OHLCV de tests vers `conftest.py` | `tests/test_equity_curve.py`, `tests/test_qa.py`, `tests/test_volume_features.py` |
| W-2 | WARNING | Consolider les fixtures dupliquées vers `conftest.py` | `tests/test_sample_builder.py`, `tests/test_warmup_validation.py`, `tests/test_splitter.py` |
| M-1 | MINEUR | Compléter les modules vides lors de M4/M5 | `baselines/`, `metrics/`, `artifacts/`, `pipeline/` |
| M-2 | MINEUR | Compléter `__main__.py` lors de WS-12.3 | `ai_trading/__main__.py` |
| M-3 | MINEUR | Harmoniser pattern `_FEATURE_NAME` vs inline | `features/rsi.py`, `features/ema.py` |
| M-4 | MINEUR | Documenter le choix IQR configurable vs traditionnel | `data/scaler.py` |

---

## Synthèse

La branche `Max6000i1` est dans un **excellent état** après l'achèvement de M3. Les 917 tests passent, le linter est propre, aucun bloquant n'est identifié. Les 34 tâches (M1+M2+M3) sont toutes DONE avec code et tests correspondants. Toutes les formules métier implémentées (F-1 à F-13) sont conformes à la spécification. Les règles non négociables (strict code, config-driven, anti-fuite, reproductibilité) sont respectées. Les 2 warnings portent exclusivement sur la consolidation DRY des helpers de tests — aucun impact sur le code de production. La branche est prête pour le gate M3 et le démarrage de M4.
