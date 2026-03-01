# Tâche — Sample builder (N, L, F)

Statut : DONE
Ordre : 016
Workstream : WS-4
Milestone : M2
Gate lié : G-Split

## Contexte
Le sample builder transforme le DataFrame 2D de features et le vecteur de labels en tenseurs 3D alignés pour l'entraînement des modèles. Chaque sample t correspond à une fenêtre glissante de L bougies sur F features.

Références :
- Plan : `docs/plan/implementation.md` (WS-4.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§7.1)
- Config : `configs/default.yaml` (section `window.L`)
- Code : `ai_trading/data/dataset.py` (à créer)

Dépendances :
- Tâche 015 — Calcul de la cible y_t (doit être DONE)

## Objectif
Pour chaque timestamp de décision t valide, construire la matrice `X_t ∈ R^{L×F}` (fenêtre `[t-L+1, ..., t]`). Produire :
- `X_seq` de shape `(N, L, F)` — float32.
- `y` de shape `(N,)` — float32.
- `timestamps` — index des timestamps de décision correspondants.

N = nombre de samples valides (après application de tous les masques).

## Règles attendues
- **Config-driven** : `L` lu depuis `config.window.L`.
- **Float conventions** : `X_seq` et `y` en float32 (spec §17).
- **Strict code** : aucun NaN dans `X_seq` ni `y` pour les samples retenus. Validation explicite.
- **Anti-fuite** : chaque fenêtre `[t-L+1, t]` ne contient que des données passées/présentes.

## Évolutions proposées
- Créer `ai_trading/data/dataset.py` avec `build_samples(features_df, y, final_mask, config) -> (X_seq, y_out, timestamps)`.
- Itérer sur les positions valides de `final_mask` et `label_mask`.
- Ne retenir que les positions t telles que `final_mask[t] == True` et toute la fenêtre `[t-L+1, t]` est dans `final_mask`.
- Convertir en `np.float32`.
- Valider l'absence de NaN dans les tenseurs produits.

## Critères d'acceptation
- [x] Shape `X_seq` correcte : `(N, L, F)` avec les bonnes dimensions.
- [x] Shape `y` correcte : `(N,)`.
- [x] `X_seq.dtype == np.float32` et `y.dtype == np.float32`.
- [x] Pas de NaN dans `X_seq` ni `y` pour les samples retenus.
- [x] N < N_total (warmup + trous + label invalides éliminés).
- [x] `L` lu depuis la config (pas hardcodé).
- [x] Chaque fenêtre contient les bonnes valeurs de features aux bons timestamps.
- [x] `timestamps` correspond aux timestamps de décision de chaque sample.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/016-sample-builder` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/016-sample-builder` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-4] #016 RED: tests sample builder`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-4] #016 GREEN: sample builder`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-4] #016 — Sample builder (N, L, F)`.
