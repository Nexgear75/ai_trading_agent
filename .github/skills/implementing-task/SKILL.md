---
name: implementing-task
description: Implémenter une ou plusieurs tâches de docs/tasks/ via TDD strict (tests d'acceptation → rouge → vert), conventions du repo AI Trading Pipeline, seuils de couverture, mise à jour du fichier de tâche et commits. À utiliser quand l'utilisateur demande « implémente/exécute/travaille sur la tâche #NNN ».
---

# Agent Skill — Implementing Task (AI Trading Pipeline)

## Objectif
Exécuter des tâches décrites dans `docs/tasks/NNN__slug.md` selon un workflow **TDD strict**, en respectant les conventions du dépôt AI Trading Pipeline, puis livrer proprement (tests, couverture, statut de tâche, commits).

## Contexte repo

> Les conventions complètes, la stack, les principes non négociables et la structure des workstreams sont définis dans **`AGENTS.md`** (racine du repo). Ce skill ne duplique pas AGENTS.md — il le **complète** avec le workflow opérationnel spécifique à l'implémentation de tâches.

- **Tâches** : `docs/tasks/NNN__slug.md`
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
- **Pull Request obligatoire** vers `Max6000i1` après commit GREEN.
- **Ambiguïté** : si specs ou tâche ambiguës → demander des clarifications avant d'implémenter.
- **Zéro `# noqa` injustifié** : `# noqa` est interdit sauf pour les noms imposés par la spec (ex : `horizon_H_bars`, `L`). Tout diagnostic ruff fixable doit être corrigé à la source, jamais masqué par une suppression.

## Discipline de contexte

- Lire **ciblé** : utiliser grep/recherche et ne charger que les sections pertinentes de la spec.
- Ne pas charger le document de spécification par défaut : le lire **uniquement si nécessaire**.
- Préférer **exécuter** une commande plutôt que décrire longuement.

## Workflow standard (1 tâche)

### 0. Pré-condition GREEN
Exécuter `pytest` → **tous les tests existants doivent être GREEN**.
Si RED : corriger d'abord les régressions avant de commencer la tâche.

### 0b. Créer la branche dédiée
```bash
git checkout Max6000i1
git pull
git checkout -b task/NNN-short-slug
```

### 1. Lire la tâche
Ouvrir `docs/tasks/NNN__slug.md` et extraire :
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
- **Atomicité des tests** : chaque test doit vérifier **un seul scénario**. Ne pas empiler plusieurs `pytest.raises` ou assertions indépendantes dans un même test body. Si le premier échoue, les suivants ne s'exécutent pas.
- Utiliser des données synthétiques (fixtures `conftest.py`), jamais de données réseau.
- Si la tâche concerne l'anti-fuite : inclure un test de perturbation (modifier prix futurs → résultat identique pour t ≤ T).
- **Exports `__init__.py`** : si le module créé doit être importé automatiquement (ex : features enregistrées via décorateur à l'import), s'assurer que `__init__.py` du package importe le module. Le test d'enregistrement dans le registre valide implicitement cet import.
- **Lancer `ruff check` sur le fichier test après écriture**, avant le commit RED. Corriger tout diagnostic à la source (réordonner, supprimer l'import, renommer) — jamais de `# noqa` comme contournement.

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
- **Strict code** : validation explicite + `raise`. Pas de fallbacks, pas de defaults implicites.
- **Config-driven** : paramètres dans `configs/default.yaml`, pas hardcodés.
- **DRY** : éviter la duplication de code, extraire des fonctions/classes réutilisables.
- **Anti-fuite** : aucun `.shift(-n)` sans justification temporelle correcte.
- **Float32** pour tenseurs X_seq et y. **Float64** pour calculs de métriques.
- **Nommage** : snake_case, anglais pour le code.
- **Imports** : pas d'import `*`, pas d'imports inutilisés, pas de variables assignées mais jamais référencées (dead code). Ordre isort strict (stdlib → third-party → local).
- **Pas de print()** : utiliser `logging` uniquement si le module en a besoin. Ne pas importer `logging` ni créer `logger` « au cas où ».
- **Exports `__init__.py`** : si le nouveau module doit être découvert à l'import du package (ex : feature enregistrée via `@register_feature`), ajouter l'import dans le `__init__.py` du package (ex : `from ai_trading.features import ema  # noqa: F401` dans `ai_trading/features/__init__.py`).
- **Cohérence intermodule** : avant d'implémenter, identifier les modules existants qui consomment ou produisent les mêmes structures (DataFrames, configs, registres). S'assurer que les signatures, noms de colonnes, types de retour et conventions adoptées dans le nouveau code sont alignés avec les modules voisins. En cas de doute, lire le code appelant/appelé pour vérifier la cohérence.
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

**Vérifications complémentaires** (exécuter si disponibles dans l'environnement) :
```bash
# Type checking (si Pylance/pyright disponible)
pyright ai_trading/ tests/        # ou vérifier les erreurs Pylance dans l'IDE

# Couverture — prépare les gates G-Features (>=90%), M1 (>=95%)
pytest --cov=ai_trading --cov-report=term-missing
```
Si Pylance/pyright signale des erreurs de type dans les fichiers modifiés, les corriger (utiliser `np.asarray()` au lieu de `.values`, typer les retours, etc.). Ne pas ignorer les erreurs de type.

**Ne jamais** passer à l'étape 8 si `ruff check` ou `pytest` échoue.

### 8. Audit strict (obligatoire — ne pas escamoter)
Relecture manuelle de **chaque fichier modifié**. Checklist minimale :

> **Limite structurelle** : l'agent qui implémente est le même qui audite. Pour mitiger ce biais, envisager de lancer le skill `pr-reviewer` sur sa propre branche avant le commit GREEN si la tâche est complexe.

#### 8a. Traçabilité critères ↔ tests ↔ code
- [ ] Chaque critère d'acceptation a au moins un test correspondant.
- [ ] Chaque test correspond à un comportement attendu.
- [ ] **Vérification texte AC ↔ valeurs du code** : pour chaque critère d'acceptation contenant des bornes, indices ou valeurs numériques (ex : « NaN aux positions t < X »), vérifier que le **texte** du critère correspond **exactement** aux valeurs produites par le code. Un off-by-one entre le texte de la tâche et le comportement réel est bloquant — corriger le texte de la tâche si nécessaire.
- [ ] Ajouter des tests de bords/erreurs si nécessaire.

#### 8b. Anti-fuite
- [ ] Aucun accès à des données futures (look-ahead).
- [ ] Cohérence avec la spec v1.0.

#### 8c. Qualité du code (post-implémentation)
- [ ] **Aucun import inutilisé** : chaque `import` est référencé dans le code.
- [ ] **DRY** : pas de duplication de code dans le projet. Si un bloc de code est copié-collé, extraire une fonction ou classe réutilisable. 
- [ ] **PYLANCE** : corriger les erreurs de type signalées par Pylance/pyright dans les fichiers du projet.
- [ ] **Aucune variable morte** : chaque variable assignée est utilisée au moins une fois.
- [ ] **Aucun `# noqa` injustifié** : seuls les `# noqa` pour des noms imposés par la spec sont tolérés (ex : `N815` sur `horizon_H_bars`). Si un `# noqa` existe, vérifier qu'il est encore nécessaire.
- [ ] **Imports ordonnés** : stdlib → third-party → local, séparés par des lignes vides. Pas de `# noqa: I001`.
- [ ] **Pas de code mort, commenté, ou TODO orphelin.**
- [ ] **Pas de `print()`** restant.
- [ ] **`__init__.py` à jour** : si un nouveau module a été créé, vérifier que le `__init__.py` du package l'importe si nécessaire (ex : pour l'enregistrement automatique des features).

#### 8d. Cohérence intermodule
Vérifier que les changements ne créent pas de divergence avec les modules existants qui interagissent avec le code modifié.

- [ ] **Signatures et types de retour** : les fonctions/classes modifiées ou créées respectent les signatures attendues par les modules appelants existants (mêmes noms de paramètres, mêmes types, même ordre). Si une signature est modifiée, vérifier tous les appels dans le codebase (`grep_search`).
- [ ] **Noms de colonnes DataFrame** : les colonnes produites ou consommées (ex : `close`, `logret_1`, `vol_24`) sont identiques à celles utilisées dans les modules amont/aval. Pas de renommage silencieux.
- [ ] **Clés de configuration** : les clés lues depuis `configs/default.yaml` correspondent aux noms définis dans le modèle Pydantic (`config.py`). Pas de clé orpheline ni manquante.
- [ ] **Registres et conventions partagées** : si le module s'inscrit dans un registre (ex : `FEATURE_REGISTRY`), vérifier que l'interface implémentée (méthodes, attributs comme `name`, `min_periods`) est cohérente avec les autres entrées du registre et avec le code qui itère sur le registre.
- [ ] **Structures de données partagées** : les dataclasses, TypedDict ou NamedTuple partagées entre modules sont utilisées de manière identique (mêmes champs, mêmes types). Pas de champ ajouté dans un module sans mise à jour des consommateurs.
- [ ] **Conventions numériques** : les dtypes (float32 vs float64), les conventions NaN (NaN en tête vs valeurs par défaut), et les index (DatetimeIndex, RangeIndex) sont cohérents avec les modules voisins.

Si un point de cette checklist échoue, corriger et **revenir à l'étape 7** pour revalider.

### 9. Mettre à jour la tâche
Dans `docs/tasks/NNN__slug.md` :
- Cocher chaque critère d'acceptation vérifié : `- [x]`
- Cocher chaque item de la checklist de fin de tâche : `- [x]`
- Passer `Statut : DONE`
- **Corriger les sections descriptives** (Objectif, Évolutions proposées, Règles attendues) si elles sont factuellement incorrectes après implémentation (ex : `min_periods` retourne une valeur différente de celle annoncée dans la tâche). Le fichier de tâche doit refléter fidèlement le code livré.

### 10. Commit GREEN (clôture)
Conditions requises : tests GREEN + tous les critères d'acceptation validés + checklist cochée.

**Contenu attendu** du commit GREEN :
- Fichiers d'implémentation (`ai_trading/`) — obligatoire.
- `__init__.py` modifiés — si nécessaire.
- `docs/tasks/NNN__slug.md` — obligatoire (statut DONE).
- `configs/default.yaml` — si des paramètres ont été ajoutés/modifiés.
- Fichiers de test (`tests/`) — autorisé pour ajustements mineurs post-implémentation (tolérances, noms de colonnes, etc.).

```bash
git add ai_trading/ tests/ docs/tasks/NNN__slug.md configs/
git commit -m "[WS-X] #NNN GREEN: <résumé du livrable>"
```

### 11. Push et Pull Request
```bash
git push -u origin task/NNN-short-slug
```
- Titre de la PR : `[WS-X] #NNN — <titre de la tâche>`
- Description : résumé des changements, lien vers la tâche.

### 12. Itération post-revue

Après la revue de la PR (skill `pr-reviewer` ou revue humaine), des corrections peuvent être demandées. Workflow pour chaque itération :

1. Appliquer les corrections demandées (code, tests, docs).
2. Exécuter les validations de l'étape 7 (`ruff check` + `pytest`).
3. Commiter avec le format :
```bash
git commit -m "[WS-X] #NNN FIX: <résumé des corrections>"
```
4. Push sur la même branche : `git push`.

**Règles des commits FIX** :
- Chaque commit FIX doit laisser les tests GREEN.
- Le contenu peut mélanger code + tests + docs (pas de séparation RED/GREEN en itération).
- Pas de modification du skill ou de fichiers hors périmètre de la tâche dans un commit FIX.
- Si les corrections sont substantielles (> 50 lignes), envisager un squash avant merge : `git rebase -i` pour fusionner les FIX dans le GREEN.

## Format de commits

| Moment | Format | Contenu |
|---|---|---|
| Après tests RED | `[WS-X] #NNN RED: <résumé>` | Fichiers de tests (+ conftest.py, configs/ si nécessaire) |
| Clôture tâche | `[WS-X] #NNN GREEN: <résumé>` | Implémentation + tests ajustés + tâche + configs |
| Itération post-revue | `[WS-X] #NNN FIX: <résumé>` | Corrections demandées (code + tests + docs mélangés) |

Aucun commit intermédiaire entre RED et GREEN sauf refactoring mineur (tests verts).

## Workflow variante : tâche de refactoring

Pour les tâches de type refactoring (ex : renommer, clarifier un contrat, unifier une convention) où les tests **existants passent déjà**, le cycle RED classique ne s'applique pas directement.

### Adaptation du workflow
1. **Étapes 0–2** : identiques au workflow standard.
2. **Étape 3 (RED adapté)** : écrire/modifier des tests qui **capturent le nouveau comportement attendu** et qui échouent avec le code actuel. Exemples :
   - Un test qui vérifie la nouvelle valeur de retour (ex : `assert feature.min_periods == 14` alors que le code retourne `15`).
   - Un test de cohérence cross-module (ex : `min_periods` correspond au nombre réel de NaN).
   Si le refactoring ne change aucun comportement observable (renommage interne pur), les tests existants suffisent — dans ce cas, le commit RED peut contenir uniquement des tests de non-régression renforcés.
3. **Étapes 4–12** : identiques au workflow standard.

## Plusieurs tâches

- Traiter **dans l'ordre**, en respectant les dépendances.
- Terminer le workflow complet (0→12) **pour chaque tâche** avant de passer à la suivante.
- Commits **par tâche** (pas de batch multi-tâches).
- Chaque tâche a sa propre branche et sa propre PR.

## Procédure d'abandon

Si à n'importe quelle étape la tâche s'avère irréalisable (spec ambiguë non résoluble, dépendance manquante, contradiction dans les exigences) :

1. **Sauvegarder le travail partiel** : `git stash push -m "WIP #NNN"`.
2. **Documenter le blocage** dans le fichier de tâche : ajouter une section `## Blocage` avec la raison précise et la date.
3. **Passer le statut** à `BLOCKED` (pas `DONE`, pas `IN_PROGRESS`).
4. **Informer l'utilisateur** avec la raison et la suggestion d'action (clarifier la spec, résoudre la dépendance, etc.).
5. **Ne pas supprimer la branche** tant que le blocage n'est pas résolu.

## Conventions Python / AI Trading

> Source de vérité : **`AGENTS.md` § Conventions de code**. Points opérationnels complémentaires ci-dessous.

- **API random NumPy** : toujours utiliser `np.random.default_rng(seed)` (nouvelle API). Ne jamais utiliser `np.random.seed()` ni `np.random.randn()` (legacy API).
- **Exports `__init__.py`** : tout module qui s'enregistre via décorateur à l'import (features, modèles, baselines) doit être importé dans le `__init__.py` de son package. Vérifier cet import à chaque nouveau module.
- **Nommage tests** : structurés par module (`test_config.py`, `test_features.py`, `test_splitter.py`, etc.). Identifiant tâche `#NNN` dans les docstrings uniquement.
- **Ordre des imports** : toujours stdlib → third-party → local, séparés par une ligne vide. Ne jamais contourner I001 avec `# noqa`.
- **Politique `# noqa`** : interdit sauf pour les noms imposés par la spec (ex : `N815` sur `horizon_H_bars`, `L`). Chaque `# noqa` restant doit être justifié par un commentaire.
- **Type checking** : corriger les erreurs Pylance/pyright dans les fichiers modifiés. Ne pas laisser de types `Any` implicites si le type réel est connu.
