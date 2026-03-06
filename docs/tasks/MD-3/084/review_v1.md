# Revue PR — [WS-D-4] #084 — Page 3 : courbes d'équité superposées et radar chart

Branche : `task/084-wsd4-equity-overlay-radar`
Tâche : `docs/tasks/MD-3/084__wsd4_equity_overlay_radar.md`
Date : 2026-03-06

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation propre de l'overlay d'equity curves (§7.3) et du radar chart (§7.4) dans la page de comparaison, avec dégradation gracieuse et tests complets. Code DRY (réutilisation de `chart_equity_overlay`, `chart_radar`, `load_equity_curve`). Un item mineur identifié sur la docstring module non mise à jour.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/084-*` | ✅ | `git branch --show-current` → `task/084-wsd4-equity-overlay-radar` |
| Commit RED présent | ✅ | `9113f93` — `[WS-D-4] #084 RED: tests overlay equity et radar chart` |
| Commit RED = tests uniquement | ✅ | `git show --stat 9113f93` → `tests/test_dashboard_comparison.py | 248 +++` (1 file) |
| Commit GREEN présent | ✅ | `2a96055` — `[WS-D-4] #084 GREEN: page comparaison — overlay equity et radar` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 2a96055` → 3 fichiers : task md, `3_comparison.py`, `comparison_logic.py` |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline 9113f93..2a96055` → 1 seul commit (GREEN) |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le fichier de tâche |
| Critères d'acceptation cochés | ✅ (7/7) | Tous `[x]` — vérification croisée ci-dessous |
| Checklist cochée | ✅ (8/9) | Seul le dernier item (PR ouverte) non coché — attendu |

**Vérification croisée des critères d'acceptation :**

