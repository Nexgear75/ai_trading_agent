# Request Changes — Revue globale branche Max6000i1


Statut : TODO
Ordre : 0001

**Date** : 2026-03-01
**Périmètre** : Tout le code `ai_trading/` et `tests/` (WS-1 à WS-3)
**Résultat** : 363 tests GREEN, ruff clean
**Verdict** : ⚠️ REQUEST CHANGES

---

## BLOQUANTS

### B-1. Mismatch colonne `timestamp` vs `timestamp_utc` entre QA et ingestion

**Fichiers** : `ai_trading/data/qa.py` (L14), `ai_trading/data/ingestion.py` (L196)
**Sévérité** : BLOQUANT — les deux modules ne peuvent pas fonctionner ensemble.

`qa.py` exige :
```python
_REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
```

Or `ingestion.py` produit un DataFrame avec la colonne `timestamp_utc`, conforme à la spec §4.1 :
> Colonnes minimales : `timestamp_utc`, `open`, `high`, `low`, `close`, `volume`, `symbol`.

Passer la sortie d'ingestion directement à `run_qa_checks()` lèvera `ValueError("Column(s) missing from DataFrame: ['timestamp']")`. Le test `tests/test_qa.py` utilise sa propre fixture `_make_ohlcv()` qui crée une colonne `timestamp`, masquant le bug en production.

Toutes les références internes dans `qa.py` (`df["timestamp"]` aux lignes 96, 126, 127, 135) sont aussi impactées.

**Action** :
1. Remplacer `"timestamp"` par `"timestamp_utc"` dans `_REQUIRED_COLUMNS` de `qa.py`.
2. Remplacer toutes les occurrences `df["timestamp"]` par `df["timestamp_utc"]` dans `qa.py`.
3. Adapter `tests/test_qa.py` : remplacer `"timestamp"` par `"timestamp_utc"` dans `_make_ohlcv()` et tous les tests.

---

### B-2. `min_periods` hardcodé dans RSI et EMA — diverge si config change

**Fichiers** : `ai_trading/features/rsi.py` (L45), `ai_trading/features/ema.py` (L65)
**Sévérité** : BLOQUANT — risque de samples incorrects en downstream.

| Feature | `min_periods` retourné | Valeur réelle | Condition de validité |
|---|---|---|---|
| `rsi_14` | `return 14` | `rsi_period` (config) | Seulement si `rsi_period == 14` |
| `ema_ratio_12_26` | `return 25` | `ema_slow - 1` (config) | Seulement si `ema_slow == 26` |

L'interface `BaseFeature.min_periods` est définie comme property sans argument `params`, ce qui rend impossible le calcul dynamique. Si un utilisateur change `rsi_period: 20` ou `ema_slow: 50` dans la config, `min_periods` retourne une valeur fausse.

Le `window.min_warmup` cross-field validator dans `config.py` protège partiellement (il vérifie `min_warmup >= max(rsi_period, ema_slow, ...)`), mais tout code downstream utilisant `feature.min_periods` directement recevra une valeur incorrecte.

**Cause racine** : L'ABC `BaseFeature` définit `min_periods` comme propriété sans argument. Les classes concrètes ne peuvent pas incorporer les valeurs de config.

**Action** (deux options) :
- **Option A** : Refactorer l'ABC pour que `min_periods` accepte `params` : `def min_periods(self, params: dict) -> int`. Impact sur toutes les features existantes.
- **Option B** : Ajouter une assertion runtime dans `compute()` de chaque feature, vérifiant que le nombre de NaN réel est cohérent avec la valeur de `min_periods`. Moins intrusif mais ne résout pas le problème architectural.

---

## WARNINGS

### W-1. `vol_windows` config param trompeur — n'affecte pas le calcul des features

**Fichiers** : `configs/default.yaml` (L67), `ai_trading/features/volatility.py` (L51), `ai_trading/config.py` (L346)
**Sévérité** : WARNING — config trompeuse pour l'utilisateur.

