---
name: implementing-task
description: Implémenter une ou plusieurs tâches de docs/tasks/ via TDD strict (tests d'acceptation → rouge → vert), conventions du repo AI Trading Pipeline, seuils de couverture, mise à jour du fichier de tâche et commits. Orchestre 3 parties : A (implémentation par subagent), B (revue par subagent + corrections itératives). À utiliser quand l'utilisateur demande « implémente/exécute/travaille sur la tâche #NNN ».
---

# Agent Skill — Implementing Task (AI Trading Pipeline)

## Objectif
Orchestrer l'implémentation de tâches décrites dans `docs/tasks/<milestone>/NNN__slug.md` en déléguant le travail à des **subagents spécialisés** via un workflow en 3 parties :

- **Partie A** : Subagent d'implémentation (TDD strict RED→GREEN).
- **Partie B** : Subagent de revue de branche + stockage du rapport.
- **Partie C** (conditionnel) : Subagent de correction si la revue relève des items.

Les parties B+C sont itérées jusqu'à 5 fois maximum, ou jusqu'à obtention d'un verdict CLEAN.

## Contexte repo

> Les conventions complètes, la stack, les principes non négociables et la structure des workstreams sont définis dans **`AGENTS.md`** (racine du repo). Ce skill ne duplique pas AGENTS.md — il le **complète** avec le workflow opérationnel spécifique à l'implémentation de tâches.

- **Tâches** : `docs/tasks/<milestone>/NNN__slug.md` (ex : `docs/tasks/M1/001__ws1_config_loader.md`)
- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2)
- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Code source** : `ai_trading/` (package Python principal)
- **Tests** : `tests/` (pytest, config dans `pyproject.toml`)
- **Configs** : `configs/default.yaml` (Pydantic v2)
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)
- **Langue** : anglais pour code/tests, français pour docs/tâches

## Principes non négociables

> Source de vérité : **`AGENTS.md` § Règles non négociables**. Résumé opérationnel ci-dessous.

