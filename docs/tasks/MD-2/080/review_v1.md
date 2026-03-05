# Revue PR — [WS-D-3] #080 — Page 2 : en-tête du run et KPI cards

Branche : `task/080-wsd3-run-header-kpi`
Tâche : `docs/tasks/MD-2/080__wsd3_run_header_kpi.md`
Date : 2026-03-06

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Implémentation fonctionnellement correcte de l'en-tête du run (§6.1) et des KPI cards (§6.2) avec 27 tests passants. Architecture propre : séparation logique métier (`run_detail_logic.py`) / rendu Streamlit (`2_run_detail.py`). Trois patterns de fallback silencieux violent §R1 (strict code) et empêchent le verdict CLEAN.

---

## Phase A — Compliance

### Structure branche & commits
| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche | ✅ | `git branch --show-current` → `task/080-wsd3-run-header-kpi` |
| Commit RED présent | ✅ | `69c5a6f [WS-D-3] #080 RED: tests en-tête run et KPI cards` — `git show --stat` : 1 fichier (`tests/test_dashboard_run_detail.py`, 501 insertions) |
| Commit GREEN présent | ✅ | `1ede361 [WS-D-3] #080 GREEN: en-tête run et KPI cards métriques agrégées` — `git show --stat` : 4 fichiers (task + 2 src + test fix) |
| RED contient uniquement tests | ✅ | `git show --stat 69c5a6f` : 1 fichier `tests/test_dashboard_run_detail.py` |
| GREEN contient implémentation + tâche | ✅ | `git show --stat 1ede361` : `run_detail_logic.py`, `2_run_detail.py`, task MD, test fix |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` : exactement 2 commits (RED + GREEN) |

### Tâche
| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés | ✅ (10/10) |
| Checklist cochée | ✅ (8/9 — seule la PR non encore ouverte) |

### CI
| Check | Résultat |
|---|---|
| `pytest tests/test_dashboard_run_detail.py -v --tb=short` | **27 passed**, 0 failed |
| `ruff check` (3 fichiers modifiés) | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (§R1) | `grep 'or []\|or {}\|if .* else'` | **2 matches** — L139: ternaire Sharpe (faux positif, conditional légitime), L244: `std_val if std_val is not None else 0.0` (vrai fallback — voir W1) |
| Except trop large (§R1) | `grep 'except:$\|except Exception:'` | 0 occurrences |
| noqa (§R7) | `grep 'noqa'` | 0 occurrences |
| Print résiduel (§R7) | `grep 'print('` | 0 occurrences |
| Shift négatif (§R3) | `grep '.shift(-'` | 0 occurrences |
| Legacy random API (§R4) | `grep 'np.random.seed\|...'` | 0 occurrences |
| TODO/FIXME orphelins (§R7) | `grep 'TODO\|FIXME\|HACK\|XXX'` | 0 occurrences |
| Chemins hardcodés (§R7) | `grep '/tmp\|/var/tmp'` | 0 occurrences |
| Mutable defaults (§R6) | `grep 'def.*=[]\|def.*={}'` | 0 occurrences |
| Imports absolus __init__ (§R7) | N/A (pas de `__init__.py` modifié) | N/A |

### Annotations par fichier (B2)

#### `scripts/dashboard/pages/run_detail_logic.py` (255 lignes)

- **L61** `dataset = manifest.get("dataset", manifest["config_snapshot"]["dataset"])`
  Sévérité : **MINEUR**
  Observation : Fallback silencieux entre deux sources de données. La spec §6.1 indique `manifest.json → dataset.*` comme source canonique (top-level). Si le champ top-level `dataset` est absent, le code tombe silencieusement sur `config_snapshot.dataset` au lieu de lever une erreur explicite.
  Suggestion : Utiliser `manifest["dataset"]` directement (KeyError explicite si absent) ou documenter le fallback dans un commentaire clair.

- **L137-139** `config_snapshot.get("metrics", {}).get("sharpe_annualized", False)`
  Sévérité : **WARNING** (§R1)
  Observation : Double `.get()` chaîné avec defaults silencieux. Si le `config_snapshot` n'a pas de clé `"metrics"` ou `"sharpe_annualized"`, le code utilise silencieusement `False` au lieu d'échouer explicitement. Cela masque un config snapshot incomplet ou corrompu. La spec §6.2 dit explicitement « le dashboard doit lire ce paramètre ».
  Suggestion : Accès direct `config_snapshot["metrics"]["sharpe_annualized"]` avec KeyError explicite, ou validation préalable.

- **L244** `std=std_val if std_val is not None else 0.0`
  Sévérité : **WARNING** (§R1)
  Observation : Fallback silencieux `None → 0.0`. Quand `std_val` est None (agrégat non calculé), le code substitue 0.0 au lieu de propager l'absence. Si `mean_val` est non-None mais `std_val` est None, le dashboard affiche « mean ± 0.00% » ce qui est sémantiquement trompeur (on ne sait pas si std est réellement 0 ou non calculé).
  Suggestion : Si `mean_val` est non-None et `std_val` est None, passer `std=0.0` avec un commentaire justificatif (ex : « single fold, std undefined → display 0 ») ou modifier `format_mean_std` pour accepter `std: float | None`.

- **L147-214** Construction séquentielle des 6 cards avec `_add_card` puis append direct pour trades.
  Sévérité : RAS
  Observation : Code clair, ordre conforme à §6.2 (PnL, Sharpe, MDD, Hit Rate, PF, Trades). Le traitement spécial de n_trades (entier, sans std) est légitime.

- **L226** Signature `_add_card(cards: list[dict], *, ...)`
  Sévérité : RAS
  Observation : Accumulator pattern correct. Tous les paramètres post-`*` sont keyword-only. Pas de mutable default.

#### `scripts/dashboard/pages/2_run_detail.py` (100 lignes)

- **L31** `runs: list[dict] = st.session_state.get("runs", [])`
  Sévérité : RAS
  Observation : Fallback `.get(, [])` suivi immédiatement d'une validation explicite L33 (`if not runs ... st.error ... st.stop()`). Pattern acceptable aux frontières Streamlit.

- **L40** `run_ids = [r["run_id"] for r in runs]`
  Sévérité : RAS
  Observation : Accès direct `r["run_id"]` — KeyError si absent. Strict ✅.

- **L53** `n_folds = len(metrics.get("folds", []))`
  Sévérité : **MINEUR** (§R1)
  Observation : Fallback silencieux si `"folds"` absent du `metrics.json`. Le schéma JSON du pipeline garantit la clé, mais le code masque silencieusement une absence par `n_folds=0`.
  Suggestion : `n_folds = len(metrics["folds"])` — KeyError explicite si données corrompues.

- **L89-96** Rendu HTML KPI cards avec `unsafe_allow_html=True`
  Sévérité : RAS
  Observation : Les valeurs injectées dans le HTML (`card['value']`, `card['color']`) sont produites par `format_mean_std` et les couleurs sont des constantes hex hardcodées dans `utils.py`. Pas de risque XSS car aucune donnée utilisateur non-filtrée.

- **L63-74** Affichage en-tête avec `st.columns(3)`
  Sévérité : RAS
  Observation : Framework conditionnel (`if header["framework"] is not None`) — conforme au test `test_framework_missing_key`.

#### `tests/test_dashboard_run_detail.py` (498 lignes)

- **L1-15** Docstring avec ref tâche `#080` et sections spec.
  Sévérité : RAS
  Observation : Convention respectée.

