# Tâche — DummyModel pour tests d'intégration

Statut : DONE
Ordre : 025
Workstream : WS-6
Milestone : M3
Gate lié : G-Doc

## Contexte
Avant d'intégrer les vrais modèles ML/DL, le pipeline a besoin d'un modèle factice (`DummyModel`) pour valider le workflow de bout en bout : fit → predict → save → load. Ce modèle retourne des prédictions aléatoires (seed fixée) ou une constante, permettant de tester toute la chaîne sans dépendance à des frameworks ML.

Références :
- Plan : `docs/plan/implementation.md` (WS-6.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§10)
- Code : `ai_trading/models/dummy.py` (à créer)

Dépendances :
- Tâche 024 — BaseModel ABC et MODEL_REGISTRY (doit être DONE)

## Objectif
Implémenter `DummyModel(BaseModel)` enregistré via `@register_model("dummy")`, avec sérialisation JSON minimale et prédictions reproductibles.

## Règles attendues
- **Reproductibilité** : prédictions identiques pour une même seed, vérifiable sur plusieurs appels.
- **Strict code** : pas de logique complexe — le DummyModel est un outil de test, pas un modèle réel.
- **Contrat BaseModel** : doit satisfaire intégralement le contrat défini en WS-6.1.

## Évolutions proposées

### 1. Classe `DummyModel(BaseModel)` dans `ai_trading/models/dummy.py`
- `output_type = "regression"` (le DummyModel simule un modèle supervisé)
- `execution_mode = "standard"` (hérité du défaut BaseModel)
- `fit()` : stocke la seed, ne fait rien d'autre (no-op fonctionnel)
- `predict(X)` : retourne un vecteur `y_hat` de shape `(N,)` généré avec `numpy.random.default_rng(seed)` ou une constante configurable
- `save(path)` : exporte un fichier JSON minimal `{"seed": 42, "constant": 0.0}`
- `load(path)` : recharge le JSON et restaure l'état interne

### 2. Enregistrement dans le registre
- Décorateur `@register_model("dummy")` sur la classe
- Auto-import dans `ai_trading/models/__init__.py` pour que le registre soit peuplé à l'import du package

## Critères d'acceptation
- [x] `DummyModel` hérite de `BaseModel` et est importable depuis `ai_trading.models.dummy`
- [x] `DummyModel.output_type == "regression"`
- [x] `DummyModel.execution_mode == "standard"`
- [x] `fit()` exécutable sans erreur (accepte tous les paramètres du contrat, y compris `meta_train`, `meta_val`, `ohlcv`)
- [x] `predict(X)` retourne un `ndarray` de shape `(N,)` en float
- [x] Prédictions reproductibles : deux appels avec la même seed produisent le même résultat
- [x] `save(path)` crée un fichier JSON lisible
- [x] `load(path)` restaure l'état et `predict()` donne le même résultat qu'avant `save()`
- [x] `MODEL_REGISTRY["dummy"]` résout vers `DummyModel`
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/025-dummy-model` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/025-dummy-model` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-6] #025 RED: tests DummyModel fit/predict/save/load` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-6] #025 GREEN: DummyModel pour tests d'intégration`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-6] #025 — DummyModel pour tests d'intégration`.
