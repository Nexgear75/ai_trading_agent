# Revue PR — [WS-6] #025 — DummyModel pour tests d'intégration

Branche : `task/025-dummy-model`
Tâche : `docs/tasks/M3/025__ws6_dummy_model.md`
Date : 2025-03-02
Itération : v1

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

L'implémentation de `DummyModel` est propre, bien testée et conforme au contrat `BaseModel`. Le modèle est correctement enregistré dans `MODEL_REGISTRY`, les signatures correspondent exactement au contrat ABC, et les 22 tests couvrent les critères d'acceptation (nominaux, erreurs, bords, reproductibilité). Deux points mineurs à corriger : un commit parasite non lié à la tâche dans la branche, et un écart entre le format JSON de `save()` décrit dans la tâche et l'implémentation effective.

## Fichiers modifiés (vs Max6000i1)

| Fichier | Rôle |
|---|---|
| `ai_trading/models/dummy.py` | Implémentation DummyModel |
| `ai_trading/models/__init__.py` | Auto-import pour peuplement registre |
| `tests/test_dummy_model.py` | 22 tests (6 classes) |
| `docs/tasks/M3/025__ws6_dummy_model.md` | Tâche mise à jour DONE |
| `pyproject.toml` | Per-file-ignores ruff N803/N806 |
| `.github/skills/implementing-task/SKILL.md` | Modification du skill (non liée) |

## Structure branche & commits

| Critère | Verdict | Commentaire |
|---|---|---|
| Convention de branche `task/025-dummy-model` | ✅ | |
| Commit RED présent `[WS-6] #025 RED: tests DummyModel fit/predict/save/load` | ✅ | `148fd50` — contient uniquement `tests/test_dummy_model.py` |
| Commit GREEN présent `[WS-6] #025 GREEN: DummyModel pour tests d'intégration` | ✅ | `f9006a1` — implémentation + __init__ + task + pyproject + tests |
| Pas de commits parasites entre RED et GREEN | ✅ | Aucun commit entre RED et GREEN |
| Commit parasite hors périmètre | ⚠️ | `eb5bc48` modifie `.github/skills/implementing-task/SKILL.md` — non lié à la tâche #025 (voir remarque 1) |

Historique des commits :
```
eb5bc48 correction skill ajout fichiers de revue dans commit pre PR  ← parasite
148fd50 [WS-6] #025 RED: tests DummyModel fit/predict/save/load
f9006a1 [WS-6] #025 GREEN: DummyModel pour tests d'intégration
```

## Tâche

| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés (12/12) | ✅ |
| Checklist cochée (8/8) | ✅ |

## Tests

| Critère | Verdict | Commentaire |
|---|---|---|
| Convention nommage `test_dummy_model.py` | ✅ | ID #025 dans docstrings |
| Couverture des critères d'acceptation | ✅ | Chaque critère a ≥1 test |
| Cas nominaux | ✅ | Attributs, fit, predict, save/load, registry |
| Cas d'erreur | ✅ | Fichier manquant, JSON corrompu, clé manquante |
| Cas bords | ✅ | N=0 (empty array), N=1 (single sample) |
| Boundary fuzzing | ✅ | N=0 et N=1 testés ; pas de paramètre numérique borné |
| `pytest` GREEN | ✅ | 712 passed, 0 failed |
| `ruff check` clean | ✅ | All checks passed |
| Déterministes (seeds fixées) | ✅ | Seeds explicites (42, 77, 99, 123, etc.) |
| Données synthétiques | ✅ | numpy.random.default_rng, pas de réseau |
| Tests désactivés | ✅ | Aucun skip/xfail |

## Code — Règles non négociables

| Règle | Verdict | Commentaire |
|---|---|---|
| Strict code (no fallbacks) | ✅ | `load()` : validation explicite + raise (FileNotFoundError, KeyError). Pas de `except` large. |
| Config-driven | ✅ / N/A | DummyModel est un outil de test, pas de paramètre à lire depuis config. `seed` passé au constructeur. |
| Anti-fuite | ✅ / N/A | Pas de données temporelles, pas de split. `fit()` est no-op. |
| Reproductibilité | ✅ | `default_rng(seed)` recréé à chaque `predict()` → même seed = même sortie. Testé. |
| Float conventions | ✅ | `predict()` retourne float32 (`.astype(np.float32)`). Vérifié par test. |
| Defensive indexing | ✅ | Seul accès : `X.shape[0]` — pas de slicing risqué. Cas N=0 testé. |