| AC | Code/Test prouvant la satisfaction |
|---|---|
| Courbes d'équité superposées normalisées à 1.0 avec légende interactive | `3_comparison.py:154` → `chart_equity_overlay(curves)`, charts.py L261 normalise par `eq / eq_start`, légende L280 `itemclick: toggle` |
| Radar chart 5 axes avec normalisation min-max correcte | `comparison_logic.py:290-308` → extraction 5 métriques, `chart_radar()` L316-333 normalisation min-max |
| Dégradation si equity curves partiellement absentes | `3_comparison.py:149-152` → `if missing_labels: st.info(...)`, radar affiché indépendamment en dessous |
| Dégradation si toutes les equity curves sont absentes | `3_comparison.py:154-157` → `if curves:` plotly chart, `else:` info message |
| Tests synthétiques multi-runs | `TestBuildRadarData` (5 tests), `TestLoadComparisonEquityCurves` (5 tests) |
| Suite de tests verte | 2166 passed, 0 failed |
| ruff check passe | All checks passed |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **2166 passed**, 27 deselected, 0 failed |
| `ruff check ai_trading/ tests/ scripts/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep ' or []\| or {}...'` SRC | 3 matches — **faux positifs** : ternaires display `"✅" if criteria["pnl_ok"] else "❌"` (L120-121 3_comparison, L166 comparison_logic). Pattern conditionnel d'affichage, pas fallback. |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` SRC | 0 occurrences (grep exécuté) |
| §R7 — noqa | `grep 'noqa'` ALL | 0 occurrences (grep exécuté) |
| §R7 — Print résiduel | `grep 'print('` SRC | 0 occurrences (grep exécuté) |
| §R3 — Shift négatif | `grep '.shift(-'` SRC | 0 occurrences (grep exécuté) |
| §R4 — Legacy random | `grep 'np.random.seed...'` ALL | 0 occurrences (grep exécuté) |
| §R7 — TODO/FIXME | `grep 'TODO\|FIXME'` ALL | 0 occurrences (grep exécuté) |
| §R7 — Chemins hardcodés | `grep '/tmp\|C:\\'` TEST | 0 occurrences (grep exécuté) |
| §R7 — Imports absolus `__init__` | `grep 'from ai_trading\.'` SRC | 0 occurrences (grep exécuté) — pas de `__init__.py` dans `pages/` (convention Streamlit multipage) |
| §R7 — Registration manuelle | `grep 'register_model...'` TEST | 0 occurrences (grep exécuté) — N/A |
| §R6 — Mutable defaults | `grep 'def .*=[]\|def .*={}'` ALL | 0 occurrences (grep exécuté) |
| §R6 — open() sans context manager | `grep '.read_text\|open('` SRC | 0 occurrences (grep exécuté) |
| §R6 — Bool par identité numpy | `grep 'is True\|is False'` ALL | Matches dans `comparison_logic.py:165` et tests — **faux positifs** : valeurs Python natives `bool`/`None`, `is True` intentionnel pour distinguer `True` de `None` pour `mdd_ok` |
| §R6 — Dict collision | `grep '[.*] = .*'` SRC | Matches analysés : `label_to_metrics[label]` (L56) protégé par guard L54-55 `if label in label_to_metrics: raise ValueError` ; itérations sur clés fixes (`_NUMERIC_COLS`, `_RADAR_METRIC_KEYS`) — aucune collision possible |
| §R9 — for range | `grep 'for .* in range'` SRC | 0 occurrences (grep exécuté) |
| §R6 — isfinite | `grep 'isfinite'` SRC | 0 occurrences — N/A (pas de validation de bornes numériques dans ce module, les métriques viennent de metrics.json validé en amont) |
| §R9 — numpy compréhension | `grep 'np.[a-z]*(.*for'` SRC | 0 occurrences (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` TEST | 0 occurrences (grep exécuté) |

### Annotations par fichier (B2)

#### `scripts/dashboard/pages/3_comparison.py` (172 lignes)

- **L1-7** Module docstring : la description mentionne uniquement « tableau comparatif » et la ligne Ref liste §7.1, §7.2, §10.2 mais omet §7.3 (equity overlay) et §7.4 (radar chart) qui sont maintenant implémentés. L'ancienne version (avant #083) mentionnait « overlay d'equity curves, radar charts » — cette info a été supprimée par #083 et non restaurée par #084.
  Sévérité : **MINEUR**
  Suggestion : mettre à jour la docstring et la ligne Ref pour inclure §7.3 et §7.4.

- **L34-43** Gestion session state : validation `"runs" not in st.session_state or st.session_state["runs"] is None` puis `not runs`. Correct, pas de fallback silencieux. RAS.

- **L50-57** Construction `label_to_metrics` avec guard `if label in label_to_metrics: raise ValueError(...)`. Strict code, guard §R6 dict collision respecté. RAS.

- **L107-115** Chargement `config_snapshot` avec `try/except (FileNotFoundError, ValueError)` : exceptions spécifiques, cohérentes avec la doc de `load_config_snapshot`. RAS.

- **L118-133** Affichage critères : ternaires `"✅" if ... else "❌"`, gestion `mdd_ok is None` → "—". Pas de fallback, affichage conditionnel correct. RAS.

- **L141-158** §7.3 equity overlay : chargement conditionnel si `runs_dir is not None`, message info si missing, message info si aucune courbe. Dégradation gracieuse conforme §7.3 et tâche. RAS.

- **L163-167** §7.4 radar chart : appel `build_radar_data(selected_runs)` sans try/except. Si une métrique est None, ValueError non capturée → crash Streamlit visible. Comportement strict code, conforme à la spec (le radar requiert toutes les métriques). RAS.

#### `scripts/dashboard/pages/comparison_logic.py` (351 lignes)

- **L1-8** Module docstring à jour avec §7.3 et §7.4. RAS.

- **L19-36** `_NUMERIC_COLS` et `_HIGHER_IS_BETTER` : constantes module-level lisibles. MDD traité comme "lowest abs value is best" — correct. RAS.

- **L47-64** `build_comparison_dataframe` : délègue à `build_overview_dataframe` (DRY §5.2). RAS.

- **L72-105** `highlight_best_worst` : gestion NaN via `dropna()`, MDD via `abs()`, conversion `int()` des indices. Logique correcte pour higher-is-better/lower-is-better/abs. RAS.

- **L113-168** `check_pipeline_criteria` : extrait les 3 critères, `is True` pour distinguer `True` de `None` (Python natif, pas numpy). RAS.

- **L176-216** `apply_highlight_styles` : guard `best_idx != worst_idx` évite le styling quand une seule valeur. Utilisation de `iloc` pour positionnement correct. RAS.

- **L224-240** `get_aggregate_notes` : `if not notes: return None` gère à la fois `None` et `""`. RAS.

- **L248-262** `format_run_label` : accès direct à `metrics["run_id"]` et `metrics["strategy"]["name"]` — strict code, pas de `.get()`. RAS.

- **L270-308** `build_radar_data` : itère sur `_RADAR_METRIC_KEYS`, vérifie `value is None → raise ValueError`. Strict code conforme. RAS.

- **L316-351** `load_comparison_equity_curves` : itère sur les runs, appelle `load_equity_curve(run_dir)`, trie entre `curves` et `missing`. Contrat de retour clair. RAS.

#### `tests/test_dashboard_comparison.py` (847 lignes)

- Imports lazy (dans chaque méthode) — cohérent avec le pattern existant dans les tests dashboard.
- Helper `_make_metrics()` : construit un dict minimal valide, paramétrable avec kwargs. Réaliste.
- #084 docstrings : tâche ID `#084` présent dans chaque docstring de test. Conforme.

RAS après lecture complète du diff (847 lignes).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_dashboard_comparison.py`, ID `#084` dans docstrings |
| Couverture des critères | ✅ | AC1→`TestLoadComparisonEquityCurves.test_all_runs_have_equity`, AC2→`TestBuildRadarData.test_basic_two_runs`, AC3→`test_some_runs_missing_equity`, AC4→`test_all_runs_missing_equity`, AC5→10 tests #084 total |
| Cas nominaux + erreurs + bords | ✅ | Nominal : 2 runs ; Erreur : None metric raises ; Bord : empty list, single run, all missing |
| Boundary fuzzing | ✅ | `test_empty_runs` (0 runs), `test_none_metric_value_raises`, `test_all_runs_missing_equity`, `test_some_runs_missing_equity` |
| Déterministes | ✅ | Pas d'aléatoire dans ces tests |
| Données synthétiques | ✅ | Helper `_make_metrics()`, CSV créés via `tmp_path` |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé, utilise `tmp_path` pytest |
| Tests registre | N/A | Pas de registre concerné |
| Contrat ABC | N/A | Pas d'ABC |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback réel. `build_radar_data` raises ValueError pour None. Guard duplicate labels. |
| §R10 Defensive indexing | ✅ | Pas d'indexation array directe dans le code ajouté. `iloc` utilisé avec indices validés. |
| §R2 Config-driven | ✅ | Pas de paramètre hardcodé — les métriques viennent de `metrics.json`, le seuil MDD de `config_snapshot.yaml`. |
| §R3 Anti-fuite | ✅ | N/A — dashboard en lecture seule, pas de calcul de features/labels. Scan B1 : 0 `.shift(-`. |
| §R4 Reproductibilité | ✅ | N/A — pas d'aléatoire. Scan B1 : 0 legacy random API. |
| §R5 Float conventions | ✅ | N/A — pas de tenseurs. Métriques en float natif Python. |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 open() sans CM, `is True` sur Python natif (faux positif), dict collision gardé. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `build_radar_data`, `load_comparison_equity_curves`, `chart_equity_overlay` |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO |
| Imports propres / relatifs | ✅ | Pas de `__init__.py` dans `pages/` (convention Streamlit). Imports spécifiques. |
| DRY | ✅ | Réutilise `chart_equity_overlay`, `chart_radar`, `load_equity_curve`, `build_overview_dataframe`, `format_run_label` |
| Pas de fichiers générés dans la PR | ✅ | Diff ne contient que .py et .md |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Normalisation equity à 1.0 (déléguée à charts.py), MDD abs value, radar axes conformes spec §7.4 |
| Nommage métier cohérent | ✅ | `equity_curve`, `net_pnl`, `sharpe`, `max_drawdown`, `hit_rate`, `profit_factor` |
| Séparation des responsabilités | ✅ | Logic dans `comparison_logic.py`, affichage dans `3_comparison.py`, graphiques dans `charts.py` |
| Invariants de domaine | ✅ | `chart_equity_overlay` valide `eq_start > 0` avant normalisation |
| Cohérence des unités/échelles | ✅ | Métriques passées brutes au radar, normalisation min-max dans `chart_radar` |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| §7.3 — Superposition equity curves | ✅ | Graphique unique, courbe par run, légende cliquable, normalisé départ=1.0 |
| §7.4 — Radar chart 5 axes | ✅ | Net PnL, Sharpe, 1-MDD (inversé dans chart_radar), Win Rate, PF, normalisation min-max |
| Plan WS-D-4.2 | ✅ | 4 tâches du plan toutes implémentées |
| Formules doc vs code | ✅ | N/A — pas de formule mathématique dans cette tâche |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `chart_equity_overlay(curves: dict[str, pd.DataFrame]) -> go.Figure` — appel conforme. `chart_radar(runs_data: list[dict]) -> go.Figure` — `build_radar_data` produit `list[dict]` avec les clés attendues (`label`, `net_pnl`, `sharpe`, `max_drawdown`, `hit_rate`, `profit_factor`). `load_equity_curve(run_dir: Path) -> pd.DataFrame | None` — appelé correctement. |
| Structures de données partagées | ✅ | Dict metrics format identique à `discover_runs()` output |
| Imports croisés | ✅ | `chart_equity_overlay`, `chart_radar` (charts.py), `load_equity_curve` (data_loader.py), `build_overview_dataframe` (overview_logic.py) — tous existent dans Max6000i1 |
| Forwarding kwargs | ✅ | Pas de wrapper/orchestrateur avec kwargs à transmettre |
| Pattern existant respecté | ✅ | `comparison_logic.py` suit le pattern de `overview_logic.py` et `run_detail_logic.py` |

---

## Remarques

1. [MINEUR] Module docstring de `scripts/dashboard/pages/3_comparison.py` non mise à jour pour §7.3/§7.4.
   - Fichier : `scripts/dashboard/pages/3_comparison.py`
   - Ligne(s) : 1-7
   - Description : La description mentionne « tableau comparatif de métriques avec surbrillance meilleur/pire, critères pipeline §14.4, warnings » mais omet l'overlay d'equity curves et le radar chart. La ligne Ref (`§7.1, §7.2, §10.2`) n'inclut pas §7.3 et §7.4 qui sont maintenant implémentés. Ironiquement, l'ancienne docstring (avant #083) mentionnait « overlay d'equity curves, radar charts ».
   - Suggestion : mettre à jour la docstring :
     ```python
     """Page 3 — Comparaison de runs (Comparison).

     Comparaison côte à côte de plusieurs runs : tableau comparatif de métriques
     avec surbrillance meilleur/pire, overlay d'equity curves normalisées,
     radar chart 5 axes, critères pipeline §14.4, warnings.

     Ref: §7.1 multiselect, §7.2 tableau comparatif, §7.3 equity overlay,
     §7.4 radar chart, §14.4 critères pipeline, §10.2 — pages/3_comparison.py
     """
     ```

---

## Actions requises

1. Mettre à jour la docstring module de `3_comparison.py` pour inclure §7.3, §7.4, overlay et radar (MINEUR).
