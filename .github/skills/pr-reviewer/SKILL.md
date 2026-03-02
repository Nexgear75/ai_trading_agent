---
name: pr-reviewer
description: Revue systématique de Pull Request pour le projet AI Trading Pipeline. Vérifie conformité TDD, anti-fuite, strict code, config-driven, conventions de branche et qualité globale. À utiliser quand l'utilisateur demande « review la PR », « revue de la branche task/NNN-* », « vérifie avant merge ».
argument-hint: "[branche: task/NNN-short-slug] ou [PR number]"
---

# Agent Skill — PR Reviewer (AI Trading Pipeline)

## Objectif
Effectuer une revue systématique et exigeante d'une Pull Request (ou d'une branche `task/NNN-*`) avant merge vers `Max6000i1`, en vérifiant la conformité avec les règles du projet AI Trading Pipeline.

## Contexte repo

- **Spécification** : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (v1.0 + addendum v1.1 + v1.2)
- **Plan** : `docs/plan/implementation.md` (WS-1..WS-12, M1..M5)
- **Tâches** : `docs/tasks/<milestone>/NNN__slug.md`
- **Code source** : `ai_trading/` (package Python principal)
- **Tests** : `tests/` (pytest)
- **Configs** : `configs/default.yaml`
- **Linter** : ruff (`line-length = 100`, `target-version = "py311"`)
- **Langue** : anglais pour code/tests, français pour docs/tâches

## Rôle de l'agent

Tu dois :
- auditer **tous les fichiers modifiés** de la PR/branche par rapport à `Max6000i1` ;
- vérifier la conformité avec chaque règle du projet (voir grille ci-dessous) ;
- produire un **rapport de revue structuré** avec verdict global ;
- ne jamais approuver une PR qui viole une règle non négociable.

## Workflow de revue

### 1. Identifier le périmètre

- Déterminer la branche source (`task/NNN-short-slug`).
- Identifier la tâche associée dans `docs/tasks/<milestone>/NNN__slug.md`.
- Lister les fichiers modifiés vs `Max6000i1` :
  ```
  git diff --name-only Max6000i1...task/NNN-short-slug
  ```

### 2. Vérifier la structure de branche et commits

- [ ] La branche suit la convention `task/NNN-short-slug`.
- [ ] Il existe un commit RED au format `[WS-X] #NNN RED: <résumé>`.
- [ ] Il existe un commit GREEN au format `[WS-X] #NNN GREEN: <résumé>`.
- [ ] Le commit RED contient uniquement des fichiers de tests.
- [ ] Le commit GREEN contient l'implémentation + mise à jour de la tâche.
- [ ] Pas de commits parasites entre RED et GREEN (sauf refactoring mineur).

### 3. Vérifier la tâche associée

- [ ] Le fichier `docs/tasks/<milestone>/NNN__slug.md` est modifié dans la PR.
- [ ] `Statut` est passé à `DONE`.
- [ ] Tous les critères d'acceptation sont cochés `[x]`.
- [ ] Toute la checklist de fin de tâche est cochée `[x]`.
- [ ] Les critères cochés correspondent à des preuves vérifiables (code, tests, artefacts).

### 4. Vérifier les tests

- [ ] Les tests dans `tests/` suivent la convention du plan (`test_config.py`, `test_features.py`, `test_splitter.py`, etc.). L'ID tâche `#NNN` dans les docstrings, pas les noms de fichiers.
- [ ] Chaque critère d'acceptation est couvert par au moins un test.
- [ ] Les tests couvrent : cas nominaux, cas d'erreur, cas de bords.
- [ ] **Boundary fuzzing mental** : pour chaque paramètre numérique d'entrée (`n`, `L`, `H`, taille, etc.), vérifier qu'il existe un test pour chacune de ces situations : `param = 0`, `param = 1`, `param > n` (dépassement), `param = n` (limite exacte). Si une combinaison critique manque, la signaler comme bloquante.
- [ ] Exécuter `pytest` → **tous les tests GREEN**, 0 échec, 0 erreur.
- [ ] Exécuter `ruff check ai_trading/ tests/` → 0 erreur.
- [ ] Pas de test désactivé (`@pytest.mark.skip`, `xfail`) sans justification explicite.
- [ ] Les tests sont déterministes (seeds fixées si aléatoire).
- [ ] Les tests utilisent des données synthétiques (pas de dépendance réseau).

