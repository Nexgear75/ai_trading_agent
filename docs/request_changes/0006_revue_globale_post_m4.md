# Request Changes — Revue globale post-M4 (branche Max6000i1)

Statut : DONE
Ordre : 0006

**Date** : 2026-03-03
**Périmètre** : Audit complet de tous les modules source (`ai_trading/`) et tests (`tests/`) de la branche `Max6000i1`, couvrant M1 à M4 (WS-1 à WS-10), 43 tâches DONE.
**Résultat** : 1221 tests GREEN, ruff clean
**Verdict** : ✅ CLEAN (après corrections)

---

## Résultats d'exécution

| Check | Résultat |
|---|---|
| `pytest tests/` | **1220 passed** / 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |
| `print()` résiduel | Aucun |
| `TODO`/`FIXME` orphelin | Aucun |
| `.shift(-n)` (look-ahead) | Aucun |
| Broad `except` | Aucun |
| Legacy random API | Aucun |
| `or default` / silent fallback | Aucun (docstrings seuls) |

---

## BLOQUANTS (1)

### ~~B-1. `FoldTrainer.train_fold()` ne transmet pas `meta_test` à `model.predict()` — rupture avec SmaRuleBaseline~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/training/trainer.py` (L95–L96), `ai_trading/baselines/sma_rule.py` (L100–L104)
**Sévérité** : BLOQUANT — le pipeline intégré ne peut pas exécuter la baseline SMA sur le split test.

Le `FoldTrainer.train_fold()` n'accepte pas de paramètre `meta_test` et appelle :

```python
y_hat_test = model.predict(X=x_test_scaled, ohlcv=ohlcv)
```

sans passer `meta`. Or `SmaRuleBaseline.predict()` lève `ValueError("SmaRuleBaseline.predict() requires meta (got None).")` si `meta is None`.

Le test `test_fold_trainer.py` (L562) confirme explicitement : `meta=None` pour test predict. Ce comportement est correct pour DummyModel et les baselines no_trade/buy_hold, mais casse l'intégration avec SMA.

**Action** :
1. Ajouter `meta_test: Any = None` comme paramètre de `train_fold()`.
2. Passer `meta=meta_test` dans l'appel `model.predict()` pour X_test.
3. Ajouter un test d'intégration FoldTrainer + SmaRuleBaseline.

> **Résolu** : commit `74ed7cf` — `[RC-0006] FIX B-1: add meta_test to FoldTrainer.train_fold() and forward to model.predict() for test split`

---

## WARNINGS (3)

### ~~W-1. `DummyModel.__init__` a un default implicite `seed=42`~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/models/dummy.py` (L28)
**Sévérité** : WARNING — violation de la convention strict-code (pas de valeurs par défaut implicites).

Le constructeur `DummyModel(seed: int = 42)` fournit un défaut sans référence au fichier config (`reproducibility.global_seed`). La seed devrait être fournie explicitement par l'appelant.

**Action** : Supprimer le défaut (`seed: int`) et imposer l'injection explicite, ou documenter que le défaut 42 est volontaire pour les tests d'intégration uniquement.

> **Résolu** : commit `884ab29` — `[RC-0006] FIX W-1: remove implicit seed=42 default from DummyModel.__init__()`

### ~~W-2. Formule `net_pnl` incohérente entre `calibrate_threshold()` et `compute_net_pnl()`~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/calibration/threshold.py` (L257–L258), `ai_trading/metrics/trading.py` (L104–L107)
**Sévérité** : WARNING — divergence masquée quand `initial_equity = 1.0`, mais bug si `initial_equity ≠ 1.0`.

- `compute_net_pnl()` : `equity[-1] / equity[0] - 1.0` (rendement relatif)
- `calibrate_threshold()` : `final_equity - initial_equity` (variation absolue)

Avec `initial_equity = 1.0` (config par défaut), les deux sont identiques. Mais si `initial_equity` change (ex: 10000), le net_pnl de la calibration serait ~10000× plus grand, faussant la sélection du θ.

**Action** : Aligner la calibration sur `compute_net_pnl()` : `net_pnl = final_equity / initial_equity - 1.0`.

> **Résolu** : commit `8cca371` — `[RC-0006] FIX W-2: align net_pnl in calibrate_threshold() to relative formula (E_T/E_0 - 1)`

