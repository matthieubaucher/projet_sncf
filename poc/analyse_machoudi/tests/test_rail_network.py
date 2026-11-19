"""Unit tests of the simplified rail network."""

import json
import pandas as pd
import pytest

from analyse_machoudi.rail_network import build_network, parse_paths, simplify


def line(*points):
    """Write a LineString as GeoJSON text.

    Args:
        *points (tuple[float, float]): Points (longitude, latitude).

    Returns:
        str: The geometry as JSON text.
    """
    return json.dumps({"type": "LineString", "coordinates": [list(p) for p in points]})


def test_parse_paths_reads_line_and_multiline():
    """Check the two supported geometry types.

    Returns:
        None: Passes if a LineString gives one path and a MultiLineString two.
    """
    multi = json.dumps(
        {"type": "MultiLineString", "coordinates": [[[0, 0], [1, 1]], [[2, 2], [3, 3]]]}
    )
    assert len(parse_paths(line((0, 0), (1, 1)))) == 1
    assert len(parse_paths(multi)) == 2


def test_parse_paths_ignores_missing_malformed_or_other_geometries():
    """Check the inputs that give no path.

    Returns:
        None: Passes if NaN, broken text and a Point all give an empty list.
    """
    point = json.dumps({"type": "Point", "coordinates": [0, 0]})
    assert parse_paths(float("nan")) == []
    assert parse_paths("not json") == []
    assert parse_paths(point) == []


def test_simplify_removes_aligned_points_and_keeps_ends():
    """Check the simplification of a straight path.

    Returns:
        None: Passes if only the two ends remain.
    """
    path = [[0, 0], [1, 0.0001], [2, 0], [3, 0.0001], [4, 0]]
    assert simplify(path, tolerance=0.01) == [[0, 0], [4, 0]]


def test_simplify_keeps_a_corner():
    """Check that a real change of direction is kept.

    Returns:
        None: Passes if the corner point stays in the path.
    """
    path = [[0, 0], [1, 0], [2, 0], [2, 1], [2, 2]]
    assert [2, 0] in simplify(path, tolerance=0.01)


def test_build_network_keeps_only_lines_in_service_inside_france():
    """Check the filters on status and location.

    Returns:
        None: Passes if the closed line and the line outside France are dropped, and
        the coordinates of the kept one are rounded.
    """
    lines = pd.DataFrame(
        {
            "MNEMO": ["EXPLOITE", "FERME", "EXPLOITE"],
            "Geo Shape": [
                line((2.123456, 48.1), (3.0, 48.5)),
                line((2.0, 48.0), (3.0, 48.5)),
                line((20.0, 48.0), (21.0, 48.5)),
            ],
        }
    )
    network = build_network(lines)
    assert network == [[[2.123, 48.1], [3.0, 48.5]]]


def test_build_network_without_status_column_keeps_everything():
    """Check a file without the status column.

    Returns:
        None: Passes if every valid line is kept.
    """
    lines = pd.DataFrame({"Geo Shape": [line((2.0, 48.0), (3.0, 48.5))]})
    assert len(build_network(lines)) == 1


def test_build_network_without_shape_column_raises_key_error():
    """Check the error when the geometry column is absent.

    Returns:
        None: Passes if a KeyError naming the column is raised.
    """
    with pytest.raises(KeyError, match="Geo Shape"):
        build_network(pd.DataFrame({"a": [1]}))