La config expose `features.params.vol_windows: [24, 72]`, mais `Volatility24` et `Volatility72` utilisent `_WINDOW = 24` / `_WINDOW = 72` en dur. Modifier `vol_windows` n'a aucun effet sur le calcul des features — il n'est utilisé que dans la validation cross-field de `config.py` (qui inclut déjà un hardcode `72`).

Si un utilisateur met `vol_windows: [24, 48]`, aucune erreur n'est levée, les features calculent toujours sur 24/72, et le warmup check utilise `max(48, 72)=72` — accidentellement correct mais trompeur.

**Action** : Ajouter un validateur config rejetant toute valeur autre que `[24, 72]`, ou documenter clairement le caractère informatif du paramètre.

---

### W-2. Aucune validation des prix à zéro (division par zéro dans les features)

**Fichiers** : `ai_trading/data/qa.py` (L75), `ai_trading/features/log_returns.py`, `ai_trading/features/ema.py`
**Sévérité** : WARNING — data corruption silencieuse possible.

Le QA rejette les prix **négatifs** (`df[_PRICE_COLUMNS] < 0`) mais pas les prix **à zéro**. Or :
- `log_returns.py` fait `np.log(close / close.shift(k))` → un close à 0 produit `-inf` ou `NaN`.
- `ema.py` fait `ema_fast_arr[i] / ema_slow_arr[i]` → si `ema_slow == 0`, division par zéro.

Tout prix `close <= 0` est pathologique pour des données financières.

**Action** : Ajouter dans `_check_negative_prices` (ou un check séparé) : `close <= 0 → raise ValueError`.

---

### W-3. API random legacy dans `test_rsi.py`

**Fichier** : `tests/test_rsi.py` (lignes 172, 227, 298, 375, 390, 418)
**Sévérité** : WARNING — violation convention projet.

6 occurrences de `np.random.RandomState(42)` (legacy API) alors que AGENTS.md impose `np.random.default_rng(seed)`. Les autres fichiers tests (volatility, ema) utilisent correctement la nouvelle API.

**Action** : Remplacer `np.random.RandomState(seed)` par `np.random.default_rng(seed)` et adapter les appels (`.standard_normal()` au lieu de `.randn()`, etc.).

---

### W-4. `SmaConfig.slow` sans contrainte de borne inférieure

**Fichier** : `ai_trading/config.py` (L156)
**Sévérité** : WARNING — validation incomplète.

```python
class SmaConfig(_StrictBase):
    fast: int = Field(ge=2)
    slow: int  # Aucune contrainte !
```

`slow` accepte `0` ou des valeurs négatives sans erreur de validation. La validation cross-field (`fast < slow`) ne s'applique que quand `strategy.name == "sma_rule"`.

**Action** : Ajouter `slow: int = Field(ge=2)`.

---

### W-5. Risque timezone dans `_check_missing_candles` du module QA

**Fichier** : `ai_trading/data/qa.py` (L115)
**Sévérité** : WARNING — faux positifs silencieux possible.

```python
expected_grid = pd.date_range(start=first, end=last, freq=expected_delta)
existing_set = set(ts_sorted)
missing = [ts for ts in expected_grid if ts not in existing_set]
```

Si le DataFrame d'entrée contient des timestamps tz-aware (`datetime64[ns, UTC]`, comme produit par l'ingestion) mais que `pd.date_range` crée des timestamps tz-naive (ou vice versa), la comparaison `set` ne matchera jamais — tous les timestamps apparaîtront "manquants".

**Action** : Propager explicitement le timezone : `pd.date_range(start=first, end=last, freq=expected_delta, tz=first.tzinfo)`, ou convertir en tz-naive avant comparaison.

---

### W-6. Pagination ingestion — arrêt prématuré silencieux sur page vide

**Fichier** : `ai_trading/data/ingestion.py` (L143)
**Sévérité** : WARNING — données tronquées possible.

Si l'exchange retourne une page vide avant d'atteindre `end_ms` (trou temporaire côté exchange), la pagination s'arrête sans warning. Le résultat pourrait être un dataset tronqué accepté silencieusement (l'appel `if not rows: raise` ne protège que le cas "zéro données", pas "données partielles").

