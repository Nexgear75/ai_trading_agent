---
name: implementing-request-change
description: Implémenter les corrections issues d'un document request_changes (revue globale ou PR). Traite les items BLOQUANT/WARNING/MINEUR par ordre de sévérité, avec tests, validation et commits structurés. À utiliser quand l'utilisateur demande « implémente les request changes 0001 », « corrige les bloquants du rapport ».
argument-hint: "[fichier: docs/request_changes/NNNN_slug.md] [scope: all|bloquants|warnings|mineurs|B-1,W-3]"
---

# Agent Skill — Implementing Request Change (AI Trading Pipeline)

## Objectif
Implémenter méthodiquement les corrections identifiées dans un document `docs/request_changes/NNNN_slug.md`, en respectant les conventions du projet, en préservant la cohérence intermodule et en livrant des corrections vérifiables avec tests et commits structurés.

## Contexte repo

> Les conventions complètes, la stack, les principes non négociables et la structure des workstreams sont définis dans **`AGENTS.md`** (racine du repo). Ce skill ne duplique pas AGENTS.md — il le **complète** avec le workflow opérationnel spécifique à l'implémentation de request changes.

- **Request changes** : `docs/request_changes/NNNN_slug.md`
- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`
- **Code source** : `ai_trading/` (package Python principal)
- **Tests** : `tests/` (pytest, config dans `pyproject.toml`)
- **Configs** : `configs/default.yaml` (Pydantic v2)
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)
- **Langue** : anglais pour code/tests, français pour docs/tâches

## Principes non négociables

> Source de vérité : **`AGENTS.md` § Règles non négociables**. Résumé opérationnel ci-dessous.

- **Zéro régression** : chaque correction doit laisser la suite de tests GREEN. Jamais de fix qui casse autre chose.
- **Strict code (no fallbacks)** : aucun fallback silencieux, aucun `or default`, aucun `except` trop large. Validation explicite + `raise`.
- **Config-driven** : tout paramètre modifiable lu depuis `configs/default.yaml`. Zéro hardcoding.
- **Anti-fuite** : ne jamais introduire de look-ahead. Données point-in-time.
- **Cohérence intermodule** : chaque correction doit être propagée à tous les modules impactés (appelants, consommateurs, tests). Un fix isolé qui crée une divergence ailleurs est interdit.
- **Ambiguïté** : si l'action demandée dans le rapport est ambiguë ou propose plusieurs options sans choix clair → demander des clarifications avant d'implémenter.

## Discipline de contexte

- Lire **ciblé** : charger uniquement les fichiers référencés dans chaque item du rapport.
- Ne pas charger le document de spécification par défaut : le lire **uniquement si nécessaire** pour vérifier une conformité.
- Préférer **exécuter** une commande plutôt que décrire longuement.

## Workflow standard

### 0. Pré-condition GREEN
Exécuter `pytest` → **tous les tests existants doivent être GREEN**.
Si RED : corriger d'abord les régressions avant de commencer les request changes.

### 1. Lire le document request_changes
Ouvrir `docs/request_changes/NNNN_slug.md` et extraire :
- Le **statut** du document (`TODO`, `IN_PROGRESS`, `DONE`). Si `DONE`, confirmer avec l'utilisateur avant de retravailler.
- La liste des items avec leur sévérité (BLOQUANT `B-N`, WARNING `W-N`, MINEUR `M-N`).
- Pour chaque item : fichiers impactés, description du problème, action demandée.
- Le scope demandé par l'utilisateur (all, bloquants uniquement, items spécifiques).

### 2. Trier et planifier

**Ordre d'implémentation obligatoire** : BLOQUANTS → WARNINGS → MINEURS.

Au sein d'une même sévérité, regrouper les items par **module impacté** pour minimiser les conflits et faciliter la cohérence :
- Si B-1 et B-2 touchent le même module, les traiter dans le même batch.
- Si un WARNING dépend d'un BLOQUANT (ex : W-2 dépend de B-1 car même fichier), traiter le BLOQUANT d'abord.

Créer un plan de travail via `manage_todo_list` avec un item par correction (ou par groupe de corrections liées).

### 3. Analyser l'impact de chaque item

Avant de coder, pour chaque item :

1. **Lire les fichiers référencés** dans le rapport pour comprendre le problème en contexte.
2. **Identifier tous les modules impactés** — pas seulement ceux listés dans le rapport. Utiliser `grep_search` pour trouver :
   - Tous les appels à la fonction/classe modifiée.
   - Tous les usages de la colonne/clé/constante renommée ou modifiée.
   - Tous les tests qui exercent le code modifié.
3. **Évaluer l'effet domino** : si le fix dans le module A change une signature ou un nom de colonne, lister tous les modules B, C, D qui doivent être mis à jour simultanément.
4. **Documenter le périmètre réel** dans le plan de travail (via `manage_todo_list`).

### 4. Implémenter la correction

Pour chaque item (ou groupe d'items liés) :

#### 4a. Écrire ou adapter les tests
- Si le rapport identifie un test manquant : l'écrire.
- Si le rapport identifie un test qui masque un bug (ex : fixture avec mauvais nom de colonne) : le corriger.
- Si la correction change un comportement observable : adapter les tests existants ET ajouter un test qui vérifie le nouveau comportement.
- **Vérifier que le test échoue avant le fix** (esprit TDD) quand c'est possible. Pour les corrections de cohérence (renommage, type), le test peut échouer avec `ImportError` ou `KeyError` — c'est suffisant.

#### 4b. Appliquer le fix dans le code source
- Modifier **tous** les fichiers impactés en une seule passe. Ne pas commiter un module corrigé si un autre module dépendant n'est pas encore mis à jour.
- **Strict code** : validation explicite + `raise`. Pas de fallbacks.
- **Cohérence intermodule** : après chaque modification, vérifier :
  - Les signatures sont cohérentes avec les appelants.
  - Les noms de colonnes/clés sont identiques partout.
  - Les types de retour sont inchangés ou mis à jour partout.
  - Les tests reflètent le nouveau comportement.

#### 4c. Corrections en cascade
Si le fix d'un item révèle un problème non listé dans le rapport (effet domino) :
- Le corriger immédiatement s'il est trivial (< 10 lignes, même module).
- Le documenter dans le commit message si c'est substantiel.
- Ne jamais laisser un état intermédiaire incohérent.

### 5. Valider (commandes exactes, obligatoires)

Exécuter **exactement** ces commandes après chaque groupe de corrections :
```bash
ruff check ai_trading/ tests/
pytest
```
- `ruff check ai_trading/ tests/` → **0 erreur, 0 warning**.
- `pytest` → **tous GREEN** (nouveaux + existants), aucune régression, 0 échec.

**Vérifications complémentaires** (si disponibles) :
```bash
pyright ai_trading/ tests/
```

**Ne jamais** passer au commit si `ruff check` ou `pytest` échoue.

### 6. Audit post-correction

Pour chaque groupe de corrections, vérifier :

#### 6a. Cohérence intermodule
- [ ] Aucune divergence de nommage entre modules (colonnes, clés config, signatures).
- [ ] Les registres (features, modèles) sont cohérents avec le code qui les consomme.
- [ ] Les structures de données partagées sont identiques partout.
- [ ] Les conventions numériques (dtypes, NaN, index) sont uniformes.
- [ ] Les imports croisés sont valides.

#### 6b. Non-régression
- [ ] Aucun test existant cassé.
- [ ] Aucun comportement modifié involontairement (vérifier les tests de non-régression).
- [ ] Les modules non listés dans le rapport mais impactés par effet domino ont été vérifiés.

#### 6c. Complétude du fix
- [ ] L'action demandée dans le rapport est entièrement réalisée.
- [ ] Le problème décrit ne peut plus se reproduire (pas de fix partiel).
- [ ] Si le rapport propose plusieurs options, le choix est documenté dans le commit.

### 7. Commit

**Format de commit** : un commit par item ou par groupe d'items liés.

```bash
git add <fichiers modifiés>
git commit -m "[RC-NNNN] FIX B-1: <résumé de la correction>"
```

**Convention de préfixe** :
- `[RC-NNNN] FIX B-1:` — correction d'un item BLOQUANT.
- `[RC-NNNN] FIX W-3:` — correction d'un item WARNING.
- `[RC-NNNN] FIX M-2:` — correction d'un item MINEUR.
- `[RC-NNNN] FIX B-1,B-2:` — correction groupée d'items liés.

**Contenu attendu** :
- Fichiers d'implémentation (`ai_trading/`) — si modifiés.
- Fichiers de tests (`tests/`) — si modifiés ou ajoutés.
- `configs/default.yaml` — si modifié.
- Jamais de fichiers hors périmètre de la correction.

### 8. Mettre à jour le document request_changes

Après correction de chaque item, mettre à jour le document `docs/request_changes/NNNN_slug.md` :

#### 8a. Transition de statut
- Au **premier item corrigé** : passer `Statut : TODO` → `Statut : IN_PROGRESS`.
- Quand **tous les items** du scope sont traités : passer `Statut : IN_PROGRESS` → `Statut : DONE`.
- Si le verdict initial était `⚠️ REQUEST CHANGES` et que tout est résolu : mettre à jour le verdict en `✅ CLEAN (après corrections)`.

#### 8b. Marquage des items
- Ajouter un indicateur de résolution en tête de chaque item traité :
  ```markdown
  ### B-1. ~~Mismatch colonne `timestamp` vs `timestamp_utc`~~ ✅ RÉSOLU
  ```
- Ajouter sous l'item la référence au commit :
  ```markdown
  > **Résolu** : commit `abc1234` — `[RC-0001] FIX B-1: timestamp → timestamp_utc dans QA`
  ```

### 9. Itérer

Répéter les étapes 3 à 8 pour chaque item ou groupe, dans l'ordre de sévérité.

### 10. Validation finale

Quand tous les items du scope demandé sont traités :

1. Exécuter la suite complète une dernière fois :
   ```bash
   ruff check ai_trading/ tests/
   pytest
   ```
2. Vérifier que **tous les items ciblés** sont marqués ✅ dans le document.
3. Pousser la branche :
   ```bash
   git push
   ```

## Gestion des choix (options multiples)

Quand le rapport propose plusieurs options pour un item (ex : « Option A: refactorer l'ABC » / « Option B: ajouter une assertion ») :

1. **Si l'utilisateur a précisé son choix** : l'implémenter.
2. **Si aucun choix n'est précisé** : demander à l'utilisateur via `ask_questions` avant d'implémenter. Ne pas deviner.
3. **Documenter le choix** dans le commit message et dans le document request_changes.

## Gestion des effets domino

Un fix peut révéler des problèmes non identifiés dans le rapport initial. Règles :

| Situation | Action |
|---|---|
| Fix trivial (< 10 lignes, même module) | Corriger immédiatement, documenter dans le commit. |
| Fix substantiel (nouveau module, > 10 lignes) | Documenter le nouveau problème, demander à l'utilisateur s'il faut le traiter maintenant ou créer un item séparé. |
| Contradiction avec la spec | **Stopper**. Signaler la contradiction à l'utilisateur. Ne pas choisir arbitrairement. |

## Procédure d'abandon

Si un item s'avère irréalisable (contradiction avec la spec, dépendance non mergée, impact trop large) :

1. **Documenter le blocage** dans le document request_changes sous l'item concerné.
2. **Informer l'utilisateur** avec la raison précise et la suggestion d'action.
3. **Passer à l'item suivant** sauf si le blocage impacte les items restants.
4. **Ne pas marquer l'item comme résolu**.

## Conventions

- **Branche** : les corrections sont appliquées sur la branche courante (typiquement `Max6000i1` ou une branche dédiée `rc/NNNN-slug` selon le choix de l'utilisateur).
- **Pas de mélange** : ne pas profiter d'un commit de correction pour ajouter des features ou du refactoring non demandé.
- **Atomicité** : chaque commit doit laisser la suite de tests GREEN. Pas de commit intermédiaire cassé.
- **Traçabilité** : chaque correction est traçable via le préfixe `[RC-NNNN]` dans le commit et la mise à jour du document.

## Exemple de session

```
Utilisateur : « implémente les request changes 0001, tous les bloquants »

Agent :
1. Lit docs/request_changes/0001_revue_globale_max6000i1.md
2. Identifie B-1 (timestamp mismatch) et B-2 (min_periods hardcodé)
3. Planifie : B-1 d'abord (qa.py + tests), puis B-2 (registry + features + tests)
4. Pour B-1 :
   - grep "timestamp" dans qa.py, test_qa.py → liste toutes les occurrences
   - grep "timestamp_utc" dans ingestion.py → confirme le nom canonique
   - Corrige qa.py + test_qa.py
   - pytest → GREEN
   - Commit : [RC-0001] FIX B-1: timestamp → timestamp_utc dans QA
5. Pour B-2 :
   - Demande à l'utilisateur : Option A ou B ?
   - Implémente le choix
   - pytest → GREEN
   - Commit : [RC-0001] FIX B-2: min_periods dynamique via config
6. Met à jour le document 0001 (items marqués ✅)
7. Push
```

````
