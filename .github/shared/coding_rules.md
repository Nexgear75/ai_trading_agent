# Règles de code partagées — AI Trading Pipeline

> **Source de vérité unique** pour les règles de code appliquées par les skills `pr-reviewer` et `implementing-task`.
> Chaque agent doit lire ce fichier au début de son workflow.
>
> **Convention** : les sections sont numérotées `§R1` à `§R10` + `§GREP` pour référence croisée.

---

## §R1 — Strict code (no fallbacks)

- [ ] Aucun fallback silencieux (pattern `or []`, `or {}`, `or ""`, `or 0`, `value if value else default`).
- [ ] Aucun `except:` ou `except Exception:` trop large qui continue l'exécution.
- [ ] Aucun paramètre optionnel avec default implicite masquant une erreur.
- [ ] Validation explicite aux frontières (entrées utilisateur, données externes).
- [ ] Erreur explicite (`raise`) en cas d'entrée invalide ou manquante.

## §R2 — Config-driven (pas de hardcoding)

- [ ] Tout paramètre modifiable est lu depuis `configs/default.yaml` via l'objet config Pydantic v2.
- [ ] Aucune valeur magique ou constante significative hardcodée dans le code.
- [ ] Les formules respectent celles de la spec (§6 features, §5 labels, §8 splits, §12 backtest).
- [ ] Tout choix implementation-defined est explicite dans la config YAML.

## §R3 — Anti-fuite (look-ahead)

- [ ] Aucun accès à des données futures (point-in-time respecté).
- [ ] Embargo respecté : `embargo_bars >= label.horizon_H_bars` (§8.2).
- [ ] Pas de `.shift(-n)` ou équivalent sans justification temporelle correcte.
- [ ] Scaler fit sur train uniquement (pas de données val/test dans fit).
- [ ] Splits walk-forward séquentiels (train < val < test).
- [ ] θ calibré uniquement sur val, jamais sur test.
- [ ] Features causales : backward-looking uniquement.

## §R4 — Reproductibilité

- [ ] Seeds fixées et tracées via `utils/seed.py`.
- [ ] Pas de legacy random API (`np.random.seed`, `np.random.randn`, `np.random.RandomState`, `random.seed`). Toujours utiliser `np.random.default_rng(seed)`.
- [ ] Hashes SHA-256 (données, config) si applicable.
- [ ] Résultats reproductibles sur relance (test de déterminisme si pertinent).

## §R5 — Float conventions

- [ ] Float32 pour tenseurs X_seq et y (mémoire).
- [ ] Float64 pour calculs de métriques (précision).

## §R6 — Anti-patterns Python / numpy / pandas

