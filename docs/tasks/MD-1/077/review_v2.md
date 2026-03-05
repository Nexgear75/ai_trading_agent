# Revue PR — [WS-D-1] #077 — Bibliothèque de graphiques Plotly (v2)

Branche : `task/077-wsd1-charts-library`
Tâche : `docs/tasks/MD-1/077__wsd1_charts_library.md`
Date : 2026-03-05
Itération : v2 (post-corrections review v1)

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Toutes les 6 corrections demandées en v1 sont correctement appliquées dans le commit FIX (`21a71fa`). Guards division par zéro, assertion doublons `time_utc`, tests boxplot vide et radar valeurs égales sont en place. 40 tests passent (vs 38 en v1). Un nouvel item MINEUR détecté : l'assignation des axes du scatter plot (§8.3) est inversée par rapport à la spécification (y_true sur X au lieu de ŷ sur X).

---

## Phase A — Compliance

### Structure branche & commits
| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/077-wsd1-charts-library` | ✅ | `git branch --show-current` → `task/077-wsd1-charts-library` |
| Commit RED présent | ✅ | `7c067fa` — `[WS-D-1] #077 RED: tests bibliothèque graphiques Plotly` |
| Commit GREEN présent | ✅ | `7cb14cd` — `[WS-D-1] #077 GREEN: bibliothèque graphiques Plotly` |
| RED contient uniquement tests | ✅ | `git show --stat 7c067fa` → `tests/test_dashboard_charts.py` uniquement |
| GREEN contient implémentation + tâche | ✅ | `git show --stat 7cb14cd` → `scripts/dashboard/charts.py`, `docs/tasks/...`, `tests/...` |
| Pas de commits parasites entre RED/GREEN | ✅ | 3 commits : RED → GREEN → FIX (post-review) |
| Commit FIX post-review | ✅ | `21a71fa` — `[WS-D-1] #077 FIX: guards division par 0, assertion doublons time_utc, tests boxplot vide et radar valeurs égales, checklist tâche` |

### Tâche
| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Ligne 3 du fichier de tâche |
| Critères d'acceptation cochés | ✅ (10/10) | Tous `[x]` |
| Checklist cochée | ✅ (8/9) | Seul « Pull Request ouverte » non coché — normal avant ouverture effective de la PR |

