# Revue PR — [WS-8] #035 — Journal de trades (trades.csv) — v2

Branche : `task/035-trade-journal`
Tâche : `docs/tasks/M4/035__ws8_trade_journal.md`
Date : 2026-03-02
Itération : v2 (après corrections v1 : 1 BLOQUANT + 2 MINEURS corrigés)

## Verdict global : ✅ CLEAN

## Résumé

Les trois items identifiés en v1 (BLOQUANT — path parent non créé, MINEUR — checklist commit GREEN non cochée, MINEUR — DRY validation des taux) ont été correctement corrigés dans le commit FIX `a5f347e`. La fonction `validate_cost_rates` a été factorisée dans `costs.py` avec validation `math.isfinite` et est réutilisée par `journal.py`. Quatre nouveaux tests NaN/inf ont été ajoutés dans `test_cost_model.py`. L'audit v2 complet (scans GREP, lecture diff, CI) ne révèle aucun item résiduel. Code prêt pour merge.

---

## Vérification des corrections v1

| Item v1 | Sévérité | Correction | Verdict |
|---|---|---|---|
| Path parent non créé avant `to_csv` | BLOQUANT | `path.parent.mkdir(parents=True, exist_ok=True)` ajouté à L107 de `journal.py` | ✅ Corrigé |
| Checklist Commit GREEN non cochée | MINEUR | Item `[x]` coché dans la tâche (L62) | ✅ Corrigé |
| DRY — validation des taux dupliquée entre `costs.py` et `journal.py` | MINEUR | `validate_cost_rates()` factorisée dans `costs.py` (L14-39), importée par `journal.py` (L16) et utilisée par `apply_cost_model` (L72). `math.isfinite` ajouté aux deux modules via la fonction partagée. 4 tests NaN/inf ajoutés dans `test_cost_model.py` | ✅ Corrigé |

---

## Phase A — Compliance

### A1. Périmètre

Fichiers modifiés vs `Max6000i1` (5 fichiers) :
- `ai_trading/backtest/costs.py` (source)
- `ai_trading/backtest/journal.py` (source — nouveau)
- `tests/test_cost_model.py` (test)
- `tests/test_trade_journal.py` (test — nouveau)
- `docs/tasks/M4/035__ws8_trade_journal.md` (tâche)

### A2. Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention `task/035-trade-journal` | ✅ | `git branch --show-current` → `task/035-trade-journal` |
| Commit RED présent | ✅ | `840a2e3` — `[WS-8] #035 RED: tests journal de trades CSV` |
| Commit RED = tests uniquement | ✅ | `git show --stat 840a2e3` → 1 fichier : `tests/test_trade_journal.py` (454 insertions) |
| Commit GREEN présent | ✅ | `43930d4` — `[WS-8] #035 GREEN: export trade journal CSV` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 43930d4` → `ai_trading/backtest/journal.py` (141), `docs/tasks/M4/035__ws8_trade_journal.md` (63), `tests/test_trade_journal.py` (5 ajustements) |
| Commit FIX post-review | ✅ | `a5f347e` — `[WS-8] #035 FIX: création répertoire parent, checklist, harmonisation validation` — 4 fichiers (costs.py, journal.py, test_cost_model.py, tâche) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 3 commits : RED, GREEN, FIX |

### A3. Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en tête du fichier |
| Critères d'acceptation cochés | ✅ (12/12) | Tous `[x]` (lignes 37-48) |
| Checklist cochée | ✅ (8/9) | 8/9 `[x]`, 1 restant = PR non ouverte (attendu) |

**Vérification des critères ↔ preuves** :
- AC1 (colonnes §12.6) : `_COLUMN_ORDER` L32-47 journal.py, test `TestColumnOrder.test_columns_match_spec_order`
- AC2 (fees_paid) : L97 journal.py `fee_rate_per_side * (entry_price + exit_price)`, tests `TestFeesPaid` (3 tests)
- AC3 (slippage_paid) : L98 journal.py, tests `TestSlippagePaid` (3 tests)
- AC4 (gross_return) : L85 journal.py `(exit_price / entry_price) - 1.0`, tests `TestGrossReturn` (3 tests)
- AC5 (net_return) : L102 journal.py `trade["r_net"]`, tests `TestNetReturn` (2 tests)
- AC6 (cohérence équité) : test `TestEquityCoherence.test_product_of_net_returns_equals_equity_ratio`
- AC7 (y_hat) : L99-100 journal.py passthrough, tests `TestYHat` (3 tests)
- AC8 (0 trades) : tests `TestEmptyTrades` (2 tests)
- AC9-10 (multiple trades) : tests `TestMultipleTradesCsv` (3 tests)
- AC11-12 (suite verte, ruff) : CI vérifié ci-dessous

