# Tâche — Utilitaires de formatage et palette de couleurs

Statut : DONE
Ordre : 076
Workstream : WS-D-1
Milestone : MD-1
Gate lié : N/A

## Contexte
Le module `utils.py` centralise les fonctions de formatage des métriques (pourcentages, floats, entiers, timestamps, mean±std), la gestion des valeurs `null` (affichage `—`), la palette de couleurs du dashboard, les fonctions de seuils colorés pour les KPI cards, et le formatage spécial du Sharpe/Trade.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (WS-D-1.4)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§6.2, §6.4, §9.2, §9.3, Annexe B)
- Code : `scripts/dashboard/utils.py` (à implémenter)

Dépendances :
- Tâche 073 — Structure projet et dépendances dashboard (doit être DONE)

## Objectif
Implémenter dans `utils.py` toutes les fonctions de formatage conformes à §9.3, la palette de couleurs conforme à §9.2, les fonctions de seuils colorés pour KPI cards (§6.2), et le formatage spécial Sharpe/Trade (§6.4).

## Règles attendues
- **Strict code** : pas de fallback silencieux — les valeurs `None`/`null` sont explicitement traitées et affichées comme `—` (tiret cadratin).
- **Config-driven** : les couleurs sont définies comme constantes dans `utils.py`, pas dispersées dans les pages.
- Notation scientifique pour `|sharpe_per_trade| > 1000` (spec §6.4).
- Indicateur ⚠️ si `n_trades ≤ 2` (spec §6.4).

## Évolutions proposées
- Implémenter `format_pct(value, decimals=2)` → `{value:.2%}`.
- Implémenter `format_float(value, decimals=2)` → `{value:.2f}`.
- Implémenter `format_int(value)` → `{value:,d}`.
- Implémenter `format_timestamp(ts)` → `YYYY-MM-DD HH:MM`.
- Implémenter `format_mean_std(mean, std, fmt_type)` : formatage `mean ± std` selon le type, avec gestion count si folds < total (spec §6.2).
- Gestion `None` → `—` dans chaque fonction de formatage.
- Définir constantes palette : `COLOR_PROFIT`, `COLOR_LOSS`, `COLOR_NEUTRAL`, `COLOR_WARNING`, `COLOR_DRAWDOWN`, `COLOR_FOLD_BORDER` (§9.2).
- Implémenter seuils colorés : `pnl_color(value)`, `sharpe_color(value)`, `mdd_color(value)`, `hit_rate_color(value)`, `profit_factor_color(value)` (§6.2).
- Implémenter `format_sharpe_per_trade(value, n_trades)` : notation scientifique si `|value| > 1000`, indicateur ⚠️ si `n_trades ≤ 2` (§6.4).

## Critères d'acceptation
- [x] Formatage conforme à §9.3 pour chaque type de métrique (pct, float, int, timestamp).
- [x] Valeurs `None`/`null` affichées comme `—` (tiret cadratin).
- [x] `format_mean_std()` produit le format `mean ± std` avec gestion count.
- [x] Palette de couleurs conforme à §9.2 (6 constantes).
- [x] Seuils colorés conformes à §6.2 (5 fonctions).
- [x] `format_sharpe_per_trade()` : notation scientifique pour `|value| > 1000`, indicateur ⚠️ pour `n_trades ≤ 2`.
- [x] Tests unitaires pour chaque fonction de formatage : valeurs normales, `None`, cas limites (0, négatif, très grand).
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/076-wsd1-utils-formatting` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/076-wsd1-utils-formatting` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-1] #076 RED: tests utilitaires formatage et couleurs` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-D-1] #076 GREEN: utilitaires formatage et couleurs`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-1] #076 — Utilitaires formatage et couleurs`.
