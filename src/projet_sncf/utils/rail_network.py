"""Simplified drawing of the French rail network, used as the background of the map.

Source: "Fichier de formes des lignes du Réseau Ferré National" (SNCF Réseau, ODbL).
The CSV has one row per line segment, with its geometry as GeoJSON text in the
``Geo Shape`` column. Only the lines in service are kept and their paths are
simplified, so that the result is small enough to be versioned.

Usage,, from poc/analyse_machoudi/:
    uv run python -m projet_sncf.utils.rail_network <lignes.csv> <output.json>
"""

import json
import logging
import math
import sys
import pandas as pd

logger = logging.getLogger(__name__)

COL_SHAPE = "Geo Shape"
COL_STATUS = "MNEMO"
STATUS_IN_SERVICE = "EXPLOITE"
TOLERANCE = 0.01  # degrees
DECIMALS = 3
LATITUDE_RANGE = (41.0, 52.0)
LONGITUDE_RANGE = (-5.5, 10.0)


def parse_paths(shape: str) -> list[list[list[float]]]:
    """Read the paths of a GeoJSON geometry given as text.

    Args:
        shape (str): GeoJSON geometry, of type LineString or MultiLineString.

    Returns:
        list[list[list[float]]]: The paths, each a list of [longitude, latitude].
        Empty if the text is missing, malformed or of another type.
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
    """Compute the distance from a point to a segment, in degrees.

    Args:
        point (list[float]): [longitude, latitude] of the point.
        start (list[float]): First end of the segment.
        end (list[float]): Second end of the segment.

    Returns:
        float: The distance, in the plane of the coordinates.
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
    """Simplify a path with the Douglas-Peucker algorithm.

    Args:
        path (list[list[float]]): Points [longitude, latitude].
        tolerance (float): Largest distance, in degrees, between the path and its
            simplification.

    Returns:
        list[list[float]]: A path with fewer points, keeping both ends.
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
    """Build the simplified paths of the network.

    Args:
        lines (pd.DataFrame): The lines CSV, with the column ``Geo Shape`` and,
            if present, ``MNEMO`` (only the value ``EXPLOITE`` is kept).
        tolerance (float): Tolerance of the simplification, in degrees.

    Returns:
        list[list[list[float]]]: The paths [longitude, latitude], rounded and limited
        to metropolitan France.

    Raises:
        KeyError: If the column ``Geo Shape`` is missing.
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
    """Read the lines CSV and write the simplified network as JSON.

    Args:
        lines_path (str): Lines CSV (separator ``;``).
        output_path (str): Where to write the JSON list of paths.
    """
    lines = pd.read_csv(lines_path, sep=";")
    network = build_network(lines)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(network, file, separators=(",", ":"))
    points = sum(len(path) for path in network)
    print(f"{len(network)} tracés, {points} points, écrit dans {output_path}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
