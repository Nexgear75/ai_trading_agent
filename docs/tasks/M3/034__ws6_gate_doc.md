# Tâche — Pré-gate G-Doc (vérification structurelle M3)

Statut : DONE
Ordre : 034
Workstream : WS-6
Milestone : M3
Gate lié : G-Doc

## Contexte
Le pré-gate G-Doc est positionné après tous les WS de M3 et sert de pré-condition au gate M3. Il vérifie la cohérence structurelle du contrat plug-in, des registres et des attributs. Sans G-Doc validé, le gate M3 ne peut pas être `GO`. Note : la vérification de complétude des registres (incluant les baselines) est déportée au gate M4.

Références :
- Plan : `docs/plan/implementation.md` (Pré-gate M3 : G-Doc)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§10, §11)
- Code : `ai_trading/models/`, `ai_trading/calibration/`

Dépendances :
- Tâche 024 — BaseModel ABC et MODEL_REGISTRY (doit être DONE)
- Tâche 025 — DummyModel (doit être DONE)
- Tâche 028 — Fold trainer (doit être DONE)
- Tâche 033 — Bypass calibration θ (doit être DONE)
- Toutes les tâches M3 doivent être DONE

## Objectif
Écrire les tests de validation structurelle G-Doc qui vérifient les 6 critères du pré-gate : attributs, registres, docstrings, bypass θ, et anti-fuite calibration.

## Règles attendues
- **Automatisable** : chaque critère G-Doc est vérifié par un test automatisé (`pytest`).
- **Non-régression** : ces tests restent dans la suite de tests pour prévenir les régressions.
- **Exhaustif** : les 6 critères du plan doivent être couverts.

## Évolutions proposées

### 1. Tests G-Doc dans `tests/test_gate_doc.py`

**Critère 1 — `output_type` déclaré et correct :**
- `DummyModel.output_type == "regression"`
- Vérifier que l'attribut est un attribut de classe (pas d'instance)

**Critère 2 — `execution_mode` par défaut :**
- `DummyModel.execution_mode == "standard"` (hérité de BaseModel)

**Critère 3 — Cohérence registres partielle :**
- `set(MODEL_REGISTRY.keys()) ⊆ set(VALID_STRATEGIES)` (sous-ensemble, pas égalité)
- À M3, `MODEL_REGISTRY` contient au minimum `{"dummy"}`
- Note : la complétude `==` est vérifiée au gate M4 après ajout des baselines

**Critère 4 — Docstrings conformes :**
- `BaseModel` a une docstring non vide
- `DummyModel` a une docstring non vide
- Les méthodes abstraites (`fit`, `predict`, `save`, `load`) ont des docstrings
- Les docstrings mentionnent les shapes et types (vérification par inspection)

**Critère 5 — Bypass θ fonctionnel :**
- Un modèle factice avec `output_type = "signal"` → calibration bypassée sur données synthétiques
- Les signaux binaires passent directement sans modification

**Critère 6 — Anti-fuite calibration (G-Leak/Calibration) :**
- Test de perturbation : calibrer θ sur `y_hat_val`, puis modifier `y_hat_test` arbitrairement → θ retourné est identique
- θ est indépendant de `y_hat_test`

## Critères d'acceptation
- [x] Critère G-Doc 1 vérifié par test : `DummyModel.output_type == "regression"`
- [x] Critère G-Doc 2 vérifié par test : `DummyModel.execution_mode == "standard"`
- [x] Critère G-Doc 3 vérifié par test : `set(MODEL_REGISTRY) ⊆ set(VALID_STRATEGIES)`
- [x] Critère G-Doc 4 vérifié par test : docstrings présentes et conformes sur `BaseModel` et `DummyModel`
- [x] Critère G-Doc 5 vérifié par test : bypass θ fonctionnel pour `output_type == "signal"`
- [x] Critère G-Doc 6 vérifié par test : θ indépendant de `y_hat_test` (perturbation)
- [x] Tous les tests G-Doc passent (`pytest tests/test_gate_doc.py -v`)
- [x] Suite de tests complète verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/034-gate-doc` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/034-gate-doc` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-6] #034 RED: tests pré-gate G-Doc` (fichiers de tests uniquement).
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-6] #034 GREEN: pré-gate G-Doc validé`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-6] #034 — Pré-gate G-Doc (vérification structurelle M3)`.
