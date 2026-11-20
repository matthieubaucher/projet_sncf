# Données

Ce dossier contient les données du projet.

## Jeu de données de régularité

Le fichier `regularite-mensuelle-tgv-aqst.csv` est versionné dans le dépôt : il n'y a rien à télécharger.

Il décrit la régularité mensuelle des TGV, avec une ligne par liaison (gare de départ, gare d'arrivée, service) et par mois.

Les données sont mensuelles. L'analyse utilise une période fixe, de janvier 2018 à juin 2026. Les mois plus récents du fichier sont ignorés, pour que les résultats restent reproductibles.

Pour mettre à jour le jeu de données, télécharger l'export sur SNCF Open Data (lien dans la section Source) et remplacer le fichier.

## Sous-dossiers

- `map/` : les données de la carte de fiabilité, voir `map/README.md`.
- `predictions/` : les résultats des modèles de prévision.

## Source

Données : SNCF Open Data.

- Régularité mensuelle TGV (jeu de données utilisé) : https://ressources.data.sncf.com/explore/dataset/regularite-mensuelle-tgv-aqst/
- Régularité mensuelle TGV globale : https://www.data.gouv.fr/datasets/regularite-mensuelle-tgv-globale