# Revue PR — [WS-12] #053 — Makefile (pilotage du pipeline)

Branche : `task/053-makefile`
Tâche : `docs/tasks/M5/053__ws12_makefile.md`
Date : 2026-03-03

## Verdict global : ⚠️ REQUEST CHANGES

## Résumé

Le Makefile est bien structuré et couvre toutes les cibles principales, utilitaires, et de gate demandées par la tâche. Les tests (52 tests) sont complets et passent tous. Cependant, plusieurs gates milestone/intra-milestone divergent du plan WS-12.6 (tests manquants, couverture non mesurée), et des détails de conformité spec/plan restent à corriger.

---

## Phase A — Compliance

### Structure branche & commits

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de branche `task/053-makefile` | ✅ | `git branch --show-current` → `task/053-makefile` |
| Commit RED présent | ✅ | `90b3621` — `[WS-12] #053 RED: tests Makefile` |
| Commit GREEN présent | ✅ | `48179a0` — `[WS-12] #053 GREEN: Makefile` |
| Commit RED = tests uniquement | ✅ | `git show --stat 90b3621` → `tests/test_makefile.py` (1 file, 411 insertions) |
| Commit GREEN = implémentation + tâche | ✅ | `git show --stat 48179a0` → `Makefile` (166 lines) + `docs/tasks/M5/053__ws12_makefile.md` (48 changes) |
| Pas de commits parasites | ✅ | `git log --oneline Max6000i1...HEAD` → 2 commits uniquement |

### Tâche

| Critère | Verdict | Preuve |
|---|---|---|
| Statut DONE | ✅ | diff montre `Statut : TODO` → `Statut : DONE` |
| Critères d'acceptation cochés | ✅ (15/15) | Tous `[ ]` → `[x]` dans le diff |
| Checklist cochée | ✅ (8/9) | 1 item non coché : PR non encore ouverte — attendu à ce stade |

### CI

| Check | Résultat |
|---|---|
| `pytest tests/ -v --tb=short` | **1555 passed**, 0 failed |
| `pytest tests/test_makefile.py -v` | **52 passed**, 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |

---

## Phase B — Code Review

### Résultats du scan automatisé (B1)

| Pattern recherché | Commande | Résultat |
|---|---|---|
| Fallbacks silencieux (§R1) | `grep 'or []\|or {}...'` sur `tests/test_makefile.py` | 0 occurrences |
| Except trop large (§R1) | `grep 'except:$\|except Exception:'` | 0 occurrences |
| Print résiduel (§R7) | `grep 'print('` | 0 occurrences |
| Shift négatif (§R3) | `grep '.shift(-'` | 0 occurrences |
| Legacy random API (§R4) | `grep 'np.random.seed...'` | 0 occurrences |
| TODO/FIXME orphelins (§R7) | `grep 'TODO\|FIXME...'` | 0 occurrences |
| Chemins hardcodés (§R7) | `grep '/tmp\|C:\\'` sur tests | 0 occurrences |
| Mutable defaults (§R6) | `grep 'def.*=[]\|def.*={}'` | 0 occurrences |
| noqa (§R7) | `grep 'noqa'` sur fichiers modifiés | 0 occurrences |
| Identité booléenne (§R6) | `grep 'is np.bool_\|is True\|is False'` | 0 occurrences |
| per-file-ignores (§R7) | `grep 'per-file-ignores' pyproject.toml` | Pré-existant (N803 sur base_model/dummy/trainer) — non modifié par cette PR |

### Annotations par fichier (B2)

#### `Makefile` (166 lignes, nouveau fichier)