### 5. Audit du code — Règles non négociables

#### 5a. Strict code (no fallbacks)
- [ ] Aucun fallback silencieux (`or default`, `value if value else default`).
- [ ] Aucun `except` trop large qui continue l'exécution.
- [ ] Aucun paramètre optionnel avec default implicite masquant une erreur.
- [ ] Validation explicite aux frontières (entrées utilisateur, données externes).
- [ ] Erreur explicite (`raise`) en cas d'entrée invalide ou manquante.

#### 5a-bis. Revue défensive indexing / slicing
- [ ] Pour tout `array[expr:]` ou `array[:expr]` : vérifier manuellement le comportement quand `expr` est **négatif**, **zéro**, ou **> len(array)**. En Python/NumPy, `array[-k:]` ne fait **pas** `array[0:]` — c'est un piège silencieux.
- [ ] Pour tout `range(a, b)` ou `mask[lo : hi + 1]` : vérifier que `lo` et `hi` sont clampés (`max(0, ...)`, `min(n-1, ...)`) pour toutes les valeurs extrêmes des paramètres d'entrée.
- [ ] Si un paramètre numérique peut dépasser la taille des données (ex. `H > N`), vérifier que le code produit un résultat correct (tout False, raise, etc.) et non un comportement silencieusement faux.

#### 5b. Config-driven (pas de hardcoding)
- [ ] Tout paramètre modifiable est lu depuis `configs/default.yaml` via l'objet config Pydantic v2.
- [ ] Aucune valeur magique ou constante significative hardcodée dans le code.
- [ ] Les formules respectent celles de la spec (§6 features, §5 labels, §8 splits, §12 backtest).
- [ ] Tout choix implementation-defined est explicite dans la config YAML.

#### 5c. Anti-fuite (look-ahead)
- [ ] Aucun accès à des données futures (point-in-time respecté).
- [ ] Embargo respecté : `embargo_bars >= label.horizon_H_bars` (§8.2).
- [ ] Pas de `.shift(-n)` ou équivalent sans justification temporelle correcte.
- [ ] Scaler fit sur train uniquement (pas de données val/test dans fit).
- [ ] Splits walk-forward séquentiels (train < val < test).
- [ ] θ calibré uniquement sur val, jamais sur test.
- [ ] Features causales : backward-looking uniquement.

#### 5d. Reproductibilité
- [ ] Seeds fixées et tracées via `utils/seed.py`.
- [ ] Hashes SHA-256 (données, config) si applicable.
- [ ] Résultats reproductibles sur relance (test de déterminisme si pertinent).

#### 5e. Float conventions
- [ ] Float32 pour tenseurs X_seq et y (mémoire).
- [ ] Float64 pour calculs de métriques (précision).

### 6. Qualité du code

- [ ] Nommage snake_case cohérent.
- [ ] Pas de code mort, commenté ou TODO orphelin.
- [ ] Pas de `print()` de debug restant (utiliser `logging` si nécessaire).
- [ ] Imports propres (pas d'imports inutilisés, pas d'imports `*`).
- [ ] Pas de fichiers générés ou temporaires inclus dans la PR.
- [ ] `.gitignore` couvre les artefacts générés.
- [ ] **DRY — pas de duplication de constantes/mappings** entre modules du même package. Si un dict, une constante ou un mapping est identique dans 2+ fichiers, exiger l'extraction vers un module partagé. Classer comme **bloquant** (risque de drift silencieux).

### 6-bis. Bonnes pratiques métier (concepts de domaine)

