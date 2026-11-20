"""Construit le tableau des coordonnées des gares utilisées par la carte.

Depuis la racine du dépôt, exécuter le module en lui passant les chemins des
fichiers de référence, de données et de sortie.
"""

# Imports
import sys

import pandas as pd

from projet_sncf.utils.stations import match_stations


# Functions
def main(reference_path: str, dataset_path: str, output_path: str) -> None:
    """Associe les gares du jeu de données à leurs coordonnées et les écrit.

    Les gares sont lues dans les colonnes de départ et d'arrivée (les 3e et 4e
    colonnes). Le programme affiche le nombre de gares localisées, la source
    de leurs coordonnées, puis les gares sans correspondance.

    Args:
        reference_path (str): CSV « Gares de voyageurs », séparé par `;`.
        dataset_path (str): CSV des liaisons, séparé par `;`.
        output_path (str): Où écrire le tableau des coordonnées.

    Returns:
        None: Les coordonnées sont écrites dans `output_path`.
    """
    reference = pd.read_csv(reference_path, sep=";")
    dataset = pd.read_csv(dataset_path, sep=";")
    names = sorted(set(dataset.iloc[:, 2]) | set(dataset.iloc[:, 3]))
    matched, unmatched = match_stations(names, reference)
    matched.to_csv(output_path, sep=";", index=False)
    print(f"{len(matched)} gares localisées sur {len(names)}")
    print(matched["source"].value_counts().to_string())
    if len(unmatched):
        print("\nSans correspondance :")
        print(unmatched.to_string(index=False))


# Main program
if __name__ == "__main__":
    main(*sys.argv[1:4])
