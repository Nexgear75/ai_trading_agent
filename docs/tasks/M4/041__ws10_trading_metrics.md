# Tâche — Métriques de trading

Statut : TODO
Ordre : 041
Workstream : WS-10
Milestone : M4
Gate lié : M4

## Contexte
Les métriques de trading évaluent la performance effective du backtest à partir de la courbe d'équité et du journal de trades. Elles sont calculées par fold sur la période test, puis agrégées inter-fold (tâche #042).

Références :
- Plan : `docs/plan/implementation.md` (WS-10.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§14.2, Annexe E.2.5)
- Code : `ai_trading/metrics/trading.py` (à créer)

Dépendances :
- Tâche 036 — Validation du gate G-Backtest (doit être DONE)

## Objectif
Implémenter le module `metrics/trading.py` calculant toutes les métriques de trading spécifiées, à partir de la courbe d'équité et des trades.

## Règles attendues
- **Métriques obligatoires** :
  - `net_pnl = E_T - 1` (avec E_0 = 1.0)
  - `net_return = E_T - 1` (équivalent en mode all-in)
  - `max_drawdown = max_t((peak_t - E_t) / peak_t)`, MDD ∈ [0, 1]
  - `sharpe = mean(r_t) / (std(r_t) + ε)` avec `r_t = E_t / E_{t-1} - 1` sur toute la grille test (y compris hors trade où `r_t = 0`). `ε = config.metrics.sharpe_epsilon`.
  - `profit_factor` : cf. Annexe E.2.5 — cas limites gérés (0 trades → null, que gagnants → null, que perdants → 0.0).
  - `hit_rate = n_winning_trades / n_trades`
  - `n_trades` : nombre de trades exécutés
  - `avg_trade_return = mean(r_net)` sur les trades
  - `median_trade_return = median(r_net)` sur les trades
  - `exposure_time_frac = n_bougies_en_trade / n_bougies_total_test`
  - `sharpe_per_trade = mean(r_net_trades) / (std(r_net_trades) + ε)` — complémentaire, non agrégé inter-fold.
- **Sharpe annualisé** (optionnel) : `sharpe * sqrt(K)` avec `K = 365.25 * 24 / Δ_hours`. Contrôlé par `config.metrics.sharpe_annualized`.
- **Cas `n_trades == 0`** : `net_pnl = 0`, `net_return = 0`, `max_drawdown = 0`, `sharpe = null`, `profit_factor = null`, `hit_rate = null`, `avg_trade_return = null`, `median_trade_return = null`, `exposure_time_frac = 0.0`, `sharpe_per_trade = null`.
- **Float conventions** : métriques en float64.
- **Config-driven** : `sharpe_epsilon`, `sharpe_annualized` lus depuis `configs/default.yaml`.
- **Strict code** : pas de fallback, cas limites traités explicitement.

## Évolutions proposées
- Créer `ai_trading/metrics/trading.py` avec des fonctions : `compute_net_pnl`, `compute_max_drawdown`, `compute_sharpe`, `compute_profit_factor`, `compute_hit_rate`, `compute_exposure_time_frac`, `compute_sharpe_per_trade`, et une fonction agrégée `compute_trading_metrics(equity_curve, trades, config)`.
- Mettre à jour `ai_trading/metrics/__init__.py`.
- Créer `tests/test_trading_metrics.py`.

## Critères d'acceptation
- [ ] `net_pnl` et `net_return` corrects sur equity synthétique.
- [ ] `max_drawdown` ∈ [0, 1], test numérique sur courbe avec drawdown connu.
- [ ] `sharpe` calculé sur toute la grille test (y compris r_t = 0 hors trade), avec epsilon.
- [ ] `profit_factor` : 0 trades → null, que gagnants → null, que perdants → 0.0, cas normal → ratio correct.
- [ ] `hit_rate` : ratio wins/total, test numérique.
- [ ] `n_trades` : comptage correct.
- [ ] `avg_trade_return` et `median_trade_return` : tests numériques.
- [ ] `exposure_time_frac` : correct pour standard et single_trade modes.
- [ ] `sharpe_per_trade` : calculé sur r_net des trades uniquement, null si 0 trades.
- [ ] Cas `n_trades == 0` : toutes les métriques conformes aux valeurs spécifiées.
- [ ] Sharpe annualisé calculé si `config.metrics.sharpe_annualized == true`.
- [ ] Métriques en float64.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/041-trading-metrics` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/041-trading-metrics` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-10] #041 RED: <résumé>` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-10] #041 GREEN: <résumé>`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-10] #041 — Métriques de trading`.
