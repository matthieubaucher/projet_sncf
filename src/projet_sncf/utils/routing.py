"""Find the path of each liaison along the rail network (SNCF Réseau lines)."""

# Imports
import heapq
import json
import logging
import math
import sys
from dataclasses import dataclass, field
import pandas as pd

from projet_sncf.utils.rail_network import (
    COL_SHAPE,
    COL_STATUS,
    LATITUDE_RANGE,
    LONGITUDE_RANGE,
    STATUS_IN_SERVICE,
    parse_paths,
    simplify,
)

logger = logging.getLogger(__name__)

# Constants
MAX_SPACING_KM = 0.2
JOIN_DISTANCE = 0.003
STATION_DISTANCE = 0.06
OUTPUT_TOLERANCE = 0.002
MAX_DETOUR = 1.8
CELL = 0.01
DECIMALS = 4
COL_STATION = "gare"
COL_LATITUDE = "latitude"
COL_LONGITUDE = "longitude"
COL_DEPARTURE = "Gare de départ"
COL_ARRIVAL = "Gare d'arrivée"


# Functions
def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Rough distance in km between two points (longitude, latitude)."""
    mean_latitude = math.radians((a[1] + b[1]) / 2)
    dx = (b[0] - a[0]) * math.cos(mean_latitude) * 111.32
    dy = (b[1] - a[1]) * 110.57
    return math.hypot(dx, dy)


def route_key(station_a: str, station_b: str) -> str:
    """Key of a pair of stations, the same in both directions."""
    first, second = sorted([station_a, station_b])
    return f"{first}|{second}"


@dataclass
class Network:
    """Rail network as a graph."""

    nodes: list = field(default_factory=list)
    adjacency: list = field(default_factory=list)
    grid: dict = field(default_factory=dict)


def _cell(point: tuple[float, float]) -> tuple[int, int]:
    """Grid cell of a point."""
    return math.floor(point[0] / CELL), math.floor(point[1] / CELL)


def _densify(path: list[list[float]]) -> list[tuple[float, float]]:
    """Add points on long segments."""
    points = [(round(path[0][0], DECIMALS), round(path[0][1], DECIMALS))]
    for (x0, y0), (x1, y1) in zip(path[:-1], path[1:]):
        parts = max(1, math.ceil(distance_km((x0, y0), (x1, y1)) / MAX_SPACING_KM))
        for i in range(1, parts + 1):
            x = x0 + (x1 - x0) * i / parts
            y = y0 + (y1 - y0) * i / parts
            points.append((round(x, DECIMALS), round(y, DECIMALS)))
    return points


def nearest_node(
    network: Network, point: tuple[float, float], max_distance: float
) -> int | None:
    """Closest node within max_distance degrees, or None."""
    reach = math.ceil(max_distance / CELL)
    cx, cy = _cell(point)
    best, best_distance = None, math.inf
    for i in range(cx - reach, cx + reach + 1):
        for j in range(cy - reach, cy + reach + 1):
            for node in network.grid.get((i, j), ()):
                x, y = network.nodes[node]
                if abs(x - point[0]) > max_distance or abs(y - point[1]) > max_distance:
                    continue
                d = distance_km(point, (x, y))
                if d < best_distance:
                    best, best_distance = node, d
    return best


def _largest_component(network: Network) -> Network:
    """Keep only the biggest connected part, small isolated pieces would block some stations."""
    seen = [False] * len(network.nodes)
    best: list[int] = []
    for start in range(len(network.nodes)):
        if seen[start]:
            continue
        seen[start] = True
        component, stack = [start], [start]
        while stack:
            node = stack.pop()
            for neighbor in network.adjacency[node]:
                if not seen[neighbor]:
                    seen[neighbor] = True
                    component.append(neighbor)
                    stack.append(neighbor)
        if len(component) > len(best):
            best = component

    new_index = {old: new for new, old in enumerate(sorted(best))}
    result = Network()
    for old in sorted(best):
        result.nodes.append(network.nodes[old])
        result.adjacency.append(
            {new_index[n]: w for n, w in network.adjacency[old].items()}
        )
        result.grid.setdefault(_cell(network.nodes[old]), []).append(new_index[old])
    return result


def build_graph(paths: list[list[list[float]]]) -> Network:
    """Build the graph from the paths.

    Points with the same rounded coordinates are one node. A line end that stops
    next to another line is joined to it.
    """
    network = Network()
    index: dict[tuple[float, float], int] = {}
    ends: list[int] = []

    def node_of(point: tuple[float, float]) -> int:
        if point not in index:
            index[point] = len(network.nodes)
            network.nodes.append(point)
            network.adjacency.append({})
            network.grid.setdefault(_cell(point), []).append(index[point])
        return index[point]

    for path in paths:
        if len(path) < 2:
            continue
        points = _densify(path)
        previous = node_of(points[0])
        ends.append(previous)
        for point in points[1:]:
            current = node_of(point)
            if current != previous:
                length = distance_km(network.nodes[previous], network.nodes[current])
                network.adjacency[previous][current] = length
                network.adjacency[current][previous] = length
            previous = current
        ends.append(previous)

    for end in set(ends):
        point = network.nodes[end]
        reach = math.ceil(JOIN_DISTANCE / CELL)
        cx, cy = _cell(point)
        best, best_distance = None, math.inf
        for i in range(cx - reach, cx + reach + 1):
            for j in range(cy - reach, cy + reach + 1):
                for node in network.grid.get((i, j), ()):
                    if node == end or node in network.adjacency[end]:
                        continue
                    d = distance_km(point, network.nodes[node])
                    if d < best_distance and d <= JOIN_DISTANCE * 111:
                        best, best_distance = node, d
        if best is not None:
            network.adjacency[end][best] = best_distance
            network.adjacency[best][end] = best_distance

    logger.info("Graphe : %d noeuds", len(network.nodes))
    return _largest_component(network)


def shortest_path(
    network: Network, source: int, target: int
) -> tuple[list[int], float] | None:
    """A* shortest path between two nodes: the nodes and the length in km, or None."""
    goal = network.nodes[target]
    best = {source: 0.0}
    parent: dict[int, int] = {}
    closed: set[int] = set()
    heap = [(distance_km(network.nodes[source], goal), 0.0, source)]
    while heap:
        _, cost, node = heapq.heappop(heap)
        if node == target:
            path = [node]
            while node in parent:
                node = parent[node]
                path.append(node)
            return path[::-1], cost
        if node in closed:
            continue
        closed.add(node)
        for neighbor, weight in network.adjacency[node].items():
            new_cost = cost + weight
            if new_cost < best.get(neighbor, math.inf):
                best[neighbor] = new_cost
                parent[neighbor] = node
                estimate = new_cost + distance_km(network.nodes[neighbor], goal)
                heapq.heappush(heap, (estimate, new_cost, neighbor))
    return None


def route_pair(
    network: Network,
    start: tuple[float, float],
    end: tuple[float, float],
    max_detour: float = MAX_DETOUR,
) -> list[list[float]] | None:
    """Path of a liaison along the network, or None if it cannot be routed.

    It is rejected if a station is too far from the network, if the stations are not
    connected, or if the path is much longer than the straight line.
    """
    source = nearest_node(network, start, STATION_DISTANCE)
    target = nearest_node(network, end, STATION_DISTANCE)
    if source is None or target is None or source == target:
        return None
    found = shortest_path(network, source, target)
    if found is None:
        return None
    nodes, length = found
    straight = distance_km(start, end)
    if straight < 1 or length > max_detour * straight:
        return None
    line = [list(network.nodes[n]) for n in nodes]
    line = simplify(line, OUTPUT_TOLERANCE)
    return [list(start)] + line + [list(end)]


def build_routes(
    network: Network,
    stations: pd.DataFrame,
    pairs: list[tuple[str, str]],
    max_detour: float = MAX_DETOUR,
) -> tuple[dict[str, list[list[float]]], list[tuple[str, str]]]:
    """Route several pairs of stations.

    Returns:
        The paths by route key, and the pairs that failed.
    """
    coordinates = stations.dropna(subset=[COL_LATITUDE, COL_LONGITUDE]).set_index(
        COL_STATION
    )
    routes: dict[str, list[list[float]]] = {}
    failed: list[tuple[str, str]] = []
    done: set[str] = set()
    for a, b in pairs:
        key = route_key(a, b)
        if key in done:
            continue
        done.add(key)
        first, second = key.split("|")
        if first not in coordinates.index or second not in coordinates.index:
            failed.append((first, second))
            continue
        start = (
            coordinates.loc[first, COL_LONGITUDE],
            coordinates.loc[first, COL_LATITUDE],
        )
        end = (
            coordinates.loc[second, COL_LONGITUDE],
            coordinates.loc[second, COL_LATITUDE],
        )
        path = route_pair(network, start, end, max_detour)
        if path is None:
            failed.append((first, second))
        else:
            routes[key] = path
    return routes, failed


def read_paths(lines: pd.DataFrame) -> list[list[list[float]]]:
    """Read the lines in service inside metropolitan France.

    Raises:
        KeyError: if the "Geo Shape" column is missing.
    """
    if COL_SHAPE not in lines.columns:
        raise KeyError(
            f"Colonne manquante : {COL_SHAPE}. Colonnes : {list(lines.columns)}"
        )
    if COL_STATUS in lines.columns:
        lines = lines[lines[COL_STATUS] == STATUS_IN_SERVICE]
    paths = []
    for shape in lines[COL_SHAPE]:
        for path in parse_paths(shape):
            inside = all(
                LONGITUDE_RANGE[0] <= p[0] <= LONGITUDE_RANGE[1]
                and LATITUDE_RANGE[0] <= p[1] <= LATITUDE_RANGE[1]
                for p in path
            )
            if inside and len(path) >= 2:
                paths.append(path)
    return paths


def main(
    lines_path: str, stations_path: str, scores_path: str, output_path: str
) -> None:
    """Route every liaison and write the paths as JSON."""
    logging.basicConfig(level=logging.INFO)
    paths = read_paths(pd.read_csv(lines_path, sep=";"))
    network = build_graph(paths)
    stations = pd.read_csv(stations_path, sep=";")
    scores = pd.read_csv(scores_path)
    pairs = list(zip(scores[COL_DEPARTURE], scores[COL_ARRIVAL]))
    routes, failed = build_routes(network, stations, pairs)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                k: [[round(x, DECIMALS), round(y, DECIMALS)] for x, y in v]
                for k, v in routes.items()
            },
            file,
            separators=(",", ":"),
        )
    print(
        f"{len(routes)} trajets calculés, {len(failed)} sans trajet (dessinés en courbe)."
    )
    for a, b in failed:
        print(f"  sans trajet : {a} - {b}")


# Main program
if __name__ == "__main__":
    main(*sys.argv[1:5])
