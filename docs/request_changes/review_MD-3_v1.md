# Global Review — milestone/MD-3 v1

**Date** : 2026-03-09
**Branche** : `milestone/MD-3`
**Scope** : Pages 3 (Comparison) et 4 (Fold Analysis) du dashboard Streamlit

## Résultats CI

- **pytest** : 90 passed, 0 failed (tests/test_dashboard_comparison.py + tests/test_dashboard_fold_analysis.py)
- **ruff** : `ruff check scripts/dashboard/ tests/` → All checks passed

## Audit détaillé

### 1. Conformité spec

| Section spec | Implémentation | Statut |
|---|---|---|
| §7.1 Multiselect 2-10 runs | `3_comparison.py` : `st.sidebar.multiselect` avec `max_selections=10`, label `strategy_name (run_id)` | ✅ |
| §7.2 Tableau comparatif | Délègue à `build_overview_dataframe` (DRY §5.2), surbrillance best/worst, §14.4 ✅/❌ | ✅ |
| §7.2 Notes/warnings | `get_aggregate_notes` lit `aggregate.notes`, affiché via `st.warning` | ✅ |
| §7.3 Equity overlay | `build_equity_overlay_curves` → `chart_equity_overlay`, normalisé à 1.0, légende cliquable | ✅ |
| §7.4 Radar chart | `build_radar_data` → `chart_radar`, 5 axes, min-max normalisé | ✅ |
| §8.1 Sélection fold | Dropdown run + fold + slider synchronisé | ✅ |
| §8.2 Equity fold + drawdown | `chart_fold_equity` + `add_drawdown_to_figure`, marqueurs ▲/▼, zone ombrée `COLOR_DRAWDOWN` | ✅ |
| §8.3 Scatter predictions | `chart_scatter_predictions`, coloration Go/No-Go, détection signal via `output_type` + fallback `method` | ✅ |
| §8.3 Métriques encart | MAE, RMSE, DA, IC, θ affichés en 5 colonnes `st.metric` | ✅ |
| §8.3 Signal type | Message informatif si `output_type == "signal"` | ✅ |
| §8.4 Journal trades fold | `build_fold_trade_journal` sans colonne Fold, filtres signe/période, pagination 50/page | ✅ |
| §9.3 Conventions affichage | Formatage via `format_overview_dataframe` (DRY), `format_pct`, `format_float`, `format_theta` | ✅ |
| §9.3 Null display | `_NULL_DISPLAY = "—"` utilisé partout | ✅ |
| §14.4 Criterion check | `check_criterion_14_4` : P&L > 0, PF > 1.0, MDD > mdd_cap (strict inequality) | ✅ |

### 2. DRY inter-modules

| Pattern DRY | Mécanisme | Statut |
|---|---|---|
| Tableau comparatif ↔ overview | `build_comparison_dataframe` délègue à `build_overview_dataframe` | ✅ |
| Formatage comparatif ↔ overview | `format_comparison_dataframe` délègue à `format_overview_dataframe` | ✅ |
| filter_trades (Page 2 ↔ Page 4) | `4_fold_analysis.py` importe `filter_trades` de `run_detail_logic` | ✅ |
| paginate_dataframe (Page 2 ↔ Page 4) | `4_fold_analysis.py` importe `paginate_dataframe` de `run_detail_logic` | ✅ |
| join_equity_after vs join_fold_equity_after | Deux fonctions distinctes : multi-fold (per-fold loop) vs single-fold (simplifié) | ✅ Justifié |
| build_trade_journal vs build_fold_trade_journal | Deux fonctions distinctes : multi-fold (col Fold) vs single-fold (sans col Fold) | ✅ Justifié |

**Note** : `join_fold_equity_after` et `build_fold_trade_journal` sont des variantes simplifiées de `run_detail_logic.join_equity_after` et `build_trade_journal`. L'algorithme interne utilise `pd.merge_asof` dans les deux cas mais la version fold n'a pas de boucle per-fold. La duplication structurelle est minime et justifiée par la différence d'interface (single-fold vs multi-fold avec colonne `fold`).

### 3. Strict code

| Vérification | Résultat |
|---|---|
| `or default`, `value if value else default` | Aucune occurrence trouvée (grep) |
| `except:` broad | Aucune. Seul `except FileNotFoundError` ciblé dans `3_comparison.py:90` avec `logger.warning` |
| Validation explicite + raise | `get_fold_threshold` → `raise ValueError` si fold non trouvé |
| `check_criterion_14_4` : config None | Retourne `False` explicitement |

### 4. Config-driven

| Paramètre | Source | Statut |
|---|---|---|
| Seuil MDD (§14.4) | `config_snapshot.yaml → thresholding.mdd_cap` | ✅ Non hardcodé |
| P&L > 0, PF > 1.0 | Hardcodés dans le dashboard (conformes à la spec pipeline §14.4) | ✅ Conforme spec |

