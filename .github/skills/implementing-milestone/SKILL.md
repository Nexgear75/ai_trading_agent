---
name: implementing-milestone
description: Implémente toutes les tâches d'un milestone AI Trading Pipeline (M1..M6, MX-1..MX-3, MD-1..MD-4) de bout en bout. Crée la branche milestone, invoque implementing-task pour chaque tâche, effectue une revue globale itérative, puis ouvre et merge la PR. À utiliser quand l'utilisateur demande « implémente le milestone M1 », « travaille sur MX-2 », « lance le milestone MD-1 ».
argument-hint: "[milestone: M1|M2|M3|M4|M5|M6|MX-1|MX-2|MX-3|MD-1|MD-2|MD-3|MD-4]"
---

# Agent Skill — Implementing Milestone (AI Trading Pipeline)

## Objectif

Orchestrer l'implémentation complète d'un milestone en enchaînant quatre phases :

- **Phase A** : création de la branche milestone + implémentation de chaque tâche via le skill `implementing-task`.
- **Phase B** : revue de code globale itérative (jusqu'à 5 passages) + application des corrections.
- **Phase C** : ouverture de la Pull Request + traitement de la review GitHub automatique.
- **Phase D** : merge de la PR.

## Contexte repo

Le projet comprend le **pipeline principal** et des **extensions** (modèles, dashboard). Le skill détecte automatiquement le scope à partir du préfixe du milestone.

### Scope : Pipeline principal (milestones M1..M6)

- **Plan** : `docs/plan/implementation.md` (WS-1..WS-13, M1..M6)
- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`
- **Code source** : `ai_trading/`
- **Tâches** : `docs/tasks/M<N>/NNN__slug.md`
- **Linter** : `ruff check ai_trading/ tests/`
- **Git add** : `git add ai_trading/ tests/ configs/`

### Scope : Extension modèle (milestones MX-*)

- **Plan** : `docs/plan/models/` (ex : `implementation_xgboost.md`)
- **Spécification** : `docs/specifications/models/` (ex : `Specification_Modele_XGBoost_v1.0.md`)
- **Code source** : `ai_trading/` (principalement `ai_trading/models/`)
- **Tâches** : `docs/tasks/MX-<N>/NNN__slug.md`
- **Linter** : `ruff check ai_trading/ tests/`
- **Git add** : `git add ai_trading/ tests/ configs/`

### Scope : Extension Streamlit dashboard (milestones MD-*)

- **Plan** : `docs/plan/streamlit/implementation.md`
- **Spécification** : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md`
- **Code source** : `scripts/dashboard/`
- **Tâches** : `docs/tasks/MD-<N>/NNN__slug.md`
- **Linter** : `ruff check scripts/dashboard/ tests/`
- **Git add** : `git add scripts/dashboard/ tests/`

### Commun à tous les scopes

- **Tests** : `tests/` (pytest)
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)
- **Revues globales** : `docs/request_changes/review_<MILESTONE>_v<N>.md`
- **Branche par défaut** : `Max6000i1`

### Détection automatique du scope

À l'étape A.a, le préfixe du milestone détermine le scope :
- `MX-*` → scope **modèle** → chemins code `ai_trading/`, spec `docs/specifications/models/`
- `MD-*` → scope **streamlit** → chemins code `scripts/dashboard/`, spec `docs/specifications/streamlit/`
- `M<N>` (sans X ni D) → scope **pipeline** → chemins code `ai_trading/`, spec pipeline

Dans tout le workflow, les commandes `ruff check`, `git add` et la vérification de pertinence (spec de référence) utilisent les chemins du scope détecté. Les exemples ci-dessous utilisent le placeholder `<CODE_DIR>` pour le répertoire code source du scope.

## Principes non négociables

- **Zéro ghost completion** : ne jamais sauter une tâche, ne jamais marquer DONE sans exécution vérifiée.
- **Ordre des tâches** : respecter les dépendances déclarées dans chaque fichier de tâche.
- **Toutes sévérités corrigées** : lors de la revue globale (Phase B), les items BLOQUANT, WARNING **et** MINEUR sont tous corrigés après vérification de leur pertinence.
- **Pas de merge si tests RED** : vérifier `pytest` GREEN avant chaque étape de push/merge.

---

