# Tâche — Validation de l'adapter tabulaire XGBoost (flatten_seq_to_tab)

Statut : DONE
Ordre : 059
Workstream : WS-XGB-1
Milestone : MX-1
Gate lié : G-XGB-Ready

## Contexte

L'adapter tabulaire `flatten_seq_to_tab()` est déjà implémenté dans `ai_trading/data/dataset.py` (WS-4.3 du plan pipeline) et testé dans `tests/test_adapter_xgboost.py` (tâche #017). Ce work stream ne crée pas de nouveau code fonctionnel : il audite la couverture des tests existants par rapport à la spec modèle XGBoost §3 et complète les cas manquants si nécessaire.

Références :
- Plan : `docs/plan/models/implementation_xgboost.md` (WS-XGB-1.1)
- Spécification modèle : `docs/specifications/models/Specification_Modele_XGBoost_v1.0.md` (§3.1, §3.2, §3.3)
- Spécification pipeline : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§7.2)
- Code : `ai_trading/data/dataset.py` (`flatten_seq_to_tab`)
- Tests : `tests/test_adapter_xgboost.py`

Dépendances :
- Tâche 017 — WS-4 adapter XGBoost (doit être DONE) ✅

## Objectif

Valider que la fonction `flatten_seq_to_tab()` satisfait toutes les exigences de la spec XGBoost §3 :
1. Aplatissement C-order `reshape(X_seq, (N, L * F))`
2. Nommage des colonnes `{feature}_{lag}` (convention pipeline §7.2)
3. Conservation du dtype float32
4. Rejet des entrées non-3D avec `ValueError`

Compléter les tests si des cas de la spec ne sont pas couverts.

## Règles attendues

- **Pas de modification du code fonctionnel** : seuls les tests peuvent être ajoutés ou complétés.
- **Véracité C-order** : vérifier numériquement que les valeurs aplaties correspondent à `np.reshape` C-order (déjà couvert par `TestValues` dans les tests existants).
- **Stricte cohérence spec** : tout critère de §3 non couvert par un test doit être ajouté.

## Évolutions proposées

- Auditer `tests/test_adapter_xgboost.py` et comparer chaque critère de §3 de la spec modèle XGBoost.
- Ajouter les tests manquants identifiés lors de l'audit. Cas potentiels à vérifier :
  - Vérification que le dtype d'entrée autre que float32 est préservé (ou lever une erreur si la spec l'impose)
  - Test avec `feature_names` de longueur incorrecte → `ValueError`
  - Test edge case : `L=1` (une seule timestep) → shape `(N, F)`
  - Test edge case : `F=1` (une seule feature) → shape `(N, L)`
  - Test avec N grand (vérification shape seulement, pas de valeurs)

## Critères d'acceptation

- [x] Audit des tests existants documenté (couverture des 4 exigences §3)
- [x] Shape `(N, L·F)` correcte validée par tests (cas nominaux + bords)
- [x] Valeurs C-order vérifiées numériquement par tests
- [x] Dtype float32 préservé validé par tests
- [x] `ValueError` sur entrée non-3D validé par tests
- [x] Nommage colonnes `{feature}_{lag}` conforme validé par tests
- [x] Edge cases couverts : `L=1`, `F=1`, `feature_names` longueur incorrecte
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage

- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/059-xgb-adapter-validation` depuis `Max6000i1`.

## Checklist de fin de tâche

- [x] Branche `task/059-xgb-adapter-validation` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-XGB-1] #059 RED: tests complémentaires adapter tabulaire XGBoost` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-XGB-1] #059 GREEN: validation adapter tabulaire XGBoost`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-XGB-1] #059 — Validation adapter tabulaire XGBoost`.
