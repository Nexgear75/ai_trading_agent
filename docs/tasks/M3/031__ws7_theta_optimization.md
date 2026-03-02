# Tâche — Objectif d'optimisation et sélection du seuil θ

Statut : DONE
Ordre : 031
Workstream : WS-7
Milestone : M3
Gate lié : M3

## Contexte
La calibration θ sélectionne le seuil optimal parmi les candidats de la grille de quantiles (WS-7.1) en exécutant un backtest sur la validation pour chaque θ candidat. Le θ retenu maximise le P&L net sous contraintes de MDD et nombre minimum de trades. Ce module est le point de convergence des deux chaînes parallèles de M3 (modèle + backtest).

Références :
- Plan : `docs/plan/implementation.md` (WS-7.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§11.3)
- Code : `ai_trading/calibration/threshold.py` (extension du module existant)

Dépendances :
- Tâche 030 — WS-7 quantile grid (doit être DONE) — fournit les θ candidats
- Tâche 026 — WS-8 trade execution (doit être DONE) — exécution des trades pour chaque θ
- Tâche 027 — WS-8 cost model (doit être DONE) — rendement net pour le P&L
- Tâche 029 — WS-8 equity curve (doit être DONE) — equity curve pour le MDD

## Objectif
Implémenter la boucle d'optimisation qui, pour chaque θ candidat : (1) génère les signaux Go/No-Go sur validation, (2) exécute le backtest, (3) calcule P&L net et MDD, (4) retient le θ optimal sous contraintes.

## Règles attendues
- **Anti-fuite** : θ calibré uniquement sur val, jamais sur test. Test de perturbation : modifier `y_hat_test` → θ identique.
- **Config-driven** : `thresholding.objective`, `thresholding.mdd_cap`, `thresholding.min_trades` lus depuis la config.
- **Strict code** : pas de fallback silencieux — si aucun θ ne satisfait les contraintes, c'est WS-7.3 qui prend le relais (pas de logique implicite).
- **Indépendance entre candidats** : equity réinitialisée à `E_0 = 1.0` pour chaque θ candidat.

## Évolutions proposées

### 1. Boucle d'optimisation `calibrate_threshold(...)`
Pour chaque `θ` dans les candidats (issus de WS-7.1) :
1. Générer les signaux : `signals = apply_threshold(y_hat_val, θ)`
2. Exécuter le backtest sur validation avec `signals` → obtenir les trades et l'equity curve
3. Réinitialiser `E_0 = 1.0` pour chaque candidat (indépendance)
4. Calculer :
   - `net_pnl = E_final - E_0` (P&L net sur la validation)
   - `mdd` = max drawdown sur la courbe d'equity
   - `n_trades` = nombre de trades exécutés
5. Filtrer : `mdd <= config.thresholding.mdd_cap` ET `n_trades >= config.thresholding.min_trades`
6. Parmi les θ faisables : retenir celui qui maximise `net_pnl`
7. En cas d'ex-aequo : préférer le quantile le plus haut (le plus conservateur)

### 2. Retour structuré
- `theta` : le seuil retenu (float)
- `quantile` : le quantile correspondant (float)
- `method` : `"quantile_grid"`
- `net_pnl`, `mdd`, `n_trades` : métriques du θ retenu sur validation
- Détails de tous les candidats évalués (pour traçabilité)

## Critères d'acceptation
- [x] Le θ retenu respecte `mdd <= mdd_cap` ET `n_trades >= min_trades`
- [x] Le θ retenu maximise `net_pnl` parmi les θ faisables
- [x] En cas d'ex-aequo sur `net_pnl` : le quantile le plus haut est préféré
- [x] Test : données synthétiques où un seul θ est faisable → sélection correcte
- [x] Test : plusieurs θ faisables → celui avec le meilleur `net_pnl` est retenu
- [x] Equity réinitialisée à `E_0 = 1.0` pour chaque candidat (pas d'effet de bord entre candidats)
- [x] Anti-fuite : modifier `y_hat_test` arbitrairement → θ identique
- [x] Paramètres lus depuis `config.thresholding` — pas de valeurs hardcodées
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/031-theta-optimization` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/031-theta-optimization` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-7] #031 RED: tests objectif d'optimisation et sélection θ` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-7] #031 GREEN: objectif d'optimisation et sélection θ`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-7] #031 — Objectif d'optimisation et sélection du seuil θ`.