- [ ] **Exactitude des concepts financiers** : les indicateurs techniques (RSI, EMA, volatilité, log-returns, etc.) sont implémentés conformément à leur définition canonique (formules standard de référence). Toute déviation par rapport à la formule standard doit être justifiée et documentée.
- [ ] **Nommage métier cohérent** : les noms de variables, fonctions et classes reflètent fidèlement les concepts financiers qu'ils modélisent (ex. `log_return` et non `lr`, `equity_curve` et non `curve`). Pas d'abréviation ambiguë.
- [ ] **Séparation des responsabilités métier** : chaque module encapsule un concept métier unique (ex. features ≠ labels ≠ backtest). Pas de mélange de responsabilités de domaine dans un même module.
- [ ] **Invariants de domaine respectés** : les invariants propres au domaine financier sont vérifiés explicitement dans le code (ex. prix > 0, volume >= 0, equity curve monotone sur un trade, etc.).
- [ ] **Cohérence des unités et échelles** : les grandeurs sont manipulées avec des unités cohérentes (returns en log vs arithmétique, prix en quote currency, timestamps en UTC). Pas de mélange implicite d'échelles.
- [ ] **Patterns de calcul financier** : utilisation des bonnes pratiques pour les calculs numériques financiers (ex. `np.log` au lieu de `math.log` sur des Series, rolling windows via pandas natif, éviter les boucles Python sur les séries temporelles).

### 7. Cohérence avec les specs

- [ ] Le code est conforme à la spec v1.0 (sections référencées dans la tâche).
- [ ] Le code est conforme au plan d'implémentation.
- [ ] Pas d'exigence inventée hors des documents source.
- [ ] **Formules doc vs code** : si la tâche ou un critère d'acceptation contient une formule mathématique (intervalles, bornes, indices), vérifier qu'elle correspond **exactement** à l'implémentation et aux tests. Un off-by-one entre la doc et le code est **bloquant** (ambiguïté potentiellement masquant un bug).

### 8. Cohérence intermodule

Vérifier que les changements de la PR ne créent pas de divergence avec les modules existants.

- [ ] **Signatures et types de retour** : les fonctions/classes modifiées ou créées respectent les signatures attendues par les modules appelants existants (mêmes noms de paramètres, mêmes types, même ordre). Si une signature existante est modifiée, vérifier tous les appels dans le codebase (`grep_search`).
- [ ] **Noms de colonnes DataFrame** : les colonnes produites ou consommées (ex : `close`, `logret_1`, `vol_24`) sont identiques à celles utilisées dans les modules amont/aval. Pas de renommage silencieux ni de divergence de convention.
- [ ] **Clés de configuration** : les clés lues depuis `configs/default.yaml` correspondent aux noms définis dans le modèle Pydantic (`config.py`). Pas de clé orpheline (présente en YAML mais pas lue) ni manquante (lue mais absente du YAML).
- [ ] **Registres et conventions partagées** : si le module s'inscrit dans un registre (ex : `FEATURE_REGISTRY`), vérifier que l'interface implémentée (méthodes, attributs comme `name`, `min_periods`) est cohérente avec les autres entrées du registre et avec le code qui itère dessus.
- [ ] **Structures de données partagées** : les dataclasses, TypedDict ou NamedTuple partagées entre modules sont utilisées de manière identique (mêmes champs, mêmes types). Pas de champ ajouté dans un module sans mise à jour des consommateurs.
- [ ] **Conventions numériques** : les dtypes (float32 vs float64), les conventions NaN (NaN en tête vs valeurs par défaut), et les index (DatetimeIndex, RangeIndex) sont cohérents avec les modules voisins.
- [ ] **Imports croisés** : si le nouveau code importe des symboles d'autres modules du projet, vérifier que ces symboles existent bien dans la branche `Max6000i1` (pas de dépendance sur du code non encore mergé).

Une incohérence intermodule est **bloquante** — elle provoque des bugs silencieux à l'intégration.

## Format du rapport de revue