**Action** : Logger un warning quand `since < end_ms` au moment du `break` sur page vide.

---

## MINEURS

### M-1. Fixtures dupliquées entre fichiers de tests

**Fichiers** : `tests/test_config.py`, `tests/test_config_validation.py`, `tests/test_rsi.py`, `tests/test_ema_ratio.py`
**Sévérité** : MINEUR — DRY violation, risque de drift.

| Helper dupliqué | Fichiers |
|---|---|
| `tmp_yaml` + `default_yaml_data` fixtures | `test_config.py`, `test_config_validation.py` |
| `_make_ohlcv(close_values)` | `test_rsi.py`, `test_ema_ratio.py` (code identique) |

**Action** : Extraire les fixtures communes vers `tests/conftest.py`.

---

### M-2. Pattern de registry fixture incohérent entre fichiers de tests

**Fichiers** : `tests/test_log_returns.py`, `tests/test_volatility.py`, `tests/test_ema_ratio.py`, `tests/test_rsi.py`, `tests/test_feature_registry.py`
**Sévérité** : MINEUR — fragilité, maintenance.

Trois stratégies différentes pour le même besoin (isolation du registre) :

| Approche | Fichiers |
|---|---|
| `importlib.reload()` après `FEATURE_REGISTRY.clear()` | `test_log_returns.py`, `test_volatility.py`, `test_ema_ratio.py` |
| `clear()` + `register_feature()` manuel dans fixture | `test_rsi.py` |
| `clear()` + restore sans reload | `test_feature_registry.py` |

**Action** : Standardiser sur un seul pattern (recommandé : `importlib.reload()`) et l'extraire dans une fixture partagée dans `conftest.py`.

---

### M-3. Nommage `Series.name` incohérent entre features

**Fichiers** : `ai_trading/features/rsi.py`, `ai_trading/features/log_returns.py`, `ai_trading/features/ema.py`, `ai_trading/features/volatility.py`
**Sévérité** : MINEUR — incohérence d'interface.

| Feature | `name` sur la Series retournée |
|---|---|
| `rsi_14` | `"rsi_14"` |
| `logret_*` | `None` (explicitement effacé) |
| `ema_ratio_12_26` | `None` (par défaut) |
| `vol_24` / `vol_72` | `None` (par défaut rolling) |

Si du code downstream utilise `series.name` pour identifier la feature, le comportement sera incohérent.

**Action** : Adopter une convention uniforme — soit toutes les features nomment leur Series (e.g. `name="ema_ratio_12_26"`), soit aucune ne le fait.

---

### M-4. `QAReport.missing_timestamps` typé `list` au lieu de `list[pd.Timestamp]`

**Fichier** : `ai_trading/data/qa.py` (L26)
**Sévérité** : MINEUR — perte d'information de type.

```python
missing_timestamps: list  # Devrait être list[pd.Timestamp]
```

**Action** : Typer explicitement `missing_timestamps: list[pd.Timestamp]`.

---

### M-5. `_resolve_symbol` — heuristique `base_len in (3, 4)` limitée

**Fichier** : `ai_trading/data/ingestion.py` (L75)
**Sévérité** : MINEUR — limitation connue non documentée.

```python
for base_len in (3, 4):
    candidate = f"{symbol_config[:base_len]}/{symbol_config[base_len:]}"
```

Ne gère pas les symboles crypto avec base > 4 chars (PEPE, SHIB, DOGE, etc.).

**Action** : Ajouter un commentaire documentant la limitation, ou étendre la heuristique.

---

### M-6. Nom `"rsi_14"` dupliqué entre `@register_feature` et `pd.Series(name=...)`

**Fichier** : `ai_trading/features/rsi.py` (L88)
**Sévérité** : MINEUR — risque de désynchronisation.

Le string `"rsi_14"` apparaît à la fois dans `@register_feature("rsi_14")` et dans `pd.Series(result, index=ohlcv.index, name="rsi_14")`. Si le nom de registry change, il faut penser à mettre à jour les deux.

