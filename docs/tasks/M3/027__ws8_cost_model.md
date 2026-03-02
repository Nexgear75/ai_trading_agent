# Tâche — Modèle de coûts de transaction

Statut : TODO
Ordre : 027
Workstream : WS-8
Milestone : M3
Gate lié : M3

## Contexte
Le backtest doit calculer le rendement net de chaque trade en intégrant les frais (fees) et le slippage. Le modèle de coûts multiplicatif per-side est défini dans la spécification §12.2–12.3. Ce module est utilisé par le moteur de backtest (WS-8.1) et par la calibration θ (WS-7.2) pour évaluer les candidats θ.

Références :
- Plan : `docs/plan/implementation.md` (WS-8.2)
- Spécification : `docs/specifications/Specification_Pipeline_Commun_AI_Trading_v1.0.md` (§12.2, §12.3)
- Code : `ai_trading/backtest/engine.py` (extension du module existant ou module dédié `costs.py`)

Dépendances :
- Tâche 026 — WS-8 trade execution (doit être DONE)

## Objectif
Implémenter le calcul du rendement net d'un trade long-only avec le modèle de coûts multiplicatif per-side, conforme à la spécification §12.3.

## Règles attendues
- **Config-driven** : `costs.fee_rate_per_side` et `costs.slippage_rate_per_side` lus depuis la config. Pas de valeurs hardcodées.
- **Strict code** : pas de fallback si les paramètres de coûts sont absents — lever une erreur.
- **Formules conformes à la spec** : exactement les formules §12.3, pas d'approximation.

## Évolutions proposées

### 1. Calcul du rendement net par trade
Formules conformes à §12.3 :
- `f = config.costs.fee_rate_per_side`
- `s = config.costs.slippage_rate_per_side`
- `p_entry = Open[t+1]` (prix d'entrée brut)
- `p_exit = Close[t+H]` (prix de sortie brut)
- `p_entry_eff = p_entry × (1 + s)` (prix effectif d'entrée avec slippage)
- `p_exit_eff = p_exit × (1 - s)` (prix effectif de sortie avec slippage)
- `M_net = (1 - f)² × (p_exit_eff / p_entry_eff)` (multiplicateur net)
- `r_net = M_net - 1` (rendement net du trade)

### 2. Intégration avec le moteur de trades
- Le calcul de `r_net` est appliqué à chaque trade produit par WS-8.1
- Chaque trade enrichi avec `r_net` et les prix effectifs

## Critères d'acceptation
- [ ] Formule `M_net = (1 - f)² × (p_exit_eff / p_entry_eff)` implémentée exactement
- [ ] `p_entry_eff = p_entry × (1 + s)` et `p_exit_eff = p_exit × (1 - s)` corrects
- [ ] `r_net = M_net - 1` retourné pour chaque trade
- [ ] Test numérique : calcul à la main vs implémentation (exemple : `f=0.001`, `s=0.0003`, `Open=100`, `Close=102` → `r_net ≈ 0.0174`)
- [ ] Coûts symétriques : slippage à l'achat et à la vente
- [ ] Paramètres lus depuis `config.costs` — pas de valeurs hardcodées
- [ ] Cas bord : trade avec `p_entry == p_exit` → `r_net` négatif (coûts seuls)
- [ ] Cas bord : coûts à zéro (`f=0, s=0`) → `r_net = (p_exit / p_entry) - 1`
- [ ] Tests couvrent les scénarios nominaux + erreurs + bords
- [ ] Suite de tests verte après implémentation
- [ ] `ruff check` passe sans erreur

## Pré-condition de démarrage
- **Tous les tests existants sont GREEN** avant de commencer.
- **Créer une branche dédiée** `task/027-cost-model` depuis `Max6000i1`.

## Checklist de fin de tâche
- [ ] Branche `task/027-cost-model` créée depuis `Max6000i1`.
- [ ] Tests RED écrits avant implémentation.
- [ ] **Commit RED** : `[WS-8] #027 RED: tests modèle de coûts de transaction` (fichiers de tests uniquement).
- [ ] Tests GREEN passants et reproductibles.
- [ ] Critères d'acceptation tous satisfaits.
- [ ] `ruff check ai_trading/ tests/` passe sans erreur.
- [ ] Fichier de tâche mis à jour (statut DONE, critères cochés).
- [ ] **Commit GREEN** : `[WS-8] #027 GREEN: modèle de coûts de transaction`.
- [ ] **Pull Request ouverte** vers `Max6000i1` : `[WS-8] #027 — Modèle de coûts de transaction`.