- [ ] **Mutable default arguments** : pas de `def f(x=[])` ni `def f(x={})`.
- [ ] **Kwargs forwarding incomplet** : quand une fonction A délègue à une fonction B (pattern wrapper/orchestrateur), vérifier que **tous les kwargs acceptés par B et disponibles dans le scope de A sont effectivement transmis**. Un kwargs manquant dans une délégation = perte silencieuse de contexte. Exemple : si `BaseModel.predict(X, meta=, ohlcv=)` et que le wrapper appelle `model.predict(X=...)` sans passer `meta`/`ohlcv` → **BLOQUANT** (modèle RL silencieusement privé de contexte).
- [ ] **Données désérialisées non validées** : après `json.loads()`, `yaml.safe_load()` ou lecture de fichier, les valeurs sont validées en type (`isinstance`) avant utilisation. Un `data["key"]` utilisé directement sans vérification de type est un **WARNING**.
- [ ] **Path incomplet** : si un paramètre `path` est documenté comme acceptant directory OU fichier, l'implémentation gère les deux cas. Un `path.write_text()` sans vérifier `path.is_dir()` est un bug potentiel.
- [ ] **Path creation** : si un paramètre `path`/`run_dir` est reçu et utilisé pour I/O (écriture de fichiers, sous-répertoires), il doit être créé avant usage (`mkdir(parents=True, exist_ok=True)`) ou le contrat exige explicitement qu'il préexiste. **Un `run_dir / "model"` sans `run_dir.mkdir()` préalable est un bug latent — BLOQUANT.**
- [ ] **open() sans context manager** : tout `open()` utilise `with`. Les raccourcis `Path.read_text()` / `Path.write_text()` sont acceptés.
- [ ] **Comparaison float avec ==** : pas de `==` sur des floats numpy. Utiliser `np.isclose`, `np.testing.assert_allclose`, ou `pytest.approx`.
- [ ] **Comparaison booléenne par identité** : ne jamais utiliser `is np.bool_(...)`, `is True`, ou `is False` sur des valeurs numpy/pandas. L'identité d'objet (`is`) n'est pas garantie entre versions numpy. Utiliser `==` pour les booléens numpy/pandas, ou convertir avec `bool()` avant `is`.
- [ ] **`.values` perdant l'index** : pas de `.values` implicite sur un DataFrame/Series pandas sans raison documentée.
- [ ] **f-string ou format** : pas de `str + str` dans les messages d'erreur — utiliser f-string.
- [ ] **Side-effects dans les paramètres par défaut** : pas de `datetime.now()`, `time.time()`, ou appel de fonction dans les valeurs par défaut de paramètres.
- [ ] **Dict keyed par valeur calculée — collision silencieuse** : quand un `dict` est construit dans une boucle avec des clés calculées (ex : `d[computed_key] = value`), vérifier qu'une clé dupliquée ne peut pas écraser silencieusement une entrée précédente. Si la duplication est possible et constituerait une perte de données → valider avec `if key in d: raise ValueError(...)` **avant** l'assignation. Pattern typique : dict indexé par position, timestamp, ou identifiant dérivé — **BLOQUANT** si écrasement silencieux.

## §R7 — Qualité du code

- [ ] Nommage snake_case cohérent.
- [ ] Pas de code mort, commenté ou TODO orphelin.
- [ ] Pas de `print()` de debug restant.
- [ ] Imports propres : pas d'imports inutilisés, pas d'imports `*`. Ordre isort (stdlib → third-party → local, séparés par des lignes vides).
- [ ] **Imports intra-package relatifs** : les `__init__.py` qui importent des sous-modules pour side-effect (peuplement de registres) doivent utiliser des imports relatifs (`from . import module`), jamais des imports absolus auto-référençants (`from ai_trading.package import module`).
- [ ] Aucune variable morte : chaque variable assignée est utilisée au moins une fois.
- [ ] Pas de fichiers générés ou temporaires inclus dans le versionning.
- [ ] **DRY — pas de duplication de constantes/mappings** entre modules du même package. Si un dict, une constante ou un mapping est identique dans 2+ fichiers, exiger l'extraction vers un module partagé. Risque : drift silencieux — **BLOQUANT**.
- [ ] **Suppressions lint minimales** : chaque `# noqa` ou entrée `per-file-ignores` dans `pyproject.toml` est **inévitable** (ex : N803 pour un nom de paramètre imposé par la spec/l'ABC). Si une suppression peut être évitée par un simple renommage de **variable locale** (N806) ou une réorganisation du code → **MINEUR**. Distinguer systématiquement paramètres (souvent imposés par l'interface) des variables locales (toujours renommables).
- [ ] **`__init__.py` à jour** : si un nouveau module a été créé, le `__init__.py` du package l'importe si nécessaire (ex : enregistrement automatique features). Import **relatif** (`from . import module`).
- [ ] **Tests de registre** : si un test vérifie l'enregistrement dans un registre (MODEL_REGISTRY, FEATURE_REGISTRY), il doit utiliser `importlib.reload` pour tester le side-effect réel du décorateur, pas un appel manuel à `register_xxx()`.
- [ ] **Portabilité des chemins dans les tests** : aucun chemin hardcodé `/tmp/...` ou `C:\...`, toujours `tmp_path` de pytest.
- [ ] **Contrat ABC complet** : si une méthode abstraite documente qu'elle accepte directory OU fichier, l'implémentation supporte les deux cas avec tests.

## §R8 — Cohérence intermodule

Vérifier que les changements ne créent pas de divergence avec les modules existants.

