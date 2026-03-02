# Revue PR — [WS-9] #038 — Baseline buy & hold

**Branche** : `task/038-baseline-buy-hold`
**Tâche** : `docs/tasks/M4/038__ws9_baseline_buy_hold.md`
**Date** : 2025-03-02
**Itération** : v2 (après corrections v1)
**Verdict** : ✅ CLEAN

---

## Corrections v1 vérifiées

### v1 BLOQUANT #1 — Checklist tâche incomplète → ✅ CORRIGÉ

**Avant** : `[ ] Commit GREEN` non coché.
**Après** : `[x] Commit GREEN : [WS-9] #038 GREEN: BuyHoldBaseline with single_trade mode, permanent Go signal, backtest integration`.
**Preuve** : `git diff 91c98bd c55f29f -- docs/tasks/M4/038__ws9_baseline_buy_hold.md` montre le passage de `[ ]` à `[x]` pour Commit GREEN. Le seul item restant `[ ]` est « Pull Request ouverte » — attendu (dépend de la revue).

### v1 WARNING #2 — DRY save/load/_resolve_path → ✅ CORRIGÉ

**Avant** : Duplication `_resolve_path()`, `save()`, `load()` entre `buy_hold.py` et `no_trade.py`.
**Après** : Nouveau module `ai_trading/baselines/_base.py` contenant `BaselinePersistenceMixin`. Les deux baselines héritent du mixin et définissent seulement `_model_filename` et `_model_name` comme class attributes.
**Preuve** :
- `buy_hold.py` : `class BuyHoldBaseline(BaselinePersistenceMixin, BaseModel)` — L23. Lignes 63→96 (ancien save/load) supprimées : `-31 lignes`.
- `no_trade.py` : `class NoTradeBaseline(BaselinePersistenceMixin, BaseModel)` — L23. Lignes 62→95 (ancien save/load) supprimées : `-31 lignes`.
- MRO vérifié par exécution Python : `BuyHoldBaseline → BaselinePersistenceMixin → BaseModel → ABC → object`. `save` et `load` sont résolus depuis `BaselinePersistenceMixin`. `BaseModel.__abstractmethods__ = frozenset({'save', 'predict', 'load', 'fit'})`. `BuyHoldBaseline.__abstractmethods__ = frozenset()` — toutes les méthodes abstraites satisfaites.
- `_resolve_path` est `@classmethod` utilisant `cls._model_filename` → chaque sous-classe résout son propre filename. Polymorphisme correct.
- 52 tests baselines (no_trade + buy_hold) passent : `52 passed in 0.07s`.

### v1 MINEUR #3 — json.loads result ignoré → ✅ CORRIGÉ

**Avant** : `json.loads(resolved.read_text())` sans assignment dans `load()`.
**Après** : `_ = json.loads(resolved.read_text())` dans `_base.py:57` avec commentaire `# Validate the file contains valid JSON (no state to restore)`.
**Preuve** : grep `read_text` sur `ai_trading/baselines/` → 1 match unique dans `_base.py:57` : `_ = json.loads(resolved.read_text())`.

---

## Phase A — Compliance

### A1. Périmètre

```
git diff --name-only Max6000i1...HEAD
```

| Type | Fichiers | Count |
|---|---|---|
| Source | `ai_trading/baselines/__init__.py`, `_base.py`, `buy_hold.py`, `no_trade.py` | 4 |
| Test | `tests/test_baseline_buy_hold.py` | 1 |
| Doc | `docs/tasks/M4/038__ws9_baseline_buy_hold.md` | 1 |

### A2. Structure branche & commits

```
git log --oneline Max6000i1...HEAD:
c55f29f [WS-9] #038 FIX: extract BaselinePersistenceMixin (DRY save/load), fix task checklist, assign json.loads result
91c98bd [WS-9] #038 GREEN: BuyHoldBaseline with single_trade mode, permanent Go signal, backtest integration
373db1e [WS-9] #038 RED: tests for BuyHoldBaseline (class attrs, registry, fit/predict, save/load, backtest integration)
```

| Critère | Verdict | Preuve |
|---|---|---|
| Convention `task/NNN-short-slug` | ✅ | `task/038-baseline-buy-hold` |
| Commit RED présent et format correct | ✅ | `373db1e [WS-9] #038 RED: ...` |
| Commit RED = tests uniquement | ✅ | `git show --stat 373db1e` → 1 fichier : `tests/test_baseline_buy_hold.py` |
| Commit GREEN présent et format correct | ✅ | `91c98bd [WS-9] #038 GREEN: ...` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 91c98bd` → 4 fichiers source + tâche |
| Commit FIX post-revue | ✅ | `c55f29f [WS-9] #038 FIX: ...` — corrections v1 uniquement |