### 5. Couverture tests vs critères d'acceptation

#### Tâche #083 (Sélection et tableau comparatif)

| Critère | Tests | Statut |
|---|---|---|
| Multiselect 2-10 runs | `TestBuildComparisonDataframe` : empty, single, three, None | ✅ |
| Colonnes conformes §5.2 | `test_columns_match_overview` | ✅ |
| Surbrillance best/worst | `TestHighlightBestWorst` : basic, ties, single, all None | ✅ |
| §14.4 ✅/❌ | `TestCheckCriterion144` : 11 tests (all pass, PnL, PF, MDD, boundary, None) | ✅ |
| Notes/warnings | `TestGetAggregateNotes` : present, absent, empty | ✅ |

#### Tâche #084 (Equity overlay + radar)

| Critère | Tests | Statut |
|---|---|---|
| Courbes superposées | `TestBuildEquityOverlayCurves` : nominal, partial, all missing, empty, labels, DataFrame check | ✅ |
| Radar data | `TestBuildRadarData` : normal, None→0, multiple | ✅ |
| Dégradation equity absentes | `test_partial_missing`, `test_all_missing` | ✅ |

#### Tâche #085 (Navigation fold + equity)

| Critère | Tests | Statut |
|---|---|---|
| list_fold_dirs | sorted, empty, no dir, ignores files | ✅ |
| build_fold_selector_options | returns fold IDs, empty, single | ✅ |
| get_fold_dir | correct path, different IDs | ✅ |
| add_drawdown_to_figure | traces added, preserves existing, name, flat equity, same object, color | ✅ |

#### Tâche #086 (Scatter predictions)

| Critère | Tests | Statut |
|---|---|---|
| get_fold_threshold | positive θ, negative, zero, None, not found raises, multiple folds | ✅ |
| get_output_type | regression, signal, fallback none→signal, fallback quantile→regression, mixed | ✅ |
| build_prediction_metrics | known values MAE/RMSE/DA/IC, opposite directions, zeros | ✅ |
| format_theta | None→—, positive, negative, zero | ✅ |

#### Tâche #087 (Journal trades fold)

| Critère | Tests | Statut |
|---|---|---|
| prepare_fold_trades | adds costs, no modify original, multiple | ✅ |
| join_fold_equity_after | None equity, match, no backward, empty equity | ✅ |
| build_fold_trade_journal | correct columns, no Fold col, values, with equity, empty+no eq, empty+eq | ✅ |
| DRY filter_trades | sign winning/losing, date filter, no fold param | ✅ |
| DRY paginate_dataframe | first page, second page | ✅ |

### 6. Cohérence inter-modules

| Interface | Statut |
|---|---|
| `comparison_logic.py` → `overview_logic.py` (build/format) | ✅ Import et délégation corrects |
| `comparison_logic.py` → `data_loader.py` (load_equity_curve) | ✅ |
| `3_comparison.py` → `comparison_logic.py`, `charts.py`, `data_loader.py` | ✅ Imports cohérents |
| `fold_analysis_logic.py` → `utils.py` (_NULL_DISPLAY, COLOR_DRAWDOWN) | ✅ |
| `4_fold_analysis.py` → `fold_analysis_logic.py`, `run_detail_logic.py`, `charts.py`, `data_loader.py`, `utils.py` | ✅ |
| `filter_trades` appelé sans `fold=` sur données sans colonne `fold` | ✅ `fold=None` par défaut → pas d'accès à `trades_df["fold"]` |

### 7. Conventions

| Point | Résultat |
|---|---|
| snake_case | ✅ Partout |
| Pas de `print()` | ✅ Aucune occurrence (grep) |
| Pas de TODO/FIXME orphelins | ✅ Aucune occurrence (grep) |
| Imports propres | ✅ Aucun import inutilisé (ruff F401 clean) |
| Code mort | ✅ Aucun détecté |
| `logging` au lieu de `print` | ✅ `logger.warning` dans `3_comparison.py` |

## Items BLOQUANTS

Aucun.

## Items WARNING

Aucun.

## Items MINEURS

Aucun.

## Verdict

**CLEAN** — 0 bloquant, 0 warning, 0 mineur.

L'implémentation des Pages 3 et 4 du dashboard est conforme à la spécification (§7, §8, §9, §14.4), respecte le DRY via délégation systématique aux modules existants (`overview_logic`, `run_detail_logic`, `charts`, `data_loader`, `utils`), et bénéficie d'une couverture de tests complète (90 tests, 0 échec) couvrant les 5 tâches #083-#087. Le code est strict (pas de fallback silencieux), config-driven (seuil MDD lu depuis `config_snapshot.yaml`), et conforme aux conventions du projet.
