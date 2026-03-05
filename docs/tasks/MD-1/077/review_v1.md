# Revue PR — [WS-D-1] #077 — Bibliothèque de graphiques Plotly

Branche : `task/077-wsd1-charts-library`
Tâche : `docs/tasks/MD-1/077__wsd1_charts_library.md`
Date : 2026-03-05

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation solide de 8 fonctions Plotly dans `scripts/dashboard/charts.py` (513 lignes) avec 38 tests unitaires passants. Le code est propre, bien structuré, conforme à la spec §6.3–§9.2. Quelques items mineurs empêchent le verdict CLEAN : checklist de tâche incomplète, tests de bords manquants sur la normalisation, et absence de test pour le cas edge `chart_radar` valeurs égales.

---

## Phase A — Compliance

### Structure branche & commits
| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/077-wsd1-charts-library` | ✅ | `git branch --show-current` → `task/077-wsd1-charts-library` |
| Commit RED présent | ✅ | `7c067fa` — `[WS-D-1] #077 RED: tests bibliothèque graphiques Plotly` |
| Commit GREEN présent | ✅ | `7cb14cd` — `[WS-D-1] #077 GREEN: bibliothèque graphiques Plotly` |
| RED contient uniquement tests | ✅ | `git show --stat 7c067fa` → `tests/test_dashboard_charts.py` (536 ins) |
| GREEN contient implémentation + tâche | ✅ | `git show --stat 7cb14cd` → `scripts/dashboard/charts.py` (513 ins), `docs/tasks/...` (67 ins), `tests/...` (1 del) |
| Pas de commits parasites | ✅ | `git log --oneline` → 2 commits exactement (RED puis GREEN) |

### Tâche
| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Ligne 3 du fichier de tâche : `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (10/10) | Tous les critères `[x]` dans la section « Critères d'acceptation » |
| Checklist cochée | ❌ (7/9) | 2 items non cochés : « Commit GREEN » et « Pull Request ouverte » — le commit GREEN existe pourtant (`7cb14cd`) |

### CI
| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_charts.py -v --tb=short` | **38 passed**, 0 failed (0.56s) |
| `ruff check scripts/dashboard/charts.py tests/test_dashboard_charts.py` | **All checks passed** |

> Phase A : PASS (item checklist mineur, ne bloque pas Phase B).

---

## Phase B — Code Review

### B1 — Résultats du scan automatisé (GREP)