### ~~W-3. `StandardScaler.fit()` — ddof non explicite pour `std()`~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/data/scaler.py` (L92)
**Sévérité** : WARNING — le `ddof` implicite de numpy (0) est correct mais non documenté.

Le code `flat.std(axis=0)` utilise le ddof par défaut de numpy (0). La spec §9.1 dit « écart-type » sans préciser ddof. Le résultat est correct (population std pour la normalisation), mais l'absence d'argument explicite `ddof=0` est une source potentielle d'erreur lors de refactoring.

**Action** : Rendre le ddof explicite : `flat.std(axis=0, ddof=0)`.

> **Résolu** : commit `ef6bf9f` — `[RC-0006] FIX W-3: make ddof=0 explicit in StandardScaler.fit()`

---

## MINEURS (4)

### M-1. `conftest.py` — `TIMEFRAME_DELTA` importé comme `_TIMEFRAME_DELTA` dans `qa.py` mais directement dans `conftest.py`

**Fichiers** : `ai_trading/data/qa.py` (L14), `tests/conftest.py`
**Sévérité** : MINEUR — incohérence cosmétique dans la convention d'import privé.

`qa.py` importe `TIMEFRAME_DELTA as _TIMEFRAME_DELTA` (convention privée), tandis que d'autres modules (`splitter.py`) importent directement `parse_timeframe`. Convention non uniforme.

**Action** : Aucune action immédiate nécessaire. À uniformiser lors d'un refactoring.

### M-2. Feature `rsi_14` — nom hardcodé dans `Series.name`

**Fichiers** : `ai_trading/features/rsi.py` (L95, L101)
**Sévérité** : MINEUR — le nom de série `"rsi_14"` est hardcodé dans le corps de `compute()`.

Si la feature est réutilisée avec un `rsi_period` différent du 14 par défaut, le nom de la série resterait `"rsi_14"`. Cependant le registre mappe `"rsi_14"` → `RSI14`, et le pipeline renomme la série via le registre, donc pas d'impact fonctionnel dans le MVP.

**Action** : Aucune action nécessaire pour le MVP. À considérer si des RSI multi-périodes sont ajoutés.

### ~~M-3. `aggregation.py` — `_EXCLUDED_METRICS` contient `n_samples_*` non produits par les métriques actuelles~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/metrics/aggregation.py` (L49–L53)
**Sévérité** : MINEUR — clés préventives pour des métriques futures.

Les clés `n_samples_train`, `n_samples_val`, `n_samples_test` sont dans `_EXCLUDED_METRICS` mais ne sont produites par aucun module actuel. C'est une anticipation pour l'orchestrateur (WS-12).

**Action** : Documenter avec un commentaire que ces clés sont réservées pour WS-12.

> **Résolu** : commit `197d030` — `[RC-0006] FIX M-3: document _EXCLUDED_METRICS n_samples_* as reserved for WS-12`

### M-4. `EmaRatio1226.__name__` et `RSI14.__name__` — couplage nom de classe / paramètres par défaut

**Fichiers** : `ai_trading/features/ema.py`, `ai_trading/features/rsi.py`
**Sévérité** : MINEUR — les noms de classe (`EmaRatio1226`, `RSI14`) encodent les paramètres par défaut.

C'est une convention acceptable au MVP (un seul jeu de paramètres), mais rigide si l'on veut plusieurs configurations en parallèle.

**Action** : Aucune action requise pour le MVP.

---

## Conformité formules métier (§6c)