- **L22-97** Helpers `_make_manifest`, `_make_config_snapshot`, `_make_metrics`
  Sévérité : RAS
  Observation : Données synthétiques, pas de réseau. Mutable default avoidance correcte (`list | None = None` → `if None: create`).

- **Couverture critères d'acceptation** : voir section B3 ci-dessous.

- Pas de `@pytest.mark.skip` ou `xfail`.
- Tous les imports sont locaux (inside test methods) pour isolation.
- Pas de chemins hardcodés.

### Tests (B3)
| Critère | Verdict | Preuve |
|---|---|---|
| Convention nommage | ✅ | `test_dashboard_run_detail.py`, `#080` dans les docstrings |
| Couverture des critères | ✅ | Voir mapping ci-dessous |
| Cas nominaux + erreurs + bords | ✅ | 4 classes: `TestBuildHeaderInfo` (6 tests), `TestBuildKpiCards` (11 tests), `TestCountNonNullFolds` (5 tests), `TestEdgeCases` (4 tests + 1 multi-assertions mdd) |
| Boundary fuzzing | ✅ | n_folds=1 (`test_single_fold`), all null (`test_all_null`), empty folds (`test_empty_folds`), 0 trades (`test_zero_trades_fold`) |
| Déterministes | ✅ | Pas d'aléatoire, données synthétiques fixes |
| Portabilité chemins | ✅ | Scan B1: 0 `/tmp` |
| Tests registre réalistes | N/A | Pas de registre impliqué |
| Contrat ABC complet | N/A | Pas d'ABC |

