# Données de la carte

Auteur : Machoudi ADEGOUNTE

Ces fichiers servent à dessiner la carte de fiabilité (page « Carte interactive »).

| Fichier | Contenu |
| --- | --- |
| `stations_coordonnees.csv` | Latitude et longitude des gares, avec le nom de gare du jeu de régularité. |
| `reseau_ferre_simplifie.json` | Tracés du réseau ferré français, simplifiés pour rester légers. Ils servent de fond de carte. |
| `trajets_liaisons.json` | Tracé de chaque liaison le long des voies. La clé est la paire de gares triée par ordre alphabétique, séparée par `\|`. |

## Sources

- Gares : SNCF Open Data.
- Réseau ferré : SNCF Réseau, sous licence [ODbL](https://opendatacommons.org/licenses/odbl/).

Les fichiers de ce dossier sont dérivés de ces données (simplification des tracés, association aux noms de gares). Si vous les réutilisez, citez la source.