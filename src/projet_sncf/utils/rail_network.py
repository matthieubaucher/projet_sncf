"""Dessin simplifié du réseau ferré français, utilisé en fond de carte.

Source : « Fichier de formes des lignes du Réseau Ferré National » (SNCF Réseau, ODbL).

Utilisation, depuis la racine du dépôt :
    uv run python -m projet_sncf.utils.rail_network <lignes.csv> <sortie.json>
"""

# Imports
import json
import logging
import math
import sys

import pandas as pd

# Constants
logger = logging.getLogger(__name__)

COL_SHAPE = "Geo Shape"
COL_STATUS = "MNEMO"
STATUS_IN_SERVICE = "EXPLOITE"
# Tolérance de simplification, en degrés
TOLERANCE = 0.01
DECIMALS = 3
LATITUDE_RANGE = (41.0, 52.0)
LONGITUDE_RANGE = (-5.5, 10.0)


# Functions
def parse_paths(shape: str) -> list[list[list[float]]]:
    """Lit les chemins d'une géométrie GeoJSON donnée sous forme de texte.

    Args:
        shape (str): Géométrie GeoJSON, de type LineString ou MultiLineString.

    Returns:
        list[list[list[float]]]: Les chemins, chacun étant une liste de points
        [longitude, latitude]. Vide si le texte manque, est mal formé ou d'un autre
        type.
    """
    try:
        geometry = json.loads(shape)
        kind, coordinates = geometry["type"], geometry["coordinates"]
    except (TypeError, ValueError, KeyError):
        return []
    if kind == "LineString":
        return [coordinates]
    if kind == "MultiLineString":
        return list(coordinates)
    return []


def _distance_to_segment(point, start, end) -> float:
    """Calcule la distance d'un point à un segment, en degrés.

    Args:
        point (list[float]): [longitude, latitude] du point.
        start (list[float]): Première extrémité du segment.
        end (list[float]): Deuxième extrémité du segment.

    Returns:
        float: La distance, dans le plan des coordonnées.
    """
    (px, py), (sx, sy), (ex, ey) = point[:2], start[:2], end[:2]
    dx, dy = ex - sx, ey - sy
    if dx == 0 and dy == 0:
        return math.hypot(px - sx, py - sy)
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (sx + t * dx), py - (sy + t * dy))


def simplify(
    path: list[list[float]], tolerance: float = TOLERANCE
) -> list[list[float]]:
    """Simplifie un chemin avec l'algorithme de Douglas-Peucker.

    Args:
        path (list[list[float]]): Points [longitude, latitude].
        tolerance (float): Plus grande distance, en degrés, entre le chemin et sa
            version simplifiée.

    Returns:
        list[list[float]]: Un chemin avec moins de points, qui garde les deux
        extrémités.
    """
    if len(path) < 3:
        return list(path)
    keep = [False] * len(path)
    keep[0] = keep[-1] = True
    stack = [(0, len(path) - 1)]
    while stack:
        first, last = stack.pop()
        farthest, index = 0.0, None
        for i in range(first + 1, last):
            d = _distance_to_segment(path[i], path[first], path[last])
            if d > farthest:
                farthest, index = d, i
        if index is not None and farthest > tolerance:
            keep[index] = True
            stack.extend([(first, index), (index, last)])
    return [point[:2] for point, kept in zip(path, keep) if kept]


def build_network(
    lines: pd.DataFrame, tolerance: float = TOLERANCE
) -> list[list[list[float]]]:
    """Construit les chemins simplifiés du réseau.

    Args:
        lines (pd.DataFrame): Le CSV des lignes, avec la colonne `Geo Shape` et,
            si elle existe, `MNEMO` (seule la valeur `EXPLOITE` est gardée).
        tolerance (float): Tolérance de la simplification, en degrés.

    Returns:
        list[list[list[float]]]: Les chemins [longitude, latitude], arrondis et
        limités à la France métropolitaine.

    Raises:
        KeyError: Si la colonne `Geo Shape` manque.
    """
    if COL_SHAPE not in lines.columns:
        raise KeyError(
            f"Colonne manquante : {COL_SHAPE}. Colonnes : {list(lines.columns)}"
        )
    if COL_STATUS in lines.columns:
        lines = lines[lines[COL_STATUS] == STATUS_IN_SERVICE]
    network = []
    for shape in lines[COL_SHAPE]:
        for path in parse_paths(shape):
            simple = simplify(path, tolerance)
            rounded = [
                [round(lon, DECIMALS), round(lat, DECIMALS)] for lon, lat in simple
            ]
            inside = all(
                LONGITUDE_RANGE[0] <= lon <= LONGITUDE_RANGE[1]
                and LATITUDE_RANGE[0] <= lat <= LATITUDE_RANGE[1]
                for lon, lat in rounded
            )
            if inside and len(rounded) >= 2:
                network.append(rounded)
    logger.info("Réseau : %d tracés conservés", len(network))
    return network


def main(lines_path: str, output_path: str) -> None:
    """Lit le CSV des lignes et écrit le réseau simplifié en JSON.

    Args:
        lines_path (str): CSV des lignes, séparé par `;`.
        output_path (str): Fichier où écrire la liste des chemins en JSON.

    Returns:
        None: Le réseau est écrit dans `output_path`.
    """
    lines = pd.read_csv(lines_path, sep=";")
    network = build_network(lines)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(network, file, separators=(",", ":"))
    points = sum(len(path) for path in network)
    print(f"{len(network)} tracés, {points} points, écrit dans {output_path}")


# Main program
if __name__ == "__main__":
    main(*sys.argv[1:3])
