# Tâche — Embargo et purge

Statut : DONE
Ordre : 020
Workstream : WS-4
Milestone : M2
Gate lié : G-Split

## Contexte
L'embargo est le mécanisme anti-fuite central du pipeline : il garantit qu'aucun label du train/val ne dépend de prix dans la zone test. La purge retire les samples dont le look-ahead (horizon H) chevauche la zone d'embargo ou de test.

Références :
- Plan : `docs/plan/implementation.md` (WS-4.6, schéma temporel, exemple numérique, convention des bornes A-05)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§8.2, §8.4)
- Config : `configs/default.yaml` (section `splits.embargo_bars`, `label.horizon_H_bars`)
- Code : `ai_trading/data/splitter.py` (à étendre)

Dépendances :
- Tâche 019 — Walk-forward splitter (doit être DONE)

## Objectif
Appliquer la règle de purge exacte de la spec §8.2 :
1. Définir `purge_cutoff = test_start − embargo_bars × Δ`.
2. Un sample t est autorisé dans train/val ssi `t + H × Δ <= purge_cutoff`.
3. Supprimer les samples de la zone tampon entre val et test.
4. Vérifier la disjonction stricte par test automatisé.

## Règles attendues
- **Anti-fuite** : c'est la règle cruciale. Aucun label du train/val ne doit chevaucher la zone test.
- **Config-driven** : `embargo_bars` et `horizon_H_bars` lus depuis la config.
- **Strict code** : l'embargo est appliqué une seule fois (pas de double embargo). Le `purge_cutoff` du plan est équivalent au `train_end` de la spec §8.2.
- **Pas d'embargo train↔val** : conformément à la spec §8, aucun embargo entre train_only et val (hors scope MVP).

## Évolutions proposées
- Étendre le splitter (tâche 019) avec une fonction de purge :
  - `apply_purge(fold_info, timestamps, H, delta) -> fold_info_purged`.
  - Retire du train/val les samples t tels que `t + H × Δ > purge_cutoff`.
  - Met à jour les compteurs (`n_train`, `n_val`) après purge.
- Intégrer la purge dans le workflow du splitter.
- La purge produit le `purge_cutoff` pour chaque fold (stocké dans `FoldInfo`).

## Critères d'acceptation
- [x] Aucun label du train ne dépend d'un prix dans la zone test (vérifié sample par sample).
- [x] Gap d'au moins `embargo_bars` bougies entre le dernier label train/val et le premier timestamp test.
- [x] Formule respectée : pour tout sample t du train/val, `t + H × Δ <= purge_cutoff`.
- [x] **Test E2E** : pour chaque fold, `max(t + H × Δ for t in train_val_samples) < test_start`.
- [x] Pas de double embargo : gap entre `train_val_end` et `test_start` = `(embargo_bars + 1) × Δ` (convention bornes inclusives).
- [x] `embargo_bars` et `horizon_H_bars` lus depuis la config (pas hardcodés).
- [x] Exemple numérique du plan vérifié : avec les paramètres MVP, exactement 3 derniers samples de val sont purgés.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/020-embargo-purge` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/020-embargo-purge` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-4] #020 RED: tests embargo et purge`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-4] #020 GREEN: embargo et purge`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-4] #020 — Embargo et purge`.
