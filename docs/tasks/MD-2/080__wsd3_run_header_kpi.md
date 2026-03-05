# Tâche — Page 2 : en-tête du run et KPI cards

Statut : DONE
Ordre : 080
Workstream : WS-D-3
Milestone : MD-2
Gate lié : N/A

## Contexte
La page 2 (détail d'un run) débute par un bandeau d'en-tête et des cartes KPI agrégées. Le fichier `pages/2_run_detail.py` est un stub vide (créé en MD-1). Cette tâche implémente la première section de la page : en-tête et KPI cards. Les sections suivantes (equity curve, trades) sont couvertes par les tâches #081 et #082.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-3.1)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§6.1, §6.2, §9.3, §9.4)
- Code : `scripts/dashboard/pages/2_run_detail.py`

Dépendances :
- Tâche 078 — Point d'entrée et navigation (doit être DONE)
- Tâche 074 — Data loader discovery (DONE)
- Tâche 076 — Utils formatage (DONE)

## Objectif
Implémenter l'en-tête du run (bandeau d'information §6.1) et les KPI cards de métriques agrégées (§6.2) dans `pages/2_run_detail.py`.

## Règles attendues
- **Strict code** : si le `run_id` sélectionné n'est pas dans `st.session_state`, afficher un message d'erreur explicite (pas de page vide).
- **Config-driven** : le label Sharpe est conditionnel selon `metrics.sharpe_annualized` dans `config_snapshot.yaml`.
- **DRY** : réutiliser `format_mean_std()`, `format_pct()`, `format_float()`, `format_int()`, `pnl_color()`, `sharpe_color()`, `mdd_color()`, `hit_rate_color()`, `profit_factor_color()` de `utils.py`.

## Évolutions proposées
- Afficher le bandeau d'en-tête (§6.1) : Run ID, Date (`manifest.created_at_utc` → `YYYY-MM-DD HH:MM UTC`), Stratégie, Framework, Symbole (join `", "`), Timeframe, Période (`start` — `end (excl.)`), Seed, Nombre de folds.
- Lire le manifest via `load_run_manifest()` et le config snapshot via `load_config_snapshot()`.
- Implémenter les 6 KPI cards (§6.2) : Net PnL, Sharpe Ratio, Max Drawdown, Hit Rate, Profit Factor, Nombre de trades. Format `mean ± std` avec seuils colorés.
- Lire `metrics.sharpe_annualized` dans `config_snapshot.yaml` pour le label Sharpe conditionnel (§6.2).
- Calculer `n_contributing` par métrique en parcourant `folds` et comptant les non-null (§6.2). Si `n_contributing < len(folds)`, afficher `(n/total folds)`.
- Gestion des valeurs `null` : afficher `—` (§6.2, §9.3).
- Utiliser `st.columns()` pour la disposition des KPI cards (§9.4).

## Critères d'acceptation
- [x] En-tête conforme à §6.1 avec toutes les informations (Run ID, Date, Stratégie, Framework, Symbole, Timeframe, Période avec `(excl.)`, Seed, Folds).
- [x] Suffixe `(excl.)` sur la date de fin de la période.
- [x] KPI cards avec `mean ± std`, seuils colorés conformes à §6.2.
- [x] Label Sharpe conditionnel : « Sharpe Ratio (annualisé) » ou « Sharpe Ratio » selon config.
- [x] Gestion des `null` : affichage `—`, count de folds contributifs `(n/total)`.
- [x] Si aucun run sélectionné, message d'erreur explicite.
- [x] Tests avec fixture de run complète (manifest, metrics, config_snapshot).
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/080-wsd3-run-header-kpi` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/080-wsd3-run-header-kpi` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-3] #080 RED: tests en-tête run et KPI cards`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-3] #080 GREEN: en-tête run et KPI cards métriques agrégées`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-3] #080 — Page 2 : en-tête du run et KPI cards`.
