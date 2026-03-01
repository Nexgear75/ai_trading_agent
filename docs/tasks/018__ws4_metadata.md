# Tâche — Métadonnées d'exécution (meta)

Statut : DONE
Ordre : 018
Workstream : WS-4
Milestone : M2
Gate lié : G-Split

## Contexte
Pour chaque sample, le pipeline doit stocker les métadonnées d'exécution : timestamps de décision/entrée/sortie et prix d'entrée/sortie. Ces métadonnées sont nécessaires au backtest (WS-8), à la calibration θ (WS-7), et au modèle RL (qui construit son environnement interactif à partir de ces prix).

Références :
- Plan : `docs/plan/implementation.md` (WS-4.4)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§7.3)
- Code : `ai_trading/data/dataset.py` (à étendre)

Dépendances :
- Tâche 016 — Sample builder (doit être DONE)

## Objectif
Pour chaque sample t valide, construire un DataFrame `meta` avec les colonnes :
- `decision_time` : close_time(t) — timestamp de la bougie de décision.
- `entry_time` : open_time(t+1) — timestamp d'entrée en position.
- `exit_time` : close_time(t+H) — timestamp de sortie de position.
- `entry_price` : `Open[t+1]` — prix d'entrée.
- `exit_price` : `Close[t+H]` — prix de sortie.

## Règles attendues
- **Strict code** : les prix correspondent aux bonnes bougies. Aucune approximation.
- **Strict code** : si une bougie `t+1` ou `t+H` n'est pas disponible, le sample ne doit pas exister (déjà filtré par le masque de labels).
- **Anti-fuite** : les métadonnées sont stockées mais ne sont jamais utilisées comme features.

## Évolutions proposées
- Ajouter `build_meta(ohlcv, timestamps, config) -> pd.DataFrame` dans `ai_trading/data/dataset.py`.
- `timestamps` est l'index des timestamps de décision (produit par le sample builder).
- `meta` a N lignes (une par sample valide) et 5+ colonnes.

## Critères d'acceptation
- [x] `meta` de shape `(N, 5+)` avec les colonnes attendues.
- [x] Les prix correspondent aux bonnes bougies (vérification manuelle sur données synthétiques).
- [x] Cohérence `log_return_trade` : `y_t ≈ log(exit_price / entry_price)` pour les samples de ce type (tolérance `atol=1e-10`).
- [x] Cohérence `log_return_close_to_close` : `y_t ≈ log(Close[t+H] / Close[t])` (indépendant de `entry_price`).
- [x] `decision_time`, `entry_time`, `exit_time` sont des timestamps UTC valides.
- [x] `horizon_H_bars` lu depuis la config (pas hardcodé).
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/018-metadata` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/018-metadata` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-4] #018 RED: tests métadonnées d'exécution`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-4] #018 GREEN: métadonnées d'exécution`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-4] #018 — Métadonnées d'exécution`.