- **Zéro "ghost completion"** : ne jamais marquer une tâche `DONE` ni cocher un critère `[x]` sans **code + tests** et **exécution vérifiée**.
- **TDD réel** : écrire les tests avant l'implémentation, vérifier qu'ils échouent, puis implémenter.
- **Strict code (no fallbacks)** : aucun fallback silencieux, aucun `or default`, aucun `except` trop large. Validation explicite + `raise`.
- **Config-driven** : tout paramètre modifiable lu depuis `configs/default.yaml` via Pydantic v2. Zéro hardcoding.
- **Anti-fuite** : ne jamais introduire de look-ahead. Données point-in-time. Embargo `embargo_bars >= H`. Scaler fit sur train uniquement. Splits walk-forward séquentiels (train < val < test).
- **Reproductibilité** : seeds fixées et tracées. Hashes SHA-256 (données, config).
- **Branche dédiée** : `task/NNN-short-slug` depuis `Max6000i1`. Jamais de commit direct sur `Max6000i1`.
- **Pull Request obligatoire** vers `Max6000i1` — créée **uniquement par l'orchestrateur** dans la Partie Finale, après que toutes les itérations de revue (Partie B/C) aient abouti à un verdict CLEAN. Les subagents (A, B, C) ne doivent **jamais** exécuter `git push` ni créer de PR.
- **Ambiguïté** : si specs ou tâche ambiguës → demander des clarifications avant d'implémenter.
- **Zéro suppression lint injustifiée** : `# noqa` et `per-file-ignores` dans `pyproject.toml` sont interdits sauf pour les noms **imposés par l'interface/spec** (ex : N803 sur `X_train` paramètre d'une ABC). Tout diagnostic ruff fixable doit être corrigé à la source. En particulier, **distinguer paramètres** (noms imposés par l'ABC → suppression N803 justifiée) des **variables locales** (toujours renommables → suppression N806 injustifiée, renommer en snake_case).

## Discipline de contexte

> **Prérequis** : le subagent d'implémentation et le subagent de revue doivent lire `.github/shared/coding_rules.md` (§R1-§R10, §GREP) au début de leur workflow.

- Lire **ciblé** : utiliser grep/recherche et ne charger que les sections pertinentes de la spec.
- Ne pas charger le document de spécification par défaut : le lire **uniquement si nécessaire**.
- Préférer **exécuter** une commande plutôt que décrire longuement.

---

# WORKFLOW ORCHESTRATEUR (1 tâche)

L'agent orchestrateur coordonne les 3 parties. Il ne code pas lui-même — il délègue via `runSubagent`.

## Étape 0 — Préparation (orchestrateur)

1. **Pré-condition GREEN** : exécuter `pytest` → tous les tests existants doivent être GREEN. Si RED : corriger d'abord.
2. **Lire la tâche** : ouvrir `docs/tasks/<milestone>/NNN__slug.md`, extraire le milestone `<milestone>`, le numéro `NNN`, le workstream `WS-X`, le slug, les dépendances.
3. **Créer le dossier de review** : `docs/tasks/<milestone>/<NNN>/` (s'il n'existe pas).
4. **Créer la branche dédiée** :
   ```bash
   git checkout Max6000i1
   git pull
   git checkout -b task/NNN-short-slug
   ```
5. **Initialiser le compteur de review** : `review_iteration = 0`.

---

## Partie A — Implémentation (subagent)

Lancer un subagent avec le prompt suivant (adapter les variables) :

> **Prompt subagent Partie A** :
>
> Tu es un agent d'implémentation TDD strict pour le projet AI Trading Pipeline.
>
> **Tâche** : Implémenter la tâche `docs/tasks/<milestone>/NNN__slug.md`.
> **Branche** : `task/NNN-short-slug` (déjà créée et checkoutée).
>
> Suis le workflow TDD détaillé ci-dessous, étape par étape.
> À la fin, la branche doit contenir : un commit RED (tests uniquement) et un commit GREEN (implémentation + tâche DONE).
>
> <Insérer ici le contenu complet du § « Instructions subagent Partie A » ci-dessous>

Le subagent doit retourner :
- La liste des fichiers modifiés.
- Le résultat de `pytest` (nombre de tests passed/failed).
- Le résultat de `ruff check ai_trading/ tests/`.
- Confirmation du commit RED et GREEN effectués.

---

## Partie B — Revue de branche (subagent)

Incrémenter : `review_iteration += 1`.

Lancer un subagent de revue avec le prompt suivant :

> **Prompt subagent Partie B** :
>
> Tu es un agent de revue de code pour le projet AI Trading Pipeline.
>
> **Branche à auditer** : `task/NNN-short-slug`
> **Tâche associée** : `docs/tasks/<milestone>/NNN__slug.md`
> **Itération de revue** : v<review_iteration>
>
> Effectue une revue complète de la branche en suivant la grille d'audit du skill `pr-reviewer` (lire `.github/skills/pr-reviewer/SKILL.md` pour la grille complète).
>
> Produis un rapport de revue structuré et écris-le dans :
> `docs/tasks/<milestone>/<NNN>/review_v<review_iteration>.md`
>
> Le rapport doit suivre le format standard (voir ci-dessous) et se terminer par un verdict :
> - **CLEAN** : **zéro item** de quelque sévérité que ce soit — 0 BLOQUANT, 0 WARNING, **0 MINEUR**. Si tu identifies ne serait-ce qu'un seul item MINEUR, le verdict est obligatoirement REQUEST CHANGES.
> - **REQUEST CHANGES** : au moins un item, **quelle que soit sa sévérité** (BLOQUANT, WARNING, **ou MINEUR**). Un item MINEUR seul suffit à déclencher REQUEST CHANGES.
>
> **RÈGLE NON NÉGOCIABLE** : il est **interdit** de retourner un verdict CLEAN tout en mentionnant des items (même « cosmétiques » ou « mineurs »). Tout item identifié = REQUEST CHANGES. Si tu hésites entre signaler un item ou l'ignorer, signale-le.
>
> **Important** : dans ton message de retour, indique clairement :
> 1. Le verdict (CLEAN ou REQUEST CHANGES).
> 2. Le nombre d'items par sévérité (N bloquants, N warnings, N mineurs). Les trois compteurs doivent être **exactement 0** pour un verdict CLEAN.
> 3. Le chemin du fichier de rapport créé.
>
> <Insérer ici le contenu complet du § « Instructions subagent Partie B » ci-dessous>

### Décision de l'orchestrateur après Partie B

**Validation préalable obligatoire** : avant d'accepter un verdict CLEAN, l'orchestrateur **doit vérifier la cohérence** entre le verdict annoncé et les compteurs d'items retournés par le subagent. Si le subagent retourne `CLEAN` mais que le nombre de bloquants + warnings + mineurs > 0, **rejeter le verdict** et le traiter comme REQUEST CHANGES. Un verdict CLEAN n'est valide que si les trois compteurs sont **exactement 0**.

- **Si verdict = CLEAN** (validé : 0 bloquants, 0 warnings, 0 mineurs) → passer à la Partie Finale (push + PR).
- **Si verdict = REQUEST CHANGES** (ou verdict CLEAN invalidé car compteurs > 0) ET `review_iteration < 5` → lancer la Partie C.
- **Si verdict = REQUEST CHANGES** ET `review_iteration >= 5` → **stopper les itérations**. Informer l'utilisateur que 5 itérations de revue ont été effectuées sans atteindre CLEAN. Lister les items restants. Laisser l'utilisateur décider de la suite.

---

## Partie C — Corrections (subagent, conditionnel)

Lancer un subagent de correction :

> **Prompt subagent Partie C** :
>
> Tu es un agent de correction pour le projet AI Trading Pipeline.
>
> **Rapport de revue à traiter** : `docs/tasks/<milestone>/<NNN>/review_v<review_iteration>.md`
> **Branche** : `task/NNN-short-slug` (déjà checkoutée).
>
> Lis le rapport de revue et implémente **toutes les corrections** identifiées, dans l'ordre de sévérité : BLOQUANTS → WARNINGS → MINEURS.
>
> Suis le workflow de correction détaillé ci-dessous.
> À la fin, la branche doit contenir un ou plusieurs commits FIX avec tous les tests GREEN.
>
> <Insérer ici le contenu complet du § « Instructions subagent Partie C » ci-dessous>

Le subagent doit retourner :
- La liste des items corrigés.
- Le résultat de `pytest` (nombre de tests passed/failed).
- Le résultat de `ruff check ai_trading/ tests/`.
- Confirmation des commits FIX effectués.

Après la Partie C, **reboucler sur la Partie B** (nouvelle itération de revue).

---

## Partie Finale — Push et Pull Request (orchestrateur)

Quand la Partie B retourne un verdict CLEAN :

1. **Commiter les fichiers de revue** :
```bash
git add docs/tasks/<milestone>/<NNN>/
git commit -m "[WS-X] #NNN REVIEW: rapports de revue v1..v<review_iteration>"
```

2. **Mettre à jour la checklist procédurale de la tâche** :
Ouvrir `docs/tasks/<milestone>/NNN__slug.md` et cocher les items restants de la checklist qui sont désormais complétés (commit GREEN, commit RED, etc.). Amender le dernier commit si nécessaire ou inclure dans le commit REVIEW.

3. **Push et création de la PR** :
```bash
git push -u origin task/NNN-short-slug
```
- Titre de la PR : `[WS-X] #NNN — <titre de la tâche>`
- Description : résumé des changements, lien vers la tâche, nombre d'itérations de revue effectuées.

4. **Cocher l'item PR dans la checklist** :
Mettre à jour le fichier de tâche pour cocher l'item « Pull Request ouverte ». Commiter et pousser l'update.

---

# INSTRUCTIONS DÉTAILLÉES DES SUBAGENTS

## Instructions subagent Partie A — Implémentation TDD

### 1. Lire la tâche
Ouvrir `docs/tasks/<milestone>/NNN__slug.md` et extraire :
- objectif, workstream (WS-1..WS-12), milestone (M1..M5), gate lié ;
- contraintes et règles attendues ;
- critères d'acceptation ;
- dépendances : vérifier que les tâches prérequises sont **DONE et mergées dans `Max6000i1`**. Si une dépendance est DONE mais sa PR n'est pas encore mergée, la branche `Max6000i1` ne contient pas le code requis — attendre le merge ou rebaser sur la branche de la dépendance (en documentant le choix).

### 2. Lire les sections de spec nécessaires
Charger uniquement les parties référencées de la spécification et du plan. Ne pas charger tout le document.

### 3. Écrire les tests (RED)
- Créer/modifier les fichiers de test dans `tests/` (convention plan : `test_config.py`, `test_features.py`, `test_splitter.py`, `test_backtest.py`, etc.). L'identifiant `#NNN` va dans les docstrings, pas dans les noms de fichiers.
- **Imports corrects dès l'écriture** : respecter l'ordre ruff/isort (stdlib → third-party → local, séparés par une ligne vide). Ne jamais ajouter d'imports inutiles.
- Couvrir chaque critère d'acceptation avec au moins un test.
- Inclure des cas nominaux, erreurs, et bords.
- **Fuzzing priorisé des paramètres numériques** : pour chaque paramètre numérique en entrée (`n`, `L`, `H`, period, window, etc.), prioriser les tests de boundary par **risque** :
  1. **Priorité haute** (toujours tester) : valeurs causant division par zéro, indices négatifs, ou arrays vides (ex : `param = 0`, `param = 1` si `1` est un cas dégénéré).
  2. **Priorité moyenne** : `param > taille_données`, `param = taille_données` (limite exacte), combinaison de minimums simultanés (ex : `fast=1, slow=1`).
  3. **Priorité basse** (si temps disponible) : `param = valeur_max` théorique, combinaisons croisées exhaustives.
  Ne pas viser l'exhaustivité combinatoire — viser la couverture des **classes d'équivalence à risque**.
- **Fuzzing spécifique taux/proportions** : pour tout paramètre de type taux ou proportion (`fee_rate`, `slippage_rate`, `position_fraction`, ou tout paramètre apparaissant dans une formule `(1 - p)` ou `(1 + p)`) : le domaine mathématiquement valide est typiquement `[0, 1)`. Toujours tester et valider : `param = 0` (neutre), `param = 1` (boundary — souvent invalide, `(1-p)=0`), `param > 1` (invalide — doit lever une erreur). Si la validation ne couvre que `>= 0` sans borne supérieure → bug.
- **Atomicité des tests** : chaque test doit vérifier **un seul scénario**. Ne pas empiler plusieurs `pytest.raises` ou assertions indépendantes dans un même test body. Si le premier échoue, les suivants ne s'exécutent pas.
- Utiliser des données synthétiques (fixtures `conftest.py`), jamais de données réseau.
- **Portabilité des chemins** : ne jamais utiliser de chemins hardcodés OS-spécifiques (ex : `Path("/tmp/...")`) dans les tests. Toujours utiliser la fixture pytest `tmp_path` pour tout chemin temporaire (y compris `run_dir` passé aux méthodes comme `fit()`).
- Si la tâche concerne l'anti-fuite : inclure un test de perturbation (modifier prix futurs → résultat identique pour t ≤ T).
- **Exports `__init__.py`** : si le nouveau module doit être découvert à l'import du package (ex : feature enregistrée via `@register_feature`), ajouter l'import dans le `__init__.py` du package avec un **import relatif** (ex : `from . import ema  # noqa: F401` dans `ai_trading/features/__init__.py`). Toujours préférer `from . import module` à `from ai_trading.package import module` pour les imports intra-package side-effect.
- **Tests de registre via `importlib.reload`** : quand un test vérifie qu'un module s'enregistre dans un registre (ex : `MODEL_REGISTRY`, `FEATURE_REGISTRY`) via décorateur à l'import, ne **jamais** appeler manuellement `register_xxx("name")(Cls)`. À la place, utiliser `importlib.reload(module)` après nettoyage du registre par la fixture, puis vérifier que la clé est présente. Comparer avec `mod.ClassName` (module rechargé), pas avec la référence importée en haut du fichier (qui pointe vers l'ancien objet classe).