## Qualité du code

| Critère | Verdict | Commentaire |
|---|---|---|
| snake_case | ✅ | Nommage conforme. `X`, `N`, `L`, `F` suivent la convention ML (ignorés via N803/N806). |
| Pas de print() / code mort / TODO | ✅ | |
| Imports propres | ✅ | stdlib → third-party → local. |
| DRY | ✅ | Pas de duplication. |
| `# noqa` justifiés | ✅ | `F401` dans `__init__.py` pour import side-effect (peuplement registre). `N803`/`N806` dans pyproject.toml pour convention ML `X_train`, `X_val`, etc. |
| Pas de fichiers générés | ✅ | |

## Cohérence avec les specs

| Critère | Verdict | Commentaire |
|---|---|---|
| Conforme spec §10 | ✅ | Implémente le contrat BaseModel (§10.1, §10.2, §10.4). |
| Conforme plan WS-6.2 | ✅ | |
| Formules doc vs code | ⚠️ | Format save() diffère de la tâche (voir remarque 2) |

## Cohérence intermodule

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures BaseModel | ✅ | `fit()`, `predict()`, `save()`, `load()` — paramètres, types et defaults identiques à l'ABC. |
| `output_type` / `execution_mode` | ✅ | Validés par `__init_subclass__` de BaseModel. |
| Registry pattern | ✅ | `@register_model("dummy")` cohérent avec `base.py`. |
| `__init__.py` exports | ✅ | `from ai_trading.models import dummy` peuple le registre. `__all__` expose les bons symboles. |
| Imports croisés | ✅ | Dépend uniquement de `ai_trading.models.base` (présent sur Max6000i1). |
| Conventions numériques | ✅ | float32 pour predict, NaN non applicable. |

## Remarques

1. **[MINEUR]** Commit parasite dans la branche
   - Fichier : `.github/skills/implementing-task/SKILL.md`
   - Commit : `eb5bc48` — « correction skill ajout fichiers de revue dans commit pre PR »
   - Description : Ce commit modifie le workflow du skill `implementing-task` et n'a aucun rapport avec la tâche #025. Bien qu'il soit situé avant le commit RED (et non entre RED et GREEN), il pollue l'historique de la branche `task/025-dummy-model`.
   - Suggestion : Rebaser pour extraire ce commit sur une branche dédiée, ou le squasher dans une branche utilitaire séparée avant merge.

2. **[MINEUR]** Écart format JSON de `save()` entre tâche et implémentation
   - Fichier : `ai_trading/models/dummy.py`, ligne 58
   - Tâche : « `save(path)` : exporte un fichier JSON minimal `{"seed": 42, "constant": 0.0}` »
   - Code : `json.dumps({"seed": self._seed})` — la clé `"constant"` est absente.
   - Description : La tâche spécifie un format JSON incluant `"constant"`, mais l'implémentation ne sauvegarde que `"seed"` puisque la fonctionnalité de prédiction constante n'a pas été retenue (seule l'approche RNG a été implémentée). L'implémentation est cohérente en interne, mais la tâche n'a pas été mise à jour pour refléter ce choix.
   - Suggestion : Mettre à jour la description de la tâche (section « Évolutions proposées ») pour aligner le format JSON documenté avec le format réellement implémenté (`{"seed": <int>}`), ou ajouter la clé `"constant"` dans le JSON sauvegardé si la fonctionnalité constante est prévue pour plus tard.

## Résumé

Implémentation de bonne qualité : code minimal, bien structuré, tests complets (22 tests, 6 classes), conformité au contrat BaseModel vérifiée. Deux points mineurs à adresser : (1) un commit parasite dans la branche et (2) un écart entre le format JSON de save() décrit dans la tâche et celui implémenté.
