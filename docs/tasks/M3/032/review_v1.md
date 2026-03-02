# Revue PR — [WS-7] #032 — Fallback θ (aucun quantile valide)

Branche : `task/032-theta-fallback`
Tâche : `docs/tasks/M3/032__ws7_theta_fallback.md`
Date : 2026-03-02

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation est conforme à la spécification E.2.2 : la logique de fallback séquentielle (relaxation min_trades → θ = +∞) est correcte et bien testée. 3 items mineurs identifiés : checklist de tâche incomplète (2 items non cochés), docstring de test inconsistante, absence de test de filtrage partiel dans le fallback step 1.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/032-theta-fallback` | ✅ | `git branch` → `task/032-theta-fallback` |
| Commit RED présent | ✅ | `828cfb7` — `[WS-7] #032 RED: tests fallback θ` |
| Commit GREEN présent | ✅ | `fc4f304` — `[WS-7] #032 GREEN: fallback θ aucun quantile valide` |
| Commit RED = tests uniquement | ✅ | `git show --stat 828cfb7` → 1 fichier: `tests/test_theta_optimization.py` (304 insertions) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat fc4f304` → 3 fichiers: `threshold.py`, `032__ws7_theta_fallback.md`, `test_theta_optimization.py` (76 ins, 42 del) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 2 commits exactement (RED + GREEN) |

### Tâche

| Critère | Verdict | Détail |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` en tête du fichier |
| Critères d'acceptation cochés | ✅ (8/8) | Tous les 8 critères cochés `[x]` |
| Checklist cochée | ❌ (7/9) | 2 items non cochés : « Commit GREEN » et « Pull Request ouverte » — voir MINEUR #1 |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **884 passed**, 0 failed (fourni par l'utilisateur) |
| `ruff check ai_trading/ tests/` | **All checks passed** (fourni par l'utilisateur) |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep -n ' or \[\]\| or {}\| or ""\| or 0\b\| if .* else ' CHANGED_SRC` | 1 match L67 — **faux positif** : docstring `"1 if y_hat[t] > theta, else 0"` |
| §R1 — Except trop large | `grep -n 'except:$\|except Exception:' CHANGED_SRC` | 0 occurrences |
| §R7 — Print résiduel | `grep -n 'print(' CHANGED_SRC` | 0 occurrences |
| §R3 — Shift négatif | `grep -n '\.shift(-' CHANGED_SRC` | 0 occurrences |
| §R4 — Legacy random API | `grep -rn 'np\.random\.seed\|...' CHANGED` | 0 occurrences |
| §R7 — TODO/FIXME orphelins | `grep -rn 'TODO\|FIXME\|HACK\|XXX' CHANGED` | 0 occurrences |
| §R7 — Chemins hardcodés | `grep -n '/tmp\|/var/tmp\|C:\\' CHANGED_TEST` | 0 occurrences |
| §R7 — Imports absolus `__init__` | N/A | Aucun `__init__.py` modifié |
| §R7 — Registration manuelle tests | `grep -n 'register_model\|register_feature' CHANGED_TEST` | 0 occurrences |
| §R6 — Mutable default arguments | `grep -rn 'def .*=\[\]\|def .*={}' CHANGED` | 0 occurrences |
| §R6 — open() sans context manager | `grep -n '\.read_text\|open(' CHANGED_SRC` | 0 occurrences |
| §R6 — Bool identity | `grep -rn 'is np\.bool_\|is True\|is False' CHANGED` | 0 occurrences |
| §R6 — Dict collision | `grep -n '\[.*\] = .*' CHANGED_SRC` | 1 match L189 — **faux positif** : `details: list[dict] = []` (initialisation de liste vide) |
| §R9 — for range loop (vectorisation) | `grep -n 'for .* in range(.*):' CHANGED_SRC` | 0 occurrences |
| §R6 — isfinite | `grep -n 'isfinite' CHANGED_SRC` | 1 match L50 — `math.isfinite(q)` ✅ (validation q_grid existante) |
| §R9 — Numpy comprehension | `grep -n 'np\.[a-z]*(.*for .* in ' CHANGED_SRC` | 0 occurrences |
| §R7 — Fixtures dupliquées | `grep -n 'load_config.*configs/' CHANGED_TEST` | 0 occurrences |
| §R7 — noqa | `grep -rn 'noqa' CHANGED` | 0 occurrences |

### Annotations par fichier (B2)

#### `ai_trading/calibration/threshold.py`

- **L240-254** : Normal path (feasible candidates). L'inversion de la condition (`len > 0` en premier au lieu de `len == 0`) clarifie le flux et est fonctionnellement correcte. Le sort par `(-net_pnl, -quantile)` est identique à l'ancien code. RAS.

- **L256-279** : Fallback step 1. Filtre `mdd_feasible = [d for d in details if d["mdd"] <= mdd_cap]`, tri par `-d["quantile"]` → sélection du quantile le plus haut (le plus conservateur). Conforme à E.2.2 point 1. Le `logger.warning` inclut mdd_cap, min_trades, θ, quantile, mdd et n_trades — traçabilité complète. `method = "fallback_relax_min_trades"` distingue clairement du path normal. RAS.

- **L281-296** : Fallback step 2. `theta = float("inf")`, `n_trades = 0`, `net_pnl = 0.0`, `mdd = 0.0`. Conforme à E.2.2 points 2 et 4. Le `logger.warning` inclut mdd_cap. `method = "fallback_no_trade"`. `quantile = None` (aucun quantile sélectionné). RAS.

- **L4** : Ajout `import logging` — approprié pour les warnings E.2.2.

- **L15** : `logger = logging.getLogger(__name__)` — correct (module-level logger).

> RAS après lecture complète du diff (67 lignes ajoutées/modifiées).

#### `tests/test_theta_optimization.py`

- **L1-8** : Docstring mise à jour pour inclure #032. ✅

- **L14** : Ajout `import logging` pour `caplog` tests. ✅

- **L249-282** (`TestCalibrateThresholdNoFeasible`) : Test existant de #031 adapté au nouveau comportement. L'ancien `theta is None` est remplacé par `theta is not None` + `method in (fallback_relax_min_trades, fallback_no_trade)`.
  - **Observation** : La docstring dit « tight mdd_cap → fallback θ = +∞ » mais l'assertion accepte les deux méthodes de fallback. Inconsistance docstring/assertion. Voir MINEUR #2.

- **L643-670** (`_make_crashing_ohlcv`) : Helper dédié. Prix exponentiellement décroissants (100 → ~5), garantissant un MDD > 95%. Correct pour forcer le fallback step 2.

- **L673-737** (`TestCalibrateThresholdFallbackRelax`) :
  - `test_fallback_relax_selects_theta` : `mdd_cap=1.0` (permissif, tous les candidats passent) + `min_trades=10000` (impossible). Vérifie `method == "fallback_relax_min_trades"` et `quantile == 0.9` (plus haut). ✅
  - `test_fallback_relax_picks_highest_quantile_among_feasible` : Similaire, vérifie `quantile == 0.9`. ✅
  - `test_fallback_relax_emits_warning` : `caplog` + vérification que "min_trades" apparaît dans le warning. ✅
  - `test_fallback_relax_details_preserved` : Vérifie `len(details) == len(q_grid)`. ✅
  - **Observation** : Tous les tests step 1 utilisent `mdd_cap=1.0` → *tous* les candidats sont mdd-feasible. Il n'y a pas de test où seuls *certains* candidats passent mdd_cap (filtrage partiel). Voir MINEUR #3.

- **L743-836** (`TestCalibrateThresholdFallbackNoTrade`) :
  - `test_fallback_theta_infinity` : Crashing OHLCV + `mdd_cap=0.001`. Vérifie `theta == float("inf")`, `method == "fallback_no_trade"`, `n_trades == 0`, `net_pnl == 0.0`, `mdd == 0.0`. ✅
  - `test_fallback_theta_infinity_emits_warning` : `caplog`, `len(warning_msgs) >= 1`. ✅
  - `test_fallback_fold_conserved` : Vérifie que le fold est conservé (theta not None, n_trades=0, net_pnl=0.0, mdd=0.0, details complets). ✅
  - `test_fallback_theta_infinity_quantile_none` : `quantile is None`. ✅

- **L842-914** (`TestCalibrateThresholdFallbackNoRegression`) :
  - `test_feasible_theta_method_unchanged` : `mdd_cap=1.0`, `min_trades=0` → `method == "quantile_grid"`. Vérifie l'absence de régression. ✅
  - `test_feasible_no_warning_emitted` : `caplog`, `len(warning_msgs) == 0`. Prouve qu'aucun warning fallback n'est émis en mode normal. ✅

> Tous les tests utilisent `np.random.default_rng(42)` (via `_make_ohlcv`) ou des données déterministes (`np.linspace`, `np.exp`). Seeds tracées. Pas de dépendance réseau.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅ | CA1→`test_fallback_relax_selects_theta`, CA2→`test_fallback_theta_infinity`, CA3→`test_fallback_relax_emits_warning`+`test_fallback_theta_infinity_emits_warning`, CA4→`test_fallback_fold_conserved`, CA5→`TestCalibrateThresholdFallbackNoRegression`, CA6→4+4+2 tests (cas nominaux, erreurs, bords), CA7→884 passed, CA8→ruff clean |
| Cas nominaux + erreurs + bords | ✅ | Step 1 (4 tests), Step 2 (4 tests), no regression (2 tests) |
| Boundary fuzzing | ✅ (partiel) | Voir MINEUR #3 — pas de test de filtrage partiel mdd_cap dans step 1 |
| Déterministes | ✅ | `rng = np.random.default_rng(42)`, `np.linspace`, `np.exp` |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` dans les tests |
| Tests registre réalistes | N/A | Aucun registre impliqué |
| Contrat ABC complet | N/A | Aucun ABC modifié |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 vrai match. `logger.warning` explicite à chaque étape de relaxation. Pas de default silencieux. |
| §R10 Defensive indexing | ✅ | Pas d'indexation par indice dans le nouveau code. Filtrage par list comprehension + sort. |
| §R2 Config-driven | ✅ | `mdd_cap` et `min_trades` sont des paramètres (injectés par config en amont). Aucune valeur hardcodée dans le fallback. |
| §R3 Anti-fuite | ✅ | Scan B1 : 0 `.shift(-`. Le fallback opère sur `details` déjà calculés sur val uniquement. θ calibré sur val, pas test. |
| §R4 Reproductibilité | ✅ | Scan B1 : 0 legacy random. Le fallback est déterministe (filtrage + tri, pas d'aléatoire). |
| §R5 Float conventions | ✅ | `net_pnl`, `mdd` restent en float64 (métriques). `float("inf")` est un float Python standard. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable defaults, 0 open(), 0 bool identity. `isfinite` présent pour validation q_grid (existant). |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | `mdd_feasible`, `fallback_relax_min_trades`, `fallback_no_trade` — snake_case, noms explicites |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME |
| Imports propres | ✅ | `import logging` ajouté au bon endroit (stdlib). Scan B1 : 0 noqa |
| DRY | ✅ | Logique de retour factorisée (dict avec mêmes clés). Pas de duplication entre les 3 chemins. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Détail |
|---|---|---|
| Annexe E.2.2 | ✅ | Les 4 points de la spec sont implémentés : (1) relax min_trades + θ conservateur, (2) θ = +∞, (3) warning loggé, (4) fold conservé n_trades=0/PnL=0 |
| Plan WS-7.3 | ✅ | Description plan → implémentation conforme |
| Formules doc vs code | ✅ | Pas de formule mathématique nouvelle. La sélection « quantile le plus haut » et la condition `mdd <= mdd_cap` sont conformes à la spec. |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | La signature de `calibrate_threshold` est inchangée. Le dict de retour garde les mêmes clés (`theta`, `quantile`, `method`, `net_pnl`, `mdd`, `n_trades`, `details`). Les types de valeurs changent pour le fallback (`theta` = `float("inf")` au lieu de `None`) — c'est une amélioration volontaire. |
| Clés retournées | ✅ | `method` a 3 valeurs possibles : `"quantile_grid"`, `"fallback_relax_min_trades"`, `"fallback_no_trade"`. Les consommateurs aval devront gérer les nouvelles méthodes, mais le contrat dict est compatible. |
| `details` structure | ✅ | Inchangée — liste de dicts avec les mêmes clés (`quantile`, `theta`, `net_pnl`, `mdd`, `n_trades`, `feasible`). |

---

## Remarques

1. **[MINEUR]** Checklist de tâche incomplète : 2 items non cochés (`Commit GREEN`, `Pull Request ouverte`).
   - Fichier : `docs/tasks/M3/032__ws7_theta_fallback.md`
   - Ligne(s) : 69-70
   - Suggestion : Cocher « Commit GREEN » (fc4f304 existe). « Pull Request ouverte » sera cochée lors de l'ouverture de la PR.

2. **[MINEUR]** Inconsistance docstring/assertion dans `test_no_feasible_theta_triggers_fallback`.
   - Fichier : `tests/test_theta_optimization.py`
   - Ligne(s) : 254
   - Suggestion : La docstring dit « tight mdd_cap → fallback θ = +∞ » mais l'assertion accepte les deux méthodes de fallback (`fallback_relax_min_trades` ou `fallback_no_trade`). Aligner la docstring sur le comportement réel : « min_trades impossibly high → fallback E.2.2 applies ».

3. **[MINEUR]** Absence de test de filtrage partiel dans le fallback step 1 : tous les tests step 1 utilisent `mdd_cap=1.0` (permissif → tous les candidats passent MDD). Il n'y a pas de test où seuls *certains* candidats passent `mdd <= mdd_cap` et d'autres non, ce qui exercerait réellement le filtrage du step 1.
   - Fichier : `tests/test_theta_optimization.py`
   - Ligne(s) : 673-737
   - Suggestion : Ajouter un test avec `_make_crashing_ohlcv` + `mdd_cap` intermédiaire (ex : 0.5) où certains quantiles (hauts, peu de trades) passent le MDD cap et d'autres (bas, beaucoup de trades dans un marché crash) ne le passent pas. Vérifier que seul un candidat mdd-feasible est retenu.

## Résumé

L'implémentation du fallback θ est correcte, bien structurée et conforme à la spécification E.2.2. Les 3 chemins (normal, relax min_trades, θ = +∞) sont clairement séparés avec warnings explicites. Les tests couvrent les critères d'acceptation avec 10 nouveaux tests. Les 3 items identifiés sont tous mineurs (checklist process, précision docstring, test de filtrage partiel).
