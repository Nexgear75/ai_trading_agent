# Tâche — Courbe d'équité (equity curve)

Statut : DONE
Ordre : 029
Workstream : WS-8
Milestone : M3
Gate lié : M3

## Contexte
La courbe d'équité normalise la performance du portefeuille à `E_0 = 1.0` et se met à jour uniquement aux bougies de sortie des trades (pas de mark-to-market intra-trade). Elle est nécessaire pour le calcul du MDD utilisé dans la calibration θ (WS-7.2) et pour les métriques trading (M4). Le format CSV avec résolution par bougie est imposé par la spec.

Références :
- Plan : `docs/plan/implementation.md` (WS-8.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§12.4, Annexe E.2.8)
- Code : `ai_trading/backtest/engine.py` (extension du module existant)

Dépendances :
- Tâche 027 — WS-8 cost model (doit être DONE)

## Objectif
Construire la courbe d'équité normalisée avec résolution par bougie, conforme à §12.4, incluant le support du mode `single_trade` et le format CSV imposé.

## Règles attendues
- **Formules conformes à la spec** : `E_exit = E_entry × (1 + w × r_net)` avec `w = config.backtest.position_fraction`.
- **Config-driven** : `backtest.initial_equity` et `backtest.position_fraction` lus depuis la config.
- **Strict code** : pas de mark-to-market intra-trade — l'equity reste constante pendant un trade ouvert.

## Évolutions proposées

### 1. Construction de la courbe d'équité
- Initialisation : `E_0 = config.backtest.initial_equity` (défaut 1.0)
- Pour chaque trade :
  - Entre l'entrée et la sortie (exclus), l'equity reste constante à `E_entry`
  - À la bougie de sortie (t+H) : `E_exit = E_entry × (1 + w × r_net)`
  - `w = config.backtest.position_fraction` (défaut 1.0 = all-in)
- Hors trade : equity constante au dernier niveau

### 2. Colonne `in_trade`
- `in_trade[t] = False` à la bougie de décision (trade pas encore ouvert)
- `in_trade[t+1] = True` à la bougie d'entrée
- `in_trade[t+H] = True` à la dernière bougie du trade (sortie à Close)

### 3. Mode `single_trade` (Buy & Hold)
- Un seul trade couvrant toute la période test
- Equity constante sauf à la dernière bougie
- Coûts (f, s) appliqués une fois à l'entrée et une fois à la sortie

### 4. Format CSV `equity_curve.csv`
- Colonnes : `time_utc`, `equity`, `in_trade`
- Une ligne par bougie de la période considérée

### 5. Calcul du MDD et liaison métriques
- MDD calculé sur les valeurs d'equity per-candle (constantes par paliers, variant aux sorties)
- Sharpe ratio sur `r_t = E_t / E_{t-1} - 1` (0 partout sauf aux bougies de sortie)
- Note : les métriques elles-mêmes sont en M4 (WS-10), mais l'equity curve doit fournir les données nécessaires

## Critères d'acceptation
- [x] Equity initialisée à `E_0 = config.backtest.initial_equity`
- [x] Equity constante hors position (pas de changement entre les trades)
- [x] Equity constante pendant un trade ouvert (pas de mark-to-market)
- [x] Equity mise à jour uniquement à la bougie de sortie : `E_exit = E_entry × (1 + w × r_net)`
- [x] `E_final = E_0 × Π(1 + w × r_net_i)` à `atol=1e-8`
- [x] Colonne `in_trade` correcte (False à décision, True de l'entrée à la sortie)
- [x] Format CSV conforme : colonnes `(time_utc, equity, in_trade)`
- [x] Test avec `w < 1.0` : impact du trade réduit proportionnellement
- [x] Exemple numérique vérifié : `E_before=1.0`, `w=1.0`, `f=0.001`, `s=0.0003`, `Open=100`, `Close=102` → `E_exit ≈ 1.0174`
- [x] Mode `single_trade` : un seul trade, equity constante jusqu'à la dernière bougie
- [x] Un trade avec drawdown intra-marché → equity constante (MDD ne capture pas le drawdown intra-trade)
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/029-equity-curve` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/029-equity-curve` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-8] #029 RED: tests courbe d'équité` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-8] #029 GREEN: courbe d'équité`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-8] #029 — Courbe d'équité (equity curve)`.
