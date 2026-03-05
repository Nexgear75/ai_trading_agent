# Revue PR — [WS-D-2] #079 — Page 1 : tableau récapitulatif et filtres

Branche : `task/079-wsd2-overview-table-filters`
Tâche : `docs/tasks/MD-2/079__wsd2_overview_table_filters.md`
Date : 2026-03-06

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation propre et bien structurée de la page Vue d'ensemble : séparation logique métier (`overview_logic.py`) / rendu Streamlit (`1_overview.py`), 32 tests unitaires couvrant tous les critères d'acceptation. Trois points mineurs identifiés : checklist de tâche incomplète, noms de colonnes sans parenthèses (divergence cosmétique avec la spec §5.2), et un fallback défensif inutile dans `has_warnings()`. Aucun bloquant ni warning.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/NNN-short-slug` | ✅ | `git branch --show-current` → `task/079-wsd2-overview-table-filters` |
| Commit RED présent | ✅ | `51639c4` — `[WS-D-2] #079 RED: tests page overview tableau et filtres` — 1 fichier: `tests/test_dashboard_overview.py` (526 insertions) |
| Commit RED contient uniquement des tests | ✅ | `git show --stat 51639c4` → 1 seul fichier `tests/test_dashboard_overview.py` |
| Commit GREEN présent | ✅ | `328a7fa` — `[WS-D-2] #079 GREEN: page overview tableau récapitulatif et filtres` — 5 fichiers (impl + tâche + tests fix) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 2 commits uniquement (RED + GREEN) |

### Tâche

| Critère | Verdict | Commentaire |
|---|---|---|
| Statut DONE | ✅ | Ligne 3 : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (11/11) | Tous les critères `[x]` |
| Checklist cochée | ⚠️ (7/9) | Les 2 derniers items non cochés : « Commit GREEN » et « Pull Request ouverte ». Le commit GREEN existe (328a7fa) mais l'item n'est pas coché. Voir remarque #1. |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_overview.py tests/test_dashboard_structure.py -v` | **65 passed**, 0 failed, 0.07s |
| `ruff check scripts/dashboard/ tests/test_dashboard_overview.py tests/test_dashboard_structure.py` | **All checks passed** |

**Phase A : PASS** — on poursuit en Phase B.

---

## Phase B — Code Review

### Périmètre

5 fichiers modifiés vs `Max6000i1` :
- `scripts/dashboard/pages/overview_logic.py` (249 lignes, nouveau)
- `scripts/dashboard/pages/1_overview.py` (111 lignes, nouveau contenu)
- `tests/test_dashboard_overview.py` (526 lignes, nouveau)
- `tests/test_dashboard_structure.py` (diff 10 lignes, correctif filtrage)
- `docs/tasks/MD-2/079__wsd2_overview_table_filters.md` (68 lignes, mise à jour)

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks `or []`/`or {}`/`or ""`/`or 0` | `grep -rn ' or \[\]\| or {}\| or ""\| or 0\b'` | 0 occurrence |
| Ternaires fallback `if ... else` | `grep -rn 'if .* else '` sur sources | 1 match : `1_overview.py:87` — `lambda rid: f"⚠️ {rid}" if rid in warning_run_ids else rid` — **logique conditionnelle légitime** (formatage visuel), pas un fallback ✅ |
| Except trop large | `grep -rn 'except:$\|except Exception:'` | 0 occurrence |
| Print résiduel | `grep -c 'print('` sur sources | 0 occurrence (overview_logic:0, 1_overview:0) |
| Shift négatif | `grep -n 'shift(-'` | 0 occurrence |
| Legacy random API | `grep -n 'np.random.seed\|random.seed'` | 0 occurrence |
| TODO/FIXME | `grep -n 'TODO\|FIXME'` | 0 occurrence |
| Chemins hardcodés `/tmp` | `grep -n '/tmp'` sur tests | 0 occurrence |
| noqa | `grep -n 'noqa'` | 0 occurrence |
| Imports absolus `from ai_trading.` | `grep -n 'from ai_trading\.'` | 0 occurrence |
| Mutable defaults | `grep -n 'def.*=\[\]\|def.*={}'` | 0 occurrence |
| Registration manuelle | `grep -n 'register_model\|register_feature'` | 0 occurrence |

### Annotations par fichier (B2)

#### `scripts/dashboard/pages/overview_logic.py` (249 lignes)