- **L9** `SHELL := /bin/bash` : Bon, explicite.
- **L14-16** Variables `CONFIG ?=`, `MODEL ?=`, `SEED ?=` : Correctement surchargeables via `?=`.
- **L19-25** Bloc `OVERRIDES` avec `ifneq` conditionnels : Logique correcte — `--set strategy.name=$(MODEL)` et `--set reproducibility.global_seed=$(SEED)` ne sont ajoutés que si non vides.
- **L46** `run-all: fetch-data qa run` : Chaîne correcte selon spec §17.3.
- **L59** `lint:` — ne fait que `ruff check ai_trading/ tests/`. Voir WARNING 1 ci-dessous.
- **L65** `docker-run:` — utilise `$(shell pwd)` au lieu de `$$(pwd)` de la spec. Fonctionnellement équivalent.
- **L69-72** `clean:` — nettoyage plus complet que la spec (ajoute `.ruff_cache`, `.mypy_cache`, `ai_trading.egg-info`, `build`, `dist`, et `find` pour `__pycache__` et `.pyc`). Acceptable.
- **L74-77** `help:` — utilise `$(MAKEFILE_LIST)` et ajoute coloration ANSI. Pattern `##` conforme. Pas de `sort` (spec le prévoit) — acceptable, ordre de fichier plus naturel.
- **L87** `gate-m1:` — manque `test_config_validation.py`, `test_missing.py`, et `--cov-fail-under=95`. Voir WARNING 1.
- **L120** `gate-doc:` — manque `--cov=ai_trading/calibration`. Voir WARNING 2.
- **L132-136** `gate-m3:` — re-exécute les mêmes tests que `gate-doc` (dépendance) moins `test_theta_bypass.py`. Redondant mais non faux.

RAS additionnel après lecture complète du diff (166 lignes).

#### `tests/test_makefile.py` (411 lignes, nouveau fichier)

- **L10** `PROJECT_ROOT = Path(__file__).resolve().parent.parent` : Pattern standard, correct.
- **L15-17** Fixture `makefile_content` avec `pytest.fail` si fichier absent : Bon pattern défensif.
- **L20-30** `_run_make()` et `_run_make_with_vars()` : Utilise `subprocess.run` avec `capture_output=True`, `text=True`, `timeout=30`, `cwd=PROJECT_ROOT`. Correct, sûr.
- **L62-88** `TestHelpTarget` : Teste retour 0, cibles principales, utilitaires, et gates dans la sortie help. Bonne couverture.
- **L91-119** `TestVariableDefaults` : Vérifie existence des variables CONFIG, MODEL, SEED et pattern `?=`. Tests pertinents.
- **L122-166** `TestMainTargetsDryRun` : Dry-run sur install, fetch-data, qa, run, run-all. Vérifie les commandes attendues dans stdout.
- **L169-205** `TestUtilityTargetsDryRun` : Dry-run sur test, lint, docker-build, docker-run, clean.
- **L208-240** `TestVariableOverrides` : Vérifie CONFIG override, MODEL override (présence de `--set strategy.name`), SEED override (présence de `--set reproducibility.global_seed`). Bonne couverture.
- **L243-282** `TestGateTargetsDryRun` : Paramétré sur 1-5 milestones et gates intra. Vérifie que dry-run réussit, que `reports` est mentionné, et que les gates intra incluent `--cov`.
- **L285-361** `TestGateDependencies` : Vérifie chaque maillon de la chaîne de dépendances en parsant le contenu du Makefile. 8 tests couvrant GM1→G-Features→G-Split→GM2→G-Doc→GM3→G-Backtest→GM4→GM5. Complet et correct.
- **L364-411** `TestHelpComments` : Vérifie que chaque cible a un commentaire `##`.

RAS additionnel après lecture complète du diff (417 lignes de diff).

### Tests (B3)

