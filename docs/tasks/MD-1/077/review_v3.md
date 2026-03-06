# Revue PR — [WS-D-1] #077 — Bibliothèque de graphiques Plotly (v3)

Branche : `task/077-wsd1-charts-library`
Tâche : `docs/tasks/MD-1/077__wsd1_charts_library.md`
Date : 2026-03-05
Itération : v3 (post-correction review v2 — scatter axes inversés §8.3)

## Verdict global : ✅ CLEAN

## Résumé

L'unique item mineur de la v2 (axes du scatter plot inversés par rapport à §8.3) est correctement corrigé dans le commit `b71046e`. Le code place désormais ŷ sur l'axe X et y_true sur l'axe Y, conformément à la spec. Un test dédié `test_axes_labels_per_spec` vérifie les titres d'axes. 41 tests passent, ruff clean, aucun nouvel item détecté.

---

## Phase A — Compliance

### Structure branche & commits
| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/077-wsd1-charts-library` | ✅ | `git branch --show-current` → `task/077-wsd1-charts-library` |
| Commit RED présent | ✅ | `7c067fa` — `[WS-D-1] #077 RED: tests bibliothèque graphiques Plotly` |
| Commit GREEN présent | ✅ | `7cb14cd` — `[WS-D-1] #077 GREEN: bibliothèque graphiques Plotly` |
| RED contient uniquement tests | ✅ | `git show --stat 7c067fa` → `tests/test_dashboard_charts.py` uniquement (536 insertions) |
| GREEN contient implémentation + tâche | ✅ | `git show --stat 7cb14cd` → `scripts/dashboard/charts.py` (513+), `docs/tasks/...` (67+), `tests/...` (1-) |
| Pas de commits parasites entre RED/GREEN | ✅ | 4 commits : RED → GREEN → FIX v1 → FIX v2 (post-review) |
| Commit FIX v1 | ✅ | `21a71fa` — `[WS-D-1] #077 FIX: guards division par 0, assertion doublons time_utc, tests boxplot vide et radar valeurs égales, checklist tâche` |
| Commit FIX v2 | ✅ | `b71046e` — `[WS-D-1] #077 FIX: scatter plot axes inverted — ŷ on X, y_true on Y per §8.3` |

### Tâche
| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | Ligne 3 du fichier de tâche |
| Critères d'acceptation cochés | ✅ (10/10) | Tous `[x]` |
| Checklist cochée | ✅ (8/9) | Seul « Pull Request ouverte » non coché — normal avant ouverture effective |

