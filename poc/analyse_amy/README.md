# Analyse et prévision des perturbations des liaisons TGV

Ce dossier contient deux parties du projet SNCF :

1. **l'exploration et le nettoyage** des données de régularité des TGV ;
2. **la prévision** : savoir si le mois suivant sera **Normal** ou **Perturbé** pour chaque liaison, afin d'aider
   un assureur à tarifer une garantie voyage.

La prévision complète le **score de fiabilité** (notebook `01_analyse` de l'équipe), qui résume le passé de chaque
liaison.

| | Score de fiabilité | Prévision (ce dossier) |
|---|---|---|
| Question | Cette liaison est-elle fiable en général ? | Le mois prochain sera-t-il perturbé ? |
| Période | tout l'historique | le mois suivant la dernière donnée |
| Résultat | un score sur 100 et un tiers de fiabilité | une probabilité de perturbation et une prévision Normal / Perturbé |

## Structure

```
poc/analyse_amy/
├── data/
│   ├── regularite-mensuelle-tgv-aqst.csv       # régularité mensuelle par liaison (AQST)
│   ├── reglarite-mensuelle-tgv-nationale.csv   # régularité nationale mensuelle
│   └── reglarite-mensuelle-tgv-nationale.xlsx  # même fichier, format Excel
├── notebooks/
│   ├── exploration_nettoyage.ipynb  # contexte, découverte, diagnostic et règles de nettoyage
│   └── prevision.ipynb              # modèle de prévision Normal / Perturbé
├── utils/
│   ├── nettoyage.py                 # règles de nettoyage (fonction nettoyer)
│   └── journal.py                   # écriture des logs dans un fichier
├── tests/
│   └── test_nettoyage.py            # tests unitaires du nettoyage
├── logs/
│   └── sncf.log                     # journal d'exécution
├── resultats/
│   └── predictions_liaisons.csv     # prévisions du mois suivant, une ligne par liaison
├── pytest.ini                       # configuration des tests
└── README.md
```

## Données

- **Régularité mensuelle TGV par liaison** (AQST, Autorité de la qualité de service dans les transports) : une ligne
  par liaison et par mois depuis janvier 2018, avec les circulations prévues, les trains annulés, les trains en
  retard, les retards moyens et la répartition des causes de retard.
- **Régularité nationale mensuelle** (open data SNCF) : la régularité de l'ensemble des TGV depuis janvier 2015,
  utilisée pour le contexte.

Une liaison est définie par le triplet **(gare de départ, gare d'arrivée, service)** : de juillet à septembre 2025,
14 liaisons ont à la fois une offre nationale et une offre internationale le même mois.

## Exploration et nettoyage

Le notebook `exploration_nettoyage.ipynb` établit un diagnostic de la qualité des données, puis fixe et justifie
les règles de nettoyage. Ces règles sont appliquées par la fonction `nettoyer` de `utils/nettoyage.py`, utilisable
par tous les notebooks.

| Problème | Lignes | Décision |
|---|---|---|
| Colonnes commentaires (vides ou texte libre) | 3 colonnes | supprimées |
| Aucune circulation prévue (surtout avril 2020) | 73 | ligne supprimée |
| Trains en retard > 30 min négatif ou inférieur à > 60 min | 354 | case remplacée par NaN |
| Retard moyen des trains en retard négatif | 10 | case remplacée par NaN |
| Retard moyen de tous les trains négatif | 291 | case remplacée par NaN |

Une valeur fausse ne concerne qu'une case : on la remplace par NaN plutôt que de supprimer toute la ligne, pour
garder les autres informations et des séries mensuelles continues. Les trois colonnes utilisées pour le score et
la prévision (circulations prévues, trains annulés, trains en retard à l'arrivée) ne contiennent aucun NaN.

Deux constats de l'exploration :

- le point haut de régularité de 2020 s'explique par la baisse du trafic pendant le Covid (environ 264 000
  circulations prévues, contre 380 000 à 445 000 les autres années complètes) ;
- l'été est plus perturbé surtout à cause de la gestion en gare, du matériel roulant et de l'affluence des
  voyageurs, et non des travaux : la cause « infrastructure » est celle qui augmente le moins.

## Prévision

### Variable cible

Pour chaque liaison et chaque mois :

$$\tau_{\text{mois}} = \frac{\text{annulés} + \text{retards à l'arrivée}}{\text{circulations prévues}}$$

Le mois est **Perturbé** si $\tau_{\text{mois}} > 20\ \%$ (plus d'un train sur cinq n'arrive pas normalement, soit un
score du mois sous 80 / 100), **Normal** sinon. Le seuil correspond à peu près au 70e centile du taux mensuel ; le
notebook compare aussi 15 %, 25 % et 30 %.

### Variables explicatives

Huit variables, toutes connues **à la fin du mois précédent** (aucune information du mois prédit) :

| Variable | Signification |
|---|---|
| `mois` | mois de l'année visé |
| `international` | 1 si la liaison est internationale |
| `retard_mois_dernier`, `annulation_mois_dernier` | taux du mois précédent |
| `retard_12_mois`, `annulation_12_mois` | taux sur les 12 mois précédents |
| `retard_an_dernier`, `annulation_an_dernier` | taux du même mois l'année précédente |

### Apprentissage et test

- **Découpage dans le temps** : apprentissage jusqu'à décembre 2024, test à partir de janvier 2025.
- **Mois de choc retirés de l'apprentissage** : les mois où tout le réseau est très perturbé (grèves de 2018, 2019
  et 2023, confinements de 2020 et 2021), repérés avec la règle de Hampel. Ils restent dans le test.
- **Modèles comparés** : régression logistique, gradient boosting et forêt aléatoire, face à la règle de bon sens
  « comme le mois dernier ».

### Résultats

Sur la période de test (janvier 2025 → juin 2026) :

| Méthode | F1 macro | Rappel | Précision | AUC |
|---|---|---|---|---|
| Comme le mois dernier | 0,699 | 0,534 | 0,608 | — |
| Régression logistique | 0,720 | 0,698 | 0,570 | 0,821 |
| Gradient boosting | 0,713 | 0,683 | 0,563 | 0,810 |
| **Forêt aléatoire (retenue)** | **0,732** | **0,706** | **0,587** | **0,821** |

- Le modèle retenu repère environ **7 mois perturbés sur 10**, contre 5 sur 10 pour la règle « comme le mois
  dernier », pour une précision proche.
- Les modèles donnent des résultats proches : l'information utile est surtout dans le **passé récent** de la
  liaison (12 derniers mois et mois précédent). La saison compte peu.
- La probabilité de perturbation range bien les mois du plus sûr au plus risqué (AUC de 0,82).

Les chiffres peuvent varier légèrement selon la date de fin du fichier de données.

### Limites

- La prévision porte sur **le mois suivant** uniquement.
- Les perturbations soudaines (grèves, intempéries, événements exceptionnels) restent **imprévisibles** à partir du
  passé d'une liaison.
- Retards et annulations ne sont pas distingués dans la prévision.
- Les probabilités servent surtout à **comparer** les liaisons et les mois entre eux ; elles sont légèrement
  surestimées.
- Le seuil de 20 % est une convention.

## Installation

Depuis la racine du dépôt, avec [uv](https://docs.astral.sh/uv/) :

```bash
uv sync --inexact
uv pip install matplotlib seaborn openpyxl ipykernel scikit-learn pydocstyle
```

`--inexact` garde les paquets ajoutés à la main, utiles aux notebooks mais pas encore déclarés dans le
`pyproject.toml` du projet.

## Utilisation

### Nettoyer les données

```python
import pandas as pd
from utils.nettoyage import nettoyer
from utils.journal import configurer_journal

configurer_journal(dossier="logs")  # écrit les étapes du nettoyage dans logs/sncf.log
data = pd.read_csv("data/regularite-mensuelle-tgv-aqst.csv", sep=";")
df_propre, rapport = nettoyer(data)
```

`nettoyer` renvoie les données nettoyées et un rapport qui compte les lignes supprimées et les cases remplacées
par NaN. Les données d'origine ne sont pas modifiées. La documentation de chaque fonction est accessible avec
`help(nettoyer)`.

### Lancer les notebooks

Ouvrir les notebooks depuis le dossier `notebooks/` et les exécuter du début à la fin :

- `exploration_nettoyage.ipynb` lit les données dans `data/`, applique `nettoyer` et écrit le journal dans `logs/` ;
- `prevision.ipynb` écrit les prévisions dans `resultats/predictions_liaisons.csv`.

### Lancer les tests

Depuis le dossier `poc/analyse_amy/` :

```bash
python -m pytest
pydocstyle --convention=google utils/
```

Les tests utilisent un petit tableau fabriqué à la main, où chaque ligne illustre un cas (ligne valide, ligne sans
circulation, valeurs négatives…). Les exemples écrits dans les docstrings sont aussi exécutés comme des tests.
Les tests de ce dossier sont également lancés par la CI du dépôt (`uv run pytest` depuis la racine).

## Utilisation dans l'application

L'application Streamlit joint deux fichiers avec la même clé (gare de départ, gare d'arrivée, service) :

- `scores_liaisons.csv` : score de fiabilité et tiers de chaque liaison ;
- `predictions_liaisons.csv` (ce dossier) : probabilité de perturbation du mois suivant et prévision.
