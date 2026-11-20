# Données

Ce dossier contient les données du projet.

## Jeu de données de régularité

Le fichier `regularite-mensuelle-tgv-aqst.csv` est versionné dans le dépôt : il n'y a rien à télécharger.

Il décrit la régularité mensuelle des TGV, avec une ligne par liaison (gare de départ, gare d'arrivée, service) et par mois. Source : SNCF Open Data, https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/

Les données sont mensuelles. L'analyse utilise une période fixe, de janvier 2018 à juin 2026. Les mois plus récents du fichier sont ignorés, pour que les résultats restent reproductibles.

Pour mettre à jour le jeu de données, télécharger l'export sur SNCF Open Data (lien ci-dessus) et remplacer le fichier.

## Régularité nationale des TGV

Le fichier `reglarite-mensuelle-tgv-nationale.xlsx` donne la régularité de l'ensemble des TGV, mois par mois, de janvier 2015 à juin 2026 (138 mois). 

Il sert seulement à situer le contexte dans le notebook `02_exploration_nettoyage.ipynb`, en montrant l'évolution de la régularité de l'ensemble des TGV depuis 2015, avant de passer à l'étude détaillée par liaison. Ses chiffres portent sur l'ensemble des TGV : ils ne se comparent pas directement à ceux du fichier par liaison, car un même TGV peut compter dans plusieurs liaisons.

## Sous-dossiers

- `map/` : les données de la carte de fiabilité, voir `map/README.md`.
- `predictions/` : les résultats des modèles de prévision.

## Source

Données : SNCF Open Data.
Régularité mensuelle TGV globale : https://www.data.gouv.fr/datasets/regularite-mensuelle-tgv-globale