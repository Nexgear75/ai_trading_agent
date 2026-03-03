# Tâche — Seed manager

Statut : DONE
Ordre : 048
Workstream : WS-12
Milestone : M5
Gate lié : M5

## Contexte
La reproductibilité impose de fixer les seeds globales (numpy, random, torch, PYTHONHASHSEED) une seule fois au début de chaque run. Le seed manager centralise cette responsabilité. L'option `deterministic_torch` active `torch.use_deterministic_algorithms(True)` avec un fallback documenté `warn_only=True` pour les opérations CUDA non déterministes.

Références :
- Plan : `docs/plan/implementation.md` (WS-12.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§16.1)
- Code : `ai_trading/utils/seed.py`

Dépendances :
- Tâche 002 — Config loader (doit être DONE, pour `reproducibility.global_seed`)

## Objectif
Implémenter le module `ai_trading/utils/seed.py` qui :
1. Fixe la seed globale pour : `random.seed()`, `numpy.random.seed()`, `os.environ['PYTHONHASHSEED']`.
2. Si PyTorch est installé : `torch.manual_seed()`, `torch.cuda.manual_seed_all()`.
3. Si `deterministic_torch=True` et PyTorch disponible : `torch.use_deterministic_algorithms(True)`. Si une opération CUDA non déterministe lève une erreur, fallback vers `torch.use_deterministic_algorithms(True, warn_only=True)` avec un warning explicite loggé au niveau WARNING (exception documentée au strict-no-fallback).
4. Appelé une seule fois au début du run par l'orchestrateur.

## Règles attendues
- Config-driven : la seed est lue depuis `config.reproducibility.global_seed`, pas hardcodée.
- Strict code : la seed doit être un entier strictement positif — validation explicite.
- Le fallback `warn_only=True` pour le déterminisme CUDA est une **exception documentée** : jamais silencieux, toujours loggé au WARNING.
- La note XGBoost : la seed doit être transmise comme `random_state=seed` dans les hyperparamètres — à la charge de l'implémentation du modèle XGBoost (pas dans le seed manager).

## Évolutions proposées
- Fonction `set_global_seed(seed: int, deterministic_torch: bool) -> None`.
- La fonction gère gracieusement l'absence de PyTorch (import optionnel).

## Critères d'acceptation
- [x] Le module `ai_trading/utils/seed.py` existe et est importable.
- [x] `set_global_seed(42, False)` fixe les seeds pour `random`, `numpy`, `PYTHONHASHSEED`.
- [x] `set_global_seed(42, True)` active en plus `torch.use_deterministic_algorithms(True)` si PyTorch est installé.
- [x] Si PyTorch n'est pas installé, la fonction ne plante pas (import optionnel, pas de fallback silencieux — log INFO indiquant que PyTorch n'est pas disponible).
- [x] Si `deterministic_torch=True` et que l'activation échoue, le fallback `warn_only=True` est activé et un warning est loggé au niveau WARNING.
- [x] Deux appels successifs avec la même seed produisent les mêmes séquences `numpy.random.rand(10)` et `random.random()`.
- [x] Erreur explicite si seed non entier ou négatif.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/048-seed-manager` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/048-seed-manager` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-12] #048 RED: tests seed manager`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-12] #048 GREEN: seed manager`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-12] #048 — Seed manager`.
