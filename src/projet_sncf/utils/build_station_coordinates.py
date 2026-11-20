"""Build the table of coordinates of the stations used by the map.

Usage, from poc/analyse_machoudi/:
    uv run python -m projet_sncf.utils.build_station_coordinates <gares_voyageurs.csv> <dataset.csv> <output.csv>
"""

import sys
import pandas as pd

from projet_sncf.utils.stations import match_stations


def main(reference_path: str, dataset_path: str, output_path: str) -> None:
    """Match the stations of the dataset and write their coordinates.

    Args:
        reference_path (str): "Gares de voyageurs" CSV (separator ``;``).
        dataset_path (str): Liaisons CSV (separator ``;``).
        output_path (str): Where to write the table of coordinates.
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


if __name__ == "__main__":
    main(*sys.argv[1:4])
