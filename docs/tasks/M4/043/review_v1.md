# Revue PR — [WS-10] #043 — Validation du gate M4

Branche : `task/043-gate-m4`
Tâche : `docs/tasks/M4/043__gate_m4.md`
Date : 2026-03-03
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

16 tests de validation des 5 critères du gate M4 (déterminisme, pipeline sans crash, cohérence métriques, couverture, registres). Pas de code production modifié — uniquement `tests/test_gate_m4.py` et la tâche. 1 WARNING et 4 MINEURs identifiés empêchent le verdict CLEAN.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/043-gate-m4` | ✅ | `git branch --show-current` → `task/043-gate-m4` |
| Commit RED présent | ✅ | `d49c677 [WS-10] #043 RED: gate M4 validation tests — determinism, pipeline, coherence, registry` |
| Commit RED = tests uniquement | ✅ | `git show --stat d49c677` → `tests/test_gate_m4.py | 347 +++` (1 fichier test) |
| Commit GREEN présent | ✅ | `335a04c [WS-10] #043 GREEN: gate M4 validation — 16 tests covering all 5 criteria` |
| Commit GREEN = impl + tâche | ✅ | `git show --stat 335a04c` → `docs/tasks/M4/043__gate_m4.md` (tâche mise à jour uniquement — pas de code production, ce qui est normal pour un gate) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1..HEAD` → 2 commits exactement (RED + GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (8/8) |
| Checklist cochée | ✅ (9/9) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1220 passed**, 0 failed ✅ |
| `pytest tests/test_gate_m4.py -v` | **16 passed**, 0 failed ✅ |
| `ruff check ai_trading/ tests/` | **All checks passed** ✅ |

**Phase A → PASS.** Passage en Phase B.

---

## Phase B — Code Review

### B1. Résultats du scan automatisé (GREP)

Fichiers modifiés : `tests/test_gate_m4.py` (pas de fichier source `ai_trading/`).

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (§R1) | `grep -n 'or \[\]\|or {}\|or ""...'` | 0 occurrences (grep exécuté) |
| Except trop large (§R1) | `grep -n 'except:$\|except Exception:'` | 0 occurrences (grep exécuté) |
| Print résiduel (§R7) | `grep -n 'print('` | 0 occurrences (grep exécuté) |
| Shift négatif (§R3) | `grep -n '\.shift(-'` | 0 occurrences (grep exécuté) |
| Legacy random API (§R4) | `grep -n 'np.random.seed\|np.random.randn...'` | 0 occurrences (grep exécuté) |
| TODO/FIXME (§R7) | `grep -n 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences (grep exécuté) |
| **Chemins hardcodés (§R7)** | `grep -n '/tmp\|C:\\'` | **1 match : L124** `run_dir=Path("/tmp/gate_m4_unused")` |
| noqa (§R7) | `grep -n 'noqa'` | 1 match : L20 `# noqa: F401` — **justifié** (side-effect import pour registre) |
| Registration manuelle (§R7) | `grep -n 'register_model\|register_feature'` | 0 occurrences (grep exécuté) |
| Mutable defaults (§R6) | `grep -n 'def.*=\[\]\|def.*={}'` | 0 occurrences (grep exécuté) |
| is True/False (§R6) | `grep -n 'is np.bool_\|is True\|is False'` | 0 occurrences (grep exécuté) |
| isfinite (§R6) | `grep -n 'isfinite'` | 0 occurrences (grep exécuté) — N/A pour un fichier test |
| for range (§R9) | `grep -n 'for .* in range'` | 0 occurrences (grep exécuté) |
| Fixtures dupliquées (§R7) | `grep -n 'load_config.*configs/'` | 0 occurrences (grep exécuté) |

### B2. Annotations par fichier

#### `tests/test_gate_m4.py` (347 lignes ajoutées)

Lecture complète du diff (353 lignes diff).

- **L124** `run_dir=Path("/tmp/gate_m4_unused")` : chemin `/tmp` hardcodé. Même si les baselines ignorent `run_dir` (no-op fit), cela viole la règle de portabilité §R7 des tests. La fonction helper `_run_pipeline_baseline` n'est pas un test method (pas d'accès direct à `tmp_path`), mais le path devrait être paramétré ou utiliser `Path(".")`.
  Sévérité : **MINEUR**
  Suggestion : ajouter un paramètre `run_dir: Path` à `_run_pipeline_baseline` et passer `tmp_path` depuis les tests appelants, ou utiliser `Path(".")` comme valeur inerte.

- **L137** `execution_mode = getattr(model, "execution_mode", "standard")` : fallback `getattr` avec valeur par défaut. `execution_mode` est toujours défini sur `BaseModel` (attribut de classe `= "standard"`), donc le fallback est superflu. Pattern `getattr(..., default)` viole §R1 (no fallbacks).
  Sévérité : **MINEUR**
  Suggestion : remplacer par `execution_mode = model.execution_mode`.

