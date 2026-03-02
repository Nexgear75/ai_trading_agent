# Revue PR — [WS-9] #037 — Baseline no-trade

Branche : `task/037-baseline-no-trade`
Tâche : `docs/tasks/M4/037__ws9_baseline_no_trade.md`
Date : 2025-03-02
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation propre et concise de `NoTradeBaseline(BaseModel)` avec enregistrement registre, save/load, et tests d'intégration backtest. Deux items mineurs empêchent le verdict CLEAN : une couverture de test manquante pour le chemin fichier (vs répertoire) du save/load, et un test N=0 annoncé dans la docstring du fichier de test mais absent.

---

## Phase A — Compliance

### A1. Périmètre

Fichiers modifiés vs `Max6000i1` :
```
ai_trading/baselines/__init__.py       (1 fichier source)
ai_trading/baselines/no_trade.py       (1 fichier source)
docs/tasks/M4/037__ws9_baseline_no_trade.md  (tâche)
tests/test_baseline_no_trade.py        (tests)
```
2 fichiers source, 1 fichier test, 1 fichier tâche.

### A2. Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-slug` | ✅ | `git branch --show-current` → `task/037-baseline-no-trade` |
| Commit RED présent | ✅ | `a44d60d` — `[WS-9] #037 RED: tests for NoTradeBaseline — attributes, registry, fit/predict, save/load, backtest integration` |
| Commit RED = tests uniquement | ✅ | `git show --stat a44d60d` → `tests/test_baseline_no_trade.py | 333 +` (1 fichier) |
| Commit GREEN présent | ✅ | `432b47a` — `[WS-9] #037 GREEN: NoTradeBaseline — zero-signal baseline with registry, backtest integration` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 432b47a` → `no_trade.py`, `__init__.py`, tâche, tests (5 lignes de fix) |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline Max6000i1...HEAD` → 2 commits exactement |

### A3. Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (10/10) |
| Checklist cochée | ✅ (8/9 — seul « PR ouverte » reste `[ ]`, attendu) |

Vérification par critère d'acceptation :