### 4. Prouver que les tests échouent
`pytest tests/test_xxx.py -v` → RED.

### 5. Commit RED

**Contenu autorisé** dans le commit RED :
- Fichiers de test (`tests/test_xxx.py`) — obligatoire.
- `tests/conftest.py` — autorisé si de nouvelles fixtures partagées sont nécessaires pour que les tests s'exécutent (collection sans erreur d'import).
- `configs/default.yaml` — autorisé si un test vérifie la lecture d'un paramètre config qui n'existe pas encore (le test ne peut pas prouver l'échec fonctionnel sans la clé config).

**Interdit** dans le commit RED : tout fichier d'implémentation (`ai_trading/`), tout fichier de tâche (`docs/tasks/`).

```bash
git add tests/test_xxx.py             # obligatoire
git add tests/conftest.py             # si modifié
git add configs/default.yaml          # si modifié
git commit -m "[WS-X] #NNN RED: <résumé des tests ajoutés>"
```

### 6. Implémenter (GREEN)
Écrire pour faire passer les tests :

> **Règles complètes et checklists** : `.github/shared/coding_rules.md` (§R1-§R10). Résumé opérationnel ci-dessous.
- **Strict code** : validation explicite + `raise`. Pas de fallbacks, pas de defaults implicites.
- **Config-driven** : paramètres dans `configs/default.yaml`, pas hardcodés.
- **DRY** : éviter la duplication de code, extraire des fonctions/classes réutilisables.
- **Anti-fuite** : aucun `.shift(-n)` sans justification temporelle correcte.
- **Float32** pour tenseurs X_seq et y. **Float64** pour calculs de métriques.
- **Nommage** : snake_case, anglais pour le code.
- **Imports** : pas d'import `*`, pas d'imports inutilisés, pas de variables assignées mais jamais référencées (dead code). Ordre isort strict (stdlib → third-party → local).
- **Pas de print()** : utiliser `logging` uniquement si le module en a besoin. Ne pas importer `logging` ni créer `logger` « au cas où ».
- **Exports `__init__.py`** : si le nouveau module doit être découvert à l'import du package (ex : feature enregistrée via `@register_feature`), ajouter l'import dans le `__init__.py` du package avec un **import relatif** (ex : `from . import ema  # noqa: F401` dans `ai_trading/features/__init__.py`). Toujours préférer `from . import module` à `from ai_trading.package import module` pour les imports intra-package side-effect — les imports absolus auto-référençants créent des comportements confus à l'initialisation du package.
- **Cohérence intermodule** : avant d'implémenter, identifier les modules existants qui consomment ou produisent les mêmes structures (DataFrames, configs, registres). S'assurer que les signatures, noms de colonnes, types de retour et conventions adoptées dans le nouveau code sont alignés avec les modules voisins. En cas de doute, lire le code appelant/appelé pour vérifier la cohérence.
- **Contrat ABC complet** : si la classe parente (ABC) documente qu'un paramètre accepte plusieurs types d'entrées (ex : `path` = répertoire OU fichier), l'implémentation **doit** supporter tous les cas documentés. Vérifier la docstring de chaque méthode abstraite et implémenter chaque variante avec un test correspondant. Créer les répertoires parents si nécessaire (`path.parent.mkdir(parents=True, exist_ok=True)`).
- **Forwarding complet** : quand le code orchestre des appels à d'autres interfaces (model.fit(), model.predict(), scaler.transform()...), s'assurer que **tous les kwargs pertinents** reçus en entrée sont transmis au sous-appel. Ne pas « perdre » silencieusement un paramètre optionnel en omettant de le passer.
- **Defaults cohérents** : si un paramètre miroir une interface amont/aval (ex : `ohlcv: Any` qui sera passé à `BaseModel.predict(ohlcv: Any = None)`), donner le même default (`= None`). Un paramètre sémantiquement optionnel sans default crée un fardeau inutile.
- **Création run_dir** : si une fonction reçoit un `run_dir: Path` et y écrit des fichiers ou sous-répertoires, appeler `run_dir.mkdir(parents=True, exist_ok=True)` au début de la fonction — ne jamais supposer que le répertoire existe.
- **Ajustement des tests autorisé** : si l'implémentation révèle une inexactitude mineure dans les tests RED (ex : tolérance numérique, nom de colonne), corriger les tests dans le commit GREEN. Les modifications de tests dans le GREEN doivent rester mineures et tracées.
- **Corrections à la source** : si ruff signale un problème, corriger la cause (renommer, réordonner, supprimer). Ne jamais appliquer deux corrections contradictoires en même temps (ex : renommer un symbol ET ajouter un `# noqa` sur le même diagnostic).

### 7. Valider la suite complète (commandes exactes, obligatoires)
Exécuter **exactement** ces commandes, telles quelles (pas fichier par fichier) :
```bash
ruff check ai_trading/ tests/
pytest
```
- `ruff check ai_trading/ tests/` → **0 erreur, 0 warning**. Si une erreur persiste, revenir à l'étape 6 et corriger à la source.
- `pytest` → **tous GREEN** (nouveaux + existants), aucune régression, 0 échec, 0 erreur de collection.

**Pylance / type checking (obligatoire)** :
Appeler l'outil `get_errors` sur **chaque fichier modifié** (`ai_trading/` et `tests/`). C'est l'équivalent IDE de Pylance — il est **toujours disponible** et ne nécessite pas `pyright` en CLI.
```
get_errors(filePaths=[...tous les fichiers modifiés...])
```
Si des erreurs de type sont signalées, les corriger (utiliser des variables locales pour le type narrowing sur `self.attr`, `np.asarray()` au lieu de `.values`, typer les retours, etc.). **Ne pas ignorer les erreurs de type.**

**Ne jamais** passer à l'étape 8 si `get_errors` retourne des erreurs sur les fichiers modifiés.

**Vérification complémentaire** (exécuter si disponible dans l'environnement) :
```bash
# Couverture — prépare les gates G-Features (>=90%), M1 (>=95%)
pytest --cov=ai_trading --cov-report=term-missing
```

**Ne jamais** passer à l'étape 8 si `ruff check`, `pytest` ou `get_errors` échoue.

### 8. Audit strict (obligatoire — ne pas escamoter)
Relecture manuelle de **chaque fichier modifié**. Checklist minimale :

#### 8a. Traçabilité critères ↔ tests ↔ code
- [ ] Chaque critère d'acceptation a au moins un test correspondant.
- [ ] Chaque test correspond à un comportement attendu.
- [ ] **Vérification texte AC ↔ valeurs du code** : pour chaque critère d'acceptation contenant des bornes, indices ou valeurs numériques (ex : « NaN aux positions t < X »), vérifier que le **texte** du critère correspond **exactement** aux valeurs produites par le code. Un off-by-one entre le texte de la tâche et le comportement réel est bloquant — corriger le texte de la tâche si nécessaire.
- [ ] Ajouter des tests de bords/erreurs si nécessaire.

#### 8b. Anti-fuite
- [ ] Aucun accès à des données futures (look-ahead).
- [ ] Cohérence avec la spec v1.0.

#### 8c. Qualité du code (post-implémentation)
> Checklist : `.github/shared/coding_rules.md` §R7. Vérifier chaque item et corriger.

Complément spécifique implémentation :
- [ ] **PYLANCE (via `get_errors`)** : appeler `get_errors` sur chaque fichier modifié et corriger toutes les erreurs de type. Attention aux pièges courants : type narrowing sur `self.attr` (Pylance ne narrow pas les attributs `self` après affectation — utiliser des variables locales), `Optional` non vérifié, retours `Any` implicites.

#### 8d. Cohérence intermodule
> Checklist : `.github/shared/coding_rules.md` §R8 + §R6 (path creation, kwargs forwarding).
> Vérifier que les changements ne créent pas de divergence avec les modules existants.

Si un point de cette checklist échoue, corriger et **revenir à l'étape 7** pour revalider.

### 9. Mettre à jour la tâche
Dans `docs/tasks/<milestone>/NNN__slug.md` :
- Cocher chaque critère d'acceptation vérifié : `- [x]`
- Cocher chaque item de la checklist de fin de tâche : `- [x]`
- Passer `Statut : DONE`
- **Corriger les sections descriptives** (Objectif, Évolutions proposées, Règles attendues) si elles sont factuellement incorrectes après implémentation (ex : `min_periods` retourne une valeur différente de celle annoncée dans la tâche). Le fichier de tâche doit refléter fidèlement le code livré.

### 10. Commit GREEN (clôture)
Conditions requises : tests GREEN + tous les critères d'acceptation validés + checklist cochée.

**Contenu attendu** du commit GREEN :
- Fichiers d'implémentation (`ai_trading/`) — obligatoire.
- `__init__.py` modifiés — si nécessaire.
- `docs/tasks/<milestone>/NNN__slug.md` — obligatoire (statut DONE).
- `configs/default.yaml` — si des paramètres ont été ajoutés/modifiés.
- Fichiers de test (`tests/`) — autorisé pour ajustements mineurs post-implémentation (tolérances, noms de colonnes, etc.).

```bash
git add ai_trading/ tests/ docs/tasks/<milestone>/NNN__slug.md configs/
git commit -m "[WS-X] #NNN GREEN: <résumé du livrable>"
```

### 11. Retourner le résultat à l'orchestrateur

**INTERDIT** : ne jamais exécuter `git push` ni créer de Pull Request. Le push et la PR sont gérés exclusivement par l'orchestrateur dans la Partie Finale.

Le subagent doit retourner au format suivant :
```
RÉSULTAT PARTIE A :
- Fichiers modifiés : <liste>
- pytest : <N> passed, <N> failed
- ruff check : <clean / N erreurs>
- get_errors : <clean / N erreurs>
- Commit RED : <hash> — <message>
- Commit GREEN : <hash> — <message>
```

---

## Instructions subagent Partie B — Revue de branche

> **Source de vérité unique** : `.github/skills/pr-reviewer/SKILL.md` contient la grille d'audit complète (Phase A compliance + Phase B code review adversariale), les commandes grep obligatoires, la grille de lecture diff, et le template de rapport. Ce skill ne duplique pas le pr-reviewer — il le **délègue** avec les adaptations suivantes.

### 1. Exécuter le workflow pr-reviewer

Lire **intégralement** `.github/skills/pr-reviewer/SKILL.md` et exécuter son workflow complet (Phase A + Phase B) avec les paramètres suivants :

| Paramètre | Valeur |
|---|---|
| Branche source | `task/NNN-short-slug` |
| Branche cible | `Max6000i1` |
| Tâche associée | `docs/tasks/<milestone>/NNN__slug.md` |

### 2. Adaptations contexte tâche

En complément du workflow pr-reviewer standard :

- **Vérification tâche (Phase A)** : vérifier que la tâche est marquée `Statut : DONE`, que tous les critères d'acceptation sont cochés `[x]`, et que la checklist est cochée `[x]`.
- **Chemin du rapport** : écrire le rapport dans `docs/tasks/<milestone>/<NNN>/review_v<review_iteration>.md` (au lieu du chemin PR standard `docs/pr_review_copilot/`).
- **Verdict** : utiliser les mêmes termes que le pr-reviewer :
  - **CLEAN** = **strictement 0 item** : 0 BLOQUANT, 0 WARNING, **0 MINEUR**. Un item MINEUR empêche le verdict CLEAN.
  - **REQUEST CHANGES** = au moins un item, **quelle que soit sa sévérité** (y compris MINEUR seul).
  - **INTERDIT** : retourner CLEAN en mentionnant des items « cosmétiques » ou « non bloquants ». Tout item identifié → REQUEST CHANGES.

### 3. Retourner le résultat à l'orchestrateur

```
RÉSULTAT PARTIE B :
- Verdict : CLEAN | REQUEST CHANGES
- Bloquants : N
- Warnings : N
- Mineurs : N
- Rapport : docs/tasks/<milestone>/<NNN>/review_v<review_iteration>.md
```

---

## Instructions subagent Partie C — Corrections

Le subagent de correction suit le workflow du skill `implementing-request-change`, adapté au contexte d'une review de tâche.

### 1. Lire le rapport de revue
Ouvrir `docs/tasks/<milestone>/<NNN>/review_v<review_iteration>.md` et extraire tous les items (BLOQUANTS, WARNINGS, MINEURS).

### 2. Trier et planifier
**Ordre obligatoire** : BLOQUANTS → WARNINGS → MINEURS.
Regrouper par module impacté quand possible.

### 3. Pour chaque item (ou groupe d'items liés)

#### 3a. Analyser l'impact
- Lire les fichiers référencés.
- Identifier tous les modules impactés via `grep_search`.
- Évaluer l'effet domino.

#### 3b. Appliquer la correction
- Écrire ou adapter les tests si nécessaire.
- Modifier le code source.
- **Strict code** : validation explicite + `raise`. Pas de fallbacks.
- **Cohérence intermodule** : vérifier signatures, colonnes, clés config, registres.

#### 3c. Valider après chaque groupe
```bash
ruff check ai_trading/ tests/
pytest
```
Appeler `get_errors` sur les fichiers modifiés.

#### 3d. Commiter
```bash
git add <fichiers modifiés>
git commit -m "[WS-X] #NNN FIX: <résumé de la correction>"
```

### 4. Règles des commits FIX
- Chaque commit FIX doit laisser les tests GREEN.
- Le contenu peut mélanger code + tests + docs.
- Pas de modification de fichiers hors périmètre de la tâche.
- Si les corrections sont substantielles (> 50 lignes), envisager un squash : `git rebase -i`.

### 5. Retourner le résultat à l'orchestrateur

```
RÉSULTAT PARTIE C :
- Items corrigés : B-1, B-2, W-1, M-1, M-2
- pytest : <N> passed, <N> failed
- ruff check : <clean / N erreurs>
- get_errors : <clean / N erreurs>
- Commits FIX : <liste hash — message>
```

---

## Workflow variante : tâche de refactoring

Pour les tâches de type refactoring (ex : renommer, clarifier un contrat, unifier une convention) où les tests **existants passent déjà**, le cycle RED classique ne s'applique pas directement.

### Adaptation du workflow
1. **Étape 0** de l'orchestrateur : identique.
2. **Partie A (RED adapté)** : le subagent d'implémentation doit écrire/modifier des tests qui **capturent le nouveau comportement attendu** et qui échouent avec le code actuel. Exemples :
   - Un test qui vérifie la nouvelle valeur de retour (ex : `assert feature.min_periods == 14` alors que le code retourne `15`).
   - Un test de cohérence cross-module (ex : `min_periods` correspond au nombre réel de NaN).
   Si le refactoring ne change aucun comportement observable (renommage interne pur), les tests existants suffisent — dans ce cas, le commit RED peut contenir uniquement des tests de non-régression renforcés.
3. **Parties B et C** : identiques au workflow standard.

## Plusieurs tâches

- Traiter **dans l'ordre**, en respectant les dépendances.
- Terminer le workflow complet (Étape 0 → Partie A → Boucle B/C → Partie Finale) **pour chaque tâche** avant de passer à la suivante.
- Commits **par tâche** (pas de batch multi-tâches).
- Chaque tâche a sa propre branche et sa propre PR.

## Procédure d'abandon

Si à n'importe quelle étape la tâche s'avère irréalisable (spec ambiguë non résoluble, dépendance manquante, contradiction dans les exigences) :

1. **Sauvegarder le travail partiel** : `git stash push -m "WIP #NNN"`.
2. **Documenter le blocage** dans le fichier de tâche : ajouter une section `## Blocage` avec la raison précise et la date.
3. **Passer le statut** à `BLOCKED` (pas `DONE`, pas `IN_PROGRESS`).
4. **Informer l'utilisateur** avec la raison et la suggestion d'action (clarifier la spec, résoudre la dépendance, etc.).
5. **Ne pas supprimer la branche** tant que le blocage n'est pas résolu.

## Format de commits

| Moment | Format | Contenu |
|---|---|---|
| Après tests RED (Partie A) | `[WS-X] #NNN RED: <résumé>` | Fichiers de tests (+ conftest.py, configs/ si nécessaire) |
| Clôture tâche (Partie A) | `[WS-X] #NNN GREEN: <résumé>` | Implémentation + tests ajustés + tâche + configs |
| Corrections post-revue (Partie C) | `[WS-X] #NNN FIX: <résumé>` | Corrections demandées (code + tests + docs mélangés) |

Aucun commit intermédiaire entre RED et GREEN sauf refactoring mineur (tests verts).

## Résumé du flux orchestrateur

```
Étape 0 : Préparation (branche, dossier review)
    │
    ▼
Partie A : Subagent implémentation TDD (RED → GREEN)
    │
    ▼
┌─► Partie B : Subagent revue → review_v<N>.md
│       │
│       ├── CLEAN → Partie Finale (push + PR) ──► FIN
│       │
│       └── REQUEST CHANGES (et N < 5)
│               │
│               ▼
│       Partie C : Subagent corrections → commits FIX
│               │
└───────────────┘  (reboucle sur Partie B, N+1)

Si N >= 5 et toujours REQUEST CHANGES → STOP, informer l'utilisateur.
```

## Conventions Python / AI Trading

> Source de vérité : **`AGENTS.md`** § Conventions de code + `.github/shared/coding_rules.md` (§R1-§R10).
> Points opérationnels complémentaires (non couverts par le fichier partagé) :

- **Nommage tests** : structurés par module (`test_config.py`, `test_features.py`, `test_splitter.py`, etc.). Identifiant tâche `#NNN` dans les docstrings uniquement.
- **Type checking** : corriger les erreurs Pylance/pyright dans les fichiers modifiés. Ne pas laisser de types `Any` implicites si le type réel est connu.
