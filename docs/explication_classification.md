# Explication détaillée de la classification utilisée

## Le code (`data/labeling/labeler.py`)

```python
future_return = df["close"].shift(-PREDICTION_HORIZON) / df["close"] - 1

df["label"] = 0
df.loc[future_return > LABEL_THRESHOLD, "label"] = 1
df.loc[future_return < -LABEL_THRESHOLD, "label"] = -1
```

Avec les constantes de `config.py` :
- `PREDICTION_HORIZON = 3` (3 bougies dans le futur)
- `LABEL_THRESHOLD = 0.02` (seuil de 2%)

---

## Ce que ça fait concrètement

### 1. Calcul du rendement futur

$$\mathrm{future{\_}return}(t) = \frac{P_{t+3}}{P_t} - 1$$

À chaque instant *t*, on regarde le prix de clôture 3 bougies plus tard et on calcule le rendement simple (pas le log-return). Avec un timeframe `1d`, ça revient à regarder 3 jours dans le futur.

### 2. Assignation du label selon un seuil fixe de ±2%

| Condition | Label | Signification |
|---|---|---|
| future_return(t) > +0.02 | **+1** | "Hausse significative" dans 3 jours |
| future_return(t) < -0.02 | **-1** | "Baisse significative" dans 3 jours |
| -0.02 ≤ future_return(t) ≤ +0.02 | **0** | "Neutre / pas de mouvement clair" |

---

## Exemple concret

Supposons BTC/USDT avec les prix de clôture suivants :

| Jour | Close | Future close (t+3) | Future return | Label |
|---|---|---|---|---|
| J1 | 40 000 $ | 41 500 $ | +3.75% | **+1** |
| J2 | 40 500 $ | 40 200 $ | -0.74% | **0** |
| J3 | 41 000 $ | 39 800 $ | -2.93% | **-1** |

---

## Les problèmes de cette approche

### 1. Le seuil de 2% est arbitraire et fixe

- Sur BTC en période calme, 2% en 3 jours est un gros mouvement → très peu de labels +1/-1.
- Sur BTC en période volatile, 2% en 3 jours c'est du bruit → trop de labels +1/-1 qui ne sont pas de vrais signaux.
- Le seuil ne s'adapte pas à la volatilité du marché ni à la crypto.

### 2. On perd l'amplitude

Un mouvement de +2.1% et un mouvement de +15% reçoivent le même label **+1**. Pourtant, en trading, la différence est énorme. Le modèle n'apprend pas à distinguer un petit gain d'un gros gain.

### 3. Le label 0 est une "poubelle"

La classe 0 mélange :
- Des mouvements de +1.9% (presque haussier)
- Des mouvements de -1.9% (presque baissier)
- Des mouvements de 0% (vraiment neutre)

Le modèle doit apprendre une classe très hétérogène → confusion.

### 4. Incompatibilité avec le Go/No-Go 

LAvec une classification, le modèle sort une classe (ou une probabilité de classe), pas un rendement. On ne peut pas directement comparer r̂ à un seuil calibré sur les frais de trading.

### 5. C'est un rendement simple, pas un log-return

Le code calcule P(t+3)/P(t) - 1 (rendement simple), et pas log(P(t+H)/P(t)). Le log-return a des propriétés mathématiques meilleures : additivité temporelle, symétrie gains/pertes, distribution plus proche d'une gaussienne. Le prix est non-stationnaire, le log-return l'est (approximativement)

---

## Ce que est plus adéquat à la place

Remplacer toute cette logique par :

$$y(t) = \log\left(\frac{P_{t+H}}{P_t}\right)$$

Une valeur continue, directement utilisable en régression. Le seuil de décision Go/No-Go est ensuite appliqué **après** la prédiction du modèle, sur validation, pas au moment de la construction des labels.
