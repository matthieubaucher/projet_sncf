# RailInsight — fiabilité des liaisons TGV

[![Dépôt GitHub](https://img.shields.io/badge/GitHub-projet__sncf-181717?logo=github)](https://github.com/projectSNCF-2026/projet_sncf)
[![Tests](https://github.com/projectSNCF-2026/projet_sncf/actions/workflows/tests.yml/badge.svg)](https://github.com/projectSNCF-2026/projet_sncf/actions/workflows/tests.yml)
[![Application Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://projetsncf-whqbqrwhzyyhbvwydecqri.streamlit.app/)

RailInsight est une application Streamlit d'analyse des retards et des
annulations sur les liaisons TGV. Elle transforme les données mensuelles de
régularité publiées par la SNCF en indicateurs et visualisations pour aider à
comprendre les risques de perturbation et leurs conséquences potentielles
pour l'assurance des voyageurs.

## Démarche et objectif

Le projet a commencé par une analyse exploratoire des données (EDA) afin
d'étudier les retards, les annulations, leurs causes et leurs variations selon
les liaisons et les périodes. Les observations issues de cette exploration nous
ont conduits à orienter l'application vers les métiers de l'assurance.

Les différentes EDA réalisées sont disponibles dans les notebooks Jupyter du
dépôt : [analyse](notebooks/01_analyse.ipynb),
[exploration et nettoyage](notebooks/02_exploration_nettoyage.ipynb) et
[prévision](notebooks/03_prevision.ipynb). C'est à partir des observations et
des analyses présentées dans ces notebooks que nous avons défini les
différents axes de l'application.

Une fois d'accord sur les informations à mettre en avant, nous avons développé
une interface avec Streamlit, en nous inspirant d'autres interfaces disponibles
en ligne. Nous avons également utilisé des modèles de langage (LLM) pour
affiner la conception et les visuels de l'application.

RailInsight est conçu comme un outil d'aide à la décision pour une compagnie
d'assurance : il permet de visualiser et de comparer les risques historiques
de perturbation des trajets, d'explorer des scénarios d'indemnisation et
d'estimer leur coût potentiel. Ces éléments peuvent contribuer à l'évaluation
du risque et à l'arbitrage du coût d'une assurance. Ils constituent des
estimations à partir des données disponibles, et non une prévision certaine
des retards ou des indemnisations futures.

**Question étudiée :** quelles liaisons présentent le plus de perturbations
dans l'historique observé, et comment ces informations peuvent-elles aider un assureur
dans l'évaluation du risque et du coût d'une couverture d'assurance ?

## Application

L'application est accessible en ligne :
[ouvrir RailInsight](https://projetsncf-whqbqrwhzyyhbvwydecqri.streamlit.app/).
Elle se met à jour automatiquement à chaque modification de la branche
`develop`.

À partir de ces travaux, l'application s'articule autour des axes suivants,
accessibles depuis le menu latéral :

- **Accueil** : indicateurs d'ensemble et répartition des liaisons par niveau
  de fiabilité ;
- **Carte interactive** : exploration des liaisons, consultation de leur
  historique et simulation d'une prime pure à partir d'une indemnité choisie ;
- **Analyse des perturbations** : saisonnalité, classement des trajets et
  évolution des causes de retard ;
- **Simulation de retard** : estimation interactive à partir d'une liaison et
  des paramètres choisis ;
- **Prévision des perturbations** : visualisation des prévisions et de leurs
  résultats de test ;
- **Clustering des modèles** : comparaison de profils de liaisons.

Le score de fiabilité est calculé à partir de l'historique d'une liaison :

```text
score = 100 × (1 − (trains annulés + trains en retard à l'arrivée)
                   / circulations prévues)
```

Le score résume les observations passées ; ce n'est pas une garantie de
ponctualité future. L'application signale également les liaisons dont
l'historique est court. La prime affichée est une estimation simplifiée :
elle ne prend notamment pas en compte le prix du billet, les frais ni la marge
de l'assureur.

## Données

Le jeu de données source est **Régularité mensuelle TGV** de SNCF Open Data :
[consulter et télécharger le jeu de données](https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/information/).
Le CSV utilisé par le projet est `data/regularite-mensuelle-tgv-aqst.csv`.

Les autres fichiers de `data/` sont utilisés par certaines pages :

- `data/map/` contient les coordonnées des gares et les données du réseau
  nécessaires à la carte ;
- `data/predictions/` contient les prévisions nécessaires à la page
  **Prévision des perturbations**.

Le chargement des données est effectué à partir de ces chemins dans le dépôt.
Si vous remplacez ou actualisez les données, conservez leurs noms et leur
structure, ou adaptez les modules correspondants dans `src/projet_sncf/`.

## Installation

Prérequis : Python **3.11 ou supérieur** et [uv](https://docs.astral.sh/uv/).

Depuis la racine du dépôt, installez les dépendances du projet et celles de
développement :

```bash
uv sync --dev
```

`uv` crée et gère automatiquement l'environnement virtuel du projet à partir
de `pyproject.toml` et `uv.lock`.

## Lancer l'application

Depuis la racine du dépôt :

```bash
uv run streamlit run src/projet_sncf/app.py
```

Streamlit affiche l'adresse locale à ouvrir dans un navigateur (par défaut
`http://localhost:8501`). Le menu de gauche permet de passer d'une analyse à
l'autre. Sur la carte, sélectionnez une liaison pour consulter ses indicateurs
et ajustez l'indemnité dans la barre latérale pour simuler la prime pure.

## Tests et couverture

Exécuter l'ensemble des tests :

```bash
uv run pytest
```

Mesurer la couverture avec le seuil minimal de 90 % demandé pour le projet :

```bash
uv run pytest --cov=src/projet_sncf --cov-report=term-missing --cov-branch --cov-fail-under=90
```

Les tests sont exécutés automatiquement par
[GitHub Actions](https://github.com/projectSNCF-2026/projet_sncf/actions/workflows/tests.yml)
sur les pushes et les pull requests. Le
[workflow de couverture](https://github.com/projectSNCF-2026/projet_sncf/actions/workflows/coverage.yml)
est configuré pour la branche `develop`.

## Organisation du dépôt

```text
src/projet_sncf/
├── app.py                 # point d'entrée et navigation Streamlit
├── pages/                 # pages de l'application
├── business/              # analyses, scores, carte et modèles
├── database/              # chargement et nettoyage des données
├── api/                   # fonctions de simulation/prévision
└── utils/                 # fonctions utilitaires et journalisation
data/                      # données source et fichiers auxiliaires
notebooks/                 # exploration et travaux d'analyse
tests/
├── unitaire/
└── integration/
```

Les dépendances et la configuration des outils sont décrites dans
`pyproject.toml`. Les tests sont écrits avec `pytest`.
