# Request Changes — Revue globale post-RC-0001

Statut : TODO
Ordre : 0002

**Date** : 2025-07-25
**Périmètre** : Branche `Max6000i1` — tous les modules source (`ai_trading/`) et tests (`tests/`)
**Résultat** : 367 tests GREEN, ruff clean
**Verdict** : ✅ CLEAN (après corrections)

---

## Résultats d'exécution

| Check | Résultat |
|---|---|
| `pytest tests/` | **367 passed** |
| `ruff check ai_trading/ tests/` | **All checks passed** |
| `print()` résiduel | Aucun |
| `TODO`/`FIXME` orphelin | Aucun |
| `.shift(-n)` (look-ahead) | Aucun |
| Broad `except` | Aucun |
| Legacy random API | Aucun |
| `import *` | Aucun |

---

## Tâches implémentées

12 tâches DONE (#001–#011, #023), 11 tâches TODO (#012–#022 sauf #023).
Modules implémentés : config, ingestion, QA, missing candles, feature registry, log_returns (×3), volatility (×2), RSI, EMA ratio, logging.

---

## BLOQUANTS (0)

Aucun bloquant identifié.

---

## WARNINGS (2)

### ~~W-1. `logvol` / `dlogvol` dans `feature_list` mais absents du registre~~ ✅ RÉSOLU

**Fichiers** : `configs/default.yaml` (L52-53), `ai_trading/features/registry.py`
**Sévérité** : WARNING — toute tentative d'utiliser `feature_list` tel quel échouera à l'exécution.

La config `default.yaml` déclare 9 features dans `feature_list`, dont `logvol` et `dlogvol`. Or ces deux features ne sont pas implémentées et absentes de `FEATURE_REGISTRY`. Tant que la tâche #012 n'est pas DONE, la config par défaut est incohérente avec le code.

**Action** :
1. Implémenter la tâche #012 (volume features) pour combler le gap, **ou**
2. Retirer temporairement `logvol` et `dlogvol` de `feature_list` dans `default.yaml` jusqu'à implémentation.

> **Résolu** : option 2 — `logvol`/`dlogvol` retirés de `feature_list` avec commentaire. `logvol_epsilon` conservé dans params (requis par le modèle Pydantic).

---

### ~~W-2. `features/__init__.py` n'auto-importe pas les modules de features~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/features/__init__.py`
**Sévérité** : WARNING — le `FEATURE_REGISTRY` sera vide si aucun module de feature n'est importé explicitement.

Le fichier `features/__init__.py` ne contient qu'un docstring. Les features sont enregistrées dans `FEATURE_REGISTRY` au moment de l'import de chaque module (`log_returns`, `rsi`, `ema`, `volatility`). Si le pipeline orchestrateur (WS-12) n'importe pas explicitement ces modules, le registre sera vide.

La fonction `load_builtin_features()` dans `log_returns.py` ne couvre que les log-returns (pas RSI, EMA, volatilité).

**Action** :
1. Ajouter un mécanisme d'auto-import dans `features/__init__.py` (import de tous les modules de features), **ou**
2. Étendre `load_builtin_features()` en une fonction globale qui importe tous les modules de features enregistrés, **ou**
3. Documenter explicitement que l'orchestrateur doit importer tous les modules de features avant d'utiliser le registre.

À traiter lors de la tâche #013 (feature pipeline).

> **Résolu** : option 1 — `features/__init__.py` importe désormais tous les modules de features (ema, log_returns, rsi, volatility). `load_builtin_features()` supprimée de `log_returns.py` (M-6 résolu conjointement).

---

## MINEURS (6)

### ~~M-1. EMA : nom `"ema_ratio_12_26"` hardcodé en deux endroits~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/features/ema.py` (L55, L124)
**Sévérité** : MINEUR — duplication du pattern corrigé pour RSI dans RC-0001 (M-6).

Le nom de la feature `"ema_ratio_12_26"` apparaît en dur à la fois dans `@register_feature("ema_ratio_12_26")` (L55) et dans `pd.Series(..., name="ema_ratio_12_26")` (L124). Le RSI a été corrigé pour extraire `_FEATURE_NAME` comme constante unique.

**Action** : Extraire `_FEATURE_NAME = "ema_ratio_12_26"` et l'utiliser dans les deux emplacements.

> **Résolu** : `_FEATURE_NAME` extrait et utilisé dans `@register_feature` et `pd.Series(name=...)`.

---

### ~~M-2. `isinstance` guard inutile dans `log_returns.py`~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/features/log_returns.py` (L48-49)
**Sévérité** : MINEUR — branche morte (le résultat de `np.log(Series / Series.shift(k))` est toujours un `pd.Series`).

```python
result = np.log(close / close.shift(k))
if isinstance(result, pd.Series):
    result = result.rename(f"logret_{k}")
return result
```

Le `if isinstance(result, pd.Series)` est toujours vrai car `close` est un `pd.Series`. La branche `False` est du code mort.

**Action** : Supprimer le `if` et appliquer `.rename()` directement.

> **Résolu** : guard `isinstance` supprimé, `.rename()` appliqué directement.

---

### ~~M-3. Noms de colonnes OHLCV répétés dans `ingestion.py`~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/data/ingestion.py` (L195, L238, L245)
**Sévérité** : MINEUR — risque de maintenance si les noms de colonnes canoniques changent.

Les noms de colonnes OHLCV (`"open"`, `"high"`, `"low"`, `"close"`, `"volume"`) apparaissent en dur à trois endroits distincts dans le fichier. Le même pattern existe dans `qa.py` avec `_REQUIRED_COLUMNS` et `_PRICE_COLUMNS` (correctement extrait là-bas).

**Action** : Extraire des constantes de module (`_OHLCV_RAW_COLUMNS`, `_PRICE_COLUMNS`, `_OHLCV_CANONICAL_COLUMNS`) et les réutiliser.

> **Résolu** : constantes `_OHLCV_RAW_COLUMNS`, `_PRICE_VOLUME_COLUMNS`, `_OHLCV_CANONICAL_COLUMNS` extraites et utilisées.

---

### ~~M-4. Chunk size `65_536` hardcodé pour le hashing SHA-256~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/data/ingestion.py` (L226)
**Sévérité** : MINEUR — constante technique non nommée.

```python
h.update(chunk) for chunk in iter(lambda: f.read(65_536), b"")
```

La valeur `65_536` (64 KB) est un buffer standard pour le streaming I/O mais n'est pas nommée.

**Action** : Extraire en constante de module : `_HASH_CHUNK_BYTES = 65_536`.

> **Résolu** : constante `_HASH_CHUNK_BYTES = 65_536` extraite.

---

### ~~M-5. EMA : `ema_fast == ema_slow` accepté silencieusement~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/features/ema.py` (L103)
**Sévérité** : MINEUR — cas dégénéré qui produit un ratio identiquement zéro.

La validation vérifie `fast > slow` (raise) mais accepte `fast == slow`. Quand `fast == slow`, le ratio `EMA_fast / EMA_slow - 1` est identiquement `0.0` pour toutes les barres — une feature constante et donc inutile. Bien que la config par défaut (12/26) ne déclenche pas ce cas, la validation pourrait être plus stricte.

**Action** : Changer la condition de `fast > slow` à `fast >= slow` avec un message clair, **ou** documenter que `fast == slow` est autorisé mais dégénéré.

> **Résolu** : condition changée en `fast >= slow` dans `ema.py` + cross-validation `ema_fast < ema_slow` ajoutée dans `config.py`. Tests mis à jour.

---

### ~~M-6. `load_builtin_features()` ne couvre que les log-returns~~ ✅ RÉSOLU

**Fichiers** : `ai_trading/features/log_returns.py` (L66-78)
**Sévérité** : MINEUR — fonction utilitaire incomplète.

La fonction `load_builtin_features()` n'importe que les 3 classes de log-returns. RSI, EMA et volatilité ne sont pas couverts. Si cette fonction est destinée à devenir le point d'entrée unique pour charger toutes les features built-in, elle devrait inclure tous les modules.

**Action** : Renommer en `load_log_return_features()` pour refléter son périmètre réel, **ou** étendre pour importer tous les modules de features. À coordonner avec W-2.

> **Résolu** : fonction supprimée, auto-import via `features/__init__.py` (voir W-2).

---

## Conformité formules métier

| Feature/Module | Section spec | Verdict | Notes |
|---|---|---|---|
| `logret_1` | §6.2 | ✅ Correct | `log(C_t / C_{t-1})`, NaN pour t < 1 |
| `logret_2` | §6.2 | ✅ Correct | `log(C_t / C_{t-2})`, NaN pour t < 2 |
| `logret_4` | §6.2 | ✅ Correct | `log(C_t / C_{t-4})`, NaN pour t < 4 |
| `vol_24` | §6.5 | ✅ Correct | `std(logret_1, window=24, ddof=config)`, NaN pour t < 24 |
| `vol_72` | §6.5 | ✅ Correct | `std(logret_1, window=72, ddof=config)`, NaN pour t < 72 |
| `rsi_14` | §6.3 | ✅ Correct | Wilder smoothing `α=1/n`, SMA init, edge cases (AG≈AL≈0 → 50) |
| `ema_ratio_12_26` | §6.4 | ✅ Correct | `α=2/(n+1)`, SMA init, ratio = EMA_fast/EMA_slow - 1 |
| `logvol` | §6.2 | ❌ Non implémenté | Tâche #012 TODO |
| `dlogvol` | §6.2 | ❌ Non implémenté | Tâche #012 TODO |
| QA checks | §4.2 | ✅ Correct | Duplicates, missing, OHLC consistency, zero vol, irregular delta, prix négatifs |
| Missing policy | §4.3 | ✅ Correct | No interpolation, invalidation samples affectés par gaps |

---

## Anti-fuite

| Module | Check | Verdict |
|---|---|---|
| `log_returns.py` | backward-looking only | ✅ `close.shift(k)` avec k > 0 |
| `rsi.py` | backward-looking only | ✅ Wilder smoothing causal |
| `ema.py` | backward-looking only | ✅ EMA causal, SMA init sur premières valeurs |
| `volatility.py` | backward-looking only | ✅ `rolling(window=n, min_periods=n)` causal |
| `missing.py` | no forward fill | ✅ Invalidation sans interpolation |
| `ingestion.py` | no future data | ✅ Fetch historique uniquement |
| `.shift(-n)` global | aucun usage | ✅ Vérifié par grep |

---

## Reproductibilité

| Check | Verdict |
|---|---|
| `np.random.seed()` / `np.random.randn()` legacy | ✅ Aucun usage |
| `np.random.default_rng(seed)` dans tests | ✅ Utilisé dans conftest (`make_ohlcv_random`) |
| Seeds déterministes | ✅ Seed fixée dans les fixtures de tests |
| SHA-256 hashing | ✅ `ingestion.py` calcule le hash des fichiers téléchargés |
| Config reproductibilité | ✅ `ReproducibilityConfig` avec `global_seed` et `deterministic_torch` |

---

## Résumé des actions

| # | Sévérité | Action | Fichier(s) |
|---|---|---|---|
| W-1 | WARNING | Implémenter #012 ou retirer logvol/dlogvol de feature_list | `configs/default.yaml` |
| W-2 | WARNING | Auto-import des modules features ou documentation | `ai_trading/features/__init__.py` |
| M-1 | MINEUR | Extraire `_FEATURE_NAME` pour EMA | `ai_trading/features/ema.py` |
| M-2 | MINEUR | Supprimer `isinstance` guard mort | `ai_trading/features/log_returns.py` |
| M-3 | MINEUR | Extraire constantes colonnes OHLCV | `ai_trading/data/ingestion.py` |
| M-4 | MINEUR | Nommer la constante chunk size | `ai_trading/data/ingestion.py` |
| M-5 | MINEUR | Rejeter `fast == slow` ou documenter | `ai_trading/features/ema.py` |
| M-6 | MINEUR | Renommer ou étendre `load_builtin_features()` | `ai_trading/features/log_returns.py` |
