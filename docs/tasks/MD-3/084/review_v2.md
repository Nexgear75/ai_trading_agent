# Revue PR — [WS-D-4] #084 — Page 3 : courbes d'équité superposées et radar chart

Branche : `task/084-wsd4-equity-overlay-radar`
Tâche : `docs/tasks/MD-3/084__wsd4_equity_overlay_radar.md`
Date : 2026-03-06
Itération : v2 (suite au FIX du MINEUR identifié en v1)

## Verdict global : ✅ CLEAN

## Résumé

L'item MINEUR de la v1 (docstring module `3_comparison.py` non mise à jour pour §7.3/§7.4) a été corrigé dans le commit `857c0e5`. La docstring mentionne désormais l'overlay d'equity curves, le radar chart 5 axes, et la ligne Ref inclut §7.3, §7.4, §14.4. Aucun nouveau problème détecté. Tous les scans GREP sont clean, les 2166 tests passent, ruff est sans erreur.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/084-*` | ✅ | `git branch --show-current` → `task/084-wsd4-equity-overlay-radar` |
| Commit RED présent | ✅ | `9113f93` — `[WS-D-4] #084 RED: tests overlay equity et radar chart` |
| Commit RED = tests uniquement | ✅ | `git show --stat 9113f93` → `tests/test_dashboard_comparison.py | 248 +++` (1 seul fichier) |
| Commit GREEN présent | ✅ | `2a96055` — `[WS-D-4] #084 GREEN: page comparaison — overlay equity et radar` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 2a96055` → 3 fichiers : tâche md, `3_comparison.py`, `comparison_logic.py` |
| Pas de commits parasites entre RED et GREEN | ✅ | `git log --oneline 9113f93..2a96055` → 1 seul commit (GREEN) |
| Commit FIX post-review v1 | ✅ | `857c0e5` — `[WS-D-4] #084 FIX: docstring module 3_comparison.py` → 1 fichier, docstring uniquement |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | `Statut : DONE` dans le fichier de tâche |
| Critères d'acceptation cochés | ✅ (7/7) | Tous `[x]` — vérification croisée ci-dessous |
| Checklist cochée | ✅ (8/9) | Seul le dernier item (PR ouverte) non coché — attendu |

**Vérification croisée des critères d'acceptation :**

| AC | Code/Test prouvant la satisfaction |
|---|---|
| Courbes d'équité superposées normalisées à 1.0 avec légende interactive | `3_comparison.py:154` → `chart_equity_overlay(curves)`, `charts.py:249-289` normalise par `eq / eq_start`, légende `itemclick: toggle` |
| Radar chart 5 axes avec normalisation min-max correcte | `comparison_logic.py:270-308` → extraction 5 métriques, `chart_radar()` L291-340 normalisation min-max |
| Dégradation si equity curves partiellement absentes | `3_comparison.py:149-152` → `if missing_labels: st.info(...)`, radar affiché indépendamment |
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

### Vérification du FIX v1

Le commit `857c0e5` corrige l'unique item MINEUR de la review v1 :

| Item v1 | Statut v2 | Preuve |
|---|---|---|
| Docstring module `3_comparison.py` manquant §7.3/§7.4 | ✅ Corrigé | `git diff 2a96055...857c0e5` → L1-8 : description inclut « overlay d'equity curves normalisées, radar chart 5 axes », Ref inclut « §7.3 equity overlay, §7.4 radar chart, §14.4 critères pipeline » |

### Résultats du scan automatisé (B1)

