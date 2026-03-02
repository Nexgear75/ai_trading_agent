# Revue PR — [WS-7] #032 — Fallback θ (aucun quantile valide)

Branche : `task/032-theta-fallback`
Tâche : `docs/tasks/M3/032__ws7_theta_fallback.md`
Date : 2026-03-02
Itération : v2 (post-FIX commit 6981b45)

## Verdict global : ✅ CLEAN

## Résumé

L'implémentation du fallback θ est conforme à la spécification E.2.2.
Les 3 items MINEUR identifiés en v1 ont tous été correctement corrigés dans le commit FIX `6981b45`.
Aucun nouvel item identifié. Verdict CLEAN.

---

## Suivi des corrections v1

| # | Sévérité | Description v1 | Corrigé ? | Preuve |
|---|---|---|---|---|
| 1 | MINEUR | Checklist item « Commit GREEN » non coché | ✅ | `git diff fc4f304...6981b45 -- docs/tasks/M3/032__ws7_theta_fallback.md` → `- [ ]` → `- [x]` |
| 2 | MINEUR | Docstring `test_no_feasible_theta_triggers_fallback` dit « fallback θ = +∞ » mais assertion accepte les 2 méthodes | ✅ | `git diff fc4f304...6981b45 -- tests/test_theta_optimization.py` → docstring changée en « fallback applies » (L254) |
| 3 | MINEUR | Absence de test de filtrage partiel MDD dans fallback step 1 | ✅ | Nouveau test `test_fallback_relax_partial_mdd_filtering` ajouté (42 lignes) avec `_make_crashing_ohlcv` + `mdd_cap=0.50` — vérifie que certains candidats sont filtrés (MDD > mdd_cap) et que le plus haut quantile mdd-feasible est sélectionné |

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/032-theta-fallback` | ✅ | `git branch` → `task/032-theta-fallback` |
| Commit RED présent | ✅ | `828cfb7` — `[WS-7] #032 RED: tests fallback θ` |
| Commit GREEN présent | ✅ | `fc4f304` — `[WS-7] #032 GREEN: fallback θ aucun quantile valide` |
| Commit RED = tests uniquement | ✅ | `git show --stat 828cfb7` → 1 fichier: `tests/test_theta_optimization.py` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat fc4f304` → 3 fichiers: `threshold.py`, `032__ws7_theta_fallback.md`, `test_theta_optimization.py` |
| Commit FIX post-revue v1 | ✅ | `6981b45` — `[WS-7] #032 FIX: corrections mineurs revue v1` → 2 fichiers: tâche + tests |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 3 commits exactement (RED + GREEN + FIX) |

### Tâche

| Critère | Verdict | Détail |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en tête du fichier |
| Critères d'acceptation cochés | ✅ (8/8) | Tous les 8 critères cochés `[x]` |
| Checklist cochée | ✅ (8/9) | Seul item non coché : « Pull Request ouverte » — attendu (PR pas encore ouverte) |

### CI