# WORKFLOW ORCHESTRATEUR

## Paramètre d'entrée

```
Milestone cible : <MILESTONE>  (ex : M1, M2, MX-1, MX-2, MD-1, MD-3)
```

---

## PHASE A — Branche milestone et implémentation des tâches

### A.a — Créer la branche milestone

1. Vérifier que `Max6000i1` est à jour :
   ```bash
   git checkout Max6000i1
   git pull
   ```

2. Créer la branche dédiée au milestone :
   ```bash
   git checkout -b milestone/<MILESTONE>
   ```

3. Vérifier que les tests existants sont GREEN (pré-condition) :
   ```bash
   pytest tests/ -v --tb=short
   ```
   Si RED → **STOPPER**. Corriger les régressions sur `Max6000i1` avant de continuer.

### A.b — Implémenter chaque tâche du milestone

1. **Lister les tâches du milestone** :
   ```bash
   ls docs/tasks/<MILESTONE>/
   ```
   Trier par numéro `NNN` croissant. Vérifier les dépendances dans chaque fichier de tâche (champ `Dépendances`).

2. **Filtrer** : ignorer les tâches dont le statut est déjà `DONE`.

3. **Pour chaque tâche `NNN__slug.md`** (dans l'ordre, en respectant les dépendances) :

   Invoquer le skill `implementing-task` en lui passant :
   ```
   Tâche : docs/tasks/<MILESTONE>/NNN__slug.md
   Branche de base : milestone/<MILESTONE>  (à la place de Max6000i1)
   ```

   > **Note d'adaptation** : le skill `implementing-task` crée normalement une sous-branche `task/NNN-*` depuis `Max6000i1`. Ici, la branche de base est `milestone/<MILESTONE>`. Les sous-branches tâches sont créées depuis `milestone/<MILESTONE>`, puis mergées dans `milestone/<MILESTONE>` à la fin de chaque tâche (pas dans `Max6000i1`). Le skill `implementing-task` **ne crée pas de Pull Request** — il s'arrête après le commit des rapports de revue. C'est l'orchestrateur `implementing-milestone` qui gère la PR unique en Phase C.

   Le skill `implementing-task` retourne :
   - Liste des fichiers modifiés.
   - Résultat `pytest` (N passed, N failed).
   - Résultat `ruff check`.
   - Hash des commits RED, GREEN et REVIEW.

4. **Après chaque tâche** : vérifier que `pytest` est GREEN sur `milestone/<MILESTONE>` avant de passer à la suivante. Si RED → résoudre la régression avant de continuer.

5. **Résumé de phase** : noter le statut de chaque tâche (DONE / BLOQUÉ) avant de passer à la Phase B.

---

## PHASE B — Revue globale itérative

### Initialisation

```
review_iteration = 0
```

### B.a — Revue de code globale

Incrémenter : `review_iteration += 1`.

Invoquer le skill `global-review` sur la branche `milestone/<MILESTONE>` :

```
Branche : milestone/<MILESTONE>
Scope : all
```

Écrire le rapport dans :
```
docs/request_changes/review_<MILESTONE>_v<review_iteration>.md
```

Le rapport liste les items classés par sévérité :
- `B-N` — BLOQUANT
- `W-N` — WARNING
- `M-N` — MINEUR

### B.b — Appliquer les corrections

**Toutes les sévérités** sont traitées (BLOQUANT, WARNING, MINEUR), dans cet ordre de priorité.

Pour chaque item du rapport `docs/request_changes/review_<MILESTONE>_v<review_iteration>.md` :

#### Étape 1 — Évaluer la pertinence

Avant d'appliquer une correction, vérifier :

- La recommandation est-elle cohérente avec la spécification du scope détecté ?
  - Pipeline : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md`
  - Modèle : spec dans `docs/specifications/models/`
  - Streamlit : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md`
- Contredit-elle les conventions du repo (`AGENTS.md`) ?
- Est-elle un faux positif (ex : pattern signalé mais utilisé correctement en contexte) ?

**Si pertinente** → appliquer la correction.
**Si faux positif ou contradiction avec les conventions** → documenter la raison dans le rapport et passer à l'item suivant. Ne pas appliquer.

#### Étape 2 — Appliquer et valider

Invoquer le skill `implementing-request-change` en lui passant :
```
Fichier : docs/request_changes/review_<MILESTONE>_v<review_iteration>.md
Scope : all
```

Après chaque groupe de corrections :
```bash
ruff check <CODE_DIR> tests/
pytest tests/ -v --tb=short
```

Si tests RED → corriger la régression avant de passer à l'item suivant. Ne jamais laisser un état intermédiaire cassé.

#### Étape 3 — Commiter les corrections

```bash
git add <CODE_DIR> tests/ docs/request_changes/review_<MILESTONE>_v<review_iteration>.md
git commit -m "[<MILESTONE>] REVIEW v<review_iteration>: corrections B+W+M appliquées"
```

### B.c — Décision d'itération

Après application de toutes les corrections de la revue `v<review_iteration>` :

```
Si review_iteration < 5 :
    Si le rapport contenait au moins 1 item pertinent corrigé :
        → Reboucler sur B.a (nouvelle revue v<review_iteration+1>)
    Sinon (0 item pertinent, tout était faux positif) :
        → Passer à la Phase C
Sinon (review_iteration == 5) :
    Si le dernier rapport contient encore des items (non faux-positifs) :
        → STOPPER. Informer l'utilisateur des items résiduels. Ne pas continuer.
    Sinon :
        → Passer à la Phase C
```

> **Règle stricte** : ne passer à la Phase C que si le dernier rapport de revue ne contient plus aucun item pertinent non corrigé (BLOQUANT, WARNING ou MINEUR).

---

## PHASE C — Pull Request et review GitHub

### C.a — Créer la Pull Request

1. Vérifier l'état final de la branche :
   ```bash
   pytest tests/ -v --tb=short
   ruff check <CODE_DIR> tests/
   ```
   Si RED → **STOPPER**. Ne pas créer la PR.

2. Pousser la branche :
   ```bash
   git push -u origin milestone/<MILESTONE>
   ```

3. Créer la Pull Request vers `Max6000i1` :
   ```bash
   gh pr create \
     --base Max6000i1 \
     --head milestone/<MILESTONE> \
     --title "[<MILESTONE>] Milestone <MILESTONE> — <titre du milestone>" \
     --body "$(cat <<'EOF'
   ## Milestone <MILESTONE> — <titre>

   ### Tâches implémentées
   <liste des tâches NNN avec leur titre>

   ### Revues globales effectuées
   - <N> itérations de revue globale (v1..v<N>)
   - Dernière revue : `docs/request_changes/review_<MILESTONE>_v<N>.md` — 0 item pertinent résiduel

   ### Résultats CI
   - pytest : <N> passed, 0 failed
   - ruff check : All checks passed

   🤖 Généré avec le skill `implementing-milestone`
   EOF
   )"
   ```

4. Noter l'URL et le numéro de la PR retournés par `gh pr create`.

### C.b — Polling de la review GitHub automatique

Après création de la PR, GitHub déclenche une review automatique (`copilot-pull-request-reviewer`).

**Stratégie de polling** :
- **Délai initial** : attendre 60 secondes après le push avant le premier poll.
- **Intervalle** : 30 secondes entre chaque tentative.
- **Durée minimale** : **15 minutes** (900 secondes). **INTERDIT** d'abandonner avant 15 minutes.
- **Détection** : la review est arrivée quand le champ `comments` contient au moins un commentaire de `copilot-pull-request-reviewer`.
- **Timeout** : après 15 minutes sans review → **STOPPER le polling**. Informer l'utilisateur. La PR reste ouverte. **NE PAS merger**. S'arrêter là.

Commande de polling :
```bash
gh pr view <PR_NUMBER> --json comments,reviews
```

### C.c — Traiter les recommandations de la review GitHub

1. **Filtrer** les commentaires : garder uniquement ceux de `copilot-pull-request-reviewer` avec statut `unresolved`.

2. **Pour chaque commentaire** :

   #### Évaluation de pertinence
   - La recommandation est-elle justifiée et conforme aux conventions du repo ?
   - Contredit-elle les règles de `AGENTS.md` ?
   - Est-ce un faux positif du reviewer automatique ?

   **Classer** :
   - **BLOQUANT** : bug signalé, régression potentielle, violation de convention.
   - **MINEUR** : style, documentation, suggestion d'amélioration.
   - **IGNORÉ** : faux positif ou contradiction avec les conventions (documenter la raison).

3. **Invoquer l'agent `PR-Review-Fixer`** avec les commentaires classifiés :
   ```
   Commentaires à traiter :
   1. [BLOQUANT|MINEUR] <résumé>
      - Fichier : <chemin>
      - Commentaire original : <texte>
      - Suggestion : <suggestion si présente>

   Commentaires IGNORÉS :
   - <commentaire> → Raison : <justification>

   Branche : milestone/<MILESTONE>
   ```

4. **Valider après corrections** :
   ```bash
   ruff check <CODE_DIR> tests/
   pytest tests/ -v --tb=short
   ```

5. **Pousser les corrections** :
   ```bash
   git push
   ```

---

## PHASE D — Merge de la Pull Request

### Pré-conditions (toutes obligatoires)

- [ ] Phase C complète : review GitHub reçue et traitée (ou tous commentaires IGNORÉS avec justification).
- [ ] `pytest` GREEN sur la branche.
- [ ] `ruff check` clean.
- [ ] Aucun item BLOQUANT non résolu dans le dernier rapport de revue globale.

### Merge

1. Vérifier la mergeabilité :
   ```bash
   gh pr view <PR_NUMBER> --json mergeable,mergeStateStatus
   ```

2. Si `mergeable == "MERGEABLE"` :
   ```bash
   gh pr merge <PR_NUMBER> --squash --delete-branch
   ```
   Confirmer le merge à l'utilisateur. **FIN**.

3. Si conflits détectés (`mergeStateStatus != "CLEAN"`) :
   - Résoudre les conflits sur `milestone/<MILESTONE>`.
   - Pousser la résolution.
   - Re-vérifier `pytest` + `ruff`.
   - Retenter le merge.

4. Si `mergeable == "BLOCKED"` (CI en cours) :
   - Attendre 60 secondes et re-vérifier. **Ne pas forcer**.

---

## Résumé du flux orchestrateur

```
PHASE A
├── A.a : git checkout -b milestone/<MILESTONE>
└── A.b : Pour chaque tâche NNN (dans l'ordre)
          └── skill implementing-task (branche base = milestone/<MILESTONE>)
                   │
                   ▼
PHASE B
├── B.a : skill global-review → docs/request_changes/review_<MILESTONE>_v<N>.md
├── B.b : skill implementing-request-change (ALL sévérités, après vérification pertinence)
│         ruff + pytest après chaque groupe
└── B.c : ┌── 0 item pertinent résiduel → Phase C
          └── items résiduels ET N < 5 → reboucler B.a (N+1)
              items résiduels ET N == 5 → STOPPER (informer utilisateur)
                   │
                   ▼
PHASE C
├── C.a : git push + gh pr create (vers Max6000i1)
├── C.b : polling review GitHub (min 15 min, timeout → STOPPER sans merger)
└── C.c : agent PR-Review-Fixer → git push corrections
                   │
                   ▼
PHASE D
└── gh pr merge --squash --delete-branch
                   │
                   ▼
                  FIN
```

---

## Procédure d'abandon

Si à n'importe quelle étape une tâche s'avère irréalisable ou bloquante :

1. **Sauvegarder** : `git stash push -m "WIP <MILESTONE>"`.
2. **Documenter** dans le fichier de tâche : section `## Blocage` avec raison et date.
3. **Passer le statut** de la tâche à `BLOCKED`.
4. **Décider** : si la tâche bloquée est une dépendance d'autres tâches → **STOPPER le milestone** et informer l'utilisateur. Sinon → passer à la tâche suivante.
5. **Ne pas supprimer la branche** `milestone/<MILESTONE>`.

## Règles complémentaires

- **Un seul milestone à la fois** : ne jamais lancer deux milestones en parallèle.
- **Pas de commits directs sur `Max6000i1`** pendant l'exécution du milestone.
- **Journalisation** : conserver tous les rapports de revue (`review_<MILESTONE>_v*.md`) même après convergence — ils font partie de l'historique du projet.
- **Revue globale vs revue de tâche** : la Phase B est une revue **globale** (inter-modules, cohérence du pipeline complet), complémentaire aux revues unitaires effectuées par `implementing-task` pour chaque tâche.