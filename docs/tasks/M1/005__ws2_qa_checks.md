# Tâche — Contrôles qualité (QA) obligatoires

Statut : DONE
Ordre : 005
Workstream : WS-2
Milestone : M1
Gate lié : M1

## Contexte
Les données OHLCV brutes téléchargées depuis Binance doivent passer des contrôles qualité (QA) obligatoires avant d'être utilisées par le pipeline. Ces contrôles détectent les anomalies structurelles qui pourraient compromettre l'intégrité des résultats.

Références :
- Plan : `docs/plan/implementation.md` (WS-2.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§4.2)
- Code : `ai_trading/data/qa.py` (à créer)

Dépendances :
- Tâche 004 — Ingestion OHLCV Binance (doit être DONE)

## Objectif
Implémenter un module `ai_trading/data/qa.py` qui effectue les contrôles qualité obligatoires sur un DataFrame OHLCV et retourne un rapport structuré ou lève des erreurs explicites.

## Règles attendues
- Strict code : chaque contrôle non satisfait lève une erreur explicite ou est reporté dans un rapport structuré (pas de passage silencieux).
- Données synthétiques pour les tests : aucun accès réseau dans les tests.
- Reproductibilité : les contrôles sont déterministes.

## Évolutions proposées
- Créer `ai_trading/data/qa.py` avec une fonction `run_qa_checks(df: pd.DataFrame, timeframe: str) -> QAReport`.
- Contrôle 1 — **Régularité temporelle** : vérifier que le pas Δ est uniforme selon le timeframe configuré. Pas de doublons de timestamp.
- Contrôle 2 — **Détection des trous** (missing candles) : identifier les positions où des bougies sont absentes par rapport au pas Δ attendu. Retourner la liste des timestamps manquants.
- Contrôle 3 — **Détection des outliers** :
  - Prix négatif (`open`, `high`, `low`, `close` < 0) → erreur.
  - Volume nul prolongé (à rapporter dans le QA report).
  - OHLC incohérent : `high >= max(open, close)` et `low <= min(open, close)`.
- `QAReport` : dataclass structurée contenant le statut de chaque contrôle, les détails des anomalies détectées et un statut global pass/fail.

## Critères d'acceptation
- [x] Données propres → QA passe (statut global = pass)
- [x] Doublons de timestamp détectés et signalés
- [x] Trous (missing candles) détectés avec la liste des timestamps manquants
- [x] Prix négatif → erreur explicite
- [x] OHLC incohérent (`high < open` ou `low > close`) → détecté et signalé
- [x] Volume nul prolongé → détecté et reporté
- [x] Pas Δ irrégulier (hors trous attendus) → détecté
- [x] `QAReport` retourné avec les détails structurés de chaque contrôle
- [x] Tests avec données synthétiques : tous les cas d'anomalie couverts
- [x] Tests couvrent les scénarios nominaux + erreurs + bords
- [x] Suite de tests verte après implémentation
- [x] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/005-qa-checks` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/005-qa-checks` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-2] #005 RED: tests contrôles qualité QA`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-2] #005 GREEN: contrôles qualité QA`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-2] #005 — Contrôles qualité QA`.
