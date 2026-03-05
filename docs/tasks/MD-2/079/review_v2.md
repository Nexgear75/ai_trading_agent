# Revue PR — [WS-D-2] #079 — Page 1 : tableau récapitulatif et filtres

Branche : `task/079-wsd2-overview-table-filters`
Tâche : `docs/tasks/MD-2/079__wsd2_overview_table_filters.md`
Date : 2026-03-06
Itération : v2 (suite au FIX commit `f367e7d`)

## Verdict global : ✅ CLEAN

## Résumé

Deuxième itération de revue. Les 3 items MINEUR identifiés en v1 (checklist « Commit GREEN » non cochée, noms de colonnes sans parenthèses, fallback défensif `metrics.get("aggregate", {})`) ont tous été correctement corrigés dans le commit FIX `f367e7d`. Aucun nouveau problème détecté. 65 tests passent, ruff clean, code conforme à la spec §5.2/§5.3/§9.3.

---

## Vérification des corrections v1

| # | Item v1 | Corrigé ? | Preuve |
|---|---------|-----------|--------|
| 1 | Checklist « Commit GREEN » non cochée | ✅ | `git diff 328a7fa..f367e7d -- docs/tasks/MD-2/079__wsd2_overview_table_filters.md` → `- [ ] **Commit GREEN**` → `- [x] **Commit GREEN**` |
| 2 | Noms de colonnes sans parenthèses (divergence §5.2) | ✅ | `git diff 328a7fa..f367e7d -- scripts/dashboard/pages/overview_logic.py` → `"Net PnL moy"` → `"Net PnL (moy)"` etc. (5 colonnes corrigées dans `_COLUMNS`, `build_overview_dataframe()` et `format_overview_dataframe()`) |
| 3 | Fallback défensif `metrics.get("aggregate", {}).get("notes")` | ✅ | `git diff 328a7fa..f367e7d -- scripts/dashboard/pages/overview_logic.py` → `metrics["aggregate"].get("notes")` |

