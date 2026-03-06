# Revue tâche #026 — v1

**Branche** : `task/026-trade-execution`
**Tâche** : `docs/tasks/M3/026__ws8_trade_execution.md`
**Date** : 2026-03-02
**Itération** : v1

## Verdict : ⚠️ REQUEST CHANGES

## Résultats d'exécution
| Check | Résultat |
|---|---|
| `pytest` | **745 passed** / 0 failed |
| `ruff check ai_trading/ tests/` | **All checks passed** |
| `get_errors` | **Clean** (0 erreur sur les 2 fichiers modifiés) |

## Structure branche & commits
| Critère | Verdict |
|---|---|
| Convention de branche (`task/026-trade-execution`) | ✅ |
| Commit RED présent (`[WS-8] #026 RED: tests règles d'exécution des trades`) | ✅ |
| Commit GREEN présent (`[WS-8] #026 GREEN: règles d'exécution des trades`) | ✅ |
| Commit RED = tests uniquement (`tests/test_trade_execution.py`) | ✅ |
| Commit GREEN = implémentation + tâche (`engine.py` + `026__ws8_trade_execution.md`) | ✅ |
| Pas de commits parasites (2 commits total : RED → GREEN) | ✅ |

## Tâche
| Critère | Verdict |
|---|---|
| Statut DONE | ✅ |
| Critères d'acceptation cochés (11/11 `[x]`) | ✅ |
| Checklist cochée (6/8 `[x]`, 2 non cochés attendus*) | ✅ |

\* Les items « Commit GREEN » et « Pull Request ouverte » ne peuvent être cochés qu'après le commit vert lui-même — c'est un problème de poule-et-l'œuf, non bloquant.

## Tests
| Critère | Verdict |
|---|---|
| Convention de nommage (`test_trade_execution.py`, `#026` en docstring) | ✅ |
| Couverture des critères d'acceptation (11/11 couverts) | ✅ |
| Cas nominaux (single signal, multiple signals, single_trade) | ✅ |
| Cas erreurs (invalid values, length mismatch, missing columns, invalid mode, horizon 0/-1) | ✅ |
| Cas bords (no signal, last bar, t+H > n, H=1 boundary) | ✅ |
| Tous GREEN (30/30 passed) | ✅ |
| Déterministes (seed 42 via `np.random.default_rng`) | ✅ |
| Données synthétiques (pas réseau) | ✅ |
| ruff clean | ✅ |

## Code — Règles non négociables
| Règle | Verdict | Commentaire |
|---|---|---|
| Strict code (no fallbacks) | ✅ | Validation explicite + `raise`. 0 fallback grep. |
| Config-driven | ✅ | `horizon` et `execution_mode` reçus en paramètres. |
| Anti-fuite | ✅ | Signaux pré-calculés, pas d'accès futur. 0 `.shift(-`. |
| Reproductibilité | ✅ | Fonction pure déterministe. |
| Float conventions | ✅ | `float()` = Python float64 pour les prix. |

## Qualité du code
| Critère | Verdict |
|---|---|
| Nommage et style (snake_case) | ✅ |
| Pas de code mort/debug (0 print, 0 TODO/FIXME) | ✅ |
| Imports propres (stdlib → third-party → local) | ✅ |
| DRY (pas de duplication) | ✅ |

## Cohérence intermodule
| Critère | Verdict |
|---|---|
| Signatures et types (`execution_mode` Literal compatible avec `base.py`) | ✅ |
| `_VALID_EXECUTION_MODES` identique dans `engine.py` et `base.py` | ✅ |
| Colonnes DataFrame (`open`, `close` vérifiées) | ✅ |
| Clés de config (`backtest.mode`, `backtest.direction` dans `default.yaml`) | ✅ |

## Scan B1 — Anti-patterns automatisés

| Pattern | Résultat |
|---|---|
| Fallbacks silencieux (`or []`, `or {}`, etc.) | 0 occurrences (grep exécuté) |
| `except:` / `except Exception:` trop large | 0 occurrences (grep exécuté) |
| `print()` résiduel | 0 occurrences (grep exécuté) |
| `.shift(-` look-ahead | 0 occurrences (grep exécuté) |
| Legacy random API | 0 occurrences (grep exécuté) |
| TODO/FIXME/HACK/XXX | 0 occurrences (grep exécuté) |
| Chemins hardcodés OS-spécifiques | 0 occurrences (grep exécuté) |
| Mutable default arguments | 0 occurrences (grep exécuté) |
| `open()` sans context manager | 0 occurrences (grep exécuté) |

---

## BLOQUANTS (0)

Aucun.

## WARNINGS (1)

### W-1. Condition de chevauchement au bar de sortie diverge de la spec E.2.3

- **Fichier** : `ai_trading/backtest/engine.py`, lignes 100-102
- **Spec** (E.2.3) : « si un signal Go arrive **pendant qu'un trade est encore ouvert** (`t' < t_exit` du trade en cours), le nouveau Go est ignoré ».
- **Comportement attendu** : Signal au bar `t_exit` (exit bar exact) → `t' < t_exit` est `False` → signal **accepté**. La décision et la sortie étant simultanées (« Décision à la clôture de t », §12.1), le nouveau trade entrerait à `Open[t_exit+1]`, **après** la fermeture à `Close[t_exit]`. Pas de chevauchement temporel.
- **Comportement implémenté** : `if position_open and t > exit_idx:` — la position n'est libérée qu'à `t = exit_idx + 1`. Un signal à `t = exit_idx` est ignoré.
- **Impact** : Un trade valide est manqué quand un signal Go tombe exactement sur le bar de sortie d'un trade actif. Le résultat est plus conservateur que la spec.
- **Test concerné** : `test_go_at_exact_exit_bar_is_ignored` — codifie le comportement divergent.
- **Correction proposée** : Remplacer `t > exit_idx` par `t >= exit_idx` dans `_execute_standard`, et ajuster le test pour `test_go_at_exact_exit_bar_is_accepted`.

## MINEURS (1)

### M-1. Pas de validation pour DataFrame OHLCV vide en mode `single_trade`

- **Fichier** : `ai_trading/backtest/engine.py`, lignes 85-94
- **Description** : Si `ohlcv` a 0 lignes et `signals` est un array vide, la validation passe (vacuous truth pour `np.all(np.isin([], [0, 1]))`) mais `_execute_single_trade` crashe sur `ohlcv.index[0]` avec `IndexError`.
- **Impact** : Cas extrêmement improbable en pratique (un backtest sans données n'a pas de sens). L'erreur reste levée, mais le message n'est pas explicite.
- **Correction proposée** : Ajouter `if len(ohlcv) == 0: raise ValueError("ohlcv must not be empty")` dans `_validate_inputs`.

## Résumé

Code propre, bien structuré, avec une validation d'entrée rigoureuse et une couverture de tests complète (30 tests couvrant tous les critères d'acceptation). La structure TDD est respectée (RED → GREEN, pas de commits parasites). Les conventions du projet sont suivies.

Un seul point significatif (W-1) : la condition de libération de position au bar de sortie utilise `t > exit_idx` au lieu de `t >= exit_idx`, ce qui diverge du texte explicite de l'annexe E.2.3 (`t' < t_exit`). La correction est minime (un caractère) mais touche la logique métier du moteur de backtest. À corriger ou à valider explicitement comme choix de design avec mise à jour de la spec.