**Mapping critères → tests** :

| Critère d'acceptation | Test(s) |
|---|---|
| En-tête conforme §6.1 | `test_nominal_all_fields`, `test_multiple_symbols_joined`, `test_date_format_utc_suffix`, `test_period_excl_suffix`, `test_seed_from_config_snapshot` |
| Suffixe `(excl.)` | `test_period_excl_suffix` |
| KPI cards mean ± std, couleurs | `test_nominal_six_cards`, `test_card_keys`, `test_card_labels_order`, `test_pnl_color_positive`, `test_pnl_color_negative`, `test_mdd_color_thresholds` |
| Label Sharpe conditionnel | `test_sharpe_label_annualized`, `test_sharpe_label_not_annualized` |
| Gestion null + count folds | `test_all_null_displays_em_dash`, `test_n_contributing_all_folds`, `test_n_contributing_partial_folds`, `TestCountNonNullFolds` (5 tests) |
| Aucun run → erreur | Implicitement couvert via `2_run_detail.py` L33–35 (pas de test unitaire dédié car code Streamlit) |
| Tests fixture complète | Helpers `_make_manifest`, `_make_metrics`, `_make_config_snapshot` |
| Cas nominaux + erreurs + bords | `TestEdgeCases` (4 tests) |
| Suite verte | ✅ 27 passed |
| ruff clean | ✅ |

### Code — Règles non négociables (B4)
| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (§R1) | ⚠️ | 2 WARNING (L137-139, L244) + 2 MINEUR (L61, L53) — fallbacks silencieux |
| Defensive indexing (§R10) | ✅ | Pas d'indexation numérique sur des arrays de taille variable |
| Config-driven (§R2) | ✅ | `sharpe_annualized` lu depuis config_snapshot (L137) |
| Anti-fuite (§R3) | N/A | Pas de données temporelles à protéger (dashboard en lecture seule) |
| Reproductibilité (§R4) | N/A | Dashboard, pas de calcul stochastique |
| Float conventions (§R5) | N/A | Dashboard display, pas de tenseurs |
| Anti-patterns Python (§R6) | ✅ | Scan B1: 0 mutable defaults, pas de `open()` brut, ternaires propres |

### Qualité du code (B5)
| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case, noms descriptifs (`build_header_info`, `count_non_null_folds`, `_add_card`) |
| Pas de code mort/debug | ✅ | Scan B1: 0 print, 0 TODO |
| Imports propres | ✅ | Imports qualifiés, pas d'imports `*`, pas d'imports inutilisés (ruff clean) |
| DRY | ✅ | Réutilisation de `format_mean_std`, `format_int`, color functions depuis `utils.py`. Pattern `_add_card` factorise la construction répétitive des cards |
| Pas de fichiers générés | ✅ | Diff ne contient que src, tests, task doc |

### Conformité spec v1.0 (B6)
| Critère | Verdict | Commentaire |
|---|---|---|
| §6.1 en-tête du run | ✅ | Run ID, Date (YYYY-MM-DD HH:MM UTC), Stratégie, Framework, Symbole (join ", "), Timeframe, Période avec (excl.), Seed, N folds — tous présents |
| §6.2 métriques agrégées | ✅ | 6 cards dans l'ordre spec, formats conformes (pct 2 déc, float 2 déc, hit_rate 1 déc, entier), seuils colorés conformes |
| §6.2 label Sharpe conditionnel | ✅ | Lu depuis `config_snapshot.metrics.sharpe_annualized`, label « Sharpe Ratio (annualisé) » ou « Sharpe Ratio » |
| §6.2 null → « — » | ✅ | `_NULL_DISPLAY = "—"`, propagé via `format_mean_std(mean=None)` et `format_int(None)` |
| §6.2 count folds contributifs | ✅ | `count_non_null_folds()` parcourt folds, affiche `(n/N folds)` si n < N |
| §9.3 conventions d'affichage | ✅ | Ratios décimaux, `:.2%` / `:.2f` / `:.1%` (hit_rate) / `:,d` (trades) |
| §9.4 responsivité | ✅ | `st.columns()` pour KPI cards |
| Plan WS-D-3.1 | ✅ | Toutes les tâches du plan couvertes |

