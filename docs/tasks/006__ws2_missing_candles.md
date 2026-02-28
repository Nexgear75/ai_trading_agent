# Tâche — Politique de traitement des trous (missing candles)

Statut : DONE
Ordre : 006
Workstream : WS-2
Milestone : M1
Gate lié : M1

## Contexte
Le pipeline MVP n'interpole pas les données manquantes. Au lieu de cela, les bougies manquantes sont détectées et tout sample dont la fenêtre d'entrée ou de sortie touche un trou est invalidé via un masque booléen. Ce masque sera combiné ultérieurement avec le masque de warmup (WS-3.7) pour produire le masque final de validité des samples.

Références :
- Plan : `docs/plan/implementation.md` (WS-2.3)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§4.3, §6.6)
- Code : `ai_trading/data/` (module à créer, ex: `missing.py`)

Dépendances :
- Tâche 005 — Contrôles qualité QA (doit être DONE)

## Objectif
Implémenter la politique MVP de traitement des bougies manquantes : pas d'interpolation, invalidation des samples affectés via un masque booléen `valid_mask`.

## Règles attendues
- Strict code : pas d'interpolation, pas de remplissage silencieux des trous.
- Anti-fuite : le masque est calculé de façon strictement causale (pas de dépendance sur des données futures).
- Les paramètres `L` (fenêtre d'entrée) et `H` (horizon label) sont lus depuis la configuration.

## Évolutions proposées
- Créer un module (ex: `ai_trading/data/missing.py`) avec une fonction `compute_valid_mask(timestamps: pd.Series, timeframe: str, L: int, H: int) -> np.ndarray`.
- Étape 1 : détecter les positions des bougies manquantes à partir des timestamps et du pas Δ attendu.
- Étape 2 : pour chaque indice `t`, marquer comme invalide (`False`) si la fenêtre d'entrée `[t-L+1, t]` ou la fenêtre de sortie `[t+1, t+H]` touche un trou.
- Retourner un masque booléen `valid_mask` de shape `(N,)` où `N` est le nombre total de bougies.

## Critères d'acceptation
- [x] Un trou à l'indice `k` invalide tous les samples dans la zone `[k-H, k+L-1]` (fenêtre d'entrée + fenêtre de sortie)
- [x] Masque booléen `valid_mask` de shape `(N,)` retourné correctement
- [x] Données sans trou → masque tout à `True` (sauf les bords qui ne peuvent pas former un sample complet)
- [x] Plusieurs trous → masque correctement combiné
- [x] Pas d'interpolation : aucune valeur n'est modifiée dans les données
- [x] Compatible avec les paramètres `L` et `H` de la configuration
- [x] Tests avec données synthétiques contenant des trous à positions connues
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/006-missing-candles` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/006-missing-candles` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-2] #006 RED: tests politique missing candles`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-2] #006 GREEN: politique missing candles`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-2] #006 — Politique missing candles`.
