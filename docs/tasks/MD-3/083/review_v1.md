# Revue PR — [WS-D-4] #083 — Page 3 : sélection et tableau comparatif

Branche : `task/083-wsd4-comparison-table`
Tâche : `docs/tasks/MD-3/083__wsd4_comparison_table.md`
Date : 2026-03-06

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation propre et bien structurée de la page comparaison avec séparation claire logique/UI, bonne réutilisation DRY de `overview_logic`, et tests complets couvrant les cas nominaux, boundary et erreurs. Un WARNING sur le rendu de la surbrillance qui dévie de la spec §7.2 (texte sous le tableau au lieu de styling gras vert / italique rouge dans les cellules), et un MINEUR sur l'absence de protection contre collision de labels dans le dict `label_to_metrics`.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/083-*` | ✅ | `task/083-wsd4-comparison-table` |
| Commit RED présent | ✅ | `8759a3a [WS-D-4] #083 RED: tests sélection runs et tableau comparatif` — 1 fichier: `tests/test_dashboard_comparison.py` (499 insertions) |
| Commit GREEN présent | ✅ | `2ee2183 [WS-D-4] #083 GREEN: page comparaison — sélection et tableau` — 4 fichiers |
| Commit RED = tests uniquement | ✅ | `git show --stat 8759a3a` → seul fichier: `tests/test_dashboard_comparison.py` |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 2ee2183` → `3_comparison.py`, `comparison_logic.py`, `tests/test_dashboard_comparison.py` (ajustements), `083__wsd4_comparison_table.md` |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → exactement 2 commits (RED + GREEN) |

### Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (9/9) |
| Checklist cochée | ✅ (8/9 — seul « PR ouverte » non coché, attendu) |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **2152 passed**, 0 failed |
| `pytest tests/test_dashboard_comparison.py -v` | **23 passed**, 0 failed |
| `ruff check ai_trading/ tests/ scripts/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| §R1 Fallbacks silencieux | `grep ' or []\| or {}\| or ""\| or 0\| if .* else '` | 3 matches — analysés : L162 `comparison_logic.py` et L119-120 `3_comparison.py` sont des ternaires bool→display, pas des fallbacks. **RAS.** |
| §R1 Except trop large | `grep 'except:$\|except Exception:'` | 0 occurrences |
| §R7 noqa | `grep 'noqa'` | 0 occurrences |
| §R7 Print résiduel | `grep 'print('` | 0 occurrences |
| §R3 Shift négatif | `grep '.shift(-'` | 0 occurrences |
| §R4 Legacy random API | `grep 'np.random.seed\|...'` | 0 occurrences |
| §R7 TODO/FIXME | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences |
| §R7 Chemins hardcodés | `grep '/tmp\|C:\\'` (tests) | 0 occurrences |
| §R6 Mutable defaults | `grep 'def.*=\[\]\|def.*={}'` | 1 match: `3_comparison.py:55: default=[]` — c'est un kwarg de `st.sidebar.multiselect()`, pas un paramètre de fonction. **RAS.** |
| §R7 Imports absolus auto-référençants | `grep 'from ai_trading\.'` (src) | 0 occurrences |

### Annotations par fichier (B2)

#### `scripts/dashboard/pages/comparison_logic.py` (213 lignes)

- **L14** `from scripts.dashboard.pages.overview_logic import build_overview_dataframe` : import correct, réutilisation DRY de la construction du DataFrame §5.2. Signature vérifiée compatible (accepte `list[dict]`, retourne `pd.DataFrame`). **RAS.**

- **L47** `build_comparison_dataframe` : délègue intégralement à `build_overview_dataframe`. DRY conforme. **RAS.**

- **L73-100** `highlight_best_worst` : itère sur `_NUMERIC_COLS`, utilise `pd.to_numeric(errors="coerce")` pour gérer les NaN, traitement MDD spécial par valeur absolue (best = plus proche de 0). Logique correcte. `int()` cast sur `idxmin()`/`idxmax()` pour compatibilité numpy int → Python int. **RAS.**

- **L108-163** `check_pipeline_criteria` : accès `metrics["aggregate"]["trading"]["mean"]` par indexation directe (contrat validé par `discover_runs` → `load_run_metrics`). `.get()` pour valeurs individuelles avec vérification explicite `is not None`. Seuil MDD lu depuis `config_snapshot` → config-driven. `abs(max_drawdown) < mdd_cap` gère correctement les MDD négatifs et positifs. **RAS.**

- **L169-187** `get_aggregate_notes` : accès `metrics["aggregate"].get("notes")` avec test falsy (`not notes` → None). Un string vide retourne None. **RAS.**

- **L193-213** `format_run_label` : accès direct `metrics["run_id"]` et `metrics["strategy"]["name"]`. Clés garanties par le contrat `discover_runs`. **RAS.**