| ID | Section spec | Formule | Fichier code | Verdict |
|---|---|---|---|---|
| F-1 | §5.2 | $y_t = \log(C_{t+H} / O_{t+1})$ | `data/labels.py` | ✅ Conforme |
| F-2 | §6.2 | $\text{logret}_k(t) = \log(C_t / C_{t-k})$ | `features/log_returns.py` | ✅ Conforme |
| F-3 | §6.2 | $\text{logvol}(t) = \log(V_t + \varepsilon)$ | `features/volume.py` | ✅ Conforme |
| F-4 | §6.2 | $\text{dlogvol}(t) = \text{logvol}(t) - \text{logvol}(t-1)$ | `features/volume.py` | ✅ Conforme |
| F-5 | §6.3 | RSI Wilder (SMA init + récursif $\alpha = 1/n$) | `features/rsi.py` | ✅ Conforme |
| F-6 | §6.4 | $\text{EMA\_ratio} = \text{EMA}_{fast}/\text{EMA}_{slow} - 1$ | `features/ema.py` | ✅ Conforme |
| F-7 | §6.5 | $\text{vol}_w(t) = \text{std}(\text{logret}_1[t\text{-}w\text{+}1:t], \text{ddof})$ | `features/volatility.py` | ✅ Conforme |
| F-8 | §8.2 | $\text{embargo\_bars} \geq H$ | `data/splitter.py` | ✅ Conforme |
| F-9 | §9.1 | $x' = (x - \mu) / (\sigma + \varepsilon)$ | `data/scaler.py` | ✅ Conforme |
| F-10 | §9.2 | Robust : $(x - \text{median}) / (\text{IQR} + \varepsilon)$ + clip | `data/scaler.py` | ✅ Conforme |
| F-11 | §11.2 | Grille quantiles sur val predictions | `calibration/threshold.py` | ✅ Conforme |
| F-12 | §12.3 | $M_{net} = (1-f)^2 \cdot \frac{C_{t+H}(1-s)}{O_{t+1}(1+s)}$, $r_{net} = M_{net} - 1$ | `backtest/costs.py` | ✅ Conforme |
| F-13 | §12.4 | $E_{exit} = E_{entry} \cdot (1 + w \cdot r_{net})$ | `backtest/engine.py` | ✅ Conforme |
| F-14 | §14.2 | $\text{Sharpe} = \frac{\mu(r)}{\sigma(r) + \varepsilon} \times \sqrt{K}$ | `metrics/trading.py` | ✅ Conforme |

> Légende : ✅ Conforme — ❌ Divergent — ⚠️ Non encore implémenté — 🔍 Spec ambiguë

**Écarts détaillés** : Aucun écart de formule métier détecté. Les 14 formules du MVP sont fidèlement implémentées.

---

## Conformité spec section-par-section (§6b)

| Section spec | Module code | Implémenté | Conforme | Remarques |
|---|---|---|---|---|
| §4.1 Source/format | `data/ingestion.py` | ✅ | ✅ | Colonnes canoniques, tz-aware UTC, SHA-256 |
| §4.2 QA checks | `data/qa.py` | ✅ | ✅ | Duplicatas, NaN, OHLC, gaps, volume nul |
| §4.3 Missing candles | `data/missing.py` | ✅ | ✅ | Forward-fill via masque booléen |
| §5.2 Label trade | `data/labels.py` | ✅ | ✅ | `log(C[t+H]/O[t+1])` exact |
| §5.3 Label C-to-C | `data/labels.py` | ✅ | ✅ | `log(C[t+H]/C[t])` activable en config |
| §6.2–§6.5 Features | `features/` | ✅ | ✅ | 9 features MVP, formules conformes |
| §6.6 Warm-up | `features/warmup.py` | ✅ | ✅ | `min_warmup ≥ max(min_periods)`, NaN check |
| §7.1–§7.3 Dataset | `data/dataset.py` | ✅ | ✅ | `(N,L,F)` float32, flatten, meta |
| §8.1–§8.4 Splits | `data/splitter.py` | ✅ | ✅ | Walk-forward, embargo, purge, date-based |
| §9.1–§9.2 Scaling | `data/scaler.py` | ✅ | ✅ | Standard + Robust, fit train-only |
| §10.1–§10.4 Modèle | `models/` | ✅ | ✅ | ABC conforme, DummyModel, registre |
| §11.1–§11.3 Calibration | `calibration/` | ✅ | ✅ | Quantile grid, MDD cap, fallback E.2.2 |
| §12.1–§12.6 Backtest | `backtest/` | ✅ | ✅ | Exécution, coûts, equity, journal |
| §13.1–§13.3 Baselines | `baselines/` | ✅ | ✅ | no-trade, buy_hold, sma_rule |
| §14.1–§14.3 Métriques | `metrics/` | ✅ | ✅ | Prédiction + trading + agrégation |
| §15.1–§15.4 Artefacts | `artifacts/` | ⚠️ | ⚠️ | Module vide (prévu WS-11, M5) |
| §16.1–§16.3 Repro | `utils/` | ⚠️ | ⚠️ | Logging seulement. Seed manager prévu WS-12. |

---

## Conformité plan → code (§6bis)