- **L75-96** `_run_pipeline_dummy` : cette fonction ne fait **pas** appel à `model.fit()` avant `model.predict()`. Or le critère (b) stipule « pipeline complet sans crash ». Pour les baselines, `_run_pipeline_baseline` appelle bien `fit()` puis `predict()`. L'asymétrie fait que `DummyModel.fit()` n'est jamais exercé dans les tests du gate M4, ce qui laisse une partie du contrat BaseModel non testée pour DummyModel dans ce contexte.
  Sévérité : **WARNING**
  Suggestion : ajouter un appel `model.fit(X_train=x_seq, y_train=..., X_val=x_seq, y_val=..., config=config, run_dir=tmp_path)` dans `_run_pipeline_dummy` pour exercer le pipeline complet.

- **L280-283** `importlib.import_module("ai_trading.models")` / `importlib.import_module("ai_trading.baselines")` : ces appels sont des no-ops. Le module `ai_trading.baselines` est déjà importé en ligne 20 (import top-level pour side-effect), et `import_module` retourne le module cached sans ré-exécuter le code. Pour une vérification de complétude gate, c'est fonctionnellement suffisant (le registre est peuplé), mais les appels `import_module` sont trompeurs — ils donnent l'impression de forcer un peuplement. §R7 recommande `importlib.reload()` pour les tests de registre.
  Sévérité : **MINEUR**
  Suggestion : soit supprimer les appels `import_module` (redondants avec l'import L20), soit les remplacer par `importlib.reload()` pour un test plus robuste du side-effect.

- **L259-266** `TestGateM4Coverage::test_coverage_verification_method_documented` : test `assert True` (placeholder). Le critère (d) est satisfait (vérifié manuellement : 99% couverture sur `ai_trading/backtest + baselines + metrics`), et la tâche autorise explicitement un placeholder documenté. Cependant, un test qui passe toujours sans rien vérifier est un anti-pattern.
  Sévérité : **MINEUR**
  Suggestion : envisager un test qui lance `pytest --cov` en subprocess et parse le résultat, ou documenter plus explicitement le chiffre vérifié (ex : ajouter dans la docstring : « Dernière vérification : 99% — 2026-03-03 »).

- **L20** `import ai_trading.baselines  # noqa: F401` : justifié — side-effect import pour peupler MODEL_REGISTRY. RAS.

- **L27** `from tests.conftest import make_ohlcv_random` : import explicite d'un helper conftest (pas une fixture décorée). Correct et propre.

- **L29-39** Constantes module-level (`HORIZON=4`, `FEE=0.0005`, etc.) : toutes cohérentes avec `configs/default.yaml` et la spec. `SHARPE_ANNUALIZED=False` conforme au critère (a) du plan (« delta Sharpe **non-annualisé** »). RAS.

- **L186-222** `TestGateM4MetricsCoherence` : 5 tests couvrant `no_trade` (pnl=0, trades=0, mdd=0), `buy_hold` (trades=1), `sma_rule` (trades>=0). Conforme à l'item (c) du plan. RAS.

- **L190-222** Cohérence assertions : les assertions utilisent `==` pour des grandeurs attendues exactement à zéro (`net_pnl == 0.0`, `n_trades == 0`, `max_drawdown == 0.0`) — correct car no_trade ne produit aucun trade, donc les valeurs sont structurellement zéro (pas de calcul floating-point). RAS.

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage `test_gate_m4.py` | ✅ | Conforme au plan (gate M4 validation) |
| ID tâche #043 dans docstrings | ✅ | Toutes les docstrings contiennent `#043` |
| Couverture critères d'acceptation | ✅ | (a)→TestGateM4Determinism (3 tests), (b)→TestGateM4PipelineNocrash (4 tests), (c)→TestGateM4MetricsCoherence (5 tests), (d)→TestGateM4Coverage (1 test placeholder), (e)→TestGateM4RegistryCompleteness (3 tests) |
| Cas nominaux + erreurs + bords | ⚠️ | Critère (a) inclut un test d'égalité exacte (bord). Pas de cas d'erreur explicite (ex : seed différente devrait donner résultats différents), mais raisonnable pour un gate test |
| Boundary fuzzing | N/A | Gate validation — pas de paramètres numériques à fuzzer |
| Déterministes | ✅ | `SEED = 42` fixé, `make_ohlcv_random(seed=SEED)` |
| Données synthétiques | ✅ | `make_ohlcv_random` — aucune dépendance réseau |
| Portabilité chemins | ❌ | L124 : `/tmp/gate_m4_unused` hardcodé |
| Tests registre (import_module vs reload) | ⚠️ | `importlib.import_module` utilisé mais c'est un no-op (module déjà importé L20) |

### B4. Code — Règles non négociables

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code / no fallbacks (§R1) | ⚠️ | L137 `getattr(model, "execution_mode", "standard")` — fallback superflu (MINEUR) |
| Defensive indexing (§R10) | ✅ | Pas d'indexing dangereux |
| Config-driven (§R2) | ✅ | Constantes test-level uniquement, `load_config(CONFIG_PATH)` pour baselines |
| Anti-fuite (§R3) | ✅ | Scan B1 : 0 `.shift(-`, pas de look-ahead |
| Reproductibilité (§R4) | ✅ | Scan B1 : 0 legacy random, seed fixée, `default_rng` dans DummyModel |
| Float conventions (§R5) | ✅ | `float32` pour X_seq/y, `float64` pour prediction metrics |
| Anti-patterns Python (§R6) | ✅ | Scan B1 : 0 mutable defaults, 0 is True/False |

### B5. Qualité du code

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Cohérent partout |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO |
| Imports propres | ✅ | noqa L20 justifié |
| DRY | ✅ | Helper functions réutilisées par tous les tests |

### B5-bis. Bonnes pratiques métier

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | ✅ | Sharpe non-annualisé conforme critère (a) |
| Nommage métier | ✅ | `sharpe`, `max_drawdown`, `net_pnl`, `n_trades` |
| Séparation responsabilités | ✅ | Gate tests uniquement |
| Invariants de domaine | ✅ | no_trade → pnl=0, buy_hold → trades=1 |
| Cohérence unités/échelles | ✅ | MDD en ratio (0.005 = 0.5pp), conforme au plan |

### B6. Conformité spec v1.0

| Critère | Verdict |
|---|---|
| Spécification | ✅ — Les 5 critères M4-framework du plan sont tous adressés |
| Plan d'implémentation | ✅ — `set(MODEL_REGISTRY) == {"dummy", "no_trade", "buy_hold", "sma_rule"}` conforme à `VALID_STRATEGIES_MVP` |
| Formules doc vs code | ✅ — delta Sharpe ≤ 0.02, delta MDD ≤ 0.005 (0.5 pp), couverture ≥ 95% (mesuré: 99%) |

### B7. Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | Appels `execute_trades`, `apply_cost_model`, `build_equity_curve`, `compute_trading_metrics`, `compute_prediction_metrics` conformes aux signatures existantes |
| Noms de colonnes DataFrame | ✅ | `close`, `open`, `high`, `low`, `volume` — standard |
| Clés de configuration | ✅ | `load_config(CONFIG_PATH)` pour baselines |
| Registres et conventions | ✅ | `MODEL_REGISTRY` accédé via import standard |
| Conventions numériques | ✅ | float32 tenseurs, float64 métriques |
| Imports croisés | ✅ | Tous les modules importés existent dans Max6000i1 |

---

## Remarques

1. **[WARNING]** `_run_pipeline_dummy` ne fait pas appel à `model.fit()` — pipeline DummyModel incomplet
   - Fichier : `tests/test_gate_m4.py`
   - Ligne(s) : 75-96
   - Suggestion : ajouter `model.fit(X_train=x_seq, y_train=np.zeros(n, dtype=np.float32), X_val=x_seq, y_val=np.zeros(n, dtype=np.float32), config=load_config(CONFIG_PATH), run_dir=tmp_path)` avant `model.predict()` pour tester le pipeline complet.

2. **[MINEUR]** Chemin hardcodé `/tmp/gate_m4_unused` — portabilité
   - Fichier : `tests/test_gate_m4.py`
   - Ligne(s) : 124
   - Suggestion : paramétrer `run_dir` dans `_run_pipeline_baseline` ou utiliser `Path(".")`.

3. **[MINEUR]** Fallback `getattr(model, "execution_mode", "standard")` — superflu
   - Fichier : `tests/test_gate_m4.py`
   - Ligne(s) : 137
   - Suggestion : remplacer par `model.execution_mode`.

4. **[MINEUR]** `importlib.import_module` au lieu de `importlib.reload` dans tests de registre
   - Fichier : `tests/test_gate_m4.py`
   - Ligne(s) : 280-283
   - Suggestion : supprimer les appels (redondants avec l'import L20) ou utiliser `reload` pour tester le side-effect réellement.

5. **[MINEUR]** Test coverage placeholder `assert True`
   - Fichier : `tests/test_gate_m4.py`
   - Ligne(s) : 265
   - Suggestion : la couverture est vérifiée à 99% manuellement. Acceptable per task spec, mais un subprocess check serait plus robuste.

## Vérification manuelle du critère (d)

```
pytest --cov=ai_trading/backtest --cov=ai_trading/baselines --cov=ai_trading/metrics tests/ --cov-report=term-missing

TOTAL    500    6    99%
```

Critère (d) ≥ 95% : ✅ **satisfait** (99%).

---

## Résumé

Les 16 tests couvrent les 5 critères du gate M4 et passent tous. Le code est propre, déterministe et conforme à la spec. Le WARNING principal concerne l'absence de `fit()` dans le pipeline DummyModel, ce qui rend le critère (b) « pipeline complet » partiellement incomplet. Les 4 items MINEUR sont des améliorations de portabilité, style et robustesse des tests de registre.