Tests également mis à jour de manière cohérente (26 modifications de noms de colonnes dans `tests/test_dashboard_overview.py`).

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `task/079-wsd2-overview-table-filters` |
| Commit RED présent | ✅ | `51639c4` — `[WS-D-2] #079 RED: tests page overview tableau et filtres` — 1 fichier: `tests/test_dashboard_overview.py` |
| Commit RED contient uniquement des tests | ✅ | `git show --stat 51639c4` → 1 seul fichier test |
| Commit GREEN présent | ✅ | `328a7fa` — `[WS-D-2] #079 GREEN: page overview tableau récapitulatif et filtres` — 5 fichiers |
| Commit FIX post-review | ✅ | `f367e7d` — `[WS-D-2] #079 FIX: colonnes §5.2 avec parenthèses, suppression fallback défensif has_warnings, checklist tâche` — 3 fichiers (corrections ciblées) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 3 commits (RED + GREEN + FIX) |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | Ligne 3 : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (11/11) | Tous les critères `[x]` |
| Checklist cochée | ✅ (8/9) | Seul « PR ouverte » reste `[ ]` — normal à ce stade |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ --tb=short` | **2031 passed**, 27 deselected, 0 failed |
| `pytest tests/test_dashboard_overview.py tests/test_dashboard_structure.py -v` | **65 passed**, 0 failed, 0.06s |
| `ruff check scripts/dashboard/ tests/test_dashboard_overview.py tests/test_dashboard_structure.py` | **All checks passed** |

**Phase A : PASS**

---

## Phase B — Code Review

### Périmètre

5 fichiers modifiés vs `Max6000i1` :
- `scripts/dashboard/pages/overview_logic.py` (249 lignes, nouveau)
- `scripts/dashboard/pages/1_overview.py` (118 lignes, nouveau contenu)
- `tests/test_dashboard_overview.py` (525 lignes, nouveau)
- `tests/test_dashboard_structure.py` (diff ~10 lignes, correctif filtrage pages)
- `docs/tasks/MD-2/079__wsd2_overview_table_filters.md` (68 lignes, mise à jour)

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks `or []`/`or {}`/`or ""`/`or 0` | `grep -n ' or \[\]\| or {}\| or ""\| or 0\b'` sur SRC | 0 occurrence (grep exécuté) |
| §R1 — Ternaires fallback `if ... else` | `grep -n ' if .* else '` sur SRC | 1 match : `1_overview.py:87` — `lambda rid: f"⚠️ {rid}" if rid in warning_run_ids else rid` — logique conditionnelle légitime ✅ |
| §R1 — Except trop large | `grep -n 'except:$\|except Exception:'` sur SRC | 0 occurrence (grep exécuté) |
| §R7 — Print résiduel | `grep -n 'print('` sur SRC | 0 occurrence (grep exécuté) |
| §R3 — Shift négatif | `grep -n '\.shift(-'` sur SRC | 0 occurrence (grep exécuté) |
| §R4 — Legacy random API | `grep -n 'np\.random\.seed\|random\.seed'` | 0 occurrence (grep exécuté) |
| §R7 — TODO/FIXME | `grep -n 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrence (grep exécuté) |
| §R7 — Chemins hardcodés | `grep -n '/tmp\|C:\\'` sur TESTS | 0 occurrence (grep exécuté) |
| §R7 — noqa | `grep -n 'noqa'` sur ALL | 0 occurrence (grep exécuté) |
| §R7 — Imports absolus `__init__` | `grep '__init__.py'` sur changed | 0 fichier `__init__.py` modifié |
| §R7 — Registration manuelle | `grep -n 'register_model\|register_feature'` sur TESTS | 0 occurrence (grep exécuté) |
| §R6 — Mutable defaults | `grep -n 'def .*=\[\]\|def .*={}'` sur ALL | 0 occurrence (grep exécuté) |
| §R6 — open() sans context manager | `grep -n 'open('` sur SRC | 0 occurrence (grep exécuté) |
| §R6 — Bool identity `is True`/`is False` | `grep -n 'is True\|is False'` sur ALL | 5 matches — tous faux positifs : `has_warnings()` retourne `bool` Python natif (3 matches tests), `tomllib` retourne `bool` Python natif (2 matches test_structure) |
| §R6 — Dict collision | `grep -n '\[.*\] = '` sur SRC | Matches analysés : `st.session_state` assignations, `_TYPE_FILTER_MAP` (statique), DataFrame column assignments — tous légitimes |
| §R9 — Boucle for range | `grep -n 'for .* in range(.*):' ` sur SRC | 0 occurrence (grep exécuté) |
| §R6 — isfinite | `grep -n 'isfinite'` sur SRC | 0 occurrence — N/A, pas de validation de bornes numériques dans ce module |
| §R9 — np comprehension | `grep -n 'np\.[a-z]*(.*for '` sur SRC | 0 occurrence (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep -n 'load_config.*configs/'` sur TESTS | 0 occurrence (grep exécuté) |

### Annotations par fichier (B2)

#### `scripts/dashboard/pages/overview_logic.py` (249 lignes)

- **L19-28** `_COLUMNS` : Noms de colonnes avec parenthèses, conformes à §5.2 : `"Net PnL (moy)"`, `"Sharpe (moy)"`, etc. ✅ (corrigé depuis v1)

- **L47-77** `build_overview_dataframe()` : Construction correcte du DataFrame depuis les dicts métriques. `trading_mean.get(...)` retourne None si clé absente, gestion correcte en aval. Tri descendant `sort_values("Run ID", ascending=False)`. ✅

- **L86-108** `filter_by_type()` : Validation stricte avec `ValueError` pour valeurs invalides. Mapping correct Tous/Modèles/Baselines. ✅

- **L111-125** `filter_by_strategy()` : Liste vide = pas de filtre. `.isin()` pour filtrage. ✅

- **L128-145** `get_unique_strategies()` : Gère le cas vide, retourne liste triée. ✅

- **L155-175** `has_warnings()` : `metrics["aggregate"].get("notes")` — accès direct à `"aggregate"` (garanti par `REQUIRED_TOP_KEYS` en amont), `.get("notes")` car optionnel §4.3. ✅ (corrigé depuis v1)

- **L178-191** `build_warnings_mask()` : Compréhension de liste simple, correct. ✅

- **L200-234** `format_overview_dataframe()` : Copie via `.copy()`, formatage via `format_pct`/`format_float` réutilisés de `utils.py` (DRY). Noms de colonnes avec parenthèses. ✅

- **L237-240** `_nan_to_none()` : `pd.isna()` gère NaN et None. ✅

- **L243-249** `_format_trades()` : `pd.isna()` + `str(int(...))` pour arrondi. Type retour `str | int` cohérent. ✅

RAS après lecture complète du diff (249 lignes).

#### `scripts/dashboard/pages/1_overview.py` (118 lignes)

- **L18-25** Import de toutes les fonctions de `overview_logic.py`. Pas d'import inutilisé. ✅

- **L30-32** Vérification stricte `st.session_state["runs"]` : `st.error()` + `st.stop()`. Pas de fallback silencieux. ✅

- **L35-37** Runs vide → `st.info()` message informatif + `st.stop()`. Conforme §12.2. ✅

- **L47-60** Filtres : `st.selectbox` pour type, `st.multiselect` pour stratégie. Conforme §5.3. ✅

- **L63-65** Application séquentielle des filtres. ✅

- **L67-69** Filtré vide → `st.info()` + `st.stop()`. ✅

- **L76-88** Warning indicators : `zip(..., strict=True)` → set de run_ids → préfixe `⚠️`. ✅

- **L91** `format_overview_dataframe(df_display)` : appliqué sur le df qui a déjà les `⚠️`. ✅

- **L97-100** `st.dataframe()` avec `hide_index=True`, `use_container_width=True`. Tri par colonne natif Streamlit. ✅

- **L106-113** Navigation : `st.selectbox` pour run selection en attendant le clic natif Streamlit. `run_ids` extrait du df filtré (sans `⚠️`). ✅

- **L115-118** `st.session_state["selected_run_id"] = selected_run` + `st.switch_page(...)`. ✅

RAS après lecture complète du diff (118 lignes).

#### `tests/test_dashboard_overview.py` (525 lignes)

- **L26-61** Helper `_make_metrics()` : Dict synthétique complet, pas de dépendance réseau. ✅

- **L70-153** `TestBuildOverviewDataframe` (6 tests) : Colonnes (avec parenthèses ✅), valeurs, multiple runs, None, 0 folds, liste vide. ✅

- **L160-178** `TestDefaultSort` : Tri descendant vérifié. ✅

- **L185-239** `TestFilterByType` (5 tests) : Tous/Modèles/Baselines + invalide + vide. ✅

- **L246-307** `TestFilterByStrategy` (4 tests) : Single, multiple, vide, inexistant. ✅

- **L314-347** `TestGetUniqueStrategies` (2 tests) : Nominal + vide. ✅

- **L354-377** `TestHasWarnings` (3 tests) : No notes, empty notes, with content. `is True`/`is False` sur `bool` natif → correct. ✅

- **L384-469** `TestFormatOverviewDataframe` (7 tests) : Tous les formats §9.3 vérifiés, colonnes avec parenthèses. ✅

- **L476-505** `TestBuildWarningsMask` (3 tests) : All false, mixed, empty. ✅

- **L512-525** `TestGetRunIdFromRow` (1 test) : Extraction run_id. ✅

- Tous les tests : tag `#079` en docstring. ✅
- Aucun `@pytest.mark.skip` ni `xfail`. ✅
- Données synthétiques. ✅
- Déterministes. ✅

RAS après lecture complète du diff (525 lignes).

#### `tests/test_dashboard_structure.py` (diff ~10 lignes)

- **L196** Filtrage pages : `f.name[0].isdigit()` pour exclure `overview_logic.py` du comptage. Correct. ✅
- **L333** Même correction pour naming convention. ✅

RAS après lecture complète du diff.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅ | 11 critères d'acceptation → tous couverts (mapping ci-dessous) |
| Cas nominaux + erreurs + bords | ✅ | Nominaux (single/multi runs), erreurs (`ValueError`), bords (empty list, 0 folds, None, nonexistent) |
| Boundary fuzzing | ✅ | `n_folds=0`, `net_pnl=None`, `strategies=[]`, type invalide |
| Déterministes | ✅ | Pas d'aléatoire |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre |
| Contrat ABC complet | N/A | Pas d'ABC |

**Mapping critères → tests :**

| Critère d'acceptation | Test(s) |
|---|---|
| Colonnes §5.2 avec formatage §9.3 | `test_single_run_columns`, `test_single_run_values`, `test_net_pnl_formatted_as_pct`, `test_sharpe_formatted_as_float`, `test_mdd_formatted_as_pct`, `test_win_rate_formatted_as_pct_1_decimal`, `test_trades_formatted_as_int`, `test_folds_unchanged`, `test_none_values_formatted_as_dash` |
| Tri descendant | `test_sorted_descending_by_run_id` |
| Filtre type | `test_filter_tous`, `test_filter_modeles`, `test_filter_baselines`, `test_filter_invalid_type_raises`, `test_filter_modeles_when_none_exist` |
| Filtre stratégie | `test_filter_single_strategy`, `test_filter_multiple_strategies`, `test_filter_empty_selection_returns_all`, `test_filter_nonexistent_strategy` |
| Tri par colonne | Supporté nativement par `st.dataframe()` — non testable unitairement |
| Navigation Page 2 | `test_extract_run_id` |
| Message vide / dummy | `test_empty_runs_list` |
| Warnings indicator | `test_no_notes_key`, `test_empty_notes`, `test_notes_with_content`, `test_no_warnings`, `test_some_warnings`, `test_empty_runs` |
| Suite verte | 65 passed ✅ |
| ruff clean | All checks passed ✅ |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback, 0 except large. `filter_by_type` raise ValueError. `st.error()+st.stop()` si état invalide. |
| Defensive indexing | ✅ | Pas de slicing complexe. DataFrame filtering via `.isin()` et `==`. |
| Config-driven | ✅ | Colonnes en constante `_COLUMNS`. Formatage via fonctions `utils.py`. Pas de valeur magique. |
| Anti-fuite | N/A | Dashboard lecture seule, pas de pipeline ML. |
| Reproductibilité | N/A | Dashboard stateless. |
| Float conventions | N/A | Couche affichage uniquement. |
| Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 open sans context manager, `is True`/`is False` sur bool natif (faux positifs). |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Fonctions/variables conformes. Colonnes FR selon spec. |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO/FIXME |
| Imports propres / relatifs | ✅ | Pas d'import inutilisé, pas d'import `*`, pas d'import absolu `__init__` |
| DRY | ✅ | Réutilise `format_pct`/`format_float` de `utils.py`. Pas de duplication. |
| `.gitignore` | ✅ | Pas de fichier généré dans la PR |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| Spec §5.2 — Colonnes | ✅ | Noms avec parenthèses conformes : `"Net PnL (moy)"`, `"Sharpe (moy)"`, etc. |
| Spec §5.3 — Filtrage/tri | ✅ | Dropdown type 3 options, multiselect stratégie, tri natif st.dataframe |
| Spec §9.3 — Formatage | ✅ | PnL/MDD `:.2%`, Sharpe `:.2f`, Win Rate `:.1%`, Trades int, None→"—" |
| Spec §4.3 — Warnings | ✅ | `aggregate.notes` détecté, indicateur `⚠️` |
| Spec §12.2 — Messages | ✅ | `st.info()` si aucun run / filtré vide |
| Plan WS-D-2.2 | ✅ | Section respectée |
| Formules doc vs code | ✅ | Pas de formule mathématique dans cette tâche |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | Fonctions bien typées, retours cohérents |
| Noms de colonnes DataFrame | ✅ | `_COLUMNS` cohérent entre overview_logic.py et tests |
| Imports croisés | ✅ | `overview_logic.py` → `utils.py` (existant). `1_overview.py` → `overview_logic.py` (nouveau). Symboles existants dans Max6000i1. |
| Structures de données partagées | ✅ | Dict métriques conforme à `discover_runs()` |
| `test_dashboard_structure.py` | ✅ | Filtrage `f.name[0].isdigit()` adapté pour `overview_logic.py` |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude concepts financiers | ✅ | Métriques correctement extraites |
| Nommage métier | ✅ | Colonnes explicites conformes spec |
| Séparation des responsabilités | ✅ | Logique métier séparée du rendu Streamlit |

---

## Remarques

Aucune remarque. Les 3 items MINEUR de la v1 ont été correctement corrigés.

---

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : docs/tasks/MD-2/079/review_v2.md
```
