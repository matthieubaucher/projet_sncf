# Prévision des perturbations des liaisons TGV

Ce dossier contient la partie **prédiction** du projet SNCF : prévoir si le mois suivant sera **Normal** ou
**Perturbé** pour chaque liaison TGV, afin d'aider un assureur à tarifer une garantie voyage.

Elle complète le **score de fiabilité** (partie 1, notebook `01_analyse`), qui résume le passé de chaque liaison.

| | Score de fiabilité (partie 1) | Prévision (ce dossier) |
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
│   ├── notebook_projet.ipynb       # compréhension, nettoyage et analyse exploratoire des données
│   ├── analyse_exploratoire.py     # fonctions utilisées par notebook_projet.ipynb
│   └── prevision.ipynb             # modèle de prévision Normal / Perturbé
├── resultats/
│   └── predictions_liaisons.csv    # prévisions du mois suivant, une ligne par liaison
└── README.md
```

## Données

Fichier **régularité mensuelle TGV** de l'AQST (Autorité de la qualité de service dans les transports) : une ligne
par liaison et par mois depuis janvier 2018, avec notamment les circulations prévues, les trains annulés et les
trains en retard à l'arrivée.

Une liaison est définie par le triplet **(gare de départ, gare d'arrivée, service)**, comme dans la partie 1.

## Méthode

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

Seules trois colonnes de comptage du fichier sont utilisées (circulations prévues, trains annulés, trains en retard
à l'arrivée). Les lignes sans circulation prévue sont exclues.

### Apprentissage et test

- **Découpage dans le temps** : apprentissage jusqu'à décembre 2024, test à partir de janvier 2025.
- **Mois de choc retirés de l'apprentissage** : les mois où tout le réseau est très perturbé (grèves de 2018, 2019
  et 2023, confinements de 2020 et 2021), repérés avec la règle de Hampel de la partie 1. Ils restent dans le test.
- **Modèles comparés** : régression logistique, gradient boosting et forêt aléatoire, face à la règle de bon sens
  « comme le mois dernier ».

## Résultats

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

## Limites

- La prévision porte sur **le mois suivant** uniquement.
- Les perturbations soudaines (grèves, intempéries, événements exceptionnels) restent **imprévisibles** à partir du
  passé d'une liaison.
- Retards et annulations ne sont pas distingués dans la prévision.
- Les probabilités servent surtout à **comparer** les liaisons et les mois entre eux ; elles sont légèrement
  surestimées.
- Le seuil de 20 % est une convention.

## Lancer le notebook

```bash
pip install pandas numpy scikit-learn matplotlib seaborn jupyter
```

Ouvrir `notebooks/prevision.ipynb` et l'exécuter du début à la fin, depuis le dossier `notebooks/`. Le notebook lit
les données dans `data/regularite-mensuelle-tgv-aqst.csv` et écrit les prévisions dans
`resultats/predictions_liaisons.csv`.

## Utilisation dans l'application

L'application Streamlit joint deux fichiers avec la même clé (gare de départ, gare d'arrivée, service) :

- `scores_liaisons.csv` (partie 1) : score de fiabilité et tiers de chaque liaison ;
- `predictions_liaisons.csv` (ce dossier) : probabilité de perturbation du mois suivant et prévision.