- **L19-28** `_COLUMNS` : Colonnes définies comme `"Net PnL moy"`, `"Sharpe moy"`, etc. La spec §5.2 utilise `"Net PnL (moy)"` avec parenthèses. Divergence cosmétique de nommage.
  Sévérité : **MINEUR** (voir remarque #2)

- **L68-72** `trading_mean.get("net_pnl")` etc. : Les `.get()` retournent `None` si la clé est absente. Acceptable car les valeurs None sont correctement gérées en aval (NaN → "—" à l'affichage). Le contrat de `discover_runs()` ne garantit pas la présence de chaque sous-clé dans `trading.mean`.
  Sévérité : **RAS** — usage justifié

- **L174** `metrics.get("aggregate", {}).get("notes")` : Double `.get()` avec fallback `{}` pour "aggregate". Or, `discover_runs()` (data_loader.py L24) valide que `"aggregate"` est une clé requise (`REQUIRED_TOP_KEYS`). Le fallback `{}` est donc inutile — "aggregate" est garanti présent. Ce pattern masquerait une corruption de données en amont.
  Sévérité : **MINEUR** (voir remarque #3)
  Suggestion : Remplacer par `metrics["aggregate"].get("notes")`.

- **L64-77** `build_overview_dataframe` : Extraction correcte des données depuis les dicts métriques. Tri descendant par Run ID (`sort_values("Run ID", ascending=False)`) conforme à la spec § « plus récent en premier ». ✅

- **L93-108** `filter_by_type` : Validation stricte du paramètre avec `ValueError` pour les valeurs invalides. Mapping correct : Tous→None, Modèles→"model", Baselines→"baseline". ✅

- **L111-125** `filter_by_strategy` : Liste vide = pas de filtre (retourne tout). Non-existant → DataFrame vide (via `.isin()`). ✅

- **L128-145** `get_unique_strategies` : Gère le cas vide, retourne une liste triée. ✅

- **L196-240** `format_overview_dataframe` : Réutilise `format_pct` et `format_float` de `utils.py` (DRY ✅). Formatage conforme §9.3 : Net PnL/MDD en `:.2%`, Sharpe en `:.2f`, Win Rate en `:.1%`, Trades en int, None → "—". ✅

#### `scripts/dashboard/pages/1_overview.py` (111 lignes)

- **L30-32** Vérification stricte de `st.session_state["runs"]` : `st.error()` + `st.stop()` si absent ou None. Pas de fallback silencieux. ✅

- **L35-37** Runs vide → `st.info()` message informatif + `st.stop()`. Conforme §12.2 (message si aucun run trouvé). ✅

- **L47-60** Filtres : `st.selectbox` pour type (3 options), `st.multiselect` pour stratégie. Conforme §5.3. ✅

- **L63-65** Application séquentielle des filtres `filter_by_type` → `filter_by_strategy`. ✅

- **L67-69** Résultat filtré vide → `st.info()` + `st.stop()`. ✅

- **L76-88** Warning indicators : construction d'un `set` de run_ids avec warnings, puis ajout du préfixe `⚠️` au Run ID. `zip(..., strict=True)` garantit la synchronisation entre `runs` et `warnings_mask`. ✅

- **L95** `st.dataframe()` avec `hide_index=True` et `use_container_width=True`. Le tri par colonne est supporté nativement par `st.dataframe()`. ✅

- **L103-108** Navigation : `st.selectbox` pour sélection de run, puis `st.session_state["selected_run_id"]` + `st.switch_page()`. Alternative acceptable à un clic direct sur ligne (limitation Streamlit). ✅

- **L110** Path `"scripts/dashboard/pages/2_run_detail.py"` : chemin relatif pour `st.switch_page()`. Conforme aux conventions Streamlit multipage.
  Sévérité : **RAS**

#### `tests/test_dashboard_overview.py` (526 lignes)

- **L26-61** Helper `_make_metrics()` : Construit un dict minimal valide simulant la sortie de `discover_runs()`. Synthétique, pas de dépendance réseau. ✅

- **L70-153** `TestBuildOverviewDataframe` (6 tests) : Colonnes, valeurs, multiple runs, None, 0 folds, liste vide. Couverture complète des cas nominaux et bords. ✅

- **L160-178** `TestDefaultSort` : Vérifie l'ordre décroissant par Run ID. ✅

- **L185-239** `TestFilterByType` (5 tests) : Tous/Modèles/Baselines + invalide (ValueError) + filtrage quand aucun modèle. ✅

- **L246-307** `TestFilterByStrategy` (4 tests) : Single, multiple, vide (all), inexistant. ✅

- **L314-347** `TestGetUniqueStrategies` (2 tests) : Cas nominal + vide. ✅

- **L354-377** `TestHasWarnings` (3 tests) : Pas de clé notes, notes vide, notes avec contenu. ✅

- **L384-432** `TestFormatOverviewDataframe` (7 tests) : Net PnL %, Sharpe float, MDD %, Win Rate .1%, Trades int, Folds inchangé, None → "—". Couverture complète §9.3. ✅

- **L439-469** `TestBuildWarningsMask` (3 tests) : Tous sans warnings, mixte, vide. ✅

- **L476-484** `TestGetRunIdFromRow` (1 test) : Extraction du run_id. ✅

- Tous les tests ont le tag `#079` dans leur docstring. ✅
- Aucun `@pytest.mark.skip` ni `xfail`. ✅
- Données synthétiques uniquement. ✅
- Déterministes (pas d'aléatoire). ✅

#### `tests/test_dashboard_structure.py` (diff 10 lignes)

- **L196** Changement du filtre de page count : `f.name != "__init__.py"` → `f.name != "__init__.py" and f.name[0].isdigit()`. Exclut les modules helper comme `overview_logic.py` du comptage des pages. Correct : les pages suivent le pattern `N_name.py`. ✅

- **L333** Même correction pour `test_pages_naming_convention`. ✅

RAS après lecture complète du diff.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères | ✅ | 11 critères → mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | Nominaux (single/multiple runs), erreurs (ValueError pour type invalide), bords (empty list, 0 folds, None values, nonexistent strategy) |
| Boundary fuzzing | ✅ | `n_folds=0`, `net_pnl=None`, `strategies=[]`, `strategy_type="Unknown"` |
| Déterministes | ✅ | Pas d'aléatoire dans les tests |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre concerné |
| Contrat ABC complet | N/A | Pas d'ABC dans cette tâche |

**Mapping critères → tests :**

| Critère d'acceptation | Test(s) |
|---|---|
| Colonnes §5.2 | `test_single_run_columns`, `test_single_run_values` |
| Tri descendant | `test_sorted_descending_by_run_id` |
| Filtre type | `test_filter_tous`, `test_filter_modeles`, `test_filter_baselines`, `test_filter_invalid_type_raises`, `test_filter_modeles_when_none_exist` |
| Filtre stratégie | `test_filter_single_strategy`, `test_filter_multiple_strategies`, `test_filter_empty_selection_returns_all`, `test_filter_nonexistent_strategy` |
| Tri par colonne | Supporté nativement par `st.dataframe()` — pas testable unitairement |
| Navigation Page 2 | `test_extract_run_id` (vérifie que run_id est accessible) |
| Message vide | `test_empty_runs_list` |
| Warnings indicator | `test_no_notes_key`, `test_empty_notes`, `test_notes_with_content`, `test_no_warnings`, `test_some_warnings`, `test_empty_runs` |
| Formatage §9.3 | `test_net_pnl_formatted_as_pct`, `test_sharpe_formatted_as_float`, `test_mdd_formatted_as_pct`, `test_win_rate_formatted_as_pct_1_decimal`, `test_trades_formatted_as_int`, `test_folds_unchanged`, `test_none_values_formatted_as_dash` |
| Suite verte | 65 passed ✅ |
| ruff clean | All checks passed ✅ |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) | ✅ | Scan B1 : 0 `or []`/`or {}`/`except:`. Un `.get("aggregate", {})` défensif en L174 (MINEUR, non bloquant). `filter_by_type` raise ValueError. Pas de fallback silencieux. |
| Defensive indexing | ✅ | Pas de slicing par index complexe. DataFrame filtering via `.isin()` et `==`. |
| Config-driven | ✅ | Colonnes définies en constante `_COLUMNS`, formatage via fonctions réutilisables. Pas de valeur magique hardcodée. |
| Anti-fuite (look-ahead) | N/A | Dashboard visualization, pas de pipeline ML. |
| Reproductibilité | N/A | Dashboard stateless (lecture seule). |
| Float conventions | N/A | Dashboard display layer. |
| Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 `open()` sans context manager. Pas de comparaison float avec `==`. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Fonctions/variables bien nommées. Colonnes en français conforme spec. |
| Pas de code mort/debug | ✅ | Scan B1 : 0 `print()`, 0 `TODO`, 0 `FIXME` |
| Imports propres / relatifs | ✅ | Imports depuis `scripts.dashboard.utils` et `scripts.dashboard.pages.overview_logic`. Pas d'import inutilisé. |
| DRY | ✅ | Réutilise `format_pct` et `format_float` de `utils.py`. Pas de duplication. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| Spécification §5.2 | ✅ | Colonnes, sources de données, tri descendant. Noms de colonnes sans parenthèses (divergence cosmétique, MINEUR). |
| Spécification §5.3 | ✅ | Filtre type (dropdown 3 options), filtre stratégie (multiselect), tri par colonne (natif st.dataframe). |
| Spécification §9.3 | ✅ | Formatage : PnL/MDD `:.2%`, Sharpe `:.2f`, Win Rate `:.1%`, Trades entier, None → "—". |
| Spécification §4.3 | ✅ | Warning indicator via `has_warnings()` basé sur `aggregate.notes`. |
| Plan d'implémentation | ✅ | Section WS-D-2.2 respectée. |
| Formules doc vs code | ✅ | Pas de formule mathématique dans cette tâche. |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | Fonctions exportées avec types annotés, retours cohérents (DataFrame, list, bool). |
| Noms de colonnes DataFrame | ✅ | Colonnes `_COLUMNS` cohérentes entre `overview_logic.py` et les tests. |
| Imports croisés | ✅ | `overview_logic.py` importe de `utils.py` (existant). `1_overview.py` importe de `overview_logic.py` (nouveau). `data_loader.py` valide les clés `run_id`, `strategy`, `aggregate` attendues par `build_overview_dataframe()`. |
| Structures de données partagées | ✅ | Le dict de métriques consommé par `build_overview_dataframe()` correspond à la structure produite par `discover_runs()` (data_loader.py). |
| `test_dashboard_structure.py` cohérence | ✅ | Filtrage adapté pour exclure `overview_logic.py` du comptage des pages (pattern `f.name[0].isdigit()`). |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts | ✅ | Métriques correctement extraites : net_pnl, sharpe, max_drawdown, hit_rate, n_trades |
| Nommage métier | ✅ | Colonnes explicites en français conformément à la spec dashboard |
| Séparation des responsabilités | ✅ | Logique métier (overview_logic.py) séparée du rendu Streamlit (1_overview.py) |

---

## Remarques

1. **[MINEUR]** Checklist de tâche incomplète
   - Fichier : `docs/tasks/MD-2/079__wsd2_overview_table_filters.md`
   - Ligne(s) : dernières lignes de la checklist
   - Description : Les 2 derniers items de la checklist (« Commit GREEN » et « Pull Request ouverte ») sont `[ ]` (non cochés). Le commit GREEN existe (`328a7fa`), donc l'item devrait être `[x]`.
   - Note : l'item « PR ouverte » est attendu non coché à ce stade. Seul « Commit GREEN » est manquant.
   - Suggestion : Cocher `[x]` pour « Commit GREEN ».

2. **[MINEUR]** Noms de colonnes divergents de la spec §5.2
   - Fichier : `scripts/dashboard/pages/overview_logic.py`
   - Ligne(s) : L19-28 (`_COLUMNS`)
   - Description : La spec §5.2 utilise `"Net PnL (moy)"`, `"Sharpe (moy)"`, etc. (avec parenthèses). Le code utilise `"Net PnL moy"`, `"Sharpe moy"`, etc. (sans parenthèses). C'est une divergence cosmétique mais techniquement non-conforme au tableau §5.2.
   - Suggestion : Aligner les noms de colonnes avec la spec : `"Net PnL (moy)"`, `"Sharpe (moy)"`, `"MDD (moy)"`, `"Win Rate (moy)"`, `"Trades (moy)"`.

3. **[MINEUR]** Fallback défensif inutile dans `has_warnings()`
   - Fichier : `scripts/dashboard/pages/overview_logic.py`
   - Ligne(s) : L174
   - Description : `metrics.get("aggregate", {}).get("notes")` utilise un fallback `{}` pour la clé `"aggregate"`. Or, `discover_runs()` (data_loader.py L24) valide que `"aggregate"` est une clé requise (`REQUIRED_TOP_KEYS`). Le fallback est donc inutile et masquerait une corruption de données en amont.
   - Suggestion : Remplacer par `metrics["aggregate"].get("notes")`. Le `.get("notes")` reste correct car `notes` est documenté comme optionnel (§4.3).

---

## Actions requises

1. Cocher l'item « Commit GREEN » dans la checklist de tâche.
2. Aligner les noms de colonnes `_COLUMNS` avec la spec §5.2 (ajouter parenthèses).
3. Remplacer `metrics.get("aggregate", {}).get("notes")` par `metrics["aggregate"].get("notes")`.

---

```
RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 3
- Rapport : docs/tasks/MD-2/079/review_v1.md
```
