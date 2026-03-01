# Request Changes — Revue globale post-M2 (features + data pipeline)

Statut : DONE
Ordre : 0003

**Date** : 2026-03-01
**Périmètre** : Ensemble du code source `ai_trading/` et `tests/` — branche `Max6000i1` — WS-1 à WS-5 (23 tâches DONE)
**Résultat** : 664 tests GREEN, ruff clean
**Verdict** : ⚠️ REQUEST CHANGES

---

## Résultats d'exécution

| Check | Résultat |
|---|---|
| `pytest tests/` | **664 passed** en 6.50s |
| `ruff check ai_trading/ tests/` | **All checks passed** |
| `print()` résiduel | Aucun |
| `TODO`/`FIXME` orphelin | Aucun |
| `.shift(-n)` (look-ahead) | Aucun |
| Broad `except` | Aucun (2 `except` ciblés, corrects) |
| Legacy random API | Aucun (tous `np.random.default_rng(seed)`) |

---

## BLOQUANTS (1)

### B-1. `logvol` et `dlogvol` : `min_periods` viole le contrat unifié (tâche #023) — ✅ RÉSOLU (4e30d84)

**Fichiers** : `ai_trading/features/volume.py` (L39, L52), `tests/test_volume_features.py` (L89–L95)
**Sévérité** : BLOQUANT — violation du contrat inter-modules établi par la tâche #023. Impact potentiel sur le calcul du warmup si `min_periods` est utilisé en aval pour déterminer automatiquement `min_warmup`.

Le contrat défini dans `ai_trading/features/registry.py` (L90–92) est :

> `min_periods` = nombre de NaN en tête du résultat de `compute()` = index 0-based du premier non-NaN.

Vérification empirique sur un dataset de 200 barres :

| Feature | `min_periods()` | NaN en tête réels | Verdict |
|---|---|---|---|
| `logvol` | **1** | **0** | ❌ MISMATCH |
| `dlogvol` | **2** | **1** | ❌ MISMATCH |
| logret_1 | 1 | 1 | ✅ |
| logret_2 | 2 | 2 | ✅ |
| logret_4 | 4 | 4 | ✅ |
| rsi_14 | 14 | 14 | ✅ |
| ema_ratio_12_26 | 25 | 25 | ✅ |
| vol_24 | 24 | 24 | ✅ |
| vol_72 | 72 | 72 | ✅ |

`logvol(t) = log(V_t + ε)` est défini dès la première barre (index 0), donc `min_periods` devrait être **0**.
`dlogvol(t) = logvol(t) - logvol(t-1)` a un NaN à l'index 0, donc `min_periods` devrait être **1**.

Les tests `test_volume_features.py` (L89, L93) assertent les valeurs incorrectes (`== 1` et `== 2`), ce qui masque le bug.

**Action** :
1. Corriger `LogVolume.min_periods()` → retourner `0` au lieu de `1`.
2. Corriger `DLogVolume.min_periods()` → retourner `1` au lieu de `2`.
3. Mettre à jour les tests `test_logvol_min_periods_is_1` → `test_logvol_min_periods_is_0` et `test_dlogvol_min_periods_is_2` → `test_dlogvol_min_periods_is_1`.

---

## WARNINGS (1)

### W-1. `warmup.py` : paramètre `params` avec default implicite `None → {}` — ✅ RÉSOLU (910cceb)

**Fichiers** : `ai_trading/features/warmup.py` (L21, L67)
**Sévérité** : WARNING — violation de la règle « strict code, no fallbacks ».

La signature `params: dict | None = None` avec le fallback `params_dict = params if params is not None else {}` (L67) est un pattern interdit par les conventions du projet (`AGENTS.md` → « Avoid patterns like `value if value else default` »).

Si `params` est `None` et qu'une feature a des `required_params` non vides, l'erreur sera levée plus tard (KeyError dans `min_periods()`, catchée L74), mais le parcours est indirect et le fallback à `{}` masque l'erreur initiale.

Impact actuel : limité car l'exception KeyError est bien catchée et ré-emballée en ValueError. Mais le pattern viole la convention projet.