### Cohérence intermodule (B7)
| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅ | `load_run_manifest`, `load_run_metrics`, `load_config_snapshot` existent dans `data_loader.py` avec signatures `(run_dir: Path) -> dict` |
| Imports croisés | ✅ | Tous les symboles importés (`format_mean_std`, `format_int`, `pnl_color`, etc.) existent dans `utils.py` |
| Structures de données partagées | ✅ | `_NULL_DISPLAY = "—"` redéfini localement dans `run_detail_logic.py` (identique à `utils.py` L15) |
| Conventions numériques | ✅ | Ratios décimaux dans metrics.json, conformes à §9.3 |

### Bonnes pratiques métier (B5-bis)
| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅ | Métriques standard (Sharpe, MDD, Hit Rate, PF, PnL) correctement nommées et formatées |
| Nommage métier cohérent | ✅ | `net_pnl`, `sharpe`, `max_drawdown`, `hit_rate`, `profit_factor`, `n_trades` |
| Séparation des responsabilités | ✅ | Logique pure dans `run_detail_logic.py`, rendu Streamlit dans `2_run_detail.py` |
| Invariants de domaine | ✅ | Pas de calcul métier, lecture seule depuis metrics.json |

---

## Remarques

1. **[WARNING]** Fallback silencieux — `config_snapshot.get("metrics", {}).get("sharpe_annualized", False)`
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 137-139
   - Observation : Double `.get()` chaîné masque l'absence de clés dans le `config_snapshot`. Si la config snapshot est corrompue ou incomplète, le dashboard affiche silencieusement "Sharpe Ratio" au lieu de signaler l'erreur.
   - Suggestion : Remplacer par `config_snapshot["metrics"]["sharpe_annualized"]` avec un `KeyError` explicite, ou encapsuler dans une validation explicite avec message d'erreur clair.

2. **[WARNING]** Fallback silencieux — `std=std_val if std_val is not None else 0.0`
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 244
   - Observation : Convertit silencieusement `None → 0.0` pour `std`, masquant potentiellement une absence de donnée. Si `mean` est non-null mais `std` est null, l'affichage « mean ± 0.00% » est sémantiquement ambigu.
   - Suggestion : Option A — Ajouter un commentaire documentant le choix (« std=None occurs only for single fold → std=0 is correct »). Option B — Modifier `format_mean_std` pour accepter `std: float | None` et afficher mean sans ± si std est None.

3. **[MINEUR]** Fallback silencieux — `manifest.get("dataset", manifest["config_snapshot"]["dataset"])`
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py`
   - Ligne(s) : 61
   - Observation : La spec §6.1 indique `manifest.json → dataset.*` comme source canonique (top-level). Le code essaie silencieusement une source alternative si absent.
   - Suggestion : `dataset = manifest["dataset"]` — KeyError explicite si absent. Le manifest pipeline garantit ce champ.

4. **[MINEUR]** Fallback silencieux — `metrics.get("folds", [])`
   - Fichier : `scripts/dashboard/pages/2_run_detail.py`
   - Ligne(s) : 53
   - Observation : Si `"folds"` est absent du `metrics.json`, `n_folds` vaut silencieusement 0 au lieu d'une erreur.
   - Suggestion : `n_folds = len(metrics["folds"])` — le schéma JSON garantit la clé.

5. **[MINEUR]** Constante `_NULL_DISPLAY` dupliquée
   - Fichier : `scripts/dashboard/pages/run_detail_logic.py` L24 et `scripts/dashboard/utils.py` L15
   - Observation : La même constante `"—"` est définie dans deux modules. Risque de drift si modifiée dans un seul endroit. (§R7 DRY)
   - Suggestion : Importer `_NULL_DISPLAY` depuis `utils.py` ou l'exposer comme `NULL_DISPLAY` (public).

---

## Résumé

L'implémentation est fonctionnellement correcte et bien structurée : séparation logique/rendu, 27 tests couvrant nominaux, erreurs et bords, conformité complète avec §6.1 et §6.2 de la spec. Les deux WARNING concernent des fallbacks silencieux qui violent §R1 (strict code) — le plus impactant étant la lecture chaînée de `sharpe_annualized` avec double `.get()`. Les 3 items MINEUR sont des améliorations de rigueur (accès direct aux clés garanties, DRY).