| WS | Tâches DONE | Module(s) code | Code présent | Tests présents | Remarques |
|---|---|---|---|---|---|
| WS-1 | #001, #002, #003 | `config.py` | ✅ | ✅ | Config loader + validation Pydantic v2 |
| WS-2 | #004, #005, #006 | `data/ingestion.py`, `data/qa.py`, `data/missing.py` | ✅ | ✅ | Ingestion ccxt + QA + missing mask |
| WS-3 | #007–#014, #023 | `features/` (8 fichiers) | ✅ | ✅ | 9 features + registre + pipeline + warmup |
| WS-4 | #015–#020 | `data/labels.py`, `data/dataset.py`, `data/splitter.py` | ✅ | ✅ | Label + samples + XGBoost adapter + meta + splits + embargo |
| WS-5 | #021, #022 | `data/scaler.py` | ✅ | ✅ | Standard + Robust scaler avec factory |
| WS-6 | #024, #025, #028, #034 | `models/base.py`, `models/dummy.py`, `training/trainer.py` | ✅ | ✅ | ABC + registre + DummyModel + FoldTrainer |
| WS-7 | #030–#033 | `calibration/threshold.py` | ✅ | ✅ | Quantile grid + θ optimization + fallback + bypass |
| WS-8 | #026, #027, #029, #035, #036 | `backtest/engine.py`, `backtest/costs.py`, `backtest/journal.py` | ✅ | ✅ | Exécution + coûts + equity curve + journal |
| WS-9 | #037–#039 | `baselines/` | ✅ | ✅ | 3 baselines conformes |
| WS-10 | #040–#043 | `metrics/` | ✅ | ✅ | Prédiction + trading + agrégation + gate M4 |
| WS-11 | — | `artifacts/__init__.py` | ⚠️ | — | Module vide, pas de tâches (M5) |
| WS-12 | — | `utils/logging.py`, `__main__.py` | ⚠️ | — | Logging + placeholder CLI, pas de tâches (M5) |

