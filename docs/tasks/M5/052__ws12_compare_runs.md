# Tâche — Script de comparaison inter-stratégies (post-MVP)

Statut : TODO
Ordre : 052
Workstream : WS-12
Milestone : M5
Gate lié : N/A

## Contexte
Après exécution de plusieurs runs (modèles + baselines), un script de comparaison charge les `metrics.json`, produit un tableau comparatif et vérifie le critère §14.4 : le meilleur modèle bat au moins une baseline en P&L net ou MDD. La comparaison distingue les stratégies Go/No-Go entre elles et la comparaison contextuelle avec buy & hold (§13.4).

Références :
- Plan : `docs/plan/implementation.md` (WS-12.5)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§13.4, §14.4)
- Code : `scripts/compare_runs.py`

Dépendances :
- Tâche 046 — Metrics builder (doit être DONE, pour les `metrics.json` produits)

## Objectif
Implémenter le script `scripts/compare_runs.py` qui :
1. Charge les `metrics.json` de plusieurs runs (passés en arguments CLI).
2. Produit un tableau comparatif (CSV et/ou Markdown).
3. Distingue explicitement :
   - (1) Comparaison « pomme-à-pomme » entre stratégies Go/No-Go (modèles, SMA, no-trade).
   - (2) Comparaison contextuelle avec buy & hold.
4. Vérifie le critère §14.4 : le meilleur modèle bat au moins une baseline.

## Règles attendues
- Post-MVP : ce script est exécuté manuellement après tous les runs, pas intégré dans le pipeline principal.
- La comparaison §13.4 est correctement séparée en deux types.
- Strict code : erreur explicite si un fichier `metrics.json` est invalide ou manquant.

## Évolutions proposées
- Script CLI standalone `scripts/compare_runs.py` avec arguments `--runs` (chemins des `metrics.json`).
- Sortie CSV (`comparison.csv`) et Markdown (`comparison.md`).
- Fonction `load_metrics(paths) -> list[dict]`.
- Fonction `compare_strategies(metrics_list) -> DataFrame`.
- Fonction `check_criterion_14_4(comparison) -> bool`.

## Critères d'acceptation
- [ ] Le script `scripts/compare_runs.py` existe et est exécutable.
- [ ] Avec 2+ fichiers `metrics.json` synthétiques, le script identifie la meilleure stratégie.
- [ ] Le critère §14.4 est vérifié et le résultat est affiché.
- [ ] Les deux types de comparaison (Go/No-Go vs contextuelle) sont clairement séparés dans la sortie.
- [ ] Le tableau CSV/Markdown est produit et lisible.
- [ ] Erreur explicite si un `metrics.json` est invalide ou introuvable.
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords.
- [ ] Suite de tests verte après implémentation.
- [ ] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/052-compare-runs` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/052-compare-runs` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-12] #052 RED: tests comparaison inter-stratégies`.
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-12] #052 GREEN: script comparaison inter-stratégies`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-12] #052 — Script de comparaison inter-stratégies`.