Scans exécutés sur les fichiers modifiés : `scripts/dashboard/pages/3_comparison.py`, `scripts/dashboard/pages/comparison_logic.py`, `tests/test_dashboard_comparison.py`.

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 — Fallbacks silencieux | `grep ' or []\| or {}...'` SRC | 0 occurrences (grep exécuté) |
| §R1 — Except trop large | `grep 'except:$\|except Exception:'` SRC | 0 occurrences (grep exécuté) |
| §R7 — noqa | `grep 'noqa'` ALL | 0 occurrences (grep exécuté) |
| §R7 — Print résiduel | `grep 'print('` SRC | 0 occurrences (grep exécuté) |
| §R3 — Shift négatif | `grep '.shift(-'` SRC | 0 occurrences (grep exécuté) |
| §R4 — Legacy random | `grep 'np.random.seed...'` ALL | 0 occurrences (grep exécuté) |
| §R7 — TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` ALL | 0 occurrences (grep exécuté) |
| §R7 — Chemins hardcodés | `grep '/tmp\|C:\\'` TEST | 0 occurrences (grep exécuté) |
| §R7 — Imports absolus `__init__` | N/A | Aucun `__init__.py` modifié (convention Streamlit multipage) |
| §R7 — Registration manuelle | `grep 'register_model...'` TEST | 0 occurrences (grep exécuté) |
| §R6 — Mutable defaults | `grep 'def .*=[]\|def .*={}'` ALL | 0 occurrences (grep exécuté) |
| §R6 — open() sans context manager | `grep '.read_text\|open('` SRC | 0 occurrences (grep exécuté) |
| §R6 — Bool par identité numpy | `grep 'is True\|is False'` ALL | 0 occurrences (grep exécuté) — le `is True` de la v1 (#083 code) a été éliminé du diff #084 |
| §R6 — Dict collision | `grep '[.*] = .*'` SRC | 0 occurrences (grep exécuté) |
| §R9 — for range | `grep 'for .* in range'` SRC | 0 occurrences (grep exécuté) |
| §R6 — isfinite | `grep 'isfinite'` SRC | 0 occurrences — N/A (métriques validées en amont par metrics.json) |
| §R9 — numpy compréhension | `grep 'np.[a-z]*(.*for'` SRC | 0 occurrences (grep exécuté) |
| §R7 — Fixtures dupliquées | `grep 'load_config.*configs/'` TEST | 0 occurrences (grep exécuté) |
| §R7 — per-file-ignores | `grep pyproject.toml` | Présent L52 — non modifié par cette PR |

### Annotations par fichier (B2)

#### `scripts/dashboard/pages/3_comparison.py` (174 lignes)

- **L1-8** Module docstring : mise à jour correcte (FIX v1). Inclut overlay, radar, §7.3, §7.4, §14.4. RAS.
- **L16-17** Imports `chart_equity_overlay`, `chart_radar` depuis `charts.py`. Signatures vérifiées : `charts.py:249` `chart_equity_overlay(curves: dict[str, pd.DataFrame]) -> go.Figure`, `charts.py:291` `chart_radar(runs_data: list[dict]) -> go.Figure`. Cohérent. RAS.
- **L141-158** §7.3 equity overlay : conditionnel `runs_dir is not None`, chargement `load_comparison_equity_curves`, messages dégradation, plotly chart. Logique correcte. RAS.
- **L163-167** §7.4 radar : appel strict `build_radar_data(selected_runs)` → `chart_radar(radar_data)`. Pas de try/except → crash visible si métrique None. Strict code conforme. RAS.

RAS après lecture complète du diff (42 lignes ajoutées par #084 + FIX).

#### `scripts/dashboard/pages/comparison_logic.py` (351 lignes)

- **L1-8** Module docstring à jour avec §7.3 et §7.4. RAS.
- **L270** `_RADAR_METRIC_KEYS` : tuple de 5 clés correspondant exactement à `chart_radar` attendues (`net_pnl`, `sharpe`, `max_drawdown`, `hit_rate`, `profit_factor`). RAS.
- **L273-308** `build_radar_data` : itère les runs, extrait `trading_mean`, boucle sur `_RADAR_METRIC_KEYS` avec `value is None → raise ValueError`. Strict code. RAS.
- **L316-351** `load_comparison_equity_curves` : itère, appelle `load_equity_curve(run_dir)`, trie `curves`/`missing` par label. Signature retour `tuple[dict, list]`. Contrat clair. RAS.

RAS après lecture complète du diff (90 lignes ajoutées par #084).

#### `tests/test_dashboard_comparison.py` (847 lignes)

- **L609-847** 10 tests #084 ajoutés, regroupés en 2 classes : `TestBuildRadarData` (5 tests) et `TestLoadComparisonEquityCurves` (5 tests).
- Imports lazy dans chaque méthode — cohérent avec le pattern existant.
- Helper `_make_metrics()` réutilisé, docstrings avec `#084`.
- Tous les tests utilisent `tmp_path` (portabilité). Données synthétiques. Pas d'aléatoire.
- Cas couverts : 2 runs, 1 run, 0 run, None metric (ValueError), partial equity, all missing equity, dict keys = labels.

