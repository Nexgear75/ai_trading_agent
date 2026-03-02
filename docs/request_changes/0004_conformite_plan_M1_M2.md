# Audit de conformité code ↔ plan d'implémentation (M1 + M2)

Statut : DONE
Ordre : 0004


**Date** : 2 mars 2026
**Branche** : `Max6000i1`
**Portée** : M1 (WS-1, WS-2) + M2 (WS-3, WS-4, WS-5)
**Verdict global** : **CONFORME** — 3 écarts corrigés (RC-0004)

---

## Résumé exécutif

L'audit croise le plan d'implémentation (`docs/plan/implementation.md`) avec le code source, les tests, la config et les tâches. Le code est **globalement conforme** au plan pour M1 et M2 :

- **23/23 tâches** : statut DONE, critères d'acceptation cochés
- **668 tests** : tous verts (pytest)
- **Linter** : ruff clean (0 erreur)
- **Couverture** : 98% sur ai_trading.config + ai_trading.data + ai_trading.features (seuils M1 ≥ 95% et G-Features ≥ 90% respectés)
- **Architecture** : registre pluggable features, anti-fuite embargo/purge, config-driven, strict code — conformes

**3 écarts détectés :**

| # | Sévérité | Description | Réf. plan |
|---|---|---|---|
| 1 | **BLOQUANT** | Scaler μ/σ stockés en float32 au lieu de float64 | Convention P-02, WS-5.1 |
| 2 | **WARNING** | `strategy.framework` déclaré dans Pydantic + YAML (devrait être dérivé par orchestrateur) | WS-12.2, WS-1.3 |
| 3 | **WARNING** | Section `[tool.mypy]` absente de `pyproject.toml` | WS-1.1, règles transverses gates |

---

## Détail des écarts

### 1. [BLOQUANT] ✅ RÉSOLU — Scaler : paramètres μ/σ en float64

**Fichier** : `ai_trading/data/scaler.py` — lignes 91-92, 253-256, 263-264

**Constat** : les paramètres du `StandardScaler` (`mean_`, `std_`) et du `RobustScaler` (`median_`, `iqr_`, `q_low_`, `q_high_`, `clip_low_`, `clip_high_`) sont stockés en `np.float32`.