| # | Pattern recherché | Commande | Résultat | Analyse |
|---|---|---|---|---|
| 1 | §R1 Fallbacks silencieux | `grep -n ' or \[\]...\| if .* else '` | 2 matches (L159, L392) | **Faux positif** : ternaires pour attribution de couleur, pas de fallback silencieux |
| 2 | §R1 Except trop large | `grep -n 'except:$\|except Exception:'` | 0 occurrences | ✅ |
| 3 | §R7 noqa | `grep -rn 'noqa'` | 0 occurrences | ✅ |
| 4 | §R7 per-file-ignores | `grep pyproject.toml` | Aucune entrée pour `charts.py` ni `test_dashboard_charts.py` | ✅ |
| 5 | §R7 Print résiduel | `grep -n 'print('` | 0 occurrences | ✅ |
| 6 | §R3 Shift négatif | `grep -n '.shift(-'` | 0 occurrences | ✅ |
| 7 | §R4 Legacy random | `grep -rn 'np.random.seed...'` | 0 occurrences | ✅ |
| 8 | §R7 TODO/FIXME | `grep -rn 'TODO\|FIXME'` | 0 occurrences | ✅ |
| 9 | §R7 Chemins hardcodés | `grep -n '/tmp\|C:\\'` (tests) | 0 occurrences | ✅ |
| 10 | §R7 Imports absolus `__init__` | `grep -rn 'from ai_trading\.'` | 0 occurrences (N/A) | ✅ |
| 11 | §R7 Registration manuelle tests | `grep -rn 'register_model\|register_feature'` | 0 occurrences (N/A) | ✅ |
| 12 | §R6 Mutable defaults | `grep -rn 'def.*=\[\]\|def.*={}'` | 0 occurrences | ✅ |
| 13 | §R6 open() sans context manager | `grep -rn '.read_text\|open('` | 0 occurrences | ✅ |
| 14 | §R6 Bool identity | `grep -rn 'is True\|is False'` | 1 match (L45) | **Faux positif** : dans une docstring, pas du code exécutable |
| 15 | §R6 Dict collision | `grep -rn '\[.*\] = '` | 3 matches (L309, L315, L317) | **Faux positif** : `normalized[axis]` itère sur clés uniques du dict `raw` (axes fixes) |
| 16 | §R9 Loop sur array numpy | `grep -rn 'for .* in range'` | 0 occurrences | ✅ |
| 17 | §R6 isfinite | `grep -rn 'isfinite'` | 0 occurrences | N/A (module de visualisation, pas de validation numérique d'entrée) |
| 18 | §R9 numpy comprehension | `grep -rn 'np\.[a-z]*(.*for .* in '` | 0 occurrences | ✅ |
| 19 | §R7 Fixtures dupliquées | `grep -rn 'load_config.*configs/'` | 0 occurrences | ✅ |
| 20 | §R6 `.values` perdant l'index | `grep -rn '.values'` | 1 match (L263) | **Faux positif** : `norm_eq.values` dans `chart_equity_overlay`, l'index n'est pas pertinent pour le `y` de Plotly |

### B2 — Annotations par fichier

#### `scripts/dashboard/charts.py` (513 lignes)

- **L55** `eq_start = df["equity"].iloc[0]` puis `norm_equity = df["equity"] / eq_start` : division par `equity[0]`. Si `equity[0] == 0`, `ZeroDivisionError`. Le domaine métier garantit `equity > 0` (capital initial), mais aucune validation explicite.
  Sévérité : **MINEUR**
  Suggestion : ajouter un guard `if eq_start == 0: raise ValueError("equity[0] must be > 0 for normalization")` ou documenter la pré-condition.

- **L259-263** `eq = curve_df["equity"]; norm_eq = eq / eq.iloc[0]` : même pattern de division dans `chart_equity_overlay`. Même risque théorique.
  Sévérité : **MINEUR**
  Suggestion : même guard ou pré-condition documentée.

- **L159** `colors = [COLOR_PROFIT if p > 0 else COLOR_LOSS for p in pnls]` : un PnL de 0 exactement est coloré en rouge (LOSS). Comportement acceptable (0 n'est pas un profit) mais non documenté.
  Sévérité : RAS (convention acceptable, signalé pour traçabilité)

- **L306-317** Min-max normalization dans `chart_radar` : le cas `mx - mn < 1e-12` (toutes valeurs égales) est correctement géré avec 0.5. Bon traitement du cas dégénéré.
  Sévérité : RAS

- **L388-392** `go_mask = np.abs(y_hat) >= theta` : Go/No-Go basé sur `|ŷ| ≥ θ`. Conforme §8.3.
  Sévérité : RAS

- **L487** `time_to_eq = dict(zip(df["time_utc"], df["equity"], strict=True))` : si `time_utc` contient des doublons, le dict les écraserait silencieusement. En pratique, les timestamps d'une equity curve sont uniques, mais aucune validation explicite.
  Sévérité : **MINEUR**
  Suggestion : ajouter un assert `len(time_to_eq) == len(df)` après la construction du dict, ou documenter la pré-condition.

- **L492-494** `entry_eq = [time_to_eq.get(t) for t in entry_times]` puis filtrage des None : traitement correct du cas où un timestamp de trade ne correspond pas exactement à un timestamp de l'equity curve. Bon pattern défensif.
  Sévérité : RAS

#### `tests/test_dashboard_charts.py` (535 lignes)

- **Tests `chart_equity_curve`** (8 tests) : couverture solide. Fold boundaries on/off, drawdown on/off, in_trade zones, single fold. Pas de test avec `equity[0] == 0` mais ce cas est un invariant de domaine.
  Sévérité : RAS

- **Tests `chart_pnl_bar`** (4 tests) : couvre figure valide, nombre de barres, couleurs profit/loss, liste vide.
  Sévérité : RAS

- **Tests `chart_returns_histogram`** (3 tests) : couvre figure valide, trace histogram, DataFrame vide.
  Sévérité : RAS

- **Tests `chart_returns_boxplot`** (3 tests) : couvre figure valide, un box par fold, single fold. **Pas de test avec DataFrame vide** (contrairement à `chart_returns_histogram` qui en a un).
  Sévérité : **MINEUR**
  Suggestion : ajouter un test `test_empty_trades` similaire à celui de `TestChartReturnsHistogram`.

- **Tests `chart_equity_overlay`** (5 tests) : couvre figure, trace count, normalisation à 1.0, légende, dict vide.
  Sévérité : RAS

- **Tests `chart_radar`** (5 tests) : couvre figure, trace count, 5 axes, valeurs normalisées [0,1], single run. **Pas de test vérifiant le cas « toutes valeurs égales → 0.5 »** (le code le gère L313-315, mais aucun test ne l'exerce).
  Sévérité : **MINEUR**
  Suggestion : ajouter un test `test_equal_values_normalize_to_half` avec des runs ayant des métriques identiques.

- **Tests `chart_scatter_predictions`** (5 tests) : couvre figure, scatter traces, diagonal line, method "none" annotation, method "none" no scatter.
  Sévérité : RAS

- **Tests `chart_fold_equity`** (5 tests) : couvre figure, equity line, entry ▲ green, exit ▼ red, empty trades.
  Sévérité : RAS

### B3 — Tests
| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères d'acceptation | ✅ | Chaque critère de la tâche est couvert par au moins 1 test (mapping ci-dessous) |
| Cas nominaux + erreurs + bords | ⚠️ | Cas nominaux bien couverts, cas vides testés pour la plupart, manque boxplot vide et radar valeurs égales |
| Boundary fuzzing | ✅ | N/A (pas de paramètres numériques de borne dans les fonctions) |
| Déterministes | ✅ | Seeds `np.random.default_rng(42)` dans toutes les fixtures |
| Portabilité chemins | ✅ | Scan B1 #9 : 0 `/tmp` hardcodé |
| Tests registre réalistes | N/A | — |
| Contrat ABC complet | N/A | — |

**Mapping critères → tests :**
| Critère | Tests |
|---|---|
| Chaque fn retourne `go.Figure` | `test_returns_figure` dans chaque classe (8 tests) |
| Couleurs §9.2 | `test_colors_profit_loss`, `test_entry_markers`, `test_exit_markers` |
| Fold boundaries par changement `fold` | `test_fold_boundaries_present`, `test_single_fold_no_boundary` |
| Drawdown ombré | `test_drawdown_trace`, `test_drawdown_disabled` |
| Zones in_trade | `test_in_trade_zones` |
| Overlay normalisation 1.0 | `test_normalization_starts_at_one` |
| Overlay légende cliquable | `test_legend_present` (vérifie noms, layout legend toggle vérifié en code) |
| Radar 5 axes | `test_five_axes` |
| Radar normalisation min-max | `test_values_normalized_0_1` |
| Scatter Go/No-Go | `test_has_scatter_traces` |
| Scatter method "none" | `test_signal_method_returns_annotation`, `test_signal_method_no_scatter` |
| Fold equity ▲/▼ | `test_entry_markers`, `test_exit_markers` |

### B4 — Code — Règles non négociables
| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 #1-2 : 0 fallback réel (2 faux positifs ternaires) |
| §R10 Defensive indexing | ✅ | Lecture diff : pas de slicing risqué |
| §R2 Config-driven | ✅ | Couleurs importées depuis `utils.py` (§9.2). Pas de paramètre config YAML nécessaire |
| §R3 Anti-fuite | N/A | Module de visualisation, pas d'accès aux données ML |
| §R4 Reproductibilité | N/A | Module de visualisation |
| §R5 Float conventions | N/A | Module de visualisation |
| §R6 Anti-patterns Python | ✅ | Scan B1 #12-20 : 0 anti-pattern. Pas de mutable default, pas d'open(), pas de float ==, pas de boucle numpy |

### B5 — Qualité du code
| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes les fonctions et variables en snake_case |
| Pas de code mort/debug | ✅ | Scan B1 #5 (print), #8 (TODO) : 0 occurrence |
| Imports propres / relatifs | ✅ | Import depuis `scripts.dashboard.utils` correct. Pas d'import `*` ni inutilisé |
| DRY | ✅ | Pas de duplication de logique entre fonctions |
| Pas de fichiers générés | ✅ | Seulement `.py` et `.md` dans le diff |

### B5-bis — Bonnes pratiques métier
| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Equity normalisée, drawdown running max, PnL par fold — concepts corrects |
| Nommage métier cohérent | ✅ | `equity`, `drawdown`, `net_pnl`, `hit_rate`, `profit_factor`, `net_return` |
| Séparation des responsabilités | ✅ | Module dédié aux graphiques, ne calcule rien |
| Invariants de domaine | ✅ | (Sauf equity[0]>0 non validé — MINEUR signalé en B2) |
| Cohérence unités/échelles | ✅ | Tout normalisé à 1.0 où spécifié, radar normalisé min-max |
| Patterns de calcul financier | ✅ | Utilise `np.abs`, pandas natif, pas de boucle Python |

### B6 — Conformité spec v1.0
| Critère | Verdict | Preuve |
|---|---|---|
| §6.3 equity curve stitchée | ✅ | Normalisation, fold boundaries, drawdown, in_trade zones |
| §6.4 PnL bar chart | ✅ | Bar chart vert/rouge par fold |
| §6.5 histogramme + boxplot | ✅ | Histogram des rendements + boxplot par fold |
| §7.3 overlay multi-runs | ✅ | Normalisation 1.0, légende cliquable (toggle/toggleothers) |
| §7.4 radar 5 axes | ✅ | 5 axes corrects, min-max normalisé, 1−MDD inversé |
| §8.2 fold equity | ✅ | Marqueurs ▲ vert / ▼ rouge |
| §8.3 scatter predictions | ✅ | Go/No-Go par |ŷ|≥θ, fallback annotation pour method "none" |
| §9.2 palette couleurs | ✅ | 5 couleurs importées depuis `utils.py` |
| Plan d'implémentation | ✅ | WS-D-1.5 conforme |
| Formules doc vs code | ✅ | Normalisation `equity/equity[0]`, drawdown `running_max - equity`, min-max `(v-min)/(max-min)` |

### B7 — Cohérence intermodule
| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | Toutes les fonctions → `go.Figure`, signatures conformes à la tâche |
| Noms de colonnes DataFrame | ✅ | `time_utc`, `equity`, `in_trade`, `fold`, `net_return`, `y_true`, `y_hat`, `entry_time_utc`, `exit_time_utc` — cohérents avec le reste du pipeline |
| Clés de configuration | N/A | Pas de lecture de config YAML |
| Registres | N/A | — |
| Structures de données partagées | ✅ | `fold_metrics: list[dict]` avec `fold` + `net_pnl` — interface simple et claire |
| Conventions numériques | ✅ | Pas de contrainte dtype dans un module de visualisation |
| Imports croisés | ✅ | Seul import externe : `scripts.dashboard.utils` (existe dans `Max6000i1`) |

---

## Remarques

1. **[MINEUR]** Checklist de tâche incomplète : 2 items non cochés (`Commit GREEN`, `Pull Request ouverte`).
   - Fichier : `docs/tasks/MD-1/077__wsd1_charts_library.md`
   - Ligne(s) : checklist fin de tâche (avant-dernière et dernière lignes)
   - Suggestion : cocher `[x]` le Commit GREEN (qui existe : `7cb14cd`). L'item PR sera coché à l'ouverture de la PR.

2. **[MINEUR]** `chart_equity_curve` L55 : division par `df["equity"].iloc[0]` sans guard contre zéro.
   - Fichier : `scripts/dashboard/charts.py`
   - Ligne(s) : 55
   - Suggestion : ajouter `if eq_start == 0: raise ValueError(...)` ou documenter la pré-condition dans la docstring.

3. **[MINEUR]** `chart_equity_overlay` L259-260 : même pattern de division non protégée.
   - Fichier : `scripts/dashboard/charts.py`
   - Ligne(s) : 259-260
   - Suggestion : même correction que #2.

4. **[MINEUR]** `chart_fold_equity` L487 : `dict(zip(...))` sur `time_utc` pourrait écraser silencieusement des entrées en cas de doublons.
   - Fichier : `scripts/dashboard/charts.py`
   - Ligne(s) : 487
   - Suggestion : ajouter `assert len(time_to_eq) == len(df), "duplicate time_utc"` ou documenter la pré-condition d'unicité.

5. **[MINEUR]** Test manquant : `chart_returns_boxplot` avec DataFrame vide (le test `chart_returns_histogram.test_empty_trades` existe mais pas son équivalent pour boxplot).
   - Fichier : `tests/test_dashboard_charts.py`
   - Suggestion : ajouter `test_empty_trades` dans `TestChartReturnsBoxplot`.

6. **[MINEUR]** Test manquant : `chart_radar` avec toutes les valeurs égales.
   - Fichier : `tests/test_dashboard_charts.py`
   - Suggestion : ajouter `test_equal_values_normalize_to_half` vérifiant que toutes les valeurs r sont 0.5 quand les métriques sont identiques pour tous les runs.

## Résumé

Implémentation de bonne qualité : 8 fonctions Plotly conformes à la spec, 38 tests passants, code propre sans anti-pattern. 6 items mineurs identifiés (checklist incomplète, divisions non protégées, tests de bords manquants). Aucun bloquant, aucun warning.

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 6
- Rapport : `docs/tasks/MD-1/077/review_v1.md`