- [ ] **Signatures et types de retour** : les fonctions/classes modifiées ou créées respectent les signatures attendues par les modules appelants existants (mêmes noms de paramètres, mêmes types, même ordre). Si une signature existante est modifiée, vérifier tous les appels dans le codebase.
- [ ] **Noms de colonnes DataFrame** : les colonnes produites ou consommées (ex : `close`, `logret_1`, `vol_24`) sont identiques à celles utilisées dans les modules amont/aval. Pas de renommage silencieux ni de divergence de convention.
- [ ] **Clés de configuration** : les clés lues depuis `configs/default.yaml` correspondent aux noms définis dans le modèle Pydantic (`config.py`). Pas de clé orpheline (présente en YAML mais pas lue) ni manquante (lue mais absente du YAML).
- [ ] **Registres et conventions partagées** : si le module s'inscrit dans un registre (ex : `FEATURE_REGISTRY`), vérifier que l'interface implémentée (méthodes, attributs comme `name`, `min_periods`) est cohérente avec les autres entrées du registre et avec le code qui itère dessus.
- [ ] **Structures de données partagées** : les dataclasses, TypedDict ou NamedTuple partagées entre modules sont utilisées de manière identique (mêmes champs, mêmes types). Pas de champ ajouté dans un module sans mise à jour des consommateurs.
- [ ] **Conventions numériques** : les dtypes (float32 vs float64), les conventions NaN (NaN en tête vs valeurs par défaut), et les index (DatetimeIndex, RangeIndex) sont cohérents avec les modules voisins.
- [ ] **Imports croisés** : si le nouveau code importe des symboles d'autres modules du projet, vérifier que ces symboles existent bien dans la branche `Max6000i1` (pas de dépendance sur du code non encore mergé).
- [ ] **Cohérence des defaults** : quand un paramètre de la fonction A miroir un paramètre de l'interface B (ex : `train_fold(ohlcv: Any)` ↔ `BaseModel.predict(ohlcv: Any = None)`), la **valeur par défaut doit être cohérente** (même default ou absence justifiée). Un paramètre sémantiquement optionnel qui n'a **pas** de default → **MINEUR**.
- [ ] **Forwarding complet des kwargs** : quand une fonction-orchestrateur (wrapper, trainer, runner) reçoit des paramètres et les délègue à un sous-appel, vérifier que **chaque paramètre pertinent du sous-appel est transmis**. Un kwargs disponible dans le scope mais non transmis → **BLOQUANT** si fonctionnel (perte de contexte métier), **WARNING** si cosmétique.

Une incohérence intermodule est **bloquante** — elle provoque des bugs silencieux à l'intégration.

## §R9 — Bonnes pratiques métier (finance)

- [ ] **Exactitude des concepts financiers** : les indicateurs techniques (RSI, EMA, volatilité, log-returns, etc.) sont implémentés conformément à leur définition canonique. Toute déviation doit être justifiée et documentée.
- [ ] **Nommage métier cohérent** : les noms reflètent les concepts financiers (ex. `log_return` et non `lr`, `equity_curve` et non `curve`). Pas d'abréviation ambiguë.
- [ ] **Séparation des responsabilités métier** : chaque module encapsule un concept métier unique (features ≠ labels ≠ backtest). Pas de mélange de responsabilités.
- [ ] **Invariants de domaine respectés** : les invariants financiers sont vérifiés explicitement (prix > 0, volume >= 0, equity curve monotone sur un trade, etc.).
- [ ] **Cohérence des unités et échelles** : grandeurs manipulées avec unités cohérentes (returns log vs arithmétique, prix en quote currency, timestamps UTC). Pas de mélange implicite.
- [ ] **Patterns de calcul financier** : bonnes pratiques numériques (`np.log` vs `math.log`, rolling windows pandas natif, pas de boucles Python sur séries temporelles).
- [ ] **Vectorisation numpy** : quand une opération sur un array numpy peut être exprimée par un slice assignment (`arr[a:b] = val`) ou une opération vectorisée, ne pas utiliser de boucle Python `for j in range(...)`. Les boucles Python sur des arrays numpy sont un anti-pattern de performance — **MINEUR** si fonctionnellement correct, **WARNING** sur des hot paths (backtest, features).