### A3. Tâche associée

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` (ligne 3) |
| Critères d'acceptation cochés | ✅ (11/11) | Tous `[x]` — grep confirme 11 critères cochés |
| Checklist cochée | ✅ (9/10) | 9 `[x]`, 1 `[ ]` = « Pull Request ouverte » (attendu) |

### A4. Suite de validation

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1038 passed**, 0 failed (6.58s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

✅ Phase A passe → Phase B.

---

## Phase B — Code Review adversariale

### B1. Scan automatisé obligatoire (GREP)

| Pattern | Règle | Résultat |
|---|---|---|
| Fallbacks (`or []`, `or {}`, `or ""`, `if … else`) | §R1 | 0 occurrences (grep exécuté) |
| Except large (`except:`, `except Exception:`) | §R1 | 0 occurrences (grep exécuté) |
| Print résiduel | §R7 | 0 occurrences (grep exécuté) |
| Shift négatif (`.shift(-`) | §R3 | 0 occurrences (grep exécuté) |
| Legacy random API | §R4 | 0 occurrences (grep exécuté) |
| TODO/FIXME/HACK/XXX | §R7 | 0 occurrences (grep exécuté) |
| Chemins hardcodés (`/tmp`, `C:\`) | §R7 | 0 occurrences (grep exécuté) |
| Imports absolus `__init__` | §R7 | 0 occurrences — imports relatifs corrects |
| Registration manuelle tests | §R7 | 0 occurrences — uses `importlib.reload` |
| Mutable default arguments | §R6 | 0 occurrences (grep exécuté) |
| `read_text` / `open()` | §R6 | 1 match : `_base.py:57 _ = json.loads(resolved.read_text())` — `Path.read_text()` acceptable |
| Bool identity (`is True/False`) | §R6 | 0 occurrences (grep exécuté) |
| Boucle `for range()` | §R9 | 0 occurrences (grep exécuté) |
| Fixtures dupliquées | §R7 | 0 occurrences (grep exécuté) |
| `noqa` suppressions | §R7 | 9 matches — N803 (params ABC imposés), F401 (__init__ side-effect). Toutes justifiées et inévitables. |

### B2. Lecture du diff ligne par ligne

#### `ai_trading/baselines/_base.py` (57 lignes — **nouveau fichier**)

- **L1-10** Module docstring : explique le contrat mixin (subclasses doivent définir `_model_filename` et `_model_name`). Clair et complet. ✅
- **L18-26** `BaselinePersistenceMixin` : 2 class-level type annotations (`_model_filename: str`, `_model_name: str`). Pas de valeur par défaut → la sous-classe DOIT les définir, sinon `AttributeError` à l'usage. Strict. ✅
- **L28-37** `_resolve_path()` : `@classmethod`, utilise `cls._model_filename`. Polymorphisme correct pour multi-baselines. Gère dir ET fichier via `path.is_dir()`. `Path(path)` conversion explicite. ✅
- **L39-43** `save()` : `resolved.parent.mkdir(parents=True, exist_ok=True)` avant écriture. Path creation correcte. `json.dumps({"model": self._model_name})` utilise `self._model_name` — résolution d'instance (identique à `cls._model_name` pour un class attribute, mais correct via `self` aussi). ✅
- **L45-57** `load()` : Existence vérifiée → `FileNotFoundError` explicite. `_ = json.loads(resolved.read_text())` — valide le JSON, résultat assigné à `_`. Commentaire explique l'intention. ✅
- **Type safety** : `json.loads` résultat ignoré (juste validation parsing). Pour un modèle stateless, correct. ✅
- **Edge cases** : `path` empty string → `Path("")` → `path.is_dir()` = False → traité comme fichier. Acceptable. ✅
- RAS après lecture complète (57 lignes).

#### `ai_trading/baselines/buy_hold.py` (65 lignes — diff: -31 lignes)

- Suppression de `import json`, `_MODEL_FILENAME`, et des méthodes `_resolve_path`, `save`, `load`. ✅
- Ajout de `from ai_trading.baselines._base import BaselinePersistenceMixin`. Import cross-package (pas intra-package auto-référençant). ✅
- `class BuyHoldBaseline(BaselinePersistenceMixin, BaseModel)` : MRO vérifié = `BuyHold → Mixin → BaseModel → ABC → object`. Le mixin est **avant** `BaseModel` dans l'héritage : ses `save`/`load` concrets prennent précédence sur les `@abstractmethod` de `BaseModel`. Correct. ✅
- `_model_filename = "buy_hold_baseline.json"` et `_model_name = "buy_hold"` : class attributes requis par le mixin. ✅
- `fit()` et `predict()` : inchangés. Signatures identiques à `BaseModel` ABC. ✅
- RAS après lecture complète du diff.

#### `ai_trading/baselines/no_trade.py` (64 lignes — diff: -31 lignes)

- Changements symétriques à `buy_hold.py`. `class NoTradeBaseline(BaselinePersistenceMixin, BaseModel)`. ✅
- `_model_filename = "no_trade_baseline.json"` et `_model_name = "no_trade"`. ✅
- RAS après lecture complète du diff.

#### `ai_trading/baselines/__init__.py` (5 lignes)

- `from . import buy_hold, no_trade  # noqa: F401` — imports relatifs, side-effect registration. ✅
- `from .buy_hold import BuyHoldBaseline  # noqa: F401` et `from .no_trade import NoTradeBaseline  # noqa: F401` — expose les symboles publics. ✅
- RAS (inchangé depuis v1 sauf contexte).

#### `tests/test_baseline_buy_hold.py` (411 lignes — inchangé dans le FIX commit)

- RAS — aucune modification dans le FIX commit. Tests validés en v1. Toujours conforme. ✅

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_baseline_buy_hold.py`, `#038` en docstring |
| Couverture critères d'acceptation | ✅ | 11/11 critères couverts (mapping v1 toujours valide) |
| Cas nominaux + erreurs + bords | ✅ | N=0, N=1, N=10000, load nonexistent, input independence |
| Boundary fuzzing | ✅ | N=0, N=1, N=10000, x négatifs, x ones |
| Boundary fuzzing taux/proportions | N/A | Pas de paramètre taux dans `BuyHoldBaseline` |
| Déterministes | ✅ | Seeds `888`, `42` via `default_rng` |
| Données synthétiques | ✅ | `_make_ohlcv()`, `_RNG.standard_normal()` |
| Portabilité chemins | ✅ | 0 `/tmp` — `tmp_path` partout |
| Tests registre réalistes | ✅ | `importlib.reload(mod)` |
| Contrat ABC (dir+file) | ✅ | `test_save_load_roundtrip` (dir) + `test_save_load_roundtrip_file_path` (file) |
| Tests désactivés | ✅ | 0 `skip`/`xfail` |

### B4. Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. `FileNotFoundError` levée explicitement. |
| §R10 Defensive indexing | ✅ | `X.shape[0]` seul accès — pas de slicing risqué. |
| §R2 Config-driven | ✅ | N/A — baseline sans paramètre configurable (conforme spec). |
| §R3 Anti-fuite | ✅ | 0 `.shift(-`. Pas d'accès données futures. `fit()` = no-op. |
| §R4 Reproductibilité | ✅ | 0 legacy random. Tests avec `default_rng`. Modèle déterministe. |
| §R5 Float conventions | ✅ | `np.float32` pour predict output. |
| §R6 Anti-patterns Python | ✅ | 0 mutable defaults, 0 bool identity. `Path.read_text()` utilisé. `_ = json.loads(...)` correct. |
| §R7 Qualité | ✅ | snake_case, 0 print, 0 TODO, imports relatifs, DRY via mixin, noqa justifiés. |
| §R8 Cohérence intermodule | ✅ | Signatures ABC respectées. MRO correct. `MODEL_REGISTRY` pas de collision. Tests no_trade passent (52/52). |
| §R9 Bonnes pratiques métier | ✅ | `np.ones` vectorisé. Signal permanent Go conforme §12.5/§13.2. |

### B5. Analyse du mixin pattern

Vérification spécifique demandée pour v2 :

| Aspect | Verdict | Détail |
|---|---|---|
| MRO correct | ✅ | `BuyHoldBaseline → BaselinePersistenceMixin → BaseModel → ABC → object`. Le mixin est avant `BaseModel`, ses méthodes concrètes satisfont les `@abstractmethod`. |
| Abstract methods satisfaites | ✅ | `BaseModel.__abstractmethods__` = `{save, predict, load, fit}`. `BuyHoldBaseline.__abstractmethods__` = `frozenset()`. |
| `save` et `load` résolus depuis mixin | ✅ | `BuyHoldBaseline.save is BaselinePersistenceMixin.save` = `True`. |
| Polymorphisme `_resolve_path` | ✅ | `@classmethod` + `cls._model_filename` → chaque sous-classe utilise son propre filename. |
| Polymorphisme `_model_name` | ✅ | `self._model_name` dans `save()` → résolu comme class attribute de la sous-classe. |
| Pas de regression no_trade | ✅ | 24 tests no_trade passent. Save/load roundtrip OK (dir + file). |
| Instanciation | ✅ | `BuyHoldBaseline()` et `NoTradeBaseline()` instanciables sans erreur. |

---

## Items

Aucun item identifié.

---

## Résumé

| Sévérité | Nombre |
|---|---|
| BLOQUANT | 0 |
| WARNING | 0 |
| MINEUR | 0 |

Les 3 items de la v1 sont tous correctement corrigés. Le pattern mixin `BaselinePersistenceMixin` est bien implémenté : MRO correct, méthodes abstraites satisfaites, polymorphisme via class attributes (`_model_filename`, `_model_name`), aucune régression sur `NoTradeBaseline`. Suite de tests complète (1038 passed, 0 failed), ruff clean.

---

RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : `docs/tasks/M4/038/review_v2.md`
