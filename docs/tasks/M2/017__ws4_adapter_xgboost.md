# Tâche — Adapter tabulaire pour XGBoost

Statut : DONE
Ordre : 017
Workstream : WS-4
Milestone : M2
Gate lié : G-Split

## Contexte
XGBoost attend des entrées 2D tabulaires. L'adapter aplatit le tenseur 3D `(N, L, F)` en `(N, L*F)` par concaténation temporelle en C-order. Cette fonction est implémentée ici mais n'est invoquée qu'après le scaling (WS-5), par le modèle XGBoost dans son `fit()`/`predict()`.

Références :
- Plan : `docs/plan/implementation.md` (WS-4.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§7.2)
- Code : `ai_trading/data/dataset.py` (à étendre)

Dépendances :
- Tâche 016 — Sample builder (doit être DONE)

## Objectif
Implémenter `flatten_seq_to_tab(X_seq, feature_names) -> (X_tab, column_names)` :
1. Aplatir `(N, L, F)` → `(N, L*F)` en C-order (`np.reshape`).
2. Nommer les colonnes : `{feature}_{lag}` avec lag de 0 (plus ancien) à L-1 (plus récent).
3. Retourner le tableau 2D et la liste des noms de colonnes.

## Règles attendues
- **Strict code** : validation de la shape d'entrée. Si X_seq n'est pas 3D → `ValueError`.
- **Strict code** : `feature_names` doit avoir exactement F éléments, sinon `ValueError`.
- **Float conventions** : le dtype est préservé (float32).
- **Ordre C-order** : cohérent avec `np.reshape(X_seq, (N, L*F))` par défaut.

## Évolutions proposées
- Ajouter `flatten_seq_to_tab(X_seq, feature_names)` dans `ai_trading/data/dataset.py`.
- Nommage des colonnes : `[f"{feat}_{lag}" for lag in range(L) for feat in feature_names]` en C-order.
- Retourner `(X_tab: np.ndarray, column_names: list[str])`.

## Critères d'acceptation
- [x] Shape `(N, L*F)` correcte (ex : L=128, F=9 → 1152 colonnes).
- [x] Nommage des colonnes : `{feature}_{lag}` conforme.
- [x] Valeurs identiques à `X_seq` réarrangé (`np.reshape` C-order).
- [x] dtype préservé (float32).
- [x] X_seq non-3D → `ValueError`.
- [x] `feature_names` de taille ≠ F → `ValueError`.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/017-adapter-xgboost` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/017-adapter-xgboost` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-4] #017 RED: tests adapter tabulaire XGBoost`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-4] #017 GREEN: adapter tabulaire XGBoost`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-4] #017 — Adapter tabulaire XGBoost`.