### A4. CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **962 passed**, 0 failed (6.59s) |
| `ruff check ai_trading/ tests/` | **All checks passed** |

Phase A : **PASS**

---

## Phase B — Code Review

### B1. Scan automatisé obligatoire (GREP)

| Pattern recherché | Règle | Résultat |
|---|---|---|
| Fallbacks silencieux (`or []`, `or {}`, `if … else`) | §R1 | 0 occurrences (grep exécuté sur SRC) |
| Except trop large (`except:`, `except Exception:`) | §R1 | 0 occurrences (grep exécuté sur SRC) |
| Suppressions lint `noqa` | §R7 | 0 occurrences (grep exécuté sur SRC+TEST) |
| `per-file-ignores` | §R7 | Existant dans `pyproject.toml` L51 — concerne d'autres modules (base.py, dummy.py, trainer.py), aucun ajout dans cette PR |
| Print résiduel | §R7 | 0 occurrences (grep exécuté sur SRC) |
| Shift négatif `.shift(-` | §R3 | 0 occurrences (grep exécuté sur SRC) |
| Legacy random API | §R4 | 0 occurrences (grep exécuté sur SRC+TEST) |
| TODO / FIXME / HACK / XXX | §R7 | 0 occurrences (grep exécuté sur SRC+TEST) |
| Chemins hardcodés `/tmp`, `C:\` | §R7 | 0 occurrences (grep exécuté sur TEST) |
| Imports absolus dans `__init__.py` | §R7 | N/A (aucun `__init__.py` modifié) |
| Registration manuelle (`register_model`, `register_feature`) | §R7 | 0 occurrences (grep exécuté sur TEST) |
| Mutable default arguments (`def f(x=[])`) | §R6 | 0 occurrences (grep exécuté sur SRC+TEST) |
| `open()` sans context manager | §R6 | 0 occurrences (grep exécuté sur SRC) — écriture via `df.to_csv()` (pandas) |
| Comparaison booléenne par identité (`is True`, `is False`) | §R6 | 0 occurrences (grep exécuté sur SRC+TEST) |
| `isfinite` présent | §R6 | `costs.py` : 2 occurrences (`math.isfinite` pour fee et slippage) ; `journal.py` : 0 (délègue à `validate_cost_rates`) |
| Boucle Python sur array numpy (`for … in range`) | §R9 | 0 occurrences (grep exécuté sur SRC) |
| Numpy compréhension vectorisable | §R9 | 0 occurrences (grep exécuté sur SRC) |
| Dict collision silencieuse | §R6 | 0 occurrences (grep exécuté sur SRC) — rows construit par `append` |
| Fixtures dupliquées (`load_config.*configs/`) | §R7 | 0 occurrences (grep exécuté sur TEST) |

### B2. Lecture du diff ligne par ligne

#### `ai_trading/backtest/journal.py` (123 lignes — nouveau fichier)

- **L16** `from ai_trading.backtest.costs import validate_cost_rates` : import correct du module partagé. Pas d'import circulaire (journal → costs, pas l'inverse). ✅
- **L18-30** `_REQUIRED_TRADE_KEYS` : `frozenset` immuable des 9 clés attendues. Cohérent avec la sortie de `apply_cost_model` + clés `y_true`/`y_hat` ajoutées par le caller. ✅
- **L32-47** `_COLUMN_ORDER` : 14 colonnes dans l'ordre exact de §12.6. Vérifié par comparaison directe avec la spec. ✅
- **L76** `validate_cost_rates(fee_rate_per_side, slippage_rate_per_side)` : validation des taux en [0, 1) avec `math.isfinite` avant les bornes. NaN, ±inf, négatifs et ≥1 tous rejetés. ✅
- **L79-80** Itération `enumerate(trades)` + `_validate_trade` : validation explicite de chaque trade (clés requises + `entry_price > 0`). ✅
- **L85** `gross_return = (exit_price / entry_price) - 1.0` : formule conforme à la tâche AC4. `entry_price > 0` garanti par `_validate_trade`. ✅
- **L97** `fees_paid = fee_rate_per_side * (entry_price + exit_price)` : formule conforme à la tâche AC2. ✅
- **L98** `slippage_paid = slippage_rate_per_side * (entry_price + exit_price)` : formule conforme à la tâche AC3. ✅
- **L102** `"net_return": trade["r_net"]` : passthrough du `r_net` calculé par `apply_cost_model`. Conforme à AC5. ✅
- **L106-109** Construction DataFrame + écriture CSV :
  - L106 : `pd.DataFrame(rows, columns=_COLUMN_ORDER)` — colonnes forcées par `_COLUMN_ORDER`. ✅
  - L107 : `path.parent.mkdir(parents=True, exist_ok=True)` — **correction v1** : création du répertoire parent avant écriture. ✅
  - L108 : `df.to_csv(path, index=False)` — pas de leak d'index. ✅
- **L114-123** `_validate_trade` : validation des clés par `_REQUIRED_TRADE_KEYS` (frozenset, O(1) lookup) et `entry_price > 0`. Messages d'erreur contextuels avec index du trade. ✅

RAS — aucune observation après lecture complète du diff (123 lignes).

#### `ai_trading/backtest/costs.py` (diff : +37/-7)

- **L10** `import math` : ajouté pour `math.isfinite`. ✅
- **L13-39** `validate_cost_rates()` : nouvelle fonction publique. Ordre correct : `isfinite` avant bornes (§R6 — NaN bypass). Validation `[0, 1)` avec messages f-string. ✅
- **L72** `validate_cost_rates(fee_rate_per_side, slippage_rate_per_side)` : remplace les 6 lignes de validation inline. DRY respecté. Comportement identique + ajout de `isfinite`. ✅

RAS — refactoring correct, aucune régression introduite.

#### `tests/test_trade_journal.py` (diff depuis GREEN : ajustements mineurs L5)

- RAS après lecture complète (455 lignes). Tests bien structurés en 12 classes. Couverture complète des AC. `pytest.approx` pour les comparaisons float. `tmp_path` pour les chemins. Données synthétiques déterministes.

#### `tests/test_cost_model.py` (diff : +24 lignes)

- **L236-260** : 4 nouveaux tests ajoutés : `test_nan_fee_rate_raises`, `test_nan_slippage_rate_raises`, `test_inf_fee_rate_raises`, `test_inf_slippage_rate_raises`. Couvrent le nouveau comportement `math.isfinite` de `validate_cost_rates`. ✅

RAS — tests corrects et pertinents.

### B3. Tests

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage (`test_trade_journal.py`, `test_cost_model.py`) | ✅ | Conforme au plan |
| ID tâche dans docstrings | ✅ | `Task #035 — WS-8` dans l'en-tête de `test_trade_journal.py` |
| Couverture des AC | ✅ (12/12) | Chaque AC mappé à au moins 1 test (détail en A3) |
| Cas nominaux + erreurs + bords | ✅ | Nominaux (8 classes), Erreurs (3 classes : MissingKeys, InvalidRates, EntryPriceValidation), Bords (EmptyTrades, fee=0, slippage=0, entry==exit) |
| Boundary fuzzing — taux | ✅ | fee=0 ✓, fee<0 ✓, fee≥1 ✓, NaN ✓, inf ✓ — idem slippage |
| Boundary fuzzing — entry_price | ✅ | entry_price=0 ✓, entry_price<0 ✓ |
| Boundary fuzzing — missing keys | ✅ | Paramétrisé sur les 9 clés (`@pytest.mark.parametrize`) |
| Déterministes | ✅ | Pas d'aléatoire — données synthétiques déterministes |
| Portabilité chemins | ✅ | Scan B1 : 0 chemin hardcodé, tous via `tmp_path` |
| Registre réaliste | N/A | Pas de registre dans ce module |
| Contrat ABC complet | N/A | Pas d'ABC dans ce module |
| Pas de `@skip`/`xfail` | ✅ | Vérifié par lecture du fichier |