RAS après lecture complète du diff (246 lignes ajoutées par #084).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_dashboard_comparison.py`, ID `#084` dans docstrings |
| Couverture des critères | ✅ | AC1→`test_all_runs_have_equity`, AC2→`test_basic_two_runs`+`test_values_extracted`, AC3→`test_some_runs_missing_equity`, AC4→`test_all_runs_missing_equity`, AC5→10 tests synthétiques |
| Cas nominaux + erreurs + bords | ✅ | Nominal : 2 runs ; Erreur : None metric raises ; Bord : empty list, all missing, single run |
| Boundary fuzzing | ✅ | 0 runs, None metric, partial/total absence equity |
| Déterministes | ✅ | Pas d'aléatoire |
| Données synthétiques | ✅ | `_make_metrics()`, CSV via `tmp_path` |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé |
| Tests registre | N/A | Pas de registre |
| Contrat ABC | N/A | Pas d'ABC |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1 : 0 fallback. `build_radar_data` raises ValueError pour None. |
| §R10 Defensive indexing | ✅ | Pas d'indexation array directe dans le code ajouté |
| §R2 Config-driven | ✅ | Pas de paramètre hardcodé — métriques de metrics.json, seuils de config_snapshot |
| §R3 Anti-fuite | ✅ | N/A — dashboard lecture seule. Scan B1 : 0 `.shift(-` |
| §R4 Reproductibilité | ✅ | N/A — pas d'aléatoire. Scan B1 : 0 legacy random |
| §R5 Float conventions | ✅ | N/A — pas de tenseurs |
| §R6 Anti-patterns Python | ✅ | Scan B1 : 0 mutable default, 0 open sans CM, 0 bool identité, 0 dict collision |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | `build_radar_data`, `load_comparison_equity_curves`, `_RADAR_METRIC_KEYS` |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO |
| Imports propres / relatifs | ✅ | Imports spécifiques, pas de `*`, pas de `__init__.py` Streamlit |
| DRY | ✅ | Réutilise `chart_equity_overlay`, `chart_radar`, `load_equity_curve`, `format_run_label` |
| Pas de fichiers générés dans la PR | ✅ | Diff ne contient que .py et .md |

### Bonnes pratiques métier (B5-bis)

| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Normalisation equity à 1.0 (charts.py), radar 5 axes conformes §7.4 |
| Nommage métier cohérent | ✅ | `equity_curve`, `net_pnl`, `sharpe`, `max_drawdown`, `hit_rate`, `profit_factor` |
| Séparation des responsabilités | ✅ | Logic dans `comparison_logic.py`, UI dans `3_comparison.py`, graphiques dans `charts.py` |
| Invariants de domaine | ✅ | `chart_equity_overlay` valide `eq_start > 0` avant normalisation |
| Cohérence des unités/échelles | ✅ | Métriques brutes passées au radar, normalisation min-max dans `chart_radar` |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| §7.3 — Superposition equity curves | ✅ | Graphique unique, courbe par run, légende cliquable, normalisé départ=1.0 |
| §7.4 — Radar chart 5 axes | ✅ | Net PnL, Sharpe, 1−MDD, Win Rate, PF, normalisation min-max |
| Plan WS-D-4.2 | ✅ | Tâche conforme au plan |
| Formules doc vs code | ✅ | N/A — pas de formule mathématique dans cette tâche |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `chart_equity_overlay(curves: dict[str, pd.DataFrame]) -> go.Figure` — conforme. `chart_radar(runs_data: list[dict]) -> go.Figure` — `build_radar_data` produit les clés attendues (`label`, `net_pnl`, `sharpe`, `max_drawdown`, `hit_rate`, `profit_factor`). `load_equity_curve(run_dir: Path) -> pd.DataFrame | None` — appelé correctement. |
| Structures de données partagées | ✅ | Dict metrics format identique à `discover_runs()` output |
| Imports croisés | ✅ | `chart_equity_overlay`, `chart_radar`, `load_equity_curve` — tous dans Max6000i1 |
| Forwarding kwargs | ✅ | Pas de wrapper avec kwargs à transmettre |
| Pattern existant respecté | ✅ | `comparison_logic.py` suit le pattern `overview_logic.py` / `run_detail_logic.py` |

---

## Remarques

Aucune remarque. L'item MINEUR v1 a été correctement corrigé.

---

## Actions requises

Aucune.
