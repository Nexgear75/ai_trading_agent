# Tâche — Standard scaler (fit-on-train)

Statut : DONE
Ordre : 021
Workstream : WS-5
Milestone : M2
Gate lié : G-Split

## Contexte
La normalisation des features est indispensable pour les modèles DL et améliore la convergence des modèles ML. Le standard scaler est la méthode par défaut du MVP. La règle anti-fuite fondamentale : le scaler est fit **uniquement** sur les données train.

Références :
- Plan : `docs/plan/implementation.md` (WS-5.1)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§9.1, Annexe E.2.7)
- Config : `configs/default.yaml` (section `scaling.method`, `scaling.epsilon`)
- Code : `ai_trading/data/scaler.py` (à créer)

Dépendances :
- Tâche 020 — Embargo et purge (doit être DONE)

## Objectif
Implémenter le standard scaler dans `ai_trading/data/scaler.py` :
1. `fit(X_train)` : estimer μ_j et σ_j sur l'ensemble des N_train × L valeurs pour chaque feature j (reshape `(N, L, F)` → `(N*L, F)`).
2. `transform(X)` : appliquer `(x - μ) / (σ + ε)` élément par élément sur le tenseur 3D (broadcast).
3. Guard constante : si `σ_j < 1e-8`, fixer la feature j à 0.0 après scaling + warning.
4. Sauvegarder/charger les paramètres (μ, σ) pour reproductibilité.

## Règles attendues
- **Anti-fuite** : `fit()` n'utilise **jamais** de données val ou test. Assertion explicite.
- **Config-driven** : `epsilon` lu depuis `config.scaling.epsilon`.
- **Strict code** : NaN dans X_train avant scaling → `raise ValueError("NaN in X_train before scaling")`.
- **Strict code** : guard constante avec seuil `CONSTANT_FEATURE_SIGMA_THRESHOLD = 1e-8` défini comme constante dans le module.
- **Float conventions** : opérations en float32 sur les tenseurs.

## Évolutions proposées
- Créer `ai_trading/data/scaler.py` avec une classe `StandardScaler` :
  - `fit(X_train: np.ndarray) -> self` : accepte shape `(N, L, F)`, calcule μ et σ par feature j.
  - `transform(X: np.ndarray) -> np.ndarray` : accepte shape `(N, L, F)`, retourne même shape.
  - `fit_transform(X_train) -> np.ndarray` : raccourci.
  - `save(path)` / `load(path)` : sérialisation des paramètres (μ, σ, ε) en npz ou JSON.
  - Constante : `CONSTANT_FEATURE_SIGMA_THRESHOLD = 1e-8`.
- Le scaler est instancié et utilisé par le fold trainer (WS-6.3), pas directement par l'orchestrateur.

## Critères d'acceptation
- [x] Stats (μ, σ) estimées uniquement sur X_train (X_val/X_test non vus).
- [x] Moyenne du train transformé ≈ 0 (tolérance `atol=1e-5`).
- [x] Écart-type du train transformé ≈ 1 (tolérance `atol=1e-5`).
- [x] `epsilon` lu depuis la config (pas hardcodé).
- [x] NaN dans X_train → `ValueError`.
- [x] Feature constante (σ < 1e-8) → sortie = 0.0 + warning émis via logging.
- [x] Paramètres (μ, σ) sérialisables et rechargeable (save/load).
- [x] Shape d'entrée validée : non-3D → `ValueError`.
- [x] Transform préserve le dtype float32.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/021-standard-scaler` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/021-standard-scaler` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-5] #021 RED: tests standard scaler`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-5] #021 GREEN: standard scaler`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-5] #021 — Standard scaler`.