### B4. Règles non négociables

#### B4a. Strict code (§R1)
✅ Scan B1 : 0 fallback, 0 except large. Validation explicite avec `raise ValueError`. Pas de paramètre optionnel avec default implicite.

#### B4a-bis. Defensive indexing (§R10)
✅ Pas de slicing critique. Itération simple sur `list[dict]`. `enumerate` pour index contextuels dans les messages d'erreur.

#### B4b. Config-driven (§R2)
✅ `fee_rate_per_side` et `slippage_rate_per_side` passés en paramètres, lus depuis config par le caller. Clés `costs.fee_rate_per_side` (L115) et `costs.slippage_rate_per_side` (L116) présentes dans `configs/default.yaml`. Pas de valeur magique hardcodée.

#### B4c. Anti-fuite (§R3)
✅ Scan B1 : 0 `.shift(-`. Module d'export pur — aucun accès aux données temporelles, pas de calcul sur séries. Aucun risque de look-ahead.

#### B4d. Reproductibilité (§R4)
✅ Scan B1 : 0 legacy random. Fonction déterministe, pas d'aléatoire. Même entrée → même sortie.

#### B4e. Float conventions (§R5)
✅ Pas de tenseurs. DataFrame utilise float64 par défaut (pandas) — correct pour métriques financières.

#### B4f. Anti-patterns Python (§R6)
✅ Scan B1 :
- 0 mutable default
- 0 `open()` direct (écriture via `df.to_csv`, lecture via `pd.read_csv` dans tests)
- `math.isfinite` présent (2 occ. dans costs.py, délégué par journal.py)
- 0 bool identity
- 0 dict collision
- `path.parent.mkdir(parents=True, exist_ok=True)` avant `to_csv` (L107)