| Check | Résultat |
|---|---|
| `pytest` | **885 passed**, 0 failed (fourni par l'utilisateur — +1 test par rapport à v1 grâce au nouveau test partiel) |
| `ruff check ai_trading/ tests/` | **All checks passed** (fourni par l'utilisateur) |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep -n ' or \[\]\| or {}\| or ""\| or 0\b\| if .* else ' CHANGED_SRC` | 1 match L67 — **faux positif** : docstring `"1 if y_hat[t] > theta, else 0"` |
| §R1 — Except trop large | `grep -n 'except:$\|except Exception:' CHANGED_SRC` | 0 occurrences (grep exécuté) |
| §R7 — Print résiduel | `grep -n 'print(' CHANGED_SRC` | 0 occurrences (grep exécuté) |
| §R3 — Shift négatif | `grep -n '\.shift(-' CHANGED_SRC` | 0 occurrences (grep exécuté) |
| §R4 — Legacy random API | `grep -rn 'np\.random\.seed\|...' CHANGED` | 0 occurrences (grep exécuté) |
| §R7 — TODO/FIXME orphelins | `grep -rn 'TODO\|FIXME\|HACK\|XXX' CHANGED` | 0 occurrences (grep exécuté) |
| §R7 — Chemins hardcodés | `grep -n '/tmp\|/var/tmp\|C:\\' CHANGED_TEST` | 0 occurrences (grep exécuté) |
| §R7 — Imports absolus `__init__` | N/A | Aucun `__init__.py` modifié |
| §R7 — Registration manuelle tests | `grep -n 'register_model\|register_feature' CHANGED_TEST` | 0 occurrences (grep exécuté) |
| §R6 — Mutable default arguments | `grep -rn 'def .*=\[\]\|def .*={}' CHANGED` | 0 occurrences (grep exécuté) |
| §R6 — open() sans context manager | `grep -n '\.read_text\|open(' CHANGED_SRC` | 0 occurrences (grep exécuté) |
| §R6 — Bool identity | `grep -rn 'is np\.bool_\|is True\|is False' CHANGED` | 0 occurrences (grep exécuté) |
| §R6 — Dict collision | `grep -n '\[.*\] = .*' CHANGED_SRC` | 1 match L189 — **faux positif** : `details: list[dict] = []` (initialisation vide, pas boucle) |
| §R9 — for range loop | `grep -n 'for .* in range(.*):' CHANGED_SRC` | 0 occurrences (grep exécuté) |
| §R6 — isfinite | `grep -n 'isfinite' CHANGED_SRC` | 1 match L50 — `math.isfinite(q)` ✅ (validation q_grid existante) |
| §R9 — Numpy comprehension | `grep -n 'np\.[a-z]*(.*for .* in ' CHANGED_SRC` | 0 occurrences (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep -n 'load_config.*configs/' CHANGED_TEST` | 0 occurrences (grep exécuté) |
| §R7 — noqa | `grep -rn 'noqa' CHANGED` | 0 occurrences (grep exécuté) |

### Annotations par fichier (B2)

#### `ai_trading/calibration/threshold.py`

Diff relu intégralement (67 lignes modifiées vs Max6000i1). Observations :

- **L4-5** : Ajout `import logging` — stdlib, correctement placé. ✅
- **L15** : `logger = logging.getLogger(__name__)` — module-level, correct. ✅
- **L240-254** : Normal path (feasible candidates). Inversion du `if len(...) > 0` (guard clause) puis sort + return. Fonctionnellement identique au code #031 avec meilleure lisibilité. RAS.
- **L256-279** : Fallback step 1. `mdd_feasible = [d for d in details if d["mdd"] <= mdd_cap]`, tri par `-d["quantile"]` → sélection du quantile le plus haut (le plus conservateur). Conforme à E.2.2 point 1. Le `logger.warning` inclut mdd_cap, min_trades, θ, quantile, mdd et n_trades — traçabilité complète. `method = "fallback_relax_min_trades"` distingue du path normal. RAS.
- **L281-296** : Fallback step 2. `theta = float("inf")`, `n_trades = 0`, `net_pnl = 0.0`, `mdd = 0.0`. Conforme à E.2.2 points 2 et 4. `logger.warning` avec mdd_cap. `method = "fallback_no_trade"`, `quantile = None`. RAS.

> RAS après lecture complète du diff (67 lignes ajoutées/modifiées).

#### `tests/test_theta_optimization.py`

Diff relu intégralement (345+ lignes ajoutées vs Max6000i1, dont 42 nouvelles dans FIX). Observations :

- **L1-8** : Docstring mise à jour `#031, #032 WS-7`. ✅
- **L14** : Ajout `import logging` pour `caplog` tests. ✅
- **L252-254** : Docstring de `test_no_feasible_theta_triggers_fallback` corrigée de « fallback θ = +∞ » à « fallback applies ». Cohérent avec l'assertion qui accepte les 2 méthodes. ✅ (correction MINEUR #2 v1)
- **L643-670** : Helper `_make_crashing_ohlcv` — prix exponentiellement décroissant, garantissant MDD > 95%. Correct pour forcer fallback step 2. RAS.
- **L673-700** : `test_fallback_relax_selects_theta` — `mdd_cap=1.0` (permissif) + `min_trades=10000` → fallback step 1. Vérifie `method == "fallback_relax_min_trades"`, `quantile == 0.9`. ✅
- **L702-724** : `test_fallback_relax_picks_highest_quantile_among_feasible` — même pattern. ✅
- **L726-748** : `test_fallback_relax_emits_warning` — `caplog` + assertion « min_trades » dans warning. ✅
- **L750-791** : `test_fallback_relax_partial_mdd_filtering` — **NOUVEAU en FIX**. `_make_crashing_ohlcv` + `mdd_cap=0.50` + `min_trades=10000`. Vérifie : (1) `method == "fallback_relax_min_trades"`, (2) `mdd <= 0.50`, (3) au moins un candidat avec `mdd > 0.50` (filtrage réel), (4) quantile sélectionné = `max(mdd_feasible_qs)`. Excellent test exerciant le filtrage partiel. ✅ (correction MINEUR #3 v1)
- **L793-813** : `test_fallback_relax_details_preserved` — `len(details) == len(q_grid)`. ✅
- **L820-841** : `test_fallback_theta_infinity` — crashing OHLCV + `mdd_cap=0.001`. Vérifie `theta == float("inf")`, `method == "fallback_no_trade"`, n_trades/net_pnl/mdd = 0. ✅
- **L843-868** : `test_fallback_theta_infinity_emits_warning` — `caplog` + `len(warning_msgs) >= 1`. ✅
- **L870-905** : `test_fallback_fold_conserved` — theta not None, n_trades=0, details complets. ✅
- **L907-930** : `test_fallback_theta_infinity_quantile_none` — `quantile is None`. ✅
- **L937-968** : `test_feasible_theta_method_unchanged` — `method == "quantile_grid"` quand θ faisable. Non-régression. ✅
- **L970-987** : `test_feasible_no_warning_emitted` — `len(warning_msgs) == 0`. Non-régression. ✅

> RAS après lecture complète du diff.

#### `docs/tasks/M3/032__ws7_theta_fallback.md`

- Checklist item « Commit GREEN » maintenant coché `[x]`. ✅ (correction MINEUR #1 v1)
- Seul item restant non coché : « Pull Request ouverte » — attendu (PR pas encore créée). ✅

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅ | CA1→`test_fallback_relax_selects_theta`, CA2→`test_fallback_theta_infinity`, CA3→`test_fallback_relax_emits_warning`+`test_fallback_theta_infinity_emits_warning`, CA4→`test_fallback_fold_conserved`, CA5→`TestCalibrateThresholdFallbackNoRegression`, CA6→5+4+2 tests, CA7→885 passed, CA8→ruff clean |
| Cas nominaux + erreurs + bords | ✅ | Step 1 (5 tests incl. filtrage partiel), Step 2 (4 tests), no regression (2 tests) |
| Boundary fuzzing | ✅ | `mdd_cap=1.0` (tout passe), `mdd_cap=0.50` (partiel), `mdd_cap=0.001` (rien ne passe). `min_trades=10000` (impossible), `min_trades=0` (tout passe), `min_trades=1` (normal). |
| Déterministes | ✅ | `np.random.default_rng(42)` (via `_make_ohlcv`), `np.random.default_rng(123)` (via `_make_y_hat_val`), `np.linspace`, `np.exp` |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` dans les tests |
| Tests registre réalistes | N/A | Aucun registre impliqué |
| Contrat ABC complet | N/A | Aucun ABC modifié |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 vrai match. `logger.warning` explicite à chaque étape de relaxation. Pas de default silencieux. |
| §R10 Defensive indexing | ✅ | Pas d'indexation par indice dans le nouveau code. Filtrage list comprehension + sort. |
| §R2 Config-driven | ✅ | `mdd_cap` et `min_trades` sont des paramètres. `test_config_keys_exist` confirme leur présence dans config. Aucune valeur hardcodée dans le fallback. |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Le fallback opère sur `details` déjà calculés sur val uniquement. θ calibré sur val, pas test. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Le fallback est déterministe (filtrage + tri, pas d'aléatoire). |
| §R5 Float conventions | ✅ | `net_pnl`, `mdd` restent en float64 (métriques). `float("inf")` est un float Python standard. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open() non-contextuel, 0 bool identity. `isfinite` présent L50. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | `mdd_feasible`, `fallback_relax_min_trades`, `fallback_no_trade` — snake_case, noms explicites |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | `import logging` ajouté au bon endroit (stdlib). 0 noqa. N/A pour `__init__.py`. |
| DRY | ✅ | Logique de retour factorisée (dict avec mêmes clés). Pas de duplication entre les 3 chemins. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Détail |
|---|---|---|
| Annexe E.2.2 | ✅ | Point 1 (relax min_trades + quantile haut) → L256-279. Point 2 (θ = +∞) → L281-296. Point 3 (warning loggé) → `logger.warning` aux L265 et L283. Point 4 (fold conservé n_trades=0/PnL=0) → L289-294. |
| Plan WS-7.3 | ✅ | Description plan → implémentation conforme |
| Formules doc vs code | ✅ | « quantile le plus haut » → `sort(key=lambda d: -d["quantile"])`. « MDD <= mdd_cap » → `d["mdd"] <= mdd_cap`. Conforme. |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | Signature `calibrate_threshold` inchangée. Dict retourné garde les mêmes 7 clés. |
| Clés retournées | ✅ | `method` : 3 valeurs possibles (`quantile_grid`, `fallback_relax_min_trades`, `fallback_no_trade`). Contrat dict compatible. |
| `details` structure | ✅ | Inchangée — mêmes clés par detail entry. |
| Conventions numériques | ✅ | float64 pour métriques, `float("inf")` Python standard. |
| Imports croisés | ✅ | Seul ajout : `import logging` (stdlib). Pas de nouvelle dépendance intra-projet. |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | θ = +∞ → 0 trades est correct (aucun signal Go ne peut dépasser +∞). |
| Nommage métier cohérent | ✅ | `fallback_relax_min_trades`, `fallback_no_trade` — explicites. |
| Séparation des responsabilités | ✅ | Le fallback reste dans `calibrate_threshold` — pas de mélange avec backtest/features. |
| Invariants de domaine | ✅ | n_trades=0 ↔ net_pnl=0, mdd=0. Cohérent. |

---

## Remarques

Aucune remarque. Les 3 items v1 ont été correctement corrigés.

---

## Résumé

Itération v2 post-corrections. Les 3 items MINEUR de v1 (checklist incomplète, docstring inconsistante, test de filtrage partiel manquant) sont tous corrigés dans le commit FIX `6981b45`. Le nouveau test `test_fallback_relax_partial_mdd_filtering` exerce effectivement le filtrage partiel avec des données crashing et un `mdd_cap` modéré. Aucun nouvel item identifié. Branche prête pour merge.