**Action** : Extraire dans une constante de classe ou dériver du nom de registry.

---

### M-7. `logvol` et `dlogvol` non implémentés mais référencés dans la config

**Fichier** : `configs/default.yaml` (L52-53)
**Sévérité** : MINEUR — attendu (tâche #012 non commencée).

La config `feature_list` référence 9 features, mais seulement 7 sont implémentées. `logvol` et `dlogvol` provoqueront un `KeyError` si le pipeline tente de les instancier.

**Action** : Aucune action immédiate — à résoudre par la tâche #012.

---

### M-8. Construction d'OHLCV incohérente entre fichiers de tests

**Fichiers** : `tests/test_qa.py`, `tests/test_volatility.py`, `tests/test_rsi.py`, `tests/test_ema_ratio.py`, `tests/test_log_returns.py`, `tests/test_ingestion.py`
**Sévérité** : MINEUR — fragilité face à un refactoring d'interface.

Au moins 4 patterns différents :

| Fichier | Helper | Colonnes | Input |
|---|---|---|---|
| `test_qa.py` | `_make_ohlcv(n, timeframe)` | `timestamp` (colonne) | count + timeframe |
| `test_volatility.py` | `_make_ohlcv(n_bars, seed)` | DatetimeIndex | count + seed RNG |
| `test_rsi.py` / `test_ema_ratio.py` | `_make_ohlcv(close_values)` | DatetimeIndex | list de clôtures |
| `test_log_returns.py` | fixtures inline | DatetimeIndex | numpy arrays |
| `test_ingestion.py` | `_make_ohlcv_rows()` | ccxt list-of-lists | count + step |

**Action** : Définir un builder OHLCV partagé dans `conftest.py` avec interface flexible.

---

### M-9. `_current_fmt` état global mutable dans le module logging

**Fichier** : `ai_trading/utils/logging.py` (L20)
**Sévérité** : MINEUR — fragilité du testing.

```python
_current_fmt: str | None = None
```

Variable module-level mutable. Les tests de logging doivent la reset manuellement (`setup_method`/`teardown_method`), ce qui est fragile.

**Action** : Considérer un pattern singleton ou un namespace (`_state` dict) pour regrouper l'état mutable.

---

## Résumé des actions

| # | Sévérité | Action | Fichier(s) principal(s) |
|---|---|---|---|
| B-1 | BLOQUANT | `timestamp` → `timestamp_utc` dans QA | `qa.py`, `test_qa.py` |
| B-2 | BLOQUANT | Refactorer `BaseFeature.min_periods` | `registry.py`, `rsi.py`, `ema.py`, tous les tests features |
| W-1 | WARNING | Verrouiller `vol_windows` dans config | `config.py` |
| W-2 | WARNING | Check QA `close <= 0` | `qa.py`, `test_qa.py` |
| W-3 | WARNING | Migrer legacy random → `default_rng` | `test_rsi.py` |
| W-4 | WARNING | `SmaConfig.slow` → `Field(ge=2)` | `config.py` |
| W-5 | WARNING | Propager timezone dans `_check_missing_candles` | `qa.py` |
| W-6 | WARNING | Logger warning sur pagination tronquée | `ingestion.py` |
| M-1 | MINEUR | Factoriser fixtures dupliquées | `conftest.py` |
| M-2 | MINEUR | Standardiser registry fixture | `conftest.py`, tous `test_*.py` features |
| M-3 | MINEUR | Convention `Series.name` uniforme | tous les modules features |
| M-4 | MINEUR | Typer `list[pd.Timestamp]` | `qa.py` |
| M-5 | MINEUR | Documenter limitation symbol resolution | `ingestion.py` |
| M-6 | MINEUR | Extraire constante nom RSI | `rsi.py` |
| M-7 | MINEUR | (Attendu) Implémenter `logvol`/`dlogvol` | tâche #012 |
| M-8 | MINEUR | Builder OHLCV partagé pour tests | `conftest.py` |
| M-9 | MINEUR | Refactorer état global logging | `logging.py` |
