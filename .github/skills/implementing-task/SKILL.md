---
name: implementing-task
description: Implémenter une ou plusieurs tâches de docs/tasks/ via TDD strict (tests d'acceptation → rouge → vert), conventions du repo AI Trading Pipeline, seuils de couverture, mise à jour du fichier de tâche et commits. À utiliser quand l'utilisateur demande « implémente/exécute/travaille sur la tâche #NNN ».
---

# Agent Skill — Implementing Task (AI Trading Pipeline)

## Objectif
Exécuter des tâches décrites dans `docs/tasks/NNN__slug.md` selon un workflow **TDD strict**, en respectant les conventions du dépôt AI Trading Pipeline, puis livrer proprement (tests, couverture, statut de tâche, commits).

## Contexte repo

- **Tâches** : `docs/tasks/NNN__slug.md`
- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2)
- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Code source** : `ai_trading/` (package Python principal)
- **Tests** : `tests/` (pytest, config dans `pyproject.toml`)
- **Configs** : `configs/default.yaml` (Pydantic v2)
- **Données brutes** : `data/raw/` (Parquet OHLCV)
- **Artefacts de run** : `runs/` (manifest.json + metrics.json)
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)
- **Langue** : anglais pour code/tests, français pour docs/tâches

## Principes non négociables

- **Zéro "ghost completion"** : ne jamais marquer une tâche `DONE` ni cocher un critère `[x]` sans **code + tests** et **exécution vérifiée**.
- **TDD réel** : écrire les tests avant l'implémentation, vérifier qu'ils échouent, puis implémenter.
- **Strict code (no fallbacks)** : aucun fallback silencieux, aucun `or default`, aucun `except` trop large. Validation explicite + `raise`.
- **Config-driven** : tout paramètre modifiable lu depuis `configs/default.yaml` via Pydantic v2. Zéro hardcoding.
- **Anti-fuite** : ne jamais introduire de look-ahead. Données point-in-time. Embargo `embargo_bars >= H`. Scaler fit sur train uniquement. Splits walk-forward séquentiels (train < val < test).
- **Reproductibilité** : seeds fixées et tracées. Hashes SHA-256 (données, config).
- **Traçabilité** : commits liés au workstream et au numéro de tâche.
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
- dépendances (vérifier que les tâches prérequises sont DONE).

### 2. Lire les sections de spec nécessaires
Charger uniquement les parties référencées de la spécification et du plan. Ne pas charger tout le document.