**Exigence plan** : Convention P-02 (section "Conventions") et WS-5.1 :
> « Les paramètres μ_j et σ_j sont stockés et appliqués en float64. »
> « Frontière float32/float64 : les paramètres du scaler (μ_j, σ_j) sont stockés et appliqués en float64 (car ils sont calculés une fois par fold et réutilisés dans les calculs de métriques via l'equity). »

**Impact** : perte de précision numérique sur les paramètres de scaling → propagation dans l'equity curve et les métriques (Sharpe, MDD). Peut affecter la reproductibilité cross-plateforme (gate M2 : tolérance `atol=1e-7` pour X_seq).

**Remédiation** :
```python
# scaler.py — StandardScaler.fit()
mean = flat.mean(axis=0).astype(np.float64)   # était np.float32
std = flat.std(axis=0).astype(np.float64)      # était np.float32

# scaler.py — RobustScaler.fit()
median = np.median(flat, axis=0).astype(np.float64)
q_low = np.quantile(flat, self._quantile_low, axis=0).astype(np.float64)
q_high = np.quantile(flat, self._quantile_high, axis=0).astype(np.float64)
iqr = (q_high - q_low).astype(np.float64)
# clip_low_ et clip_high_ suivent en float64
```
Le `transform()` doit calculer en float64 puis reconvertir la sortie en float32 :
```python
# transform() — le résultat final reste float32 (convention tenseurs)
return x_scaled.astype(np.float32)
```

**Tests impactés** : `test_standard_scaler.py`, `test_robust_scaler.py` — vérifier que `scaler.mean_.dtype == np.float64`.

---

### 2. [WARNING] ✅ RÉSOLU — `strategy.framework` retiré de config Pydantic + YAML

**Fichier** : `ai_trading/config.py` — ligne 149, `configs/default.yaml` — ligne 101

**Constat** : `StrategyConfig` contient un champ `framework: str` et `configs/default.yaml` spécifie `framework: xgboost`.

**Exigence plan** : WS-12.2 (orchestrateur) :
> « `strategy.framework` n'est PAS un champ config YAML : il n'est pas déclaré dans le modèle Pydantic (incompatible avec extra="forbid" défini en WS-1.3). L'orchestrateur le calcule en interne et l'écrit directement dans le manifest (WS-11.2), sans passer par la config. Aucune entrée strategy.framework ne doit figurer dans les fichiers YAML. »

**Impact** : non bloquant fonctionnellement (le champ sera écrasé par l'orchestrateur M5). Cependant, sa présence dans le modèle Pydantic avec `extra="forbid"` rend difficile la suppression future sans casser la rétrocompatibilité de la config YAML.

**Remédiation** :
1. Supprimer `framework: str` de `StrategyConfig` dans `config.py`
2. Supprimer `framework: xgboost` de `configs/default.yaml`
3. Supprimer toute référence à `strategy.framework` dans les tests de config
4. Le mapping sera ajouté dans l'orchestrateur WS-12.2 (M5)

**Note** : cette correction peut être différée à M3/M5 si on souhaite minimiser les changements sur M1/M2 déjà stabilisés. Mais elle doit être faite **avant** l'implémentation de WS-12.2.

---

### 3. [WARNING] ✅ RÉSOLU — Section `[tool.mypy]` ajoutée dans `pyproject.toml`

**Fichier** : `pyproject.toml`

**Constat** : aucune section `[tool.mypy]` n'est configurée.

**Exigence plan** : Section "Règles transverses (applicables à tous les gates)" :
> « Pré-requis outillage : mypy doit être configuré dans pyproject.toml (section [tool.mypy], python_version = "3.11", disallow_untyped_defs = true, warn_return_any = true). »

**Impact** : les gates de milestone exigent `mypy` vert avant décision. Sans configuration, `mypy` s'exécute avec les defaults (moins stricts) ou n'est pas lancé. Le `Makefile` (WS-12.6) prévoit `make lint` incluant `ruff check + mypy`.

**Remédiation** :
```toml
[tool.mypy]
python_version = "3.11"
disallow_untyped_defs = true
warn_return_any = true
```

**Note** : la correction complète (passer mypy clean sur tout le codebase) peut nécessiter l'ajout d'annotations de types sur les modules existants. Recommandation : configurer mypy maintenant, ajouter progressivement les annotations.

---

## Vérifications conformes (résumé)

### M1 — WS-1 (Fondations et config)

| Exigence | Status | Détail |
|---|---|---|
| WS-1.1 : `__version__ = "1.0.0"` | ✅ | `ai_trading/__init__.py` |
| WS-1.1 : pyproject.toml PEP 621 | ✅ | Version dynamique, ruff, pytest configurés |
| WS-1.1 : requirements.txt + requirements-dev.txt | ✅ | Toutes dépendances présentes |
| WS-1.1 : Logging deux phases | ✅ | `setup_logging()` + `add_file_handler()` |
| WS-1.2 : Config loader Pydantic v2 | ✅ | YAML → Pydantic, override CLI dot-notation |
| WS-1.3 : `extra="forbid"` | ✅ | Via `_StrictBase` hérité partout |
| WS-1.3 : VALID_STRATEGIES mapping | ✅ | 10 stratégies, cohérence vérifiée |
| WS-1.3 : Cross-constraints | ✅ | warmup/features, warmup/L, embargo/H, step/test, backtest mode/direction, SMA, EMA, PatchTST |
| WS-1.3 : Bornes numériques (Field) | ✅ | Tous champs bornés conformément au plan |
| WS-1.3 : val_days < 7 warning | ✅ | Logger warning implémenté |
| WS-1.3 : rolling_zscore rejeté MVP | ✅ | `model_validator` avec raise |

### M1 — WS-2 (Ingestion et QA)

| Exigence | Status | Détail |
|---|---|---|
| WS-2.1 : Ingestion ccxt + pagination + retry | ✅ | `ingestion.py` complet |
| WS-2.1 : Colonnes canoniques + SHA-256 | ✅ | 7 colonnes, hash tracé |
| WS-2.1 : Cache/idempotent | ✅ | `_cache_covers_period()` |
| WS-2.2 : QA checks (6 contrôles) | ✅ | `qa.py` : prix négatifs, doublons, trous, OHLC, volume nul, delta irrégulier |
| WS-2.3 : Missing candles (no interpolation) | ✅ | `missing.py` : masque de validité, invalidation fenêtre |

### M2 — WS-3 (Features)

| Exigence | Status | Détail |
|---|---|---|
| 9 features MVP enregistrées | ✅ | logret_1/2/4, vol_24/72, rsi_14, ema_ratio_12_26, logvol, dlogvol |
| Registre pluggable (@register_feature) | ✅ | `registry.py` + auto-import dans `__init__.py` |
| Formules conformes à la spec §6 | ✅ | Vérifiées par tests numériques |
| Causalité stricte (backward-looking) | ✅ | Toutes features causales |
| vol_24/72 : ddof configurable | ✅ | `volatility_ddof` lu depuis params |
| vol_24/72 : logret_1 recalculé en interne | ✅ | Indépendance features respectée |
| RSI : Wilder smoothing + edge cases | ✅ | AG=AL=0→50, epsilon guard |
| Pipeline : required_params validation | ✅ | `pipeline.py` vérifie avant compute() |
| Warmup masking + NaN check | ✅ | `warmup.py` combine warmup + missing mask |
| Config-driven (aucun hardcoding) | ✅ | Tous paramètres dans config.features.params |

### M2 — WS-4 (Dataset et splitting)

| Exigence | Status | Détail |
|---|---|---|
| WS-4.1 : Labels y_t (2 variantes) | ✅ | `labels.py` : log_return_trade + close_to_close |
| WS-4.2 : Sample builder (N,L,F) float32 | ✅ | `dataset.py` : build_samples() |
| WS-4.3 : Flatten XGBoost (N,L*F) C-order | ✅ | `flatten_seq_to_tab()` avec noms colonnes |
| WS-4.4 : Metadata (decision/entry/exit) | ✅ | `build_meta()` |
| WS-4.5 : Walk-forward splitter (dates UTC) | ✅ | `splitter.py` : bornes UTC, troncation, min_samples, logging n_folds |
| WS-4.5 : parse_timeframe() | ✅ | `timeframes.py` |
| WS-4.6 : Embargo + purge | ✅ | `apply_purge()` : t + H·Δ ≤ purge_cutoff |
| Anti-fuite train/val/test | ✅ | Disjonction vérifiée par tests |

### M2 — WS-5 (Scaling)

| Exigence | Status | Détail |
|---|---|---|
| WS-5.1 : StandardScaler (fit-on-train) | ✅ | 3D reshape, constant guard (σ < 1e-8) |
| WS-5.1 : NaN pre-check | ✅ | ValueError si NaN dans X_train |
| WS-5.2 : RobustScaler (median/IQR, clipping) | ✅ | Quantiles configurables |
| WS-5.2 : create_scaler() factory | ✅ | Route standard/robust, ValueError si inconnu |
| WS-5.1/5.2 : Sérialisation save()/load() | ✅ | Paramètres persistés |
| WS-5.3 : rolling_zscore rejeté MVP | ✅ | Erreur explicite dans config |

### Qualité transversale

| Critère | Status |
|---|---|
| Tests : 668 passed, 0 failed | ✅ |
| Ruff : 0 erreur | ✅ |
| Couverture : 98% (M1+M2 modules) | ✅ |
| Strict code (no fallbacks) | ✅ |
| snake_case, PEP 8 | ✅ |
| Pas de print(), code mort | ✅ |
| Imports propres | ✅ |
| DRY (pas de duplication) | ✅ |

---

## Recommandations de remédiation

### Priorité 1 (BLOQUANT — ✅ RÉSOLU)

1. **Corrigé** : dtype des paramètres scaler → float64 dans `StandardScaler.fit()` et `RobustScaler.fit()`. Tests d'assertion `scaler.mean_.dtype == np.float64` ajoutés.

### Priorité 2 (WARNING — ✅ RÉSOLU)

2. **Corrigé** : `strategy.framework` retiré du modèle Pydantic et du YAML.
3. **Corrigé** : `[tool.mypy]` ajouté dans `pyproject.toml`.

### Priorité 3 (INFORMATIF — sans urgence)

4. Trois tâches (#015, #017, #018) marquées DONE mais avec PR non ouverte dans la checklist. Impact nul si le code est déjà sur la branche, mais maintenir la traçabilité.