## §R10 — Defensive indexing / slicing

- [ ] Pour tout `array[expr:]` ou `array[:expr]` : vérifier manuellement le comportement quand `expr` est **négatif**, **zéro**, ou **> len(array)**. En Python/NumPy, `array[-k:]` ne fait **pas** `array[0:]` — c'est un piège silencieux.
- [ ] Pour tout `range(a, b)` ou `mask[lo : hi + 1]` : vérifier que `lo` et `hi` sont clampés (`max(0, ...)`, `min(n-1, ...)`) pour toutes les valeurs extrêmes des paramètres d'entrée.
- [ ] Si un paramètre numérique peut dépasser la taille des données (ex. `H > N`), vérifier que le code produit un résultat correct (tout False, raise, etc.) et non un comportement silencieusement faux.
- [ ] **Invariants amont non validés** : quand une fonction reçoit des données produites par un autre module (ex : liste de trades de `execute_trades`, enrichie par `apply_cost_model`), ne pas supposer que les invariants amont sont toujours respectés. Valider explicitement les propriétés critiques (ex : `exit_pos >= entry_pos`, pas de chevauchement de trades). Un invariant supposé sans validation est un bug latent — **WARNING** sur des fonctions internes, **BLOQUANT** sur des fonctions publiques.

---

## §GREP — Commandes de scan automatisé

> Commandes à exécuter sur les fichiers modifiés pour preuve factuelle.

```bash
# Initialisation des variables
CHANGED=$(git diff --name-only Max6000i1...HEAD | grep '\.py$')
CHANGED_SRC=$(echo "$CHANGED" | grep '^ai_trading/')
CHANGED_TEST=$(echo "$CHANGED" | grep '^tests/')

# §R1 — Fallbacks silencieux
grep -n ' or \[\]\| or {}\| or ""\| or 0\b\| if .* else ' $CHANGED_SRC

# §R1 — Except trop large
grep -n 'except:$\|except Exception:' $CHANGED_SRC

# §R7 — Suppressions lint
grep -n 'noqa' $CHANGED
grep -n 'per-file-ignores' pyproject.toml | grep -v '^#'

# §R7 — Print résiduel
grep -n 'print(' $CHANGED_SRC

# §R3 — Shift négatif (look-ahead)
grep -n '\.shift(-' $CHANGED_SRC

# §R4 — Legacy random API
grep -n 'np\.random\.seed\|np\.random\.randn\|np\.random\.RandomState\|random\.seed' $CHANGED

# §R7 — TODO/FIXME orphelins
grep -n 'TODO\|FIXME\|HACK\|XXX' $CHANGED

# §R7 — Chemins hardcodés OS-spécifiques (tests)
grep -n '/tmp\|/var/tmp\|C:\\' $CHANGED_TEST

# §R7 — Imports absolus dans __init__.py
grep -n 'from ai_trading\.' $(echo "$CHANGED" | grep '__init__.py')

# §R7 — Registration manuelle tests
grep -n 'register_model\|register_feature' $CHANGED_TEST

# §R6 — Mutable default arguments
grep -n 'def .*=\[\]\|def .*={}' $CHANGED

# §R6 — open() sans context manager
grep -n '\.read_text\|open(' $CHANGED_SRC

# §R6 — Comparaison booléenne par identité numpy/pandas
grep -n 'is np\.bool_\|is True\|is False' $CHANGED

# §R6 — Dict collision silencieuse (boucle + assignation dict sans guard)
grep -n '\[.*\] = .*' $CHANGED_SRC | grep -v 'def \|#\|"""'

# §R9 — Boucle Python sur array numpy (vectorisation manquante)
grep -n 'for .* in range(.*):' $CHANGED_SRC
```

**Pour chaque match** : analyser en contexte (lire les lignes autour) et classer :
- **BLOQUANT** si c'est un vrai problème
- **WARNING** si risque potentiel
- **Faux positif** si le pattern est utilisé correctement (noter dans le rapport)

**Si aucun match** pour un pattern → noter « 0 occurrences (grep exécuté) » dans le rapport comme preuve d'exécution.