### CI
| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_charts.py -v --tb=short` | **41 passed**, 0 failed (0.44s) |
| `ruff check scripts/dashboard/charts.py tests/test_dashboard_charts.py` | **All checks passed** |

> Phase A : PASS.

---

## Phase B — Code Review

### B1 — Résultats du scan automatisé (GREP)

| # | Pattern recherché | Règle | Résultat | Analyse |
|---|---|---|---|---|
| 1 | Fallbacks silencieux | §R1 | 2 matches (L161, L399) | **Faux positif** : ternaires pour attribution de couleur (`COLOR_PROFIT if p > 0 else COLOR_LOSS`), pas de fallback silencieux |
| 2 | Except trop large | §R1 | 0 occurrences (grep exécuté) | ✅ |
| 3 | noqa | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 4 | Print résiduel | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 5 | Shift négatif | §R3 | 0 occurrences (grep exécuté) | ✅ |
| 6 | Legacy random API | §R4 | 0 occurrences (grep exécuté) | ✅ |
| 7 | TODO/FIXME/HACK/XXX | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 8 | Chemins hardcodés (tests) | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 9 | Imports absolus `__init__` | §R7 | N/A (pas de `__init__.py` modifié) | ✅ |
| 10 | Registration manuelle tests | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 11 | Mutable defaults | §R6 | 0 occurrences (grep exécuté) | ✅ |
| 12 | open() sans context manager | §R6 | 0 occurrences (grep exécuté) | ✅ |
| 13 | Bool identity (`is True/False`) | §R6 | 1 match (L45) | **Faux positif** : dans une docstring (`is True`), pas du code exécutable |
| 14 | Dict collision (`[x] = `) | §R6 | 3 matches (L316, L322, L324) | **Faux positif** : `normalized[axis]` itère sur clés uniques du dict `raw` (5 axes fixes prédéfinis dans `_RADAR_AXES`) |
| 15 | Loop `for range` | §R9 | 0 occurrences (grep exécuté) | ✅ |
| 16 | `.values` | §R6 | 1 match (L270) | **Faux positif** : `norm_eq.values` dans `chart_equity_overlay`, l'index pandas n'est pas pertinent pour le `y` de Plotly |
| 17 | isfinite | §R6 | 0 occurrences | N/A (module de visualisation, pas de validation numérique de paramètres d'entrée) |
| 18 | numpy comprehension | §R9 | 0 occurrences (grep exécuté) | ✅ |
| 19 | Fixtures dupliquées | §R7 | 0 occurrences (grep exécuté) | ✅ |
| 20 | per-file-ignores | §R7 | L52 pyproject.toml | Existant, non modifié par cette branche |

### B2 — Annotations par fichier

#### `scripts/dashboard/charts.py` (529 lignes)

**Vérification de la correction v2 :**

- **L402-408** (v2 item #1 — CORRIGÉ ✅) : `x=y_hat, y=y_true` — les données du scatter plot placent désormais ŷ sur l'axe X et y_true sur l'axe Y.
  - Preuve programmatique : `scatter.x == y_hat` → `True`, `scatter.y == y_true` → `True`.

- **L418-419** (v2 item #1 — CORRIGÉ ✅) : `xaxis_title="ŷ"`, `yaxis_title="y_true"` — labels conformes à §8.3 (`$\hat{y}_t$ (axe X) vs $y_t$ (axe Y)`).

- RAS sur le reste du fichier (inchangé depuis v2, déjà audité en v1 et v2).

#### `tests/test_dashboard_charts.py` (584 lignes)

- **L507-513** (NOUVEAU) : `test_axes_labels_per_spec` — test dédié vérifiant `fig.layout.xaxis.title.text == "ŷ"` et `fig.layout.yaxis.title.text == "y_true"`. Couverture exacte de la correction. ✅

- RAS sur les 40 tests existants (inchangés depuis v2).

#### `docs/tasks/MD-1/077__wsd1_charts_library.md`

- Non modifié dans le commit FIX v2. Tâche déjà à jour depuis FIX v1. ✅

### B3 — Tests
| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères d'acceptation | ✅ | Chaque critère couvert + test axes labels ajouté pour §8.3 |
| Cas nominaux + erreurs + bords | ✅ | Boxplot vide, radar valeurs égales, empty trades, single fold, empty metrics, signal method, axes labels |
| Boundary fuzzing | ✅ | N/A (pas de paramètres numériques de borne dans les fonctions de visualisation) |
| Déterministes | ✅ | Seeds `np.random.default_rng(42)` dans toutes les fixtures |
| Portabilité chemins | ✅ | Scan B1 #8 : 0 `/tmp` hardcodé |
| Tests registre réalistes | N/A | — |
| Contrat ABC complet | N/A | — |

### B4 — Code — Règles non négociables
| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 #1-2 : 0 fallback réel (2 faux positifs ternaires) |
| §R10 Defensive indexing | ✅ | Lecture diff : pas de slicing risqué. Guards division/doublons en place |
| §R2 Config-driven | ✅ | Couleurs importées depuis `utils.py`. Pas de paramètre config YAML requis |
| §R3 Anti-fuite | N/A | Module de visualisation |
| §R4 Reproductibilité | N/A | Module de visualisation |
| §R5 Float conventions | N/A | Module de visualisation |
| §R6 Anti-patterns Python | ✅ | Scan B1 #11-18 : 0 anti-pattern réel (faux positifs analysés) |

### B5 — Qualité du code
| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Toutes fonctions/variables en snake_case |
| Pas de code mort/debug | ✅ | Scan B1 #4 (print), #7 (TODO) : 0 occurrence |
| Imports propres / relatifs | ✅ | Import `from scripts.dashboard.utils` correct. Pas d'import `*` ni inutilisé |
| DRY | ✅ | Pas de duplication de logique entre fonctions |
| Pas de fichiers générés | ✅ | Uniquement `.py` et `.md` dans le diff |

### B5-bis — Bonnes pratiques métier
| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Equity normalisée, drawdown running_max, PnL par fold, radar 1−MDD — corrects |
| Nommage métier cohérent | ✅ | `equity`, `drawdown`, `net_pnl`, `hit_rate`, `profit_factor`, `net_return` |
| Séparation des responsabilités | ✅ | Module dédié aux graphiques, ne calcule pas de métriques |
| Invariants de domaine | ✅ | Guards `equity[0] > 0`, assertion unicité `time_utc` |
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
| §8.2 fold equity | ✅ | Marqueurs ▲ vert / ▼ rouge |
| §8.3 scatter predictions | ✅ | **Corrigé v3** : `x=y_hat, y=y_true`, `xaxis_title="ŷ"`, `yaxis_title="y_true"` — conforme à « $\hat{y}_t$ (axe X) vs $y_t$ (axe Y) ». Vérifié programmatiquement. |
| §9.2 palette couleurs | ✅ | 5 constantes utilisées importées de `utils.py` (COLOR_PROFIT, COLOR_LOSS, COLOR_NEUTRAL, COLOR_DRAWDOWN, COLOR_FOLD_BORDER) |
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

## Vérification correction v2

| # v2 | Description | Statut v3 | Preuve |
|---|---|---|---|
| 1 | Scatter plot axes inversés (§8.3) | ✅ CORRIGÉ | Diff `b71046e` : `x=y_hat, y=y_true`, `xaxis_title="ŷ"`, `yaxis_title="y_true"`. Test `test_axes_labels_per_spec` ajouté et passant. Vérification programmatique : `scatter.x == y_hat` → True, `scatter.y == y_true` → True. |

**1/1 correction appliquée correctement.**

---

## Remarques

Aucune remarque. Tous les items des reviews v1 et v2 sont correctement corrigés. Le code est propre, 41 tests passent, ruff clean, conformité spec complète.

---

RÉSULTAT PARTIE B :
- Verdict : CLEAN
- Bloquants : 0
- Warnings : 0
- Mineurs : 0
- Rapport : `docs/tasks/MD-1/077/review_v3.md`
