# Tâche — Page 4 : scatter plot prédictions vs réalisés (Go/No-Go)

Statut : TODO
Ordre : 086
Workstream : WS-D-5
Milestone : MD-3
Gate lié : N/A

## Contexte
La seconde section de la page d'analyse par fold affiche un scatter plot des prédictions vs réalisés avec coloration Go/No-Go selon le seuil θ du fold. La logique de reconstruction du signal dépend du type de sortie du modèle (`regression` vs `signal`). La fonction `chart_scatter_predictions()` est déjà implémentée dans `charts.py` (tâche #077). Le chargement des prédictions est implémenté dans `data_loader.py` (tâche #075).

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-5.2)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§8.3)
- Code : `scripts/dashboard/pages/4_fold_analysis.py`, `scripts/dashboard/charts.py`, `scripts/dashboard/data_loader.py`

Dépendances :
- Tâche 085 — Navigation fold et equity curve (doit être DONE)
- Tâche 075 — Data loader CSV (DONE)
- Tâche 077 — Charts library (DONE)

## Objectif
Implémenter dans `pages/4_fold_analysis.py` le scatter plot prédictions vs réalisés avec coloration Go/No-Go et métriques en encart.

## Règles attendues
- **Strict code** : pas de fallback silencieux. Le type de sortie est détecté via `strategy.output_type` dans `metrics.json`. En fallback (runs antérieurs sans ce champ), détection via `threshold.method == "none"`.
- **Anti-fuite** : le signal Go/No-Go est reconstruit dynamiquement par le dashboard à partir de `y_hat` et `θ`, conformément à §8.3. Aucune colonne signal n'est attendue dans `preds_test.csv`.
- **DRY** : réutiliser `load_predictions()` de `data_loader.py` et `chart_scatter_predictions()` de `charts.py`.

## Évolutions proposées
- Charger `preds_test.csv` du fold sélectionné via `load_predictions(fold_dir, "test")`.
- Récupérer θ depuis `metrics.json → folds[i].threshold.theta` et la méthode depuis `folds[i].threshold.method`.
- Récupérer le type de sortie via `metrics.json → strategy.output_type` (fallback : `threshold.method == "none"` → `signal`).
- Reconstruire le signal Go/No-Go (§8.3) :
  - Si `output_type == "regression"` : `signal = (y_hat > theta)`. Coloration vert (Go) / gris (No-Go).
  - Si `output_type == "signal"` : afficher un message informatif « Scatter plot non disponible pour les modèles de type signal » au lieu du graphique.
- Afficher via `chart_scatter_predictions()` : scatter y_hat (X) vs y_true (Y), diagonale pointillée, coloration Go/No-Go.
- Afficher les métriques en encart : MAE, RMSE, DA, IC, θ (§8.3). θ affiché comme `—` si `null`.
- Dégradation si `preds_test.csv` absent : message informatif.

## Critères d'acceptation
- [ ] Scatter plot avec coloration Go/No-Go correcte pour `output_type == "regression"`.
- [ ] Détection du type signal via `strategy.output_type` (ou fallback `method == "none"`), message informatif affiché.
- [ ] Diagonale de prédiction parfaite visible sur le scatter plot.
- [ ] Métriques en encart : MAE, RMSE, DA, IC, θ conformes à §8.3.
- [ ] θ affiché comme `—` si `null`.
- [ ] Dégradation gracieuse si prédictions absentes (message informatif).
- [ ] Tests couvrent : θ positif, θ négatif, θ = 0, θ null, `method == "none"` (signal), prédictions absentes.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/086-wsd5-predictions-scatter` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/086-wsd5-predictions-scatter` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-D-5] #086 RED: tests scatter prédictions Go/No-Go`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-D-5] #086 GREEN: scatter prédictions Go/No-Go`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-5] #086 — Page 4 : scatter plot prédictions vs réalisés`.