| Critère | Verdict | Preuve |
|---|---|---|
| Convention de nommage | ✅ | `test_makefile.py`, docstrings avec `#053` |
| Couverture des critères d'acceptation | ✅ | Mapping : help (L68-88), install (L124), test (L169), lint (L175), run CONFIG (L136+L213), fetch-data (L128), run-all (L142), docker-build/run (L181-205), overrides (L208-240), gates m1-m5 (L247-260), gates intra (L268-278), dépendances (L285-361), commentaires help (L364-411) |
| Cas nominaux + erreurs + bords | ✅ | Nominaux couverts, dry-run évite les side-effects réels. Pas de cas d'erreur explicites mais le domaine le justifie (Makefile syntaxe) |
| Boundary fuzzing | N/A | Pas de paramètres numériques dans ce module |
| Déterministes | ✅ | Pas d'aléatoire (tests déterministes par nature — parsing Makefile) |
| Données synthétiques | ✅ | Tests basés sur parsing de fichier local et dry-run |
| Portabilité chemins | ✅ | Scan B1 : 0 `/tmp` hardcodé. Utilise `PROJECT_ROOT` |
| Tests registre réalistes | N/A | Pas de registre |
| Contrat ABC complet | N/A | Pas d'ABC |
| Tests désactivés | ✅ | 0 `@pytest.mark.skip` ou `xfail` |

### Code — Règles non négociables (B4)

| Règle | Verdict | Preuve |
|---|---|---|
| Strict code (no fallbacks) (§R1) | ✅ | Scan B1 : 0 fallback, 0 except large. Code Makefile : pas de fallback silencieux. `|| true` dans `clean` est un pattern Makefile standard pour ignorer les erreurs de `find` quand aucun fichier ne correspond — acceptable. |
| Defensive indexing (§R10) | N/A | Pas de slicing/indexing numérique |
| Config-driven (§R2) | ✅ | `CONFIG ?= configs/default.yaml`, `MODEL`, `SEED` surchargeables |
| Anti-fuite (§R3) | N/A | Pas de traitement de données temporelles |
| Reproductibilité (§R4) | N/A | Pas d'aléatoire. Scan B1 : 0 legacy random |
| Float conventions (§R5) | N/A | Pas de calcul numérique |
| Anti-patterns Python (§R6) | ✅ | Scan B1 : 0 mutable default, 0 identité booléenne |

### Qualité du code (B5)

| Critère | Verdict | Preuve |
|---|---|---|
| Nommage et style | ✅ | snake_case dans tests, kebab-case dans cibles Makefile (convention standard) |
| Pas de code mort/debug | ✅ | Scan B1 : 0 print, 0 TODO |
| Imports propres | ✅ | `subprocess`, `pathlib.Path`, `pytest` — pas d'import inutilisé, pas d'import `*` |
| DRY | ✅ | Helpers `_run_make` et `_run_make_with_vars` factorisent l'appel subprocess |
| `.gitignore` artefacts | ⚠️ | `reports/` non couvert — voir MINEUR 2 |
| Fichiers générés dans PR | ✅ | Aucun fichier généré inclus |

### Conformité spec v1.0 (B6)

| Critère | Verdict | Commentaire |
|---|---|---|
| Spec §17.3 | ⚠️ | `lint` manque `mypy` (spec explicite). Voir MINEUR 1 |
| Plan WS-12.6 | ⚠️ | `gate-m1` manque tests et couverture (voir WARNING 1). `gate-doc` manque couverture calibration (voir WARNING 2) |
| Formules doc vs code | N/A | Pas de formule mathématique dans ce module |

### Cohérence intermodule (B7)

| Critère | Verdict | Commentaire |
|---|---|---|
| Signatures et types de retour | N/A | Makefile, pas d'API Python |
| Noms de colonnes DataFrame | N/A | |
| Clés de configuration | ✅ | `strategy.name` et `reproducibility.global_seed` correspondent au config Pydantic |
| Registres | N/A | |
| Structures de données | N/A | |
| Conventions numériques | N/A | |
| Imports croisés | N/A | Test file importe uniquement stdlib + pytest |

### Bonnes pratiques métier (B5-bis)

N/A — Ce module est un outil de pilotage (Makefile), pas un module de calcul financier.

---

## Remarques

### WARNING

