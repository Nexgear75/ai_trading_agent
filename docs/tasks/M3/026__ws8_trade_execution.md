# Tâche — Règles d'exécution des trades (backtest engine)

Statut : TODO
Ordre : 026
Workstream : WS-8
Milestone : M3
Gate lié : M3

## Contexte
Le moteur de backtest est nécessaire en M3 pour la calibration du seuil θ (WS-7.2), qui doit exécuter un backtest sur validation pour chaque θ candidat. Le moteur implémente les règles d'exécution Go/No-Go → trades long-only avec mode `one_at_a_time`. Ce module constitue la chaîne backtest parallèle à la chaîne modèle au sein de M3.

Références :
- Plan : `docs/plan/implementation.md` (WS-8.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§12.1, Annexe E.2.3)
- Code : `ai_trading/backtest/engine.py` (à créer)

Dépendances :
- Tâche 018 — WS-4 metadata (doit être DONE) — fournit les DataFrame meta avec prix d'entrée/sortie

## Objectif
Implémenter le moteur d'exécution des trades dans `ai_trading/backtest/engine.py` : transformation d'un vecteur de signaux Go/No-Go en une liste de trades avec prix d'entrée/sortie et timestamps, supportant les modes `standard` et `single_trade`.

## Règles attendues
- **Anti-fuite** : les signaux à t ne dépendent pas des prix `t' > t`. Le moteur consomme un vecteur de signaux pré-calculé.
- **Strict code** : aucun fallback sur des signaux invalides — validation explicite des entrées.
- **Config-driven** : `backtest.mode = one_at_a_time`, `backtest.direction = long_only` lus depuis la config (imposés MVP).

## Évolutions proposées

### 1. Fonction/classe d'exécution des trades
- Entrée : vecteur de signaux `signals (N,)` (0/1), DataFrame OHLCV (ou meta), config
- Paramètre `execution_mode: Literal["standard", "single_trade"]`
- **Mode `standard`** :
  - Go à t → entrée long à `Open[t+1]`
  - Sortie automatique à `Close[t+H]` (`H = config.label.horizon_H_bars`)
  - Mode `one_at_a_time` : nouveau Go ignoré si un trade est déjà actif (§E.2.3)
  - Long-only : pas de position short
- **Mode `single_trade`** (Buy & Hold) :
  - Un seul trade couvrant toute la période
  - Entrée à `Open[first_timestamp]` **directement** (sans décalage t→t+1, conforme §12.5)
  - Sortie à `Close[last_timestamp]`
  - Le vecteur de signaux est ignoré

### 2. Structure de retour
- Liste de trades avec pour chaque trade : `entry_time`, `exit_time`, `entry_price` (Open[t+1]), `exit_price` (Close[t+H]), `signal_time` (t)
- Validation : aucun trade ne chevauche un autre en mode `one_at_a_time`

## Critères d'acceptation
- [ ] Le moteur accepte un vecteur de signaux (0/1) et produit une liste de trades
- [ ] Go à t → entrée à `Open[t+1]`, sortie à `Close[t+H]`
- [ ] Mode `one_at_a_time` : un Go pendant un trade actif est ignoré
- [ ] Mode `long_only` : aucun trade short généré
- [ ] Mode `single_trade` : un seul trade (entry = `Open[first_timestamp]` sans décalage, exit = `Close[last_timestamp]`) indépendamment des signaux
- [ ] Mode `standard` : trades de H bougies respectant les règles
- [ ] Cas bord : Go sur la dernière bougie (pas assez de bougies pour le trade) → trade ignoré ou tronqué selon spec
- [ ] Cas bord : aucun signal Go → liste de trades vide
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/026-trade-execution` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/026-trade-execution` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-8] #026 RED: tests règles d'exécution des trades` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-8] #026 GREEN: règles d'exécution des trades`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-8] #026 — Règles d'exécution des trades`.
