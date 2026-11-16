# POC – Prévision des perturbations par liaison TGV

Ce dossier contient ma partie du projet : **prévoir, pour chaque liaison TGV, si le mois suivant sera « Normal » ou « Perturbé »**. Cette prévision est destinée à l'application Streamlit de l'assureur, à côté du score de fiabilité de chaque liaison.

## Structure

```
poc/analyse_amy/
├── data/                              # données sources (non versionnées pour le CSV AQST)
│   ├── regularite-mensuelle-tgv-aqst.csv
│   └── reglarite-mensuelle-tgv-nationale.xlsx
├── notebooks/
│   ├── exploration_nettoyage.ipynb    # exploration, contrôles de qualité et nettoyage
│   └── prevision.ipynb                # cible, variables, modèles et prévision du mois suivant
├── utils/
│   ├── nettoyage.py                   # règles de nettoyage des données AQST
│   ├── journal.py                     # configuration des logs
│   ├── diagnostic.py                  # contrôles de qualité avant et après nettoyage
│   ├── exploration.py                 # calculs de l'analyse exploratoire
│   ├── prevision.py                   # variables, modèles et prévision du mois suivant
│   └── graphiques.py                  # graphiques des notebooks
├── tests/
│   ├── test_nettoyage.py
│   ├── test_diagnostic.py
│   ├── test_exploration.py            # tests de utils/exploration.py et utils/graphiques.py
│   └── test_prevision.py
├── logs/
│   └── sncf.log                       # journal des exécutions
├── resultats/
│   └── predictions_liaisons.csv       # prévision du mois suivant, une ligne par liaison
├── pytest.ini
└── README.md
```

Les notebooks contiennent les explications et les justifications. Les calculs sont dans `utils/`, ce qui garde les notebooks courts et permet de tester chaque fonction.

## Nettoyage des données

Fonction principale : `utils.nettoyage.nettoyer(data)`, qui renvoie les données propres et un rapport.

Principe : **on garde les lignes et on remplace une valeur impossible par une valeur manquante (NaN)**, pour ne pas perdre les autres informations du mois. Seules les lignes sans aucune circulation prévue sont supprimées.

| Règle | Effet |
|---|---|
| Colonnes de commentaires | supprimées (texte libre, inutilisé) |
| `Nombre de circulations prévues` = 0 | ligne supprimée (73 lignes) |
| `Nombre trains en retard > 30min` négatif, ou inférieur à `> 60min` | les deux colonnes mises à NaN |
| Retards moyens négatifs | valeur mise à NaN |

Résultat : 12 544 → 12 471 lignes, 655 cases mises à NaN.

## Méthode de prévision

- **Cible** : taux de perturbation du mois = (trains annulés + trains en retard à l'arrivée) / circulations prévues. Le mois est **Perturbé** si ce taux dépasse **20 %**.
- **Liaison** : gare de départ, gare d'arrivée et service (National / International).
- **8 variables**, toutes connues à la fin du mois précédent (pas de fuite de données) : le mois de l'année, liaison internationale ou non, retards et annulations du mois dernier, des 12 derniers mois et du même mois l'année dernière.
- **Mois de choc** (grèves, confinement…) repérés automatiquement et retirés de l'apprentissage seulement.
- **Découpage temporel** : apprentissage avant 2025, test sur 2025 et après.
- **Modèle de référence** : « Comme le mois dernier » (Perturbé si le mois dernier l'était).

## Résultats (test sur 2025 et après)

| Modèle | F1 | Rappel | Précision | AUC |
|---|---|---|---|---|
| Comme le mois dernier | 0,699 | 0,534 | 0,608 | – |
| Régression logistique | 0,720 | 0,698 | 0,570 | 0,821 |
| Gradient boosting | 0,713 | 0,683 | 0,563 | 0,810 |
| **Forêt aléatoire** (retenue) | **0,732** | **0,706** | **0,587** | **0,821** |

Sur 650 mois réellement perturbés, la forêt aléatoire en repère 459, en rate 191 et donne 323 fausses alertes.

## Installation

Depuis la racine du projet :

```bash
uv sync --inexact
source .venv/bin/activate
uv pip install matplotlib seaborn openpyxl ipykernel scikit-learn pydocstyle pytest-cov
```

`--inexact` évite que `uv sync` retire les bibliothèques qui ne sont pas encore dans le `pyproject.toml`.

## Utilisation

1. Placer les deux fichiers de données dans `data/`.
2. Ouvrir les notebooks depuis `notebooks/` avec le noyau `.venv`, puis tout exécuter, dans l'ordre :
   - `exploration_nettoyage.ipynb`
   - `prevision.ipynb`, qui écrit `resultats/predictions_liaisons.csv`
3. Le déroulement est enregistré dans `logs/sncf.log`.

Dans un notebook, les fonctions s'importent ainsi :

```python
import sys
sys.path.append("..")
from utils.nettoyage import nettoyer
```

## Tests

Depuis `poc/analyse_amy` :

```bash
python -m pytest                              # tests + exemples des docstrings
python -m pytest --cov=utils --cov-branch     # avec la couverture
pydocstyle --convention=google utils/         # vérification des docstrings
```
