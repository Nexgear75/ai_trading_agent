# Tâche — Grille de quantiles pour calibration θ

Statut : TODO
Ordre : 030
Workstream : WS-7
Milestone : M3
Gate lié : M3

## Contexte
La calibration du seuil θ (Go/No-Go) commence par le calcul des seuils candidats via une grille de quantiles sur les prédictions de validation. Pour chaque quantile `q` de la grille, on calcule `θ(q) = quantile_q(ŷ_val)`. Ces candidats sont ensuite évalués dans WS-7.2 (objectif d'optimisation).

Références :
- Plan : `docs/plan/implementation.md` (WS-7.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§11.2)
- Code : `ai_trading/calibration/threshold.py` (à créer)

Dépendances :
- Tâche 028 — WS-6 fold trainer (doit être DONE) — pour obtenir `y_hat_val`

## Objectif
Implémenter le calcul de la grille de quantiles dans `ai_trading/calibration/threshold.py` : pour un vecteur de prédictions `y_hat_val`, calculer `θ(q) = quantile_q(y_hat_val)` pour chaque `q` dans `config.thresholding.q_grid`.

## Règles attendues
- **Config-driven** : la grille de quantiles `q_grid` est lue depuis `config.thresholding.q_grid` (ex: `[0.5, 0.6, 0.7, 0.8, 0.9, 0.95]`). Pas de valeurs hardcodées.
- **Anti-fuite** : les quantiles sont calculés uniquement sur `y_hat_val`, jamais sur `y_hat_test`.
- **Strict code** : lever une erreur si `y_hat_val` est vide ou si `q_grid` est invalide.

## Évolutions proposées

### 1. Fonction `compute_quantile_thresholds(y_hat_val, q_grid) → dict[float, float]`
- Pour chaque `q` dans `q_grid` : `θ(q) = numpy.quantile(y_hat_val, q)`
- Retour : dictionnaire `{q: θ(q)}` ou liste ordonnée de couples `(q, θ)`

### 2. Fonction `apply_threshold(y_hat, theta) → signals`
- `signals[t] = 1 si y_hat[t] > θ, sinon 0`
- Retour : vecteur de signaux binaires (0/1) de même shape que `y_hat`
- Utilisé par l'orchestrateur après `predict(X_test)` pour les modèles supervisés

## Critères d'acceptation
- [ ] Pour `q=0.5`, `θ ≈ médiane(y_hat_val)` (test numérique)
- [ ] Pour `q=0.0`, `θ = min(y_hat_val)`
- [ ] Pour `q=1.0`, `θ = max(y_hat_val)`
- [ ] Grille complète calculée correctement pour tous les quantiles de `q_grid`
- [ ] `apply_threshold` : `y_hat[t] > θ → 1`, `y_hat[t] <= θ → 0`
- [ ] `apply_threshold` retourne un vecteur de même shape que l'entrée
- [ ] Erreur levée si `y_hat_val` est vide
- [ ] Paramètres lus depuis `config.thresholding.q_grid`
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/030-quantile-grid` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/030-quantile-grid` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-7] #030 RED: tests grille de quantiles et apply_threshold` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-7] #030 GREEN: grille de quantiles pour calibration θ`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-7] #030 — Grille de quantiles pour calibration θ`.
