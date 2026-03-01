# Tâche — Refactoring min_periods : clarification contrat et cohérence

Statut : DONE
Ordre : 023
Workstream : WS-3
Milestone : M2
Gate lié : G-Features

## Contexte
L'interface `BaseFeature.min_periods` (property, int) manque d'une définition formelle de sa sémantique. Deux conventions coexistent dans le code :
- **logret_k, vol_N** : retournent le **nombre de NaN en tête** du résultat (= index 0-based du premier valide).
- **rsi_14** : retourne `15` (= nombre de barres d'input nécessaires, soit `rsi_period + 1`), alors que le premier résultat non-NaN est à l'index `14`.

Cette incohérence n'a pas d'impact fonctionnel immédiat car le warmup pipeline utilise `config.window.min_warmup` (§6.6), mais elle viole le principe de contrat uniform et pourrait induire des bugs si `min_periods` était consommé à l'avenir.

Références :
- Plan : `docs/plan/implementation.md` (WS-3.6, point 1)
- Code : `ai_trading/features/registry.py` (BaseFeature.min_periods)
- Code : `ai_trading/features/rsi.py` (RSI14.min_periods)

Dépendances :
- Tâche 007 — Registre de features (DONE)
- Tâche 008 — Log-returns (DONE)
- Tâche 009 — Volatilité (DONE)
- Tâche 010 — RSI (DONE)

## Objectif
1. Clarifier la docstring de `BaseFeature.min_periods` avec une définition sans ambiguïté.
2. Corriger `RSI14.min_periods` pour retourner `14` au lieu de `15` (cohérence).
3. Mettre à jour les tests existants pour vérifier la convention uniformément.

## Règles attendues
- **Convention fixée** : `min_periods` = nombre de NaN en tête du résultat = index 0-based du premier valide.
- **Cohérence** : toutes les features existantes (logret_1/2/4, vol_24/72, rsi_14) respectent cette convention.
- **Pas de breaking change externe** : la property reste une property sans argument.

## Évolutions proposées
1. **`ai_trading/features/registry.py`** — Mettre à jour la docstring de `BaseFeature.min_periods` :
   - Ancienne : "Minimum number of bars before the first valid (non-NaN) value."
   - Nouvelle : "Number of leading NaN values in the output. Equivalently, the 0-based index of the first non-NaN value. Example: if compute() returns [NaN, NaN, 0.5, ...], min_periods = 2."
2. **`ai_trading/features/rsi.py`** — Modifier `RSI14.min_periods` :
   - Ancienne valeur : `15`
   - Nouvelle valeur : `14`
   - Simplifier la docstring (supprimer le long commentaire de mise en garde).
3. **`tests/test_rsi.py`** — Mettre à jour les assertions qui testent `min_periods == 15` → `14`.
4. **`tests/test_feature_registry.py`** — Ajouter un test vérifiant que `min_periods` correspond au nombre réel de NaN en tête pour une feature concrète (convention enforcement).

## Critères d'acceptation
- [x] La docstring de `BaseFeature.min_periods` définit explicitement la sémantique "nombre de NaN en tête".
- [x] `RSI14().min_periods` retourne `14`.
- [x] Pour chaque feature existante, `min_periods` correspond au nombre réel de NaN en tête sur un dataset de test suffisamment grand.
- [x] Aucune régression : `pytest` GREEN, `ruff check` clean.
- [x] Tests couvrent les scénarios nominaux + cohérence min_periods ↔ NaN count.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/023-min-periods-contract` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/023-min-periods-contract` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-3] #023 RED: tests contrat min_periods`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] **Commit GREEN** : `[WS-3] #023 GREEN: clarification contrat min_periods et correction RSI`.
- [x] `ruff check ai_trading/ tests/` clean.
- [x] Suite pytest complète GREEN.
- [x] Statut mis à jour : DONE.