#### `scripts/dashboard/pages/3_comparison.py` (135 lignes)

- **L47-50** Dict `label_to_metrics` construit par boucle avec `format_run_label(m)` comme clé. Si deux runs ont le même `run_id` + `strategy_name`, collision silencieuse. `run_id` est unique par design du pipeline (nom du répertoire), donc risque quasi-nul mais aucune validation. **MINEUR** (§R6 dict keyed by computed value).

- **L72-78** `st.dataframe(df_formatted, ...)` affiche le tableau formaté. La surbrillance est ensuite montrée en texte séparé (L81-87 : boucle `st.text(...🟢...🔴...)`) au lieu d'appliquer un styling CSS gras vert / italique rouge directement dans les cellules du tableau. La spec §7.2 dit explicitement « meilleure valeur par colonne **en gras vert**, pire **en italique rouge** ». L'implémentation affiche des indicateurs textuels sous le tableau. La logique de détection best/worst est correcte et testée, mais le rendu UI ne correspond pas à la spécification. **WARNING** (déviation spec §7.2 — critère d'acceptation #3 coché `[x]` sans être réellement implémenté comme spécifié).

- **L93-96** `config_snapshot = load_config_snapshot(run_path)` dans un `try/except (FileNotFoundError, ValueError)` : exceptions spécifiques, conformes au contrat de `load_config_snapshot`. Le fallback `None` est le comportement documenté (MDD → "—"). **RAS.**

- **L30-31** `st.session_state["runs"]` : accès direct avec garde `if "runs" not in st.session_state`. Correct. **RAS.**

#### `tests/test_dashboard_comparison.py` (520 lignes)

- **L25-68** `_make_metrics` : helper bien structuré avec tous les paramètres explicites en keyword-only. Permet de construire des metrics synthétiques réalistes. **RAS.**

- Tests `TestBuildComparisonDataframe` (4 tests) : colonnes §5.2, row count, valeurs extraites, liste vide. **RAS.**

- Tests `TestHighlightBestWorst` (5 tests) : basic 2 runs, 3 runs, numeric-only filtering, NaN handling, single run (best==worst). Commentaires clairs sur l'ordre de tri descendant. **RAS.**

- Tests `TestCheckPipelineCriteria` (10 tests) : all pass, negative pnl, pf<1, mdd>cap, config absent, mdd_cap absent, pnl=0 (boundary), pf=1.0 (boundary), None net_pnl, None profit_factor. Très bonne couverture boundary. **RAS.**

- Tests `TestGetAggregateNotes` (3 tests) : présent, absent, string vide. **RAS.**

- Tests `TestFormatRunLabel` (1 test) : vérifie présence run_id et strategy_name dans le label. **RAS.**

- **Observation** : pas de test pour `max_drawdown=None` avec `config_snapshot` présent (MDD serait `False`). Le code gère ce cas (L155: `if max_drawdown is not None else False`), mais aucun test ne le prouve explicitement. **MINEUR** (test boundary manquant, cas fonctionnellement couvert mais non prouvé).

RAS après lecture complète du diff pour le reste des tests.

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Couverture des critères d'acceptation | ✅ | Multiselect → `TestFormatRunLabel`; Tableau §5.2 → `TestBuildComparisonDataframe`; Surbrillance → `TestHighlightBestWorst`; Critères §14.4 → `TestCheckPipelineCriteria`; Notes → `TestGetAggregateNotes`; < 2 runs → implicite (UI) |
| Cas nominaux + erreurs + bords | ✅ | Nominaux (all pass, 2 runs), erreurs (None values, config absent), bords (pnl=0, pf=1.0, single run, NaN) |
| Boundary fuzzing | ✅ | `pnl=0`, `pf=1.0`, `None` values, NaN, single run, empty list |
| Déterministes | ✅ | Pas d'aléatoire dans les tests — données synthétiques déterministes |
| Données synthétiques | ✅ | `_make_metrics()` helper, aucune dépendance réseau |
| Portabilité chemins | ✅ | Scan B1: 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre dans ce module |
| Contrat ABC complet | N/A | Pas d'ABC dans ce module |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| §R1 Strict code (no fallbacks) | ✅ | Scan B1: 0 fallback réel. Ternaires bool→display acceptables. Exceptions spécifiques. |
| §R10 Defensive indexing | ✅ | `highlight_best_worst` accède par indices pandas après `dropna()`. `valid.empty` vérifié avant `idxmin/idxmax`. |
| §R2 Config-driven | ✅ | Seuil MDD lu depuis `config_snapshot.yaml` via `load_config_snapshot`. Pas de valeur hardcodée. |
| §R3 Anti-fuite | N/A | Module dashboard, pas de données temporelles. |
| §R4 Reproductibilité | N/A | Module dashboard, pas de random. Scan B1: 0 legacy random. |
| §R5 Float conventions | N/A | Module dashboard, pas de tenseurs. |
| §R6 Anti-patterns Python | ✅ | Scan B1: 0 mutable defaults (le `default=[]` est un kwarg Streamlit). Pas d'`open()` sans context manager. |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage snake_case | ✅ | Tous les noms sont snake_case. |
| Pas de code mort/debug | ✅ | Scan B1: 0 `print()`, 0 TODO. |
| Imports propres / relatifs | ✅ | Imports depuis `scripts.dashboard.*` — cohérent avec le reste du dashboard. 0 `noqa`. |
| DRY | ✅ | `build_comparison_dataframe` délègue à `build_overview_dataframe`. `format_overview_dataframe` réutilisé. |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| §7.1 Multiselect 2-10 | ✅ | `st.sidebar.multiselect` avec `max_selections=10`, garde `len < 2`. |
| §7.2 Tableau comparatif colonnes | ✅ | Mêmes colonnes que §5.2 via `build_overview_dataframe`. |
| §7.2 Surbrillance gras vert / italique rouge | ⚠️ | Logique correcte, mais rendu sous forme de texte 🟢/🔴 sous le tableau au lieu de styling cellulaire. Voir WARNING #1. |
| §14.4 Critères pipeline ✅/❌ | ✅ | P&L > 0, PF > 1.0, MDD < `mdd_cap` (config-driven). |
| §7.2 Notes/warnings | ✅ | `get_aggregate_notes` + `st.warning()`. |
| Plan WS-D-4.1 | ✅ | Conforme. |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `build_overview_dataframe(runs: list[dict]) → pd.DataFrame` — compatible. `load_config_snapshot(run_dir: Path) → dict` — compatible. |
| Noms de colonnes DataFrame | ✅ | Réutilise `_COLUMNS` de `overview_logic` via délégation. |
| Imports croisés | ✅ | `overview_logic`, `data_loader`, `utils` — tous existent sur `Max6000i1`. |

---

## Remarques

1. **[WARNING]** Surbrillance §7.2 non conforme au rendu spécifié.
   - Fichier : `scripts/dashboard/pages/3_comparison.py`
   - Ligne(s) : 72-87
   - Description : La spec §7.2 spécifie « meilleure valeur par colonne en **gras vert**, pire en **italique rouge** ». L'implémentation affiche un `st.dataframe()` sans styling, puis des lignes textuelles `🟢 best_run · 🔴 worst_run` sous le tableau. La logique de détection best/worst est correcte et bien testée, mais le rendu ne correspond pas à la spécification. Le critère d'acceptation #3 « Surbrillance meilleur (gras vert) / pire (italique rouge) par colonne » est coché `[x]` sans être réellement implémenté comme spécifié.
   - Suggestion : Utiliser `pandas.io.formats.style.Styler` pour appliquer le styling directement dans les cellules du DataFrame. Streamlit supporte `st.dataframe(df.style.apply(...))`. Exemple : `st.dataframe(df_formatted.style.apply(apply_highlight, highlights=highlights, axis=None))` avec une fonction `apply_highlight` qui retourne `"font-weight: bold; color: green"` / `"font-style: italic; color: red"`.

2. **[MINEUR]** Collision potentielle dans `label_to_metrics` (§R6).
   - Fichier : `scripts/dashboard/pages/3_comparison.py`
   - Ligne(s) : 47-50
   - Description : Le dict `label_to_metrics` est construit par boucle avec `format_run_label(m)` comme clé. Si deux runs produisent le même label (même `run_id` + `strategy_name`), le second écrase silencieusement le premier. Le `run_id` est unique par design du pipeline, donc le risque est quasi-nul, mais aucune validation ne le garantit côté dashboard.
   - Suggestion : Ajouter une assertion ou un check : `assert label not in label_to_metrics, f"Duplicate label: {label}"` avant l'assignation.

3. **[MINEUR]** Test boundary manquant : `max_drawdown=None` avec `config_snapshot` présent.
   - Fichier : `tests/test_dashboard_comparison.py`
   - Ligne(s) : (absent)
   - Description : Le code `comparison_logic.py:155` gère `max_drawdown is not None` (retourne `False` si None), mais aucun test ne couvre explicitement ce cas avec un `config_snapshot` contenant un `mdd_cap` valide et un `max_drawdown=None`. Le comportement est correct mais non prouvé.
   - Suggestion : Ajouter un test `test_mdd_none_with_config_present` dans `TestCheckPipelineCriteria`.

---

## Résumé

| Sévérité | Nombre |
|---|---|
| BLOQUANT | 0 |
| WARNING | 1 |
| MINEUR | 2 |
