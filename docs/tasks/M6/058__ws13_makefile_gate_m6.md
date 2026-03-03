# Tâche — Cible Makefile `gate-m6`

Statut : DONE
Ordre : 058
Workstream : WS-13
Milestone : M6
Gate lié : M6

## Contexte
La chaîne de gates doit être complétée avec `gate-m6` pour valider le pipeline sur données réelles BTCUSDT. La cible `gate-m6` exécute les tests fullscale et produit le rapport `reports/gate_report_M6.json`. Elle dépend de `gate-m5` (la chaîne complète : GM1 → G-Features → G-Split → GM2 → G-Doc → GM3 → G-Backtest → GM4 → GM5 → GM6).

Références :
- Plan : `docs/plan/implementation.md` (WS-13.4)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§17.3)
- Code : `Makefile`

Dépendances :
- Tâche 056 — Test fullscale make run-all (doit être DONE)
- Tâche 057 — Validation métriques fullscale (doit être DONE)
- Tâche 053 — Makefile (doit être DONE, pour `gate-m5`)

## Objectif
Ajouter la cible `gate-m6` au Makefile. Elle exécute `pytest -m fullscale tests/test_fullscale_btc.py -v --timeout=600` et génère `reports/gate_report_M6.json` avec les critères GO/NO-GO du M6.

## Règles attendues
- La cible `gate-m6` dépend de `gate-m5` (cascade de gates).
- La cible échoue si `gate-m5` n'est pas GO (dépendance Makefile).
- Le rapport `gate_report_M6.json` doit contenir les champs standard : `gate`, `status`, conformément au format utilisé par les autres gates.
- La cible doit être déclarée `.PHONY`.
- Le commentaire Makefile de la chaîne de gates doit être mis à jour pour inclure GM6.

## Évolutions proposées
- Ajouter `gate-m6` à la liste `.PHONY` (section gates).
- Ajouter la cible `gate-m6` avec dépendance sur `gate-m5` :
  ```makefile
  gate-m6: gate-m5 ## Gate M6 — Full-scale network validation (requires M5)
  	@mkdir -p reports
  	pytest -m fullscale tests/test_fullscale_btc.py -v --timeout=600
  	@echo '{"gate": "M6", "status": "GO"}' > reports/gate_report_M6.json
  	@echo "Gate M6: GO"
  ```
- Mettre à jour le commentaire de la chaîne de gates :
  ```
  # GM1 → G-Features → G-Split → GM2 → G-Doc → GM3 → G-Backtest → GM4 → GM5 → GM6
  ```
- Écrire un test dans `tests/test_makefile.py` vérifiant que la cible `gate-m6` existe dans le Makefile.

## Critères d'acceptation
- [x] Cible `gate-m6` ajoutée au Makefile avec dépendance sur `gate-m5`.
- [x] `gate-m6` déclarée `.PHONY`.
- [x] `gate-m6` exécute `pytest -m fullscale tests/test_fullscale_btc.py -v --timeout=600`.
- [x] `gate-m6` génère `reports/gate_report_M6.json`.
- [x] Le commentaire de la chaîne de gates inclut GM6.
- [x] `make gate-m6` fonctionne quand les prérequis sont satisfaits (accès réseau, gate-m5 GO).
- [x] Test dans `tests/test_makefile.py` vérifiant la présence de la cible `gate-m6`.
- [x] Tests couvrent les scénarios nominaux + erreurs + bords.
- [x] Suite de tests standard verte après implémentation.
- [x] `ruff check` passe sans erreur.

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/058-makefile-gate-m6` depuis `Max6000i1`.

## Checklist de fin de tâche
- [x] Branche `task/058-makefile-gate-m6` créée depuis `Max6000i1`.
- [x] Tests RED écrits avant implémentation.
- [x] **Commit RED** : `[WS-13] #058 RED: tests cible Makefile gate-m6`.
- [x] Tests GREEN passants et reproductibles.
- [x] Critères d'acceptation tous satisfaits.
- [x] `ruff check ai_trading/ tests/` passe sans erreur.
- [x] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [x] **Commit GREEN** : `[WS-13] #058 GREEN: cible Makefile gate-m6`.
- [x] **Pull Request ouverte** vers `Max6000i1` : `[WS-13] #058 — Cible Makefile gate-m6`.