```markdown
# Revue PR — [WS-X] #NNN — <titre de la tâche>

Branche : `task/NNN-short-slug`
Tâche : `docs/tasks/<milestone>/NNN__slug.md`
Date : YYYY-MM-DD

## Verdict global : ✅ APPROVE | ⚠️ REQUEST CHANGES | ❌ REJECT

## Résumé
[2-3 phrases résumant les changements et le verdict]

## Structure branche & commits
| Critère | Verdict |
|---|---|
| Convention de branche | ✅/❌ |
| Commit RED présent | ✅/❌ |
| Commit GREEN présent | ✅/❌ |
| Pas de commits parasites | ✅/❌ |

## Tâche
| Critère | Verdict |
|---|---|
| Statut DONE | ✅/❌ |
| Critères d'acceptation cochés | ✅/❌ |
| Checklist cochée | ✅/❌ |

## Tests
| Critère | Verdict |
|---|---|
| Couverture des critères | ✅/❌ |
| Cas nominaux + erreurs + bords | ✅/❌ |
| Tous GREEN | ✅/❌ |
| Déterministes | ✅/❌ |
| ruff clean | ✅/❌ |

## Code — Règles non négociables
| Règle | Verdict | Commentaire |
|---|---|---|
| Strict code (no fallbacks) | ✅/❌ | |
| Config-driven | ✅/❌ | |
| Anti-fuite | ✅/❌ | |
| Reproductibilité | ✅/❌ | |
| Float conventions | ✅/❌ | |

## Qualité du code
| Critère | Verdict |
|---|---|
| Nommage et style | ✅/❌ |
| Pas de code mort/debug | ✅/❌ |
| Imports propres | ✅/❌ |

## Conformité spec v1.0
| Critère | Verdict |
|---|---|
| Spécification | ✅/❌ |
| Plan d'implémentation | ✅/❌ |

## Cohérence intermodule
| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | ✅/❌ | |
| Noms de colonnes DataFrame | ✅/❌ | |
| Clés de configuration | ✅/❌ | |
| Registres et conventions partagées | ✅/❌ | |
| Structures de données partagées | ✅/❌ | |
| Conventions numériques | ✅/❌ | |
| Imports croisés | ✅/❌ | |

## Bonnes pratiques métier
| Critère | Verdict | Commentaire |
|---|---|---|
| Exactitude des concepts financiers | ✅/❌ | |
| Nommage métier cohérent | ✅/❌ | |
| Séparation des responsabilités métier | ✅/❌ | |
| Invariants de domaine | ✅/❌ | |
| Cohérence des unités/échelles | ✅/❌ | |
| Patterns de calcul financier | ✅/❌ | |

## Remarques mineures
> **Toutes les remarques, même mineures ou cosmétiques, doivent figurer ici.**
> Elles ne bloquent pas le merge mais doivent être corrigées à terme.

- [Remarque mineure 1]
- [Remarque mineure 2]

## Remarques et blocages
- [Blocage 1]
- [Blocage 2]

## Actions requises (si REQUEST CHANGES ou REJECT)
1. [Action corrective 1]
2. [Action corrective 2]
```

## Règles de verdict

| Verdict | Condition |
|---|---|
| **✅ APPROVE** | Tous les critères non négociables sont satisfaits. Remarques mineures OK post-merge. |
| **⚠️ REQUEST CHANGES** | Au moins un critère non négociable partiellement violé ou tests manquants. |
| **❌ REJECT** | Violation grave : fuite de données, ghost completion, strict code violé, tests RED, ou absence de TDD. |

## Principes de revue

1. **Factuel** : chaque verdict basé sur des preuves concrètes (fichiers, lignes, exécution).
2. **Exhaustif** : passer en revue tous les fichiers modifiés.
3. **Constructif** : chaque blocage accompagné d'une action corrective claire.
4. **Proportionné mais exhaustif** : ne pas **bloquer** pour du cosmétique, mais **toujours signaler** les points mineurs (style, nommage sous-optimal, opportunités de simplification, etc.) dans la section « Remarques mineures » du rapport. Aucune observation ne doit être omise sous prétexte qu'elle est mineure.
5. **Exécuter les tests** : toujours lancer `pytest` et `ruff check` soi-même.
6. **Adversarial** : ne pas se limiter aux tests existants. Pour chaque fonction modifiée, imaginer mentalement 2-3 inputs extrêmes (param > taille données, param = 0, tableaux vides) et vérifier que le code ou les tests les couvrent. Si non → bloquant.
7. **Domain-aware** : vérifier que l'implémentation des concepts métier (indicateurs techniques, mécaniques de trading, calculs financiers) respecte les bonnes pratiques du domaine et les définitions canoniques. Une erreur de concept métier est **bloquante**.