### CI
| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_charts.py -v --tb=short` | **40 passed**, 0 failed (0.51s) |
| `ruff check scripts/dashboard/charts.py tests/test_dashboard_charts.py` | **All checks passed** |

> Phase A : PASS.

---

## Phase B — Code Review

### B1 — Résultats du scan automatisé (GREP)

| # | Pattern recherché | Règle | Résultat | Analyse |
|---|---|---|---|---|
| 1 | Fallbacks silencieux | §R1 | 2 matches (L161, L399) | **Faux positif** : ternaires pour attribution de couleur (`COLOR_PROFIT if p > 0 else COLOR_LOSS`), pas de fallback silencieux |
| 2 | Except trop large | §R1 | 0 occurrences | ✅ |
| 3 | noqa | §R7 | 0 occurrences | ✅ |
| 4 | Print résiduel | §R7 | 0 occurrences | ✅ |
| 5 | Shift négatif | §R3 | 0 occurrences | ✅ |
| 6 | Legacy random API | §R4 | 0 occurrences | ✅ |
| 7 | TODO/FIXME/HACK/XXX | §R7 | 0 occurrences | ✅ |
| 8 | Chemins hardcodés (tests) | §R7 | 0 occurrences | ✅ |
| 9 | Mutable defaults | §R6 | 0 occurrences | ✅ |
| 10 | open() sans context manager | §R6 | 0 occurrences | ✅ |
| 11 | Bool identity (`is True/False`) | §R6 | 1 match (L45) | **Faux positif** : dans une docstring (`is True`), pas du code exécutable |
| 12 | Dict collision (`[x] = `) | §R6 | 3 matches (L316, L322, L324) | **Faux positif** : `normalized[axis]` itère sur clés uniques du dict `raw` (5 axes fixes prédéfinis dans `_RADAR_AXES`) |
| 13 | Loop `for range` | §R9 | 0 occurrences | ✅ |
| 14 | `.values` | §R6 | 1 match (L270) | **Faux positif** : `norm_eq.values` dans `chart_equity_overlay`, l'index pandas n'est pas pertinent pour le `y` de Plotly |
| 15 | isfinite | §R6 | 0 occurrences | N/A (module de visualisation, pas de validation numérique de paramètres d'entrée) |
| 16 | numpy comprehension | §R9 | 0 occurrences | ✅ |
| 17 | Fixtures dupliquées | §R7 | 0 occurrences | ✅ |
| 18 | Registration manuelle tests | §R7 | 0 occurrences (N/A) | ✅ |
| 19 | Imports absolus `__init__` | §R7 | 0 occurrences (N/A) | ✅ |

### B2 — Annotations par fichier

#### `scripts/dashboard/charts.py` (524 lignes)

**Vérification des corrections v1 :**

- **L50-51** (v1 item #2 — CORRIGÉ ✅) : `if eq_start == 0: raise ValueError("equity[0] must be > 0 for normalization")` — guard division par zéro ajouté dans `chart_equity_curve`.

- **L261-264** (v1 item #3 — CORRIGÉ ✅) : `if eq_start == 0: raise ValueError(...)` — guard ajouté dans `chart_equity_overlay` avec message incluant le label du run.

- **L475-476** (v1 item #4 — CORRIGÉ ✅) : `if len(time_to_eq) != len(df): raise ValueError("duplicate time_utc in equity DataFrame")` — assertion ajoutée après construction du dict.

**Nouvelles observations :**

- **L401-408** `go.Scatter(x=y_true, y=y_hat, ...)` + L418-419 `xaxis_title="y_true", yaxis_title="y_hat"` : la spec §8.3 définit « $\hat{y}_t$ (axe X) vs $y_t$ (axe Y) », ce qui place ŷ sur l'axe X et y sur l'axe Y. Le code fait l'inverse (y_true sur X, y_hat sur Y). La convention du code est standard en ML, mais diverge de la lettre de la spec.
  Sévérité : **MINEUR**
  Suggestion : inverser les axes pour coller à la spec (`x=y_hat, y=y_true`, `xaxis_title="ŷ"`, `yaxis_title="y_true"`), ou clarifier la spec si la convention ML standard est préférée. Note : le test `test_diagonal_line` resterait valide (diagonale x0=v_min..x1=v_max), et `go_mask` est indépendant de l'assignation d'axes.

- Tous les autres fonctions/hunks : RAS après lecture complète du diff (524 lignes source, 576 lignes tests).

#### `tests/test_dashboard_charts.py` (576 lignes)

**Vérification des corrections v1 :**

- **L314-323** (v1 item #5 — CORRIGÉ ✅) : `TestChartReturnsBoxplot::test_empty_trades` ajouté — crée un DataFrame vide avec colonnes `net_return` et `fold`, vérifie `isinstance(fig, go.Figure)` et 0 box traces.

- **L427-458** (v1 item #6 — CORRIGÉ ✅) : `TestChartRadar::test_equal_values_normalize_to_half` ajouté — 2 runs avec métriques identiques, vérifie que toutes les valeurs r sont `pytest.approx(0.5)`.

- RAS sur les 40 tests existants après lecture complète.

#### `docs/tasks/MD-1/077__wsd1_charts_library.md`

- (v1 item #1 — CORRIGÉ ✅) : ligne checklist « Commit GREEN » cochée `[x]`.
- Seul item restant non coché : « Pull Request ouverte » — attendu avant ouverture.

### B3 — Tests
| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères d'acceptation | ✅ | Chaque critère couvert (mapping inchangé vs v1, +2 tests edge) |
| Cas nominaux + erreurs + bords | ✅ | Boxplot vide et radar valeurs égales ajoutés — tous les cas de bords pertinents couverts |
| Boundary fuzzing | ✅ | N/A (pas de paramètres numériques de borne dans les fonctions) |
| Déterministes | ✅ | Seeds `np.random.default_rng(42)` dans toutes les fixtures |
| Portabilité chemins | ✅ | Scan B1 #8 : 0 `/tmp` hardcodé |
| Tests registre réalistes | N/A | — |
| Contrat ABC complet | N/A | — |

### B4 — Code — Règles non négociables
| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 #1-2 : 0 fallback réel (2 faux positifs ternaires) |
| §R10 Defensive indexing | ✅ | Lecture diff : pas de slicing risqué. Guards ajoutés pour division/doublons |
| §R2 Config-driven | ✅ | Couleurs importées depuis `utils.py`. Pas de paramètre config YAML requis |
| §R3 Anti-fuite | N/A | Module de visualisation |
| §R4 Reproductibilité | N/A | Module de visualisation |
| §R5 Float conventions | N/A | Module de visualisation |
| §R6 Anti-patterns Python | ✅ | Scan B1 #9-14 : 0 anti-pattern réel (faux positifs analysés) |

### B5 — Qualité du code
| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes fonctions/variables en snake_case |
| Pas de code mort/debug | ✅ | Scan B1 #4 (print), #7 (TODO) : 0 occurrence |
| Imports propres / relatifs | ✅ | Import `from scripts.dashboard.utils` correct. Pas d'import `*` ni inutilisé |
| DRY | ✅ | Pas de duplication de logique entre fonctions. Le pattern guard division (L50-51 et L261-264) est acceptablement dupliqué (contexte différent, messages d'erreur distincts) |
| Pas de fichiers générés | ✅ | Uniquement `.py` et `.md` dans le diff |

### B5-bis — Bonnes pratiques métier
| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Equity normalisée, drawdown running_max, PnL par fold, radar 1−MDD — corrects |
| Nommage métier cohérent | ✅ | `equity`, `drawdown`, `net_pnl`, `hit_rate`, `profit_factor`, `net_return` |
| Séparation des responsabilités | ✅ | Module dédié aux graphiques, ne calcule pas de métriques |
| Invariants de domaine | ✅ | Guards `equity[0] > 0` ajoutés, assertion unicité `time_utc` ajoutée |
| Cohérence unités/échelles | ✅ | Normalisation à 1.0 conforme, radar min-max conforme |
| Patterns de calcul financier | ✅ | Pandas natif, pas de boucle Python sur séries |

### B6 — Conformité spec v1.0
| Critère | Verdict | Preuve |
|---|---|---|
| §6.3 equity curve stitchée | ✅ | Normalisation, fold boundaries par `fold.diff()`, drawdown ombré, zones `in_trade` |
| §6.4 PnL bar chart | ✅ | Bar chart vert/rouge par fold |
| §6.5 histogramme + boxplot | ✅ | Histogram rendements + boxplot par fold |
| §7.3 overlay multi-runs | ✅ | Normalisation 1.0, légende cliquable (toggle/toggleothers) |
| §7.4 radar 5 axes | ✅ | 5 axes corrects (Net PnL, Sharpe, 1−MDD, Win Rate, PF), min-max normalisé |
| §8.2 fold equity | ✅ | Marqueurs ▲ vert / ▼ rouge. Note : drawdown non inclus dans `chart_fold_equity` (scope tâche : la page pourrait utiliser `chart_equity_curve` pour le drawdown) |
| §8.3 scatter predictions | ⚠️ | Go/No-Go `|ŷ|≥θ` correct, annotation pour `method="none"` conforme, **mais axes inversés vs spec** (voir MINEUR #1) |
| §9.2 palette couleurs | ✅ | 6 constantes dans `utils.py` correspondent exactement aux hex §9.2 |
| Plan d'implémentation | ✅ | WS-D-1.5 conforme |
| Formules doc vs code | ✅ | `equity/equity[0]`, `running_max - equity`, `(v-min)/(max-min)` — conformes |

### B7 — Cohérence intermodule
| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | Toutes les fonctions → `go.Figure`, signatures conformes à la tâche |
| Noms de colonnes DataFrame | ✅ | `time_utc`, `equity`, `in_trade`, `fold`, `net_return`, `y_true`, `y_hat`, `entry_time_utc`, `exit_time_utc` — cohérents avec data_loader et pipeline |
| Clés de configuration | N/A | Pas de lecture de config YAML |
| Registres | N/A | — |
| Structures de données partagées | ✅ | `fold_metrics: list[dict]` avec `fold` + `net_pnl` — interface simple |
| Conventions numériques | ✅ | Pas de contrainte dtype dans un module de visualisation |
| Imports croisés | ✅ | Seul import externe : `scripts.dashboard.utils` (existe dans `Max6000i1`) |

---

## Vérification corrections v1

| # v1 | Description | Statut v2 | Preuve |
|---|---|---|---|
| 1 | Checklist « Commit GREEN » non coché | ✅ CORRIGÉ | Diff tâche : `- [ ]` → `- [x]` dans `21a71fa` |
| 2 | `chart_equity_curve` L55 division sans guard | ✅ CORRIGÉ | L50-51 : `if eq_start == 0: raise ValueError(...)` |
| 3 | `chart_equity_overlay` L259 division sans guard | ✅ CORRIGÉ | L261-264 : `if eq_start == 0: raise ValueError(...)` avec label du run |
| 4 | `chart_fold_equity` L487 dict doublons | ✅ CORRIGÉ | L475-476 : `if len(time_to_eq) != len(df): raise ValueError(...)` |
| 5 | Test boxplot vide manquant | ✅ CORRIGÉ | `TestChartReturnsBoxplot::test_empty_trades` ajouté (L314-323) |
| 6 | Test radar valeurs égales manquant | ✅ CORRIGÉ | `TestChartRadar::test_equal_values_normalize_to_half` ajouté (L427-458) |

**6/6 corrections appliquées correctement.**

---

## Remarques

1. **[MINEUR]** Scatter plot §8.3 — axes inversés par rapport à la spec.
   - Fichier : `scripts/dashboard/charts.py`
   - Ligne(s) : 401-408 (data), 418-419 (layout)
   - Spec §8.3 : « $\hat{y}_t$ (axe X) vs $y_t$ (axe Y) » → ŷ sur X, y sur Y.
   - Code : `x=y_true, y=y_hat` → y sur X, ŷ sur Y (convention ML standard, mais diverge de la spec).
   - Suggestion : inverser les axes (`x=y_hat, y=y_true`, `xaxis_title="ŷ"`, `yaxis_title="y_true"`), ou amender la spec si la convention ML est préférée.

## Résumé

Les 6 items mineurs de la review v1 sont correctement corrigés. Le code est propre, 40 tests passent, ruff clean. Un nouvel item mineur détecté : assignation des axes du scatter plot inversée par rapport à la lettre de la spec §8.3. Aucun bloquant, aucun warning.

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 0
- Mineurs : 1
- Rapport : `docs/tasks/MD-1/077/review_v2.md`