1. **[WARNING] gate-m1 incomplet par rapport au plan WS-12.6**
   - Fichier : `Makefile`
   - Ligne(s) : 87-92
   - Description : Le plan WS-12.6 spécifie que `gate-m1` doit lancer `pytest tests/test_config.py tests/test_config_validation.py tests/test_ingestion.py tests/test_qa.py tests/test_missing.py --cov=ai_trading.config --cov=ai_trading.data.ingestion --cov=ai_trading.data.qa --cov=ai_trading.data.missing --cov-fail-under=95`. L'implémentation ne lance que `test_config.py`, `test_ingestion.py`, `test_qa.py` sans mesure de couverture. Les fichiers `tests/test_config_validation.py` et `tests/test_missing.py` existent dans le repo.
   - Suggestion : Ajouter les tests manquants et le flag `--cov-fail-under=95` :
     ```makefile
     gate-m1:
         @mkdir -p reports
         pytest tests/test_config.py tests/test_config_validation.py \
             tests/test_ingestion.py tests/test_qa.py tests/test_missing.py \
             -v --tb=short \
             --cov=ai_trading/config.py --cov=ai_trading/data \
             --cov-fail-under=95
         @echo '{"gate": "M1", "status": "GO"}' > reports/gate_report_M1.json
     ```

2. **[WARNING] gate-doc manque la mesure de couverture calibration**
   - Fichier : `Makefile`
   - Ligne(s) : 120-127
   - Description : Le plan WS-12.6 spécifie `--cov=ai_trading.training --cov=ai_trading.calibration --cov-fail-under=90`. L'implémentation ne mesure que `--cov=ai_trading/training` — le package `ai_trading/calibration/` (contenant `threshold.py`) n'est pas couvert.
   - Suggestion : Ajouter `--cov=ai_trading/calibration` au target `gate-doc`.

### MINEUR

1. **[MINEUR] lint target sans mypy (divergence spec §17.3)**
   - Fichier : `Makefile`
   - Ligne(s) : 58-59
   - Description : La spec §17.3 et le plan WS-12.6 spécifient `ruff check ai_trading/ tests/ && mypy ai_trading/`. L'implémentation n'exécute que `ruff check`. La tâche 053 mentionne "(+ mypy si configuré)" rendant cela conditionnel, mais les documents source sont explicites.
   - Suggestion : Ajouter `&& mypy ai_trading/` ou documenter explicitement dans le Makefile que mypy est optionnel (commentaire).

2. **[MINEUR] reports/ non couvert par .gitignore**
   - Fichier : `.gitignore` (absent de la PR)
   - Description : Les cibles de gate créent `reports/gate_report_*.json`. Ces artefacts générés ne sont pas dans `.gitignore`. §R7 exige que le gitignore couvre les artefacts générés. Un `make gate-m1` polluerait `git status`.
   - Suggestion : Ajouter `reports/` au `.gitignore`.

3. **[MINEUR] Nommage JSON des rapports de gate diverge du plan**
   - Fichier : `Makefile`
   - Lignes : 93, 101, 110, etc.
   - Description : Le plan WS-12.6 spécifie `reports/gate_report_G_<Name>.json` (underscore). L'implémentation utilise `reports/gate_report_G-<Name>.json` (hyphen). Exemples : `gate_report_G-Features.json` vs attendu `gate_report_G_Features.json`.
   - Suggestion : Aligner le nommage avec le plan (underscore) : `gate_report_G_Features.json`, `gate_report_G_Split.json`, etc.

---

## Résumé

Le Makefile est fonctionnel, bien structuré et conforme aux cibles principales de la tâche 053. Les 52 tests passent et couvrent les critères d'acceptation. Deux points nécessitent correction : les gates `gate-m1` et `gate-doc` sont moins rigoureux que spécifié dans le plan (tests et couverture manquants). Trois points mineurs concernent l'absence de mypy dans lint, le non-gitignore de `reports/`, et la convention de nommage des rapports JSON.

---

RÉSULTAT PARTIE B :
- Verdict : REQUEST CHANGES
- Bloquants : 0
- Warnings : 2
- Mineurs : 3
- Rapport : `docs/tasks/M5/053/review_v1.md`
