"""Tests for the routing."""

# Imports
import json
import pandas as pd
import pytest

from analyse_machoudi.routing import (
    build_graph,
    build_routes,
    distance_km,
    nearest_node,
    read_paths,
    route_key,
    route_pair,
)

# Test data

# a main line, a branch from its middle and an isolated line
MAIN = [[0.0, 45.0], [1.0, 45.0]]
BRANCH = [[0.5005, 45.0003], [0.5005, 45.5]]
ISLAND = [[3.0, 45.0], [3.1, 45.0]]


# Tests
def test_distance_km_matches_known_values():
    """Known distances."""
    assert distance_km((0, 45), (0, 46)) == pytest.approx(110.57, rel=0.01)
    assert distance_km((0, 45), (1, 45)) == pytest.approx(78.7, rel=0.01)


def test_route_key_is_the_same_in_both_directions():
    """Same key in both directions."""
    assert (
        route_key("NANTES", "PARIS") == route_key("PARIS", "NANTES") == "NANTES|PARIS"
    )


def test_route_follows_the_line_between_two_stations():
    """The path stays on the line."""
    network = build_graph([MAIN])
    path = route_pair(network, (0.1, 45.0), (0.9, 45.0))
    assert path[0] == [0.1, 45.0]
    assert path[-1] == [0.9, 45.0]
    assert all(point[1] == pytest.approx(45.0, abs=0.001) for point in path)


def test_route_goes_through_a_junction_in_the_middle_of_a_segment():
    """A branch that starts mid-line is connected to it."""
    network = build_graph([MAIN, BRANCH])
    path = route_pair(network, (0.0, 45.0), (0.5005, 45.5), max_detour=2.0)
    assert path is not None
    assert any(abs(p[0] - 0.5) < 0.01 and abs(p[1] - 45.0) < 0.01 for p in path)


def test_station_far_from_the_network_has_no_route():
    """A station far from the network has no route."""
    network = build_graph([MAIN])
    assert route_pair(network, (0.1, 45.0), (0.9, 46.0)) is None


def test_isolated_piece_of_network_is_ignored():
    """Isolated lines are ignored."""
    network = build_graph([MAIN, BRANCH, ISLAND])
    assert nearest_node(network, (3.05, 45.0), 0.06) is None
    assert route_pair(network, (0.1, 45.0), (3.05, 45.0)) is None


def test_route_much_longer_than_the_straight_line_is_rejected():
    """A long detour is rejected."""
    u_shape = [[0.0, 45.0], [0.0, 46.0], [1.0, 46.0], [1.0, 45.0]]
    network = build_graph([u_shape])
    assert route_pair(network, (0.0, 45.0), (1.0, 45.0)) is None
    assert route_pair(network, (0.0, 45.0), (1.0, 45.0), max_detour=5.0) is not None


def test_build_routes_keys_both_directions_once_and_lists_failures():
    """A pair is routed once, an unknown station fails."""
    network = build_graph([MAIN])
    stations = pd.DataFrame(
        {
            "gare": ["WEST", "EAST"],
            "latitude": [45.0, 45.0],
            "longitude": [0.1, 0.9],
        }
    )
    routes, failed = build_routes(
        network,
        stations,
        [("WEST", "EAST"), ("EAST", "WEST"), ("WEST", "NOWHERE"), ("NOWHERE", "WEST")],
    )
    assert list(routes) == ["EAST|WEST"]
    assert routes["EAST|WEST"][0] == [0.9, 45.0]
    assert failed == [("NOWHERE", "WEST")]


def test_read_paths_keeps_lines_in_service_inside_france():
    """Only lines in service in France are kept."""

    def shape(path):
        return json.dumps({"type": "LineString", "coordinates": path})

    lines = pd.DataFrame(
        {
            "Geo Shape": [
                shape(MAIN),
                shape(BRANCH),
                shape([[20.0, 45.0], [21.0, 45.0]]),
            ],
            "MNEMO": ["EXPLOITE", "DESAFFECTE", "EXPLOITE"],
        }
    )
    assert read_paths(lines) == [MAIN]


def test_read_paths_without_shape_column_raises_key_error():
    """A missing column raises a KeyError."""
    with pytest.raises(KeyError, match="Geo Shape"):
        read_paths(pd.DataFrame({"autre": [1]}))
