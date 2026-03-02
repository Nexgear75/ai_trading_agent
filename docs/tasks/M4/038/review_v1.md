# Revue PR — [WS-9] #038 — Baseline buy & hold

Branche : `task/038-baseline-buy-hold`
Tâche : `docs/tasks/M4/038__ws9_baseline_buy_hold.md`
Date : 2025-03-02
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation de `BuyHoldBaseline` est correcte et cohérente avec la spec (§12.5, §13.2). Les tests sont exhaustifs (nominaux, erreurs, bords, intégration backtest). Deux items bloquants identifiés : checklist de tâche incomplète (2 items non cochés malgré statut DONE) et duplication structurelle `save/load/_resolve_path` avec `no_trade.py` (risque de drift). Un mineur sur `load()` qui deserialize du JSON sans utiliser le résultat.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `* task/038-baseline-buy-hold` |
| Commit RED présent au bon format | ✅ | `373db1e [WS-9] #038 RED: tests for BuyHoldBaseline (class attrs, registry, fit/predict, save/load, backtest integration)` |
| Commit RED = tests uniquement | ✅ | `git show --stat 373db1e` → 1 fichier : `tests/test_baseline_buy_hold.py` (411 insertions) |
| Commit GREEN présent au bon format | ✅ | `91c98bd [WS-9] #038 GREEN: BuyHoldBaseline with single_trade mode, permanent Go signal, backtest integration` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 91c98bd` → 4 fichiers : `buy_hold.py`, `__init__.py`, tâche md, test (1 ligne type hint) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits (RED, GREEN) |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (11/11) | Tous les critères `[x]` |
| Checklist cochée | ❌ (7/9) | 2 items non cochés : « Commit GREEN » et « Pull Request ouverte » |

> **BLOQUANT #1** : La checklist de fin de tâche contient 2 items non cochés (`[ ]`) alors que le statut est DONE. Le commit GREEN existe (`91c98bd`) mais n'est pas coché dans la checklist. Incohérence processus.

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1038 passed**, 0 failed (6.19s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, etc.) | §R1 | 0 occurrences (grep exécuté) |
| Except trop large (`except:`, `except Exception:`) | §R1 | 0 occurrences (grep exécuté) |
| Print résiduel (`print(`) | §R7 | 0 occurrences (grep exécuté) |
| Shift négatif (`.shift(-`) | §R3 | 0 occurrences (grep exécuté) |
| Legacy random API | §R4 | 0 occurrences (grep exécuté) |
| TODO/FIXME/HACK/XXX | §R7 | 0 occurrences (grep exécuté) |
| Chemins hardcodés (`/tmp`, `C:\`) | §R7 | 0 occurrences (grep exécuté) |
| Imports absolus `__init__` | §R7 | 0 occurrences (grep exécuté) — imports relatifs corrects |
| Registration manuelle tests | §R7 | 0 occurrences — uses `importlib.reload` correctly |
| Mutable default arguments | §R6 | 0 occurrences (grep exécuté) |
| `open()` / `.read_text()` | §R6 | 1 match : `buy_hold.py:96: json.loads(resolved.read_text())` — `Path.read_text()` est acceptable (pas de context manager nécessaire) |
| Bool identity (`is True/False/np.bool_`) | §R6 | 0 occurrences (grep exécuté) |
| Dict collision silencieuse | §R6 | 0 occurrences (grep exécuté) |
| Boucle `for range()` | §R9 | 0 occurrences (grep exécuté) |
| `isfinite` check | §R6 | 0 occurrences — N/A (pas de validation de bornes numériques dans ce module) |
| np comprehension vectorisable | §R9 | 0 occurrences (grep exécuté) |
| Fixtures dupliquées (`load_config.*configs/`) | §R7 | 0 occurrences (grep exécuté) |
| `noqa` suppressions | §R7 | 6 occurrences — toutes justifiées (F401 imports side-effect, N803 params ABC) |
| `per-file-ignores` | §R7 | Présent dans `pyproject.toml:51` — non modifié par cette PR |

### Annotations par fichier (B2)

#### `ai_trading/baselines/buy_hold.py` (96 lignes)

- **L29** `execution_mode = "single_trade"` : Conforme à la spec §12.5. ✅
- **L30-43** `fit()` : No-op, retourne `{}`. Signature identique à `BaseModel.fit()` (9 paramètres, mêmes noms, mêmes types, mêmes defaults). ✅
- **L44-65** `predict()` : `np.ones(n, dtype=np.float32)`. Signature identique à `BaseModel.predict()` (3 paramètres). ✅
- **L67-76** `_resolve_path()` : Gère dir ET fichier. `Path(path)` assure la conversion. ✅
- **L78-83** `save()` : `resolved.parent.mkdir(parents=True, exist_ok=True)` avant écriture. Path creation correcte. ✅
- **L85-96** `load()` : `json.loads(resolved.read_text())` — le résultat de la désérialisation est ignoré (variable non assignée). C'est fonctionnellement correct (le modèle n'a pas d'état) mais constitue du code mort. Voir MINEUR #3.
- **Duplication** : `_resolve_path()`, `save()`, `load()` sont des copies quasi-identiques de `no_trade.py` (seuls `_MODEL_FILENAME` et le contenu JSON diffèrent). Voir WARNING #2.

#### `ai_trading/baselines/__init__.py` (5 lignes)

- **L3** `from . import buy_hold, no_trade  # noqa: F401` : Import relatif, side-effect pour registration. ✅
- **L4** `from .buy_hold import BuyHoldBaseline  # noqa: F401` : Expose le symbole public. ✅
- RAS après lecture complète du diff (3 lignes modifiées).

#### `tests/test_baseline_buy_hold.py` (411 lignes)

- **L30-35** `_clean_model_registry` fixture : Sauvegarde, clear, restore — pattern correct pour isolation des tests. ✅
- **L38-49** Données synthétiques : `np.random.default_rng(888)` — seed fixée, pas de legacy API. ✅
- **L52-57** `_import_buy_hold()` : `importlib.reload(mod)` pour tester le side-effect réel du décorateur — conforme §R7. ✅
- **L59-69** `_make_ohlcv()` : Seed `42`, données synthétiques, prix `> 50.0`. ✅
- **L73-100** `TestBuyHoldAttributes` : Héritage, output_type, execution_mode. ✅
- **L106-118** `TestBuyHoldRegistry` : Registry + `get_model_class`. ✅
- **L124-145** `TestBuyHoldFit` : No-op vérifié + pas de modification d'état. ✅
- **L151-210** `TestBuyHoldPredict` : Nominaux (ones, dtype, shape), bords (N=0, N=1, N=10000), indépendance des valeurs d'entrée. ✅
- **L216-262** `TestBuyHoldSaveLoad` : Roundtrip dir + file, création fichier, load nonexistent. ✅
- **L268-378** `TestBuyHoldBacktestIntegration` : 1 trade, entry/exit prices/times, net_return formula, zero costs, equity curve, exposure_time_frac, pipeline complète predict→execute. ✅
- **L384-397** `TestBaselinesInitBuyHold` : Import depuis package, registration via `__init__`. ✅
- RAS après lecture complète du diff (411 lignes).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage `test_baseline_buy_hold.py` | ✅ | Conforme, `#038` en docstring du module |
| Couverture des critères d'acceptation | ✅ | Mapping : CA1→`TestBuyHoldAttributes+Registry`, CA2→`test_output_type+execution_mode`, CA3→`TestBuyHoldFit`, CA4→`TestBuyHoldPredict`, CA5→`test_single_trade_produces_one_trade+test_n_trades_equals_one`, CA6→`test_net_return_formula`, CA7→`test_exposure_time_frac_is_one`, CA8→`test_get_model_class_resolves`, CA9→toutes les classes de test |
| Cas nominaux + erreurs + bords | ✅ | Nominaux (predict ones, fit no-op), erreurs (load nonexistent), bords (N=0, N=1, N=10000) |
| Boundary fuzzing | ✅ | N=0, N=1, N=10000, valeurs d'entrée variées (zeros, negatives, ones) |
| Boundary fuzzing taux/proportions | N/A | Pas de paramètres taux dans `BuyHoldBaseline` elle-même |
| Déterministes | ✅ | Seeds fixées : `888`, `42` |
| Données synthétiques | ✅ | `_make_ohlcv()`, `_RNG.standard_normal()` — aucune dépendance réseau |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` — utilise `tmp_path` de pytest |
| Tests registre réalistes | ✅ | `_import_buy_hold()` utilise `importlib.reload(mod)` |
| Contrat ABC complet (save/load dir+file) | ✅ | `test_save_load_roundtrip` (dir) + `test_save_load_roundtrip_file_path` (file) |
| Tests désactivés | ✅ | 0 `@pytest.mark.skip` ou `xfail` |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. Pas de paramètres optionnels masquant une erreur. `FileNotFoundError` levée explicitement dans `load()`. |
| §R10 Defensive indexing | ✅ | `X.shape[0]` seul accès — pas de slicing risqué. |
| §R2 Config-driven | ✅ | N/A pour cette baseline — pas de paramètre configurable (conforme à la spec : buy & hold n'a pas de paramètre). |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Pas d'accès aux données futures. `fit()` est un no-op. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Tests avec `default_rng`. Le modèle est déterministe (ones constant). |
| §R5 Float conventions | ✅ | `np.float32` pour predict output (conforme). Pas de métriques float64 dans ce module. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 bool identity, `Path.read_text()/write_text()` utilisés. `json.loads()` résultat ignoré = MINEUR (voir ci-dessous). |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `_MODEL_FILENAME`, `_resolve_path`, `buy_hold`. N803 noqa pour params ABC. |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO |
| Imports propres / relatifs | ✅ | `__init__.py` utilise imports relatifs. `buy_hold.py` importe depuis `ai_trading.models.base` (cross-package, correct). |
| DRY | ⚠️ | Duplication `_resolve_path/save/load` avec `no_trade.py`. Voir WARNING #2. |
| `noqa` suppressions justifiées | ✅ | F401 (side-effect imports), N803 (params imposés par ABC) — toutes inévitables. |
| `__init__.py` à jour | ✅ | `buy_hold` importé + `BuyHoldBaseline` exposé. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Preuve |
|---|---|---|
| §12.5 execution_mode single_trade | ✅ | `execution_mode = "single_trade"` en classe |
| §13.2 buy & hold baseline | ✅ | Signal permanent Go (ones), 1 trade, entry Open[first], exit Close[last] |
| Formule net_return | ✅ | `test_net_return_formula` vérifie `(1-f)^2 * Close_end*(1-s) / (Open_start*(1+s)) - 1` avec `pytest.approx(rel=1e-10)` |
| exposure_time_frac = 1.0 | ✅ | `test_exposure_time_frac_is_one` — assertion `== 1.0` |
| Plan WS-9.2 | ✅ | Baseline buy & hold conforme au plan |
| Formules doc vs code | ✅ | La formule net_return dans la tâche correspond exactement au test |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures BaseModel | ✅ | `fit()` : 9 params identiques (noms, types, defaults). `predict()` : 3 params identiques. `save(path)`, `load(path)` conformes. |
| Cohérence avec NoTradeBaseline | ✅ | Même structure, même pattern `_resolve_path/save/load`. |
| `MODEL_REGISTRY` | ✅ | `@register_model("buy_hold")` — clé unique, pas de collision. |
| `execute_trades(execution_mode="single_trade")` | ✅ | Testé dans `test_single_trade_produces_one_trade` — le moteur backtest existant supporte ce mode. |
| `apply_cost_model` integration | ✅ | Testé dans `test_net_return_formula` — coûts appliqués correctement. |
| `build_equity_curve` integration | ✅ | Testé dans `test_equity_curve_single_trade` — in_trade=True partout. |
| Forwarding kwargs | ✅ | `predict(X, meta=None, ohlcv=None)` — tous les params optionnels de l'ABC sont présents. |

---

## Items

### 1. [BLOQUANT] Checklist de tâche incomplète
- **Fichier** : `docs/tasks/M4/038__ws9_baseline_buy_hold.md`
- **Ligne(s)** : dernières lignes de la checklist
- **Description** : 2 items non cochés dans la checklist (`[ ] Commit GREEN`, `[ ] Pull Request ouverte`) alors que `Statut : DONE`. Le commit GREEN existe bien (`91c98bd`) mais la checklist n'est pas à jour.
- **Suggestion** : Cocher les items correspondants : `[x] Commit GREEN : [WS-9] #038 GREEN: ...` et mettre à jour le statut de la PR une fois ouverte.

### 2. [WARNING] Duplication save/load/_resolve_path entre baselines
- **Fichiers** : `ai_trading/baselines/buy_hold.py` (L67-96) et `ai_trading/baselines/no_trade.py` (L67-96)
- **Description** : Les méthodes `_resolve_path()`, `save()` et `load()` sont des copies quasi-identiques entre les deux baselines. Seuls `_MODEL_FILENAME` et le contenu JSON diffèrent. Risque de drift silencieux si l'une est modifiée sans l'autre. Ce pattern se reproduira avec SMA baseline (tâche future).
- **Suggestion** : Extraire une classe de base commune (ex. `_BaselineBase`) ou un mixin dans `ai_trading/baselines/` qui factorise `_resolve_path/save/load` avec le `_MODEL_FILENAME` et le contenu JSON en paramètres. Alternative : accepter la duplication pour 2-3 baselines très simples et documenter la décision.

### 3. [MINEUR] Résultat de `json.loads()` ignoré dans `load()`
- **Fichier** : `ai_trading/baselines/buy_hold.py`
- **Ligne** : 96
- **Description** : `json.loads(resolved.read_text())` — la valeur retournée n'est pas assignée. Le code valide implicitement que le fichier est du JSON valide, mais la donnée est perdue. Pattern identique dans `no_trade.py`.
- **Suggestion** : Assigner le résultat à `_` pour documenter l'intention : `_ = json.loads(resolved.read_text())`. Ou ajouter un commentaire `# Validate JSON format`.

---

## Résumé

| Sévérité | Nombre |
|---|---|
| BLOQUANT | 1 |
| WARNING | 1 |
| MINEUR | 1 |

L'implémentation est fonctionnellement correcte et bien testée (1038 tests, 0 échec). Le code suit les conventions du projet (imports relatifs, registre, signatures ABC). Le bloquant est purement processus (checklist non cochée) et se corrige en 30 secondes. Le warning sur la duplication n'est pas critique pour 2 baselines mais mérite attention pour la tâche SMA à venir.

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 1
- Warnings : 1
- Mineurs : 1
- Rapport : `docs/tasks/M4/038/review_v1.md`
