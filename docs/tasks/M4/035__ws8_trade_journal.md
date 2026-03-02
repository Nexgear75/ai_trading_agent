# Tâche — Journal de trades (trades.csv)

Statut : DONE
Ordre : 035
Workstream : WS-8
Milestone : M4
Gate lié : G-Backtest

## Contexte
Le moteur de backtest (WS-8.1/8.2/8.3, tâches #026/#027/#029) produit la liste des trades et la courbe d'équité. Il manque l'export du journal de trades en CSV, dernier livrable WS-8 avant le gate G-Backtest.

Références :
- Plan : `docs/plan/implementation.md` (WS-8.4)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§12.6)
- Code : `ai_trading/backtest/engine.py`

Dépendances :
- Tâche 029 — Courbe d'équité (doit être DONE)

## Objectif
Implémenter l'export du journal de trades au format CSV (`trades.csv`) avec toutes les colonnes normatives, depuis la liste de trades produite par le moteur de backtest.

## Règles attendues
- **Colonnes obligatoires** : `entry_time_utc, exit_time_utc, entry_price, exit_price, entry_price_eff, exit_price_eff, f, s, fees_paid, slippage_paid, y_true, y_hat, gross_return, net_return`.
- **Décomposition des coûts** (approximation additive) : `fees_paid = f * (entry_price + exit_price)`, `slippage_paid = s * (entry_price + exit_price)`.
- **Colonne `y_hat`** : pour `output_type == "signal"` (baselines, RL), `y_hat = 1` (Go) car un trade n'existe que si le signal est Go. Pour `output_type == "regression"`, `y_hat` contient le log-return prédit (float).
- **Cohérence** : la somme des `net_return` doit être cohérente avec l'équité finale (vérifiable via le produit cumulé `Π(1 + w * r_net_i)`).
- **Strict code** : pas de fallback, pas de valeurs par défaut implicites.
- **Config-driven** : `f` et `s` lus depuis `configs/default.yaml` (`costs.fee_rate_per_side`, `costs.slippage_rate_per_side`).

## Évolutions proposées
- Ajouter une fonction `export_trade_journal(trades, path)` dans `ai_trading/backtest/engine.py` (ou un module dédié `ai_trading/backtest/journal.py`).
- Le DataFrame retourné contient exactement les colonnes spécifiées, dans l'ordre.
- Le CSV est parseable (header + types corrects).

## Critères d'acceptation
- [x] CSV parseable avec les colonnes conformes à §12.6 dans l'ordre spécifié.
- [x] `fees_paid = f * (entry_price + exit_price)` pour chaque trade.
- [x] `slippage_paid = s * (entry_price + exit_price)` pour chaque trade.
- [x] `gross_return = (exit_price / entry_price) - 1` pour chaque trade.
- [x] `net_return` cohérent avec la formule multiplicative `M_net - 1`.
- [x] Somme cumulée des net_return cohérente avec l'équité finale (`E_final == E_0 * Π(1 + w * r_net_i)` à `atol=1e-8`).
- [x] Colonne `y_hat` = 1 pour `output_type == "signal"`, float pour `output_type == "regression"`.
- [x] Test avec 0 trades → CSV vide (header seulement).
- [x] Test avec multiple trades → colonnes et valeurs conformes.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/035-trade-journal` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/035-trade-journal` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-8] #035 RED: tests journal de trades CSV`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-8] #035 GREEN: export trade journal CSV`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-8] #035 — Journal de trades (trades.csv)`.
