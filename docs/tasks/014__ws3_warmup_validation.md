# Tâche — Warmup et validation de causalité

Statut : DONE
Ordre : 014
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
Après l'assemblage des features, il faut appliquer la zone de warmup (`min_warmup`) et vérifier l'absence de NaN résiduels dans la zone valide. Le masque de warmup est combiné avec le masque de trous (WS-2.3, tâche 006) pour produire le masque final de validité.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.7)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§6.6)
- Config : `configs/default.yaml` (section `window.min_warmup`)
- Code : `ai_trading/features/pipeline.py` (à étendre) ou `ai_trading/features/warmup.py` (à créer)

Dépendances :
- Tâche 006 — Politique de traitement des trous (doit être DONE)
- Tâche 013 — Feature pipeline (doit être DONE)

## Objectif
1. Appliquer `min_warmup` : invalider les `min_warmup` premières bougies dans le masque de validité.
2. Vérifier l'absence de NaN dans la zone valide (hors warmup) du DataFrame de features.
3. Combiner le masque de warmup avec le `valid_mask` de WS-2.3 (trous) pour produire le masque final.

## Règles attendues
- **Config-driven** : `min_warmup` lu depuis `config.window.min_warmup`.
- **Strict code** : si des NaN sont détectés dans la zone valide (hors warmup), lever une erreur explicite — pas de remplissage silencieux.
- **Assertion runtime min_warmup vs min_periods** : vérifier que `min_warmup >= max(f.min_periods for f in resolved_features)`. Cette assertion est un double-check runtime complémentaire à la validation statique de la config (tâche #003). Elle garantit que la zone de warmup couvre bien le nombre de NaN en tête de chaque feature instanciée (contrat `min_periods` = nombre de NaN en tête, cf. tâche #023).
- **Anti-fuite** : le masque n'utilise aucune information future.

## Évolutions proposées
- Implémenter une fonction `apply_warmup(features_df, valid_mask, min_warmup, feature_instances, params=None) -> final_mask` :
  - **Assertion** : `min_warmup >= max(f.min_periods for f in feature_instances)`, sinon `ValueError` explicite.
  - Crée un masque warmup : `False` pour les `min_warmup` premières lignes, `True` ensuite.
  - Combine : `final_mask = warmup_mask & valid_mask`.
  - Vérifie l'absence de NaN dans `features_df[final_mask]`. Si NaN détecté → `ValueError`.
- Retourner `final_mask` de shape `(N_total,)` booléen.

## Critères d'acceptation
- [x] Les `min_warmup` premières lignes sont toujours `False` dans le masque final.
- [x] Le masque final est la combinaison AND du masque warmup et du masque de trous.
- [x] Absence de NaN dans `features_df[final_mask]` vérifiée. NaN résiduel → `ValueError`.
- [x] `min_warmup` lu depuis la config (pas hardcodé).
- [x] `min_warmup < max(min_periods)` → `ValueError` explicite (assertion runtime).
- [x] Test : `min_warmup=200`, features avec 500 bougies sans trou → 300 samples valides.
- [x] Test : NaN injecté dans la zone post-warmup → erreur levée.
- [x] Test : combinaison avec trou dans les données → masque correct.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/014-warmup-validation` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/014-warmup-validation` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-3] #014 RED: tests warmup et validation causalité`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-3] #014 GREEN: warmup et validation causalité`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-3] #014 — Warmup et validation de causalité`.