**Anomalies plan ↔ code** :
- **Tâches DONE sans code** : Aucune.
- **Code sans tâche** : `data/timeframes.py` — module utilitaire de parsing des timeframes. Consommé par `splitter.py`, `ingestion.py`, `qa.py`. N'a pas de tâche dédiée ; probablement créé comme utilitaire pour WS-2/WS-4. Acceptable (helper pur).
- **Critères d'acceptation [x] non vérifiables** : Aucun détecté (les 43 tâches DONE ont du code et des tests correspondants).
- **Ordonnancement respecté** : Oui — les imports inter-modules reflètent les dépendances WS (features n'importe pas data, calibration importe backtest, etc.).

---

## Anti-fuite

| Module | Check | Verdict |
|---|---|---|
| `features/log_returns.py` | backward-looking only (`close.shift(k)`, k > 0) | ✅ |
| `features/volatility.py` | backward-looking rolling window | ✅ |
| `features/rsi.py` | forward-only loop, SMA init sur passé | ✅ |
| `features/ema.py` | forward-only loop, SMA init sur passé | ✅ |
| `features/volume.py` | point-in-time (`log(V_t + ε)`, `diff(shift(1))`) | ✅ |
| `features/warmup.py` | invalidation zones instables, pas d'accès futur | ✅ |
| `data/labels.py` | accès futur explicite sur y (spec-conforme), masqué par label_mask | ✅ |
| `data/dataset.py` | sliding window backward, y[t] vérifié non-NaN | ✅ |
| `data/splitter.py` | train < val < test, embargo appliqué | ✅ |
| `data/scaler.py` | `fit()` sur X_train seul, `transform()` stateless | ✅ |
| `training/trainer.py` | `scaler.fit(X_train)` uniquement | ✅ |
| `calibration/threshold.py` | θ calibré sur val, pas test | ✅ |
| `baselines/sma_rule.py` | `rolling().mean()` backward-looking | ✅ |

Aucune fuite temporelle détectée. Les conventions anti-leak sont respectées dans tout le code source.

---

## Audit inter-modules — interfaces et contrats

### Contrat de données

| Producteur → Consommateur | Interface | Verdict |
|---|---|---|
| `ingestion` → `qa` | DataFrame avec `timestamp_utc`, OHLCV | ✅ |
| `qa` → `missing` | Timestamps pd.Series | ✅ |
| `missing` → `warmup` | `ndarray[bool]` (candle valid mask) | ✅ |
| `features/pipeline` → `dataset` | `pd.DataFrame` features indexé par timestamp | ✅ |
| `labels` → `dataset` | `(y float64, label_mask bool)` | ✅ |
| `dataset` → `splitter` | `pd.DatetimeIndex` timestamps | ✅ |
| `splitter` → `trainer` | `FoldInfo` avec indices ndarray | ✅ |
| `trainer` → `model` | `(N,L,F) float32`, `(N,) float32` | ✅ |
| `model.predict` → `calibration` | `(N,) float32` y_hat | ✅ |
| `engine.execute_trades` → `costs` | `list[dict]` avec entry/exit_price | ✅ |
| `costs` → `engine.build_equity_curve` | `list[dict]` avec r_net, entry/exit_time | ✅ |
| `engine` → `metrics/trading` | DataFrame `{time_utc, equity, in_trade}` | ✅ |
| `trainer` → `sma_rule.predict(test)` | ✅ `meta=meta_test` | ✅ **B-1 résolu** |

### Contrat de registre (features)

| Config `feature_list` | Registre `FEATURE_REGISTRY` | `required_params` → `features.params` | Verdict |
|---|---|---|---|
| `logret_1` | `LogReturn1` | `[]` → — | ✅ |
| `logret_2` | `LogReturn2` | `[]` → — | ✅ |
| `logret_4` | `LogReturn4` | `[]` → — | ✅ |
| `vol_24` | `Volatility24` | `["volatility_ddof"]` → `params.volatility_ddof` | ✅ |
| `vol_72` | `Volatility72` | `["volatility_ddof"]` → `params.volatility_ddof` | ✅ |
| `logvol` | `LogVolume` | `["logvol_epsilon"]` → `params.logvol_epsilon` | ✅ |
| `dlogvol` | `DLogVolume` | `["logvol_epsilon"]` → `params.logvol_epsilon` | ✅ |
| `rsi_14` | `RSI14` | `["rsi_period", "rsi_epsilon"]` → `params.rsi_*` | ✅ |
| `ema_ratio_12_26` | `EmaRatio1226` | `["ema_fast", "ema_slow"]` → `params.ema_*` | ✅ |

Toutes les features du registre sont cohérentes avec la config par défaut.

### Contrat du model registry

| Config `strategy.name` | Registre `MODEL_REGISTRY` | `output_type` | `execution_mode` | Verdict |
|---|---|---|---|---|
| `dummy` | `DummyModel` | `regression` | `standard` | ✅ |
| `no_trade` | `NoTradeBaseline` | `signal` | `standard` | ✅ |
| `buy_hold` | `BuyHoldBaseline` | `signal` | `single_trade` | ✅ |
| `sma_rule` | `SmaRuleBaseline` | `signal` | `standard` | ✅ |

---

## Résumé des actions

| # | Sévérité | Action | Fichier(s) |
|---|---|---|---|
| B-1 | BLOQUANT | Ajouter `meta_test` à `FoldTrainer.train_fold()` et le passer à `model.predict()` pour X_test | `ai_trading/training/trainer.py`, `tests/test_fold_trainer.py` |
| W-1 | WARNING | Supprimer la valeur par défaut `seed=42` du constructeur DummyModel ou documenter la justification | `ai_trading/models/dummy.py` |
| W-2 | WARNING | Aligner le calcul de `net_pnl` dans `calibrate_threshold()` sur `compute_net_pnl()` (rendement relatif) | `ai_trading/calibration/threshold.py` |
| W-3 | WARNING | Rendre `ddof=0` explicite dans `StandardScaler.fit()` | `ai_trading/data/scaler.py` |
| M-1 | MINEUR | Uniformiser convention d'import `TIMEFRAME_DELTA` | `ai_trading/data/qa.py` |
| M-2 | MINEUR | Considérer un nom de série dynamique pour RSI si multi-périodes | `ai_trading/features/rsi.py` |
| M-3 | MINEUR | Documenter les clés `_EXCLUDED_METRICS` comme réservées WS-12 | `ai_trading/metrics/aggregation.py` |
| M-4 | MINEUR | Convention de nommage classes → paramètres (cosmétique MVP) | `ai_trading/features/ema.py`, `ai_trading/features/rsi.py` |
