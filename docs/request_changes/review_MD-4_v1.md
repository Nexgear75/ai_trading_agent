# Revue globale — milestone/MD-4 v1

**Branche** : `milestone/MD-4`
**Date** : 2026-03-09
**Scope** : Streamlit dashboard (WS-D-6) — tâches 088, 089, 090, 091

## Résultat CI

| Check | Résultat |
|---|---|
| pytest | 2283 passed, 0 failed, 27 deselected |
| ruff check | All checks passed |

## Items trouvés et corrigés

### W-1 — WARNING — `COPY runs/ runs/` dans Dockerfile.dashboard

- **Fichier** : `Dockerfile.dashboard` L9
- **Description** : `COPY runs/ runs/` échoue sur un clone frais (runs/ dans .gitignore). Le volume mount rend la copie redondante.
- **Correction** : Remplacé par `RUN mkdir -p runs/`.
- **Statut** : ✅ Corrigé

### M-1 — MINEUR — `except Exception:` large pour import guard

- **Fichier** : `scripts/dashboard/data_loader.py` L30
- **Description** : `except Exception:` trop large pour un import conditionnel.
- **Correction** : Remplacé par `except (ImportError, AttributeError):`.
- **Statut** : ✅ Corrigé

### M-2 — MINEUR — `np.random.RandomState` (legacy API) dans tests

- **Fichier** : `tests/test_dashboard_integration.py` L35, 161, 476, 477
- **Description** : API legacy au lieu de `np.random.default_rng(seed)`.
- **Correction** : Remplacé par `np.random.default_rng(42)` et `.standard_normal()`.
- **Statut** : ✅ Corrigé

### M-3 — MINEUR — Variable morte `_RNG`

- **Fichier** : `tests/test_dashboard_integration.py` L35
- **Description** : `_RNG = np.random.RandomState(42)` jamais utilisé.
- **Correction** : Supprimé.
- **Statut** : ✅ Corrigé

## Résumé

4 items trouvés (0 BLOQUANT, 1 WARNING, 3 MINEUR). Tous corrigés.
pytest GREEN (145 tests dashboard), ruff clean.
