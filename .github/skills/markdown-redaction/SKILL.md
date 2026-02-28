# Skill — Rédaction Markdown

## Déclencheurs
- « rédige un document Markdown », « normalise ce fichier .md »
- « rédige en mode Corporate FR »
- « applique les conventions Markdown du projet »

## Contexte repo
- **Langue docs** : Français
- **Langue code** : Anglais
- **Linter** : ruff (Python) ; pour Markdown, appliquer les règles ci-dessous manuellement

---

## 1 — Règles GFM de base

| Règle | Détail |
|---|---|
| Titres | `#` → `######`, saut de ligne avant/après, pas de titre orphelin en fin de fichier |
| Listes | tiret `-` (pas `*`), indentation 2 espaces pour sous-listes |
| Liens | format `[texte](url)` ; liens relatifs pour fichiers internes |
| Code inline | backticks simples `` ` `` |
| Blocs code | triple backticks avec langage (```python, ```yaml, ```bash) |
| Tableaux | alignement avec `|---|`, cellules courtes |
| Emphase | `**gras**` pour termes importants, `_italique_` pour citations/noms propres |
| Ligne vide | obligatoire entre titre et contenu, entre blocs différents |
| Trailing spaces | aucun espace en fin de ligne |
| Fin de fichier | exactement 1 newline final |

## 2 — Mode Corporate FR strict

Quand activé (par défaut pour les tâches et docs du projet) :

### Structure imposée
```
# Titre du document

> Résumé en 1-2 phrases.

## Section 1
...
## Section N
```

### Contraintes
- **Longueur titre** : ≤ 80 caractères
- **Résumé** : obligatoire (blockquote `>` après le titre principal)
- **Profondeur max** : `####` (4 niveaux max)
- **Pas de HTML** inline sauf `<br>` si nécessaire
- **Abréviations** : définies à la première occurrence
- **Acronymes** : en majuscules, définis entre parenthèses à la première occurrence
- **Langue** : français pour documentation, anglais pour code/variables/noms techniques

### Conventions spécifiques au projet
- Identifiants workstream : `WS-1` à `WS-12` (avec tiret)
- Identifiants milestone : `M1` à `M5`
- Identifiants tâche : `#NNN` (3 chiffres)
- Identifiants gate : `G-Features`, `G-Split`, `G-Backtest`, `G-Doc`, `G-Leak`, `G-Perf`
- Références spec : `§N.N` (ex. `§6.1 features`, `§8.2 embargo`)
- Chemins fichiers : backticks (`` `configs/default.yaml` ``)

## 3 — Checklist QA avant livraison

- [ ] Pas de lien cassé (vérifier chemins relatifs)
- [ ] Pas de titre dupliqué au même niveau
- [ ] Tous les blocs code ont un langage spécifié
- [ ] Pas de ligne > 120 caractères (sauf URLs et tableaux)
- [ ] Pas d'espace trailing
- [ ] Newline final unique
- [ ] Résumé présent (mode Corporate FR)
- [ ] Acronymes définis à la première occurrence
- [ ] Cohérence des identifiants (WS-X, MN, #NNN)

## 4 — Anti-patterns

| Anti-pattern | Correction |
|---|---|
| `1.` puis `1.` (numérotation manuelle) | Laisser Markdown numéroter (`1.` partout) |
| Titre sans saut de ligne avant | Ajouter ligne vide |
| Lien avec chemin absolu local | Utiliser chemin relatif |
| Bloc code sans langage | Ajouter le langage |
| Mélange `-` et `*` pour listes | Uniformiser sur `-` |
| Tableau sans alignement | Ajouter `|---|` |
| HTML complexe (`<div>`, `<table>`) | Convertir en Markdown pur |
