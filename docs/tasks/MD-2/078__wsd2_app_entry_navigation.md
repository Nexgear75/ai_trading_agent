# Tâche — Point d'entrée Streamlit et navigation multi-pages

Statut : DONE
Ordre : 078
Workstream : WS-D-2
Milestone : MD-2
Gate lié : N/A

## Contexte
Le dashboard Streamlit nécessite un point d'entrée `app.py` configuré avec le layout, le titre, le paramètre `--runs-dir`, et la navigation multi-pages. Actuellement `app.py` est un stub vide (créé en MD-1, tâche #073). Cette tâche l'implémente intégralement.

Références :
- Plan : `docs/plan/streamlit/implementation.md` (section WS-D-2.1)
- Spécification : `docs/specifications/streamlit/Specification_Dashboard_Streamlit_v1.0.md` (§5.1, §9.4, §10.2, §10.3)
- Code : `scripts/dashboard/app.py`

Dépendances :
- Tâche 073 — Structure projet et dépendances (DONE)
- Tâche 074 — Data loader discovery (DONE)

## Objectif
Implémenter `app.py` comme point d'entrée multi-pages Streamlit avec configuration de page, découverte des runs, et stockage dans `st.session_state`.

## Règles attendues
- **Config-driven** : le répertoire de runs est configurable via `--runs-dir` CLI > `AI_TRADING_RUNS_DIR` env var > défaut `runs/` (spec §5.1, ordre de précédence strict).
- **Strict code** : pas de fallback silencieux. Si le répertoire n'existe pas, lever une erreur explicite.
- **Sécurité** : validation du chemin avec `Path.resolve()` (spec §11.1).

## Évolutions proposées
- Implémenter `st.set_page_config(layout="wide", page_title="AI Trading Dashboard")` (spec §9.4).
- Implémenter la résolution du paramètre `--runs-dir` avec l'ordre de précédence : argument CLI (`sys.argv`) > variable d'environnement `AI_TRADING_RUNS_DIR` > défaut `runs/`.
- Charger les runs via `discover_runs()` de `data_loader.py` au démarrage.
- Stocker les résultats dans `st.session_state` pour réutilisation par les pages.
- Configurer la navigation multi-pages Streamlit (4 pages dans `pages/`).

## Critères d'acceptation
- [x] `st.set_page_config(layout="wide", page_title="AI Trading Dashboard")` appelé.
- [x] Paramètre `--runs-dir` fonctionnel via `sys.argv`.
- [x] Variable d'environnement `AI_TRADING_RUNS_DIR` supportée.
- [x] Ordre de précédence respecté : CLI > env var > défaut `runs/`.
- [x] Validation du chemin : erreur explicite si le répertoire n'existe pas.
- [x] `discover_runs()` appelé et résultat stocké dans `st.session_state`.
- [x] Les 4 pages sont accessibles via la navigation Streamlit.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/078-wsd2-app-entry-navigation` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/078-wsd2-app-entry-navigation` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-D-2] #078 RED: tests app entry point et navigation`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-D-2] #078 GREEN: app entry point et navigation multi-pages`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-D-2] #078 — Point d'entrée Streamlit et navigation multi-pages`.