1. **`NoTradeBaseline` hérite de `BaseModel` et est enregistrée `@register_model("no_trade")`** → `no_trade.py` L24-25 : `@register_model("no_trade")` + `class NoTradeBaseline(BaseModel)`. ✅
2. **`output_type == "signal"`, `execution_mode == "standard"`** → `no_trade.py` L27-28. ✅
3. **`fit()` est un no-op** → `no_trade.py` L44 : `return {}`. ✅
4. **`predict(X)` retourne `np.zeros(N, dtype=np.float32)`** → `no_trade.py` L62-63. ✅
5. **Soumis au backtest commun → 0 trades, equity constante à 1.0** → Tests `TestNoTradeBacktestIntegration` (5 tests d'intégration avec `execute_trades` + `build_equity_curve`). ✅
6. **Métriques attendues : `net_pnl = 0`, `n_trades = 0`, `MDD = 0`** → Tests `test_net_pnl_zero_with_no_trades`, `test_n_trades_zero`, `test_mdd_zero_with_no_trades`. ✅
7. **`"no_trade"` résolvable via `get_model_class("no_trade")`** → Test `test_get_model_class_resolves`. ✅
8. **Tests couvrent nominaux + erreurs + bords** → 22 tests, 7 classes. ✅ (avec réserves, voir Phase B)
9. **Suite de tests verte** → 1008 passed. ✅
10. **`ruff check` passe** → All checks passed. ✅

### A4. CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1008 passed**, 0 failed (7.16s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

✅ Phase A PASS.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

| # | Pattern recherché | Règle | Résultat |
|---|---|---|---|
| 1 | Fallbacks silencieux (`or []`, `or {}`, `or ""`, `or 0`, `if … else`) | §R1 | 0 occurrences (grep exécuté sur `ai_trading/baselines/`) |
| 2 | Except trop large (`except:`, `except Exception:`) | §R1 | 0 occurrences |
| 3 | `# noqa` | §R7 | 3 occurrences : `no_trade.py` L32, L34, L47 — toutes N803 pour paramètres ABC (`X_train`, `X_val`, `X`). **Inévitables** (§R7). |
| 4 | `per-file-ignores` | §R7 | Aucune entrée pour `no_trade.py` ni `test_baseline_no_trade.py`. |
| 5 | `print(` | §R7 | 0 occurrences |
| 6 | `.shift(-` | §R3 | 0 occurrences |
| 7 | Legacy random API (`np.random.seed`, etc.) | §R4 | 0 occurrences |
| 8 | `TODO` / `FIXME` / `HACK` / `XXX` | §R7 | 0 occurrences |
| 9 | Chemins hardcodés `/tmp`, `C:\` (tests) | §R7 | 0 occurrences |
| 10 | Imports absolus dans `__init__.py` (`from ai_trading.`) | §R7 | 0 occurrences — utilise `from . import no_trade` (relatif). ✅ |
| 11 | Registration manuelle dans tests (`register_model`, `register_feature`) | §R7 | 1 match : commentaire L54 `# … @register_model`. Faux positif (dans un commentaire, pas un appel). |
| 12 | Mutable default arguments (`def …=[]`, `def …={}`) | §R6 | 0 occurrences |
| 13 | `open(` / `.read_text` sans context manager | §R6 | 1 match : `no_trade.py` L95 `json.loads(resolved.read_text())`. Utilise `Path.read_text()` (raccourci autorisé §R6). ✅ |
| 14 | Comparaison booléenne identité (`is True`, `is False`, `is np.bool_`) | §R6 | 0 occurrences |
| 15 | Boucle Python `for … in range(` sur array numpy | §R9 | 0 occurrences |
| 16 | `isfinite` / `math.isfinite` / `np.isfinite` | §R6 | 0 occurrences — pas de paramètres numériques à valider en entrée (no-trade n'a aucun hyperparamètre). N/A. |
| 17 | Appels numpy dans compréhension | §R9 | 0 occurrences |
| 18 | Fixtures dupliquées (`load_config.*configs/`) | §R7 | 0 occurrences |

### B2. Annotations par fichier

#### `ai_trading/baselines/__init__.py` (3 lignes)

RAS. Import relatif correct : `from . import no_trade  # noqa: F401`. Le `noqa: F401` est justifié (import pour side-effect d'enregistrement registre).

#### `ai_trading/baselines/no_trade.py` (95 lignes)

- **L24-28** — Déclaration de classe + attributs :
  ```python
  @register_model("no_trade")
  class NoTradeBaseline(BaseModel):
      output_type = "signal"
      execution_mode = "standard"
  ```
  Conforme à la tâche et à la spec §13.1. ✅

- **L30-44** — `fit()` signature : match exact avec `BaseModel.fit()` (mêmes noms de paramètres, mêmes types, mêmes defaults `meta_train=None`, `meta_val=None`, `ohlcv=None`). Retourne `{}`. ✅

- **L46-63** — `predict()` signature : match exact avec `BaseModel.predict()`. Utilise `X.shape[0]` pour N, retourne `np.zeros(n, dtype=np.float32)`. ✅

- **L65-79** — `_resolve_path()` : gère directory ET file path conformément au contrat ABC (`path: Path — Directory or file path`). ✅

- **L81-83** — `save()` : crée les répertoires parents (`mkdir(parents=True, exist_ok=True)`) avant écriture. Conforme §R6 (path creation). ✅

- **L85-95** — `load()` : vérifie `resolved.exists()` et lève `FileNotFoundError` explicitement. Appelle `json.loads()` pour valider la structure JSON mais ne stocke pas le résultat — correct pour un modèle stateless.
  Sévérité : RAS

- **L32, L34, L47** — `# noqa: N803` sur `X_train`, `X_val`, `X` : paramètres imposés par l'ABC `BaseModel`. Inévitables (§R7). ✅

- **L12-17** — Imports : `json`, `Path`, `Any`, `numpy`, `BaseModel`/`register_model`. Tous utilisés, pas d'import superflu. ✅

- **L19** — `_MODEL_FILENAME = "no_trade_baseline.json"` : constante privée au module, pas de duplication détectée dans le codebase. ✅

#### `tests/test_baseline_no_trade.py` (317 lignes)

- **L29-35** — Fixture `_clean_model_registry` (autouse) : sauvegarde, clear, yield, clear, restore. Pattern correct pour isolation des tests de registre. ✅

- **L42-56** — Helper `_import_no_trade()` : utilise `importlib.reload(mod)` après `MODEL_REGISTRY.pop("no_trade", None)`. Conforme §R7 (test de registre réaliste). ✅

- **L41** — `_RNG = np.random.default_rng(777)` : seed fixée, pas de legacy random API. Conforme §R4. ✅

- **L207-217** — `test_save_load_roundtrip` : passe `tmp_path` (directory) → `_resolve_path` emprunte le chemin directory. **Le chemin fichier (branch `else` de `_resolve_path`) n'est pas testé en happy path.** Le contrat ABC spécifie « Directory or file path » — les deux variantes doivent être couvertes (§B3, §R7 contrat ABC).
  Sévérité : **MINEUR**

- **L1-9** — Docstring de module : « Edge cases: empty input, single sample ». `test_predict_single_sample` couvre N=1, mais **aucun test ne couvre N=0** (empty input). La docstring annonce une couverture qui n'existe pas.
  Sévérité : **MINEUR**

- **L133-141** — `test_predict_single_sample` : N=1 ✅
- **L143-150** — `test_predict_large_batch` : N=10 000 ✅
- **L152-158** — `test_predict_independent_of_input_values` : entrées variées ✅

- **L240-309** — `TestNoTradeBacktestIntegration` : 5 tests d'intégration utilisant `execute_trades` et `build_equity_curve` du moteur de backtest réel. Vérifie 0 trades, equity constante 1.0, net_pnl=0, n_trades=0, MDD=0. Conforme aux critères d'acceptation 5 et 6. ✅

- **L243-253** — `_make_ohlcv()` : données synthétiques avec seed `42`, pas de dépendance réseau. ✅

- **L315-317** — `TestBaselinesInit.test_import_from_baselines_package` : vérifie l'import depuis le package. ✅

### B3. Tests — Synthèse

| Critère | Verdict |
|---|---|
| Convention de nommage (`test_baseline_no_trade.py`) | ✅ |
| ID tâche `#037` dans docstrings (pas nom de fichier) | ✅ |
| Chaque critère d'acceptation couvert par ≥1 test | ✅ (10/10) |
| Cas nominaux | ✅ (predict, fit, save/load, registry) |
| Cas d'erreur | ✅ (load nonexistent) |
| Cas de bords | ⚠️ N=1 ok, N=10000 ok, N=0 manquant |
| Pas de test désactivé (skip, xfail) | ✅ |
| Tests déterministes (seeds fixées) | ✅ (`default_rng(777)`, `default_rng(42)`) |
| Données synthétiques (pas réseau) | ✅ |
| Chemins portables (`tmp_path`) | ✅ |
| Tests de registre réalistes (`importlib.reload`) | ✅ |
| Contrat ABC complet (directory + file) | ⚠️ Seul directory testé |

### B4. Audit du code — Règles non négociables

#### B4a. Strict code (§R1)
- Aucun fallback silencieux. ✅
- Aucun except trop large. ✅
- Validation explicite : `FileNotFoundError` dans `load()`. ✅

#### B4a-bis. Defensive indexing (§R10)
- `X.shape[0]` : pas de risque d'index négatif ou hors bornes. N/A pour cette implémentation minimale.

#### B4b. Config-driven (§R2)
- No-trade baseline n'a aucun paramètre configurable — conforme à la nature du modèle (pas de hardcoding significatif). ✅

#### B4c. Anti-fuite (§R3)
- Aucune donnée future accédée. `predict()` ignore les données d'entrée. ✅
- Aucun `.shift(-n)`. ✅

#### B4d. Reproductibilité (§R4)
- Pas de composante aléatoire (output déterministe = zéros). ✅
- Tests avec `default_rng` (seed fixée). ✅

#### B4e. Float conventions (§R5)
- `predict()` retourne `np.float32`. ✅

#### B4f. Anti-patterns (§R6)
- Pas de mutable defaults. ✅
- `Path.read_text()` / `Path.write_text()` : raccourcis autorisés. ✅
- `json.loads()` retour non stocké (L95) : intentionnel pour modèle stateless, sert de validation structurelle JSON. ✅

### B5. Qualité du code (§R7)

- snake_case cohérent. ✅
- Pas de code mort, TODO, ou print. ✅
- Imports propres et utilisés. ✅
- `__init__.py` utilise import relatif `from . import no_trade`. ✅
- `# noqa: N803` (3 occurrences) : inévitables (imposé par ABC). ✅
- Pas de fixture dupliquée depuis `conftest.py`. ✅
- Pas de fichiers générés dans le versionning. ✅

### B5-bis. Bonnes pratiques métier (§R9)

- Concept métier clair : baseline no-trade = borne inférieure (0 signal). ✅
- Nommage explicite : `NoTradeBaseline`, `no_trade`. ✅

### B6. Cohérence avec les specs

- Conforme à la spec §13.1 : baseline no-trade, zéro signal, équité constante. ✅
- Conforme au plan WS-9.1. ✅
- Pas d'exigence inventée hors spec. ✅

### B7. Cohérence intermodule (§R8)

- Signatures `fit()` / `predict()` / `save()` / `load()` : identiques à l'ABC `BaseModel`. ✅
- `output_type = "signal"` : cohérent avec le comportement du pipeline (bypass θ calibration). ✅
- `execution_mode = "standard"` : cohérent avec la convention. ✅
- `@register_model("no_trade")` : utilise le mécanisme standard du registre. ✅
- Import de `BaseModel` et `register_model` depuis `ai_trading.models.base` : symboles existants vérifiés. ✅

---

## Remarques

1. **[MINEUR]** — Test docstring annonce « empty input » mais aucun test N=0 n'existe.
   - Fichier : `tests/test_baseline_no_trade.py`
   - Ligne(s) : 9 (docstring module), classe `TestNoTradePredict`
   - Suggestion : ajouter `test_predict_empty_input` avec `X = np.zeros((0, L, F), dtype=np.float32)` et vérifier que `predict(X)` retourne un array vide de shape `(0,)`.

2. **[MINEUR]** — Contrat ABC `save(path)` / `load(path)` documente « Directory or file path » mais seul le chemin directory est testé en happy path. Le branch `else` de `_resolve_path` n'a pas de test positif.
   - Fichier : `tests/test_baseline_no_trade.py`
   - Ligne(s) : 207-230 (classe `TestNoTradeSaveLoad`)
   - Suggestion : ajouter `test_save_load_roundtrip_file_path` qui passe un chemin fichier explicite (`tmp_path / "model.json"`) à `save()` puis `load()`.

---

## Résumé

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 2
- Rapport : docs/tasks/M4/037/review_v1.md
```