### 3. Écrire les tests (RED)
- Créer/modifier les fichiers de test dans `tests/` (convention plan : `test_config.py`, `test_features.py`, `test_splitter.py`, `test_backtest.py`, etc.). L'identifiant `#NNN` va dans les docstrings, pas dans les noms de fichiers.
- **Imports corrects dès l'écriture** : respecter l'ordre ruff/isort (stdlib → third-party → local, séparés par une ligne vide). Ne jamais ajouter d'imports inutiles.
- Couvrir chaque critère d'acceptation avec au moins un test.
- Inclure des cas nominaux, erreurs, et bords.
- **Fuzzing systématique des paramètres numériques** : pour chaque paramètre numérique en entrée (`n`, `L`, `H`, period, window, etc.), inclure un test pour : `param = 0`, `param = 1`, `param = valeur_max`, combinaison de minimums simultanés (ex : `fast=1, slow=1`), `param > taille_données`. Si une combinaison critique manque, l'ajouter.
- **Atomicité des tests** : chaque test doit vérifier **un seul scénario**. Ne pas empiler plusieurs `pytest.raises` ou assertions indépendantes dans un même test body. Si le premier échoue, les suivants ne s'exécutent pas.
- Utiliser des données synthétiques (fixtures `conftest.py`), jamais de données réseau.
- Si la tâche concerne l'anti-fuite : inclure un test de perturbation (modifier prix futurs → résultat identique pour t ≤ T).
- **Lancer `ruff check` sur le fichier test après écriture**, avant le commit RED. Corriger tout diagnostic à la source (réordonner, supprimer l'import, renommer) — jamais de `# noqa` comme contournement.

### 4. Prouver que les tests échouent
`pytest tests/test_xxx.py -v` → RED.

### 5. Commit RED
```bash
git add tests/
git commit -m "[WS-X] #NNN RED: <résumé des tests ajoutés>"
```
Le commit RED ne contient **que** des fichiers de tests.

### 6. Implémenter (GREEN)
Écrire le **minimum** pour faire passer les tests :
- **Strict code** : validation explicite + `raise`. Pas de fallbacks, pas de defaults implicites.
- **Config-driven** : paramètres dans `configs/default.yaml`, pas hardcodés.
- **Anti-fuite** : aucun `.shift(-n)` sans justification temporelle correcte.
- **Float32** pour tenseurs X_seq et y. **Float64** pour calculs de métriques.
- **Nommage** : snake_case, anglais pour le code.
- **Imports** : pas d'import `*`, pas d'imports inutilisés, pas de variables assignées mais jamais référencées (dead code). Ordre isort strict (stdlib → third-party → local).
- **Pas de print()** : utiliser `logging` uniquement si le module en a besoin. Ne pas importer `logging` ni créer `logger` « au cas où ».
- **Corrections à la source** : si ruff signale un problème, corriger la cause (renommer, réordonner, supprimer). Ne jamais appliquer deux corrections contradictoires en même temps (ex : renommer un symbol ET ajouter un `# noqa` sur le même diagnostic).

### 7. Valider la suite complète (commandes exactes, obligatoires)
Exécuter **exactement** ces deux commandes, telles quelles (pas fichier par fichier) :
```bash
ruff check ai_trading/ tests/
pytest
```
- `ruff check ai_trading/ tests/` → **0 erreur, 0 warning**. Si une erreur persiste, revenir à l'étape 6 et corriger à la source.
- `pytest` → **tous GREEN** (nouveaux + existants), aucune régression, 0 échec, 0 erreur de collection.

**Ne jamais** passer à l'étape 8 si l'une de ces commandes échoue.

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
- [ ] **Aucun import inutilisé** : chaque `import` est référencé dans le code.
- [ ] **Aucune variable morte** : chaque variable assignée est utilisée au moins une fois.
- [ ] **Aucun `# noqa` injustifié** : seuls les `# noqa` pour des noms imposés par la spec sont tolérés (ex : `N815` sur `horizon_H_bars`). Si un `# noqa` existe, vérifier qu'il est encore nécessaire.
- [ ] **Imports ordonnés** : stdlib → third-party → local, séparés par des lignes vides. Pas de `# noqa: I001`.
- [ ] **Pas de code mort, commenté, ou TODO orphelin.**
- [ ] **Pas de `print()`** restant.

Si un point de cette checklist échoue, corriger **avant** de passer à l'étape 9.

### 9. Mettre à jour la tâche
Dans `docs/tasks/NNN__slug.md` :
- Cocher chaque critère d'acceptation vérifié : `- [x]`
- Cocher chaque item de la checklist de fin de tâche : `- [x]`
- Passer `Statut : DONE`
- **Corriger les sections descriptives** (Objectif, Évolutions proposées, Règles attendues) si elles sont factuellement incorrectes après implémentation (ex : `min_periods` retourne une valeur différente de celle annoncée dans la tâche). Le fichier de tâche doit refléter fidèlement le code livré.

### 10. Commit GREEN (clôture)
Conditions requises : tests GREEN + tous les critères d'acceptation validés + checklist cochée.
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

## Format de commits

| Moment | Format | Contenu |
|---|---|---|
| Après tests RED | `[WS-X] #NNN RED: <résumé>` | Fichiers de tests uniquement |
| Clôture tâche | `[WS-X] #NNN GREEN: <résumé>` | Implémentation + mise à jour tâche |

Aucun commit intermédiaire entre RED et GREEN sauf refactoring mineur (tests verts).

## Plusieurs tâches

- Traiter **dans l'ordre**, en respectant les dépendances.
- Terminer le workflow complet (0→11) **pour chaque tâche** avant de passer à la suivante.
- Commits **par tâche** (pas de batch multi-tâches).
- Chaque tâche a sa propre branche et sa propre PR.

## Conventions Python / AI Trading

- **Framework de test** : pytest (config dans `pyproject.toml`).
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`).
- **Configs** : YAML versionnées dans `configs/`.
- **Données** : `data/raw/` (Parquet OHLCV).
- **Artefacts** : `runs/` (manifest.json + metrics.json par run).
- **Seeds** et **hashes SHA-256** obligatoires pour la reproductibilité.
- **API random NumPy** : toujours utiliser `np.random.default_rng(seed)` (nouvelle API). Ne jamais utiliser `np.random.seed()` ni `np.random.randn()` (legacy API).
- **Modules attendus** : config, data/ingestion, data/qa, data/dataset, data/splitter, data/scaler, features/registry, features/pipeline, models/base, models/dummy, training/trainer, calibration/threshold, backtest/engine, baselines/*, metrics/prediction, metrics/trading, metrics/aggregation, artifacts/run_dir, artifacts/manifest, artifacts/metrics_builder, artifacts/schema_validator, utils/seed, pipeline/runner.
- **Nommage tests** : structurés par module (`test_config.py`, `test_features.py`, `test_splitter.py`, etc.). Identifiant tâche `#NNN` dans les docstrings uniquement.
- **Ordre des imports** : toujours stdlib → third-party → local, séparés par une ligne vide. Ne jamais contourner I001 avec `# noqa`.
- **Politique `# noqa`** : interdit sauf pour les noms imposés par la spec (ex : `N815` sur `horizon_H_bars`, `L`). Chaque `# noqa` restant doit être justifié par un commentaire.