### B5. Qualité du code (§R7)

| Critère | Verdict | Preuve |
|---|---|---|
| snake_case cohérent | ✅ | `export_trade_journal`, `validate_cost_rates`, `_validate_trade`, `_REQUIRED_TRADE_KEYS`, `_COLUMN_ORDER` |
| Pas de code mort / TODO | ✅ | Scan B1 : 0 TODO/FIXME |
| Pas de print | ✅ | Scan B1 : 0 `print(` |
| Imports propres | ✅ | Ordre stdlib → third-party → local. Pas d'import inutilisé. Import relatif via `from ai_trading.backtest.costs import validate_cost_rates` (inter-package, pas intra-package — correct) |
| DRY | ✅ | **Corrigé v1** : `validate_cost_rates` factorisée et partagée. Plus de duplication |
| `__init__.py` à jour | ✅ | `ai_trading/backtest/__init__.py` ne nécessite pas d'import du journal (pas de side-effect) |
| Pas de fichiers générés dans la PR | ✅ | Aucun fichier `.csv`, `__pycache__`, ou artefact |

### B5-bis. Bonnes pratiques métier (§R9)

| Critère | Verdict | Preuve |
|---|---|---|
| Exactitude des concepts financiers | ✅ | `gross_return = (exit/entry) - 1` — return arithmétique standard. `net_return` via multiplicatif M_net - 1 (passthrough). Décomposition additive des coûts conforme à la tâche |
| Nommage métier cohérent | ✅ | `fees_paid`, `slippage_paid`, `gross_return`, `net_return`, `entry_price_eff`, `exit_price_eff` |
| Séparation des responsabilités | ✅ | journal.py = export pur; costs.py = modèle de coûts; engine.py = exécution |
| Invariants de domaine | ✅ | `entry_price > 0` validé, taux dans `[0, 1)` validés |
| Cohérence des unités | ✅ | Returns arithmétiques, prix en quote currency, timestamps passthrough |
| Vectorisation | ✅ | Pas de boucle numpy inutile. Itération sur list[dict] (petit nombre de trades) puis construction DataFrame |

### B6. Cohérence avec les specs

| Critère | Verdict | Preuve |
|---|---|---|
| Spécification §12.6 | ✅ | 14 colonnes identiques à §12.6 dans `_COLUMN_ORDER` |
| Plan WS-8.4 | ✅ | Module dédié `ai_trading/backtest/journal.py` conforme |
| Formules doc vs code | ✅ | `fees_paid = f × (entry + exit)` L97 ✓, `slippage_paid = s × (entry + exit)` L98 ✓, `gross_return = (exit/entry) - 1` L85 ✓, `net_return = r_net` L102 ✓ |
| Pas d'exigence inventée | ✅ | Toutes les colonnes et formules tracées vers §12.6 |

### B7. Cohérence intermodule (§R8)

| Critère | Verdict | Preuve |
|---|---|---|
| Signatures et types de retour | ✅ | `export_trade_journal(trades, path, f, s) → pd.DataFrame` — cohérent avec l'usage attendu |
| Clés `_REQUIRED_TRADE_KEYS` vs `apply_cost_model` | ✅ | `apply_cost_model` produit `entry_price_eff`, `exit_price_eff`, `m_net`, `r_net` ; journal.py requiert `entry_price_eff`, `exit_price_eff`, `r_net` + clés originales + `y_true`/`y_hat` du caller |
| Clés de configuration | ✅ | `fee_rate_per_side`, `slippage_rate_per_side` → `configs/default.yaml` L115-116 |
| `validate_cost_rates` partagée | ✅ | Importée depuis `costs.py`, utilisée par `apply_cost_model` et `export_trade_journal` — même validation, même comportement |
| Conventions numériques | ✅ | Float64 (pandas default) pour métriques |
| Imports croisés | ✅ | `journal.py` importe `validate_cost_rates` depuis `costs.py` — symbole existant dans cette branche. `python -c "from ai_trading.backtest.costs import validate_cost_rates"` → OK |

---

## Remarques

Aucune.

---

## Résumé

Les 3 corrections v1 ont été correctement appliquées : `path.parent.mkdir(parents=True, exist_ok=True)` ajouté en L107, checklist mise à jour, et `validate_cost_rates` factorisée dans `costs.py` (DRY + ajout `math.isfinite`). L'audit v2 (scans GREP complets, lecture diff ligne par ligne, CI 962 tests passants, ruff clean) ne révèle aucun item résiduel. Le code est conforme à la spec §12.6, aux règles du projet, et prêt pour merge.