**Action** :
1. Supprimer la valeur par défaut `None` et rendre `params` obligatoire : `params: dict`.
2. Supprimer la ligne `params_dict = params if params is not None else {}`.
3. Mettre à jour les tests qui appellent `apply_warmup` sans `params` pour passer un dict explicite.

---

## MINEURS (5)

### M-1. Duplication des helpers OHLCV dans les tests — ✅ RÉSOLU (51835f3)

**Fichiers** : `tests/test_qa.py` (L28–59), `tests/test_label_target.py` (L32–54), `tests/test_metadata.py` (L20–34)
**Sévérité** : MINEUR — duplication DRY inter-fichiers de tests.

Trois fichiers de tests définissent des fonctions `_make_ohlcv()` locales qui dupliquent la logique de `conftest.make_ohlcv_from_close()` et `conftest.make_ohlcv_random()`. Les builders sont fonctionnellement similaires avec des variations mineures (dates de départ, paramètres).

**Action** : Étendre les helpers de `conftest.py` pour couvrir les cas d'usage de ces trois fichiers (paramètre `seed`, volume personnalisable), puis remplacer les helpers locaux par des imports.

### M-2. `test_feature_registry.py` : fixture `_clean_registry` locale au lieu du factory partagé — ✅ RÉSOLU (51835f3)

**Fichiers** : `tests/test_feature_registry.py` (L43–51)
**Sévérité** : MINEUR — incohérence de pattern de test.

Ce fichier réimplémente localement la fixture `_clean_registry` au lieu d'utiliser `clean_registry_with_reload()` de `conftest.py`. La version locale ne recharge pas les modules de features, ce qui est acceptable pour ce fichier spécifique, mais le pattern diverge.

**Action** : Remplacer la fixture locale par `_clean_registry = clean_registry_with_reload()` (appel sans arguments, pas de rechargement de module) ou documenter explicitement pourquoi la version locale est appropriée ici.

### M-3. Validation `Series.name` non uniforme dans les tests de features — ✅ RÉSOLU (51835f3)

**Fichiers** : `tests/test_rsi.py`, `tests/test_ema_ratio.py`, `tests/test_volatility.py`
**Sévérité** : MINEUR — couverture de test incomplète.

Seuls `test_log_returns.py` (via `pd.testing.assert_series_equal`) et `test_volume_features.py` (assertions explicites `series.name`) vérifient le nom de la Series retournée par `compute()`. Les tests RSI, EMA et volatilité n'ont pas d'assertions sur `Series.name`.

**Action** : Ajouter `assert result.name == "<expected>"` dans chaque fichier de test de feature pour garantir le contrat de nommage.

### M-4. Fixture `rng` dupliquée entre `test_standard_scaler.py` et `test_robust_scaler.py` — ✅ RÉSOLU (51835f3)

**Fichiers** : `tests/test_standard_scaler.py` (L31), `tests/test_robust_scaler.py` (L37)
**Sévérité** : MINEUR — duplication DRY mineure.

Les deux fichiers définissent `@pytest.fixture def rng(): return np.random.default_rng(42)`.

**Action** : Extraire la fixture `rng` dans `conftest.py` si pertinent, ou laisser en l'état (impact très faible).

### M-5. Builders de timestamps dupliqués entre tests — ✅ RÉSOLU (51835f3)

**Fichiers** : `tests/test_missing.py` (L14–23), `tests/test_splitter.py` (L32–44)
**Sévérité** : MINEUR — duplication DRY de helpers de test.

Les deux fichiers définissent des fonctions `_make_timestamps()` avec des signatures légèrement différentes.

**Action** : Unifier dans `conftest.py` avec une signature paramétrique couvrant les deux cas d'usage.

---

## Conformité formules métier

