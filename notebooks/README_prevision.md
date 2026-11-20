# Prévision des perturbations par liaison TGV (partie Amy)

Objectif : **prévoir, pour chaque liaison TGV, si le mois suivant sera « Normal » ou « Perturbé »**. La prévision est affichée dans l'application Streamlit (page `src/projet_sncf/pages/prevision_perturbations.py`), à côté du score de fiabilité de chaque liaison.

## Où se trouve quoi

| Fichier | Rôle |
|---|---|
| `notebooks/02_exploration_nettoyage.ipynb` | exploration, contrôles de qualité et nettoyage |
| `notebooks/03_prevision.ipynb` | cible, variables, modèles et prévision du mois suivant |
| `src/projet_sncf/database/nettoyage.py` | règles de nettoyage des données AQST |
| `src/projet_sncf/business/prevision/diagnostic.py` | contrôles de qualité avant et après nettoyage |
| `src/projet_sncf/business/prevision/exploration.py` | calculs de l'analyse exploratoire |
| `src/projet_sncf/business/prevision/prevision.py` | variables, modèles et prévision du mois suivant |
| `src/projet_sncf/utils/graphiques.py` | graphiques des notebooks |
| `src/projet_sncf/utils/logging_config.py` | écriture des logs dans `logs/sncf.log` (commun à tout le projet) |
| `data/regularite-mensuelle-tgv-aqst.csv` | données mensuelles AQST |
| `data/reglarite-mensuelle-tgv-nationale.xlsx` | régularité nationale des TGV depuis 2015 (contexte) |
| `data/predictions/` | fichiers écrits par `03_prevision.ipynb` et lus par la page Streamlit |
| `tests/unitaire/test_diagnostic.py`, `test_exploration.py`, `test_prevision.py`, `test_logging_config.py`, `test_database_nettoyage.py` | tests unitaires |

Les notebooks contiennent les explications et les justifications. Les calculs sont dans `src/`, ce qui garde les notebooks courts et permet de tester chaque fonction.

## Nettoyage des données

Fonction principale : `projet_sncf.database.nettoyage.nettoyer(data)`, qui renvoie les données propres et un rapport.

Principe : **on garde les lignes et on remplace une valeur impossible par une valeur manquante (NaN)**, pour ne pas perdre les autres informations du mois. Seules les lignes sans aucune circulation prévue sont supprimées.

| Règle | Effet |
|---|---|
| Colonnes de commentaires | supprimées (texte libre, inutilisé) |
| `Nombre de circulations prévues` = 0 | ligne supprimée (73 lignes) |
| `Nombre trains en retard > 30min` négatif, ou inférieur à `> 60min` | seule la case `> 30min` mise à NaN (354 cases) |
| Retards moyens négatifs | valeur mise à NaN |

Résultat (données jusqu'à septembre 2026) : 12 907 → 12 834 lignes, 656 cases mises à NaN.

## Méthode de prévision

- **Cible** : taux de perturbation du mois = (trains annulés + trains en retard à l'arrivée) / circulations prévues. Le mois est **Perturbé** si ce taux dépasse **20 %**.
- **Liaison** : gare de départ, gare d'arrivée et service (National / International).
- **8 variables**, toutes connues à la fin du mois précédent (pas de fuite de données) : le mois de l'année, liaison internationale ou non, retards et annulations du mois dernier, des 12 derniers mois et du même mois l'année dernière.
- **Mois de choc** (grèves, confinement…) repérés automatiquement et retirés de l'apprentissage seulement.
- **Découpage temporel** : apprentissage avant 2025, test de janvier 2025 à septembre 2026.
- **Modèle de référence** : « Comme le mois dernier » (Perturbé si le mois dernier l'était).

## Résultats (test de janvier 2025 à septembre 2026)

| Modèle | F1 | Rappel | Précision | AUC |
|---|---|---|---|---|
| Comme le mois dernier | 0,720 | 0,619 | 0,632 | – |
| Régression logistique | 0,726 | 0,755 | 0,587 | 0,830 |
| Gradient boosting | 0,733 | 0,728 | 0,607 | 0,828 |
| **Forêt aléatoire** (retenue) | **0,749** | **0,752** | **0,624** | **0,838** |

Sur 842 mois réellement perturbés, la forêt aléatoire en repère 633, en rate 209 et donne 382 fausses alertes. La prévision d'octobre 2026 annonce 72 liaisons « Perturbé » et 49 « Normal ».

## Utilisation

Depuis la racine du projet :

```bash
uv sync
source .venv/bin/activate
```

1. Placer `regularite-mensuelle-tgv-aqst.csv` dans `data/`.
2. Ouvrir les notebooks depuis `notebooks/` avec le noyau `.venv` de la racine, puis tout exécuter, dans l'ordre :
   - `02_exploration_nettoyage.ipynb`
   - `03_prevision.ipynb`, qui écrit `data/predictions/predictions_liaisons.csv` et `data/predictions/predictions_test.csv`
3. Le déroulement est enregistré dans `logs/sncf.log`.

Dans un notebook, les fonctions s'importent ainsi :

```python
from projet_sncf.business.prevision.prevision import prevoir_mois_suivant
from projet_sncf.database.dataloader import get_dataframe
```

## Tests

Depuis la racine du projet :

```bash
python -m pytest                                                # tous les tests
python -m pytest --doctest-modules src/projet_sncf/business/prevision \
    src/projet_sncf/utils/logging_config.py                     # exemples des docstrings
```