| Feature/Module | Section spec | Verdict |
|---|---|---|
| `logret_1/2/4` | §6.2 — `log(C_t / C_{t-k})` | ✅ Correct |
| `rsi_14` | §6.3 — Wilder smoothing, SMA init | ✅ Correct |
| `ema_ratio_12_26` | §6.4 — `EMA_fast / EMA_slow - 1`, SMA init | ✅ Correct |
| `vol_24`, `vol_72` | §6.5 — `std(logret_1, window, ddof=config)` | ✅ Correct |
| `logvol` | §6.2 — `log(V_t + ε)` | ✅ Correct |
| `dlogvol` | §6.2 — `logvol(t) - logvol(t-1)` | ✅ Correct |
| `y_t` (log_return_trade) | §5 — `log(C_{t+H} / O_{t+1})` | ✅ Correct |
| `y_t` (close_to_close) | §5 — `log(C_{t+H} / C_t)` | ✅ Correct |
| `StandardScaler` | §9.1 — `(x - μ) / (σ + ε)`, fit-on-train | ✅ Correct (ddof=0) |
| `RobustScaler` | §9.2 — median/IQR + clip | ✅ Correct |
| Walk-forward splitter | §8 — date-based bounds, embargo, min-samples | ✅ Correct |
| Embargo/purge | §8.2 — `purge_cutoff = test_start - embargo * Δ` | ✅ Correct |
| QA checks | §4.2 — 6 vérifications obligatoires | ✅ Correct |
| Missing candles | §4.3 — mask sans interpolation | ✅ Correct |
| Config validation | Cross-fields (warmup ≥ feature min, embargo ≥ H, etc.) | ✅ Correct |

---

## Anti-fuite

| Module | Check | Verdict |
|---|---|---|
| `log_returns.py` | `.shift(k)` backward-looking only | ✅ |
| `rsi.py` | Wilder smoothing causal | ✅ |
| `ema.py` | EMA causal (SMA init + forward pass) | ✅ |
| `volatility.py` | `.rolling(window).std()` backward-looking | ✅ |
| `volume.py` | `.shift(1)` backward-looking only | ✅ |
| `labels.py` | Forward shift `t+H` for label only (not features) | ✅ |
| `missing.py` | Mask marks boundaries, no data leakage | ✅ |
| `splitter.py` | `train < val < test` enforced, embargo applied | ✅ |
| `scaler.py` | `fit()` on train only, no test data in statistics | ✅ |
| `warmup.py` | Mask-based approach, no future data | ✅ |
| `dataset.py` | Windows `[t-L+1, t]` backward-looking | ✅ |
| Aucun `.shift(-n)` | Confirmé par grep global | ✅ |

---

## Reproductibilité

| Check | Verdict |
|---|---|
| Aucune utilisation legacy `np.random.seed()`/`RandomState()` | ✅ |
| Tests : `np.random.default_rng(seed)` partout | ✅ |
| Config : `reproducibility.global_seed = 42` | ✅ |
| Config : `deterministic_torch = true` | ✅ |

---

## Float conventions

| Usage | Type | Verdict |
|---|---|---|
| Features intermédiaires (RSI, EMA) | float64 | ✅ Correct |
| Labels `y` (computation) | float64 | ✅ Correct |
| Tenseurs `X_seq`, `y_out` (dataset builder) | float32 | ✅ Correct |
| Scaler stats (μ, σ, median, IQR) | float32 | ✅ Correct |
| Scaler output | float32 | ✅ Correct |
| Ingestion (prix OHLCV) | float64 | ✅ Correct |

---

## Résumé des actions

| # | Sévérité | Action | Fichier(s) |
|---|---|---|---|
| B-1 | BLOQUANT | Corriger `min_periods` de `logvol` (→ 0) et `dlogvol` (→ 1) + tests | `ai_trading/features/volume.py`, `tests/test_volume_features.py` |
| W-1 | WARNING | Rendre `params` obligatoire dans `apply_warmup` (supprimer default `None`) | `ai_trading/features/warmup.py`, tests appelants |
| M-1 | MINEUR | Centraliser helpers OHLCV dans conftest | `tests/test_qa.py`, `test_label_target.py`, `test_metadata.py`, `conftest.py` |
| M-2 | MINEUR | Unifier fixture `_clean_registry` dans test_feature_registry | `tests/test_feature_registry.py` |
| M-3 | MINEUR | Ajouter assertions `Series.name` dans tests RSI, EMA, volatilité | `tests/test_rsi.py`, `test_ema_ratio.py`, `test_volatility.py` |
| M-4 | MINEUR | Extraire fixture `rng` dupliquée | `tests/test_standard_scaler.py`, `test_robust_scaler.py` |
| M-5 | MINEUR | Unifier `_make_timestamps` dans conftest | `tests/test_missing.py`, `test_splitter.py` |
