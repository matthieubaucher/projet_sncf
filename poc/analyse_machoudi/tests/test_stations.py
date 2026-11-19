"""Unit tests of the station matching."""

import numpy as np
import pandas as pd
import pytest

from analyse_machoudi.stations import match_stations, normalize_name, parse_position


def make_reference():
    """Build a small reference in the format of the "Gares de voyageurs" dataset.

    Returns:
        pd.DataFrame: Four stations with their position.
    """
    return pd.DataFrame(
        {
            "Nom_Gare": [
                "Nantes",
                "Lyon-Part-Dieu",
                "Marseille-Saint-Charles",
                "Paris Gare de Lyon",
            ],
            "Position géographique": [
                "47.217, -1.542",
                "45.760, 4.859",
                "43.303, 5.380",
                "48.844, 2.374",
            ],
        }
    )


def test_normalize_name_ignores_case_accents_hyphens_and_saint_abbreviation():
    """Check that spellings of the same station give the same key.

    Returns:
        None: Passes if the dataset and reference spellings of two stations match.
    """
    assert normalize_name("MARSEILLE ST CHARLES") == normalize_name(
        "Marseille-Saint-Charles"
    )
    assert normalize_name("LYON PART DIEU") == normalize_name("Lyon-Part-Dieu")
    assert normalize_name("Mâcon  Loché") == "MACON LOCHE"


def test_parse_position_reads_latitude_and_longitude():
    """Check the reading of the position column.

    Returns:
        None: Passes if a valid string gives two floats and a malformed one gives NaN.
    """
    assert parse_position("49.6852237, 1.7743058") == pytest.approx(
        (49.6852237, 1.7743058)
    )
    assert all(np.isnan(parse_position("n/a")))
    assert all(np.isnan(parse_position(np.nan)))


def test_stations_are_matched_by_name_alias_or_manual_coordinates():
    """Check the three ways of finding the coordinates.

    Returns:
        None: Passes if a spelling variant, an alias and a foreign station are all
        found, with the expected source.
    """
    matched, unmatched = match_stations(
        ["LYON PART DIEU", "PARIS LYON", "MADRID"], make_reference()
    )
    sources = dict(zip(matched["gare"], matched["source"]))
    assert sources == {
        "LYON PART DIEU": "gares-voyageurs",
        "PARIS LYON": "gares-voyageurs",
        "MADRID": "manuel",
    }
    assert len(unmatched) == 0
    assert matched.set_index("gare").loc["LYON PART DIEU", "latitude"] == pytest.approx(
        45.76
    )


def test_unknown_station_is_returned_with_candidates():
    """Check a station that has no match.

    Returns:
        None: Passes if it is in the unmatched table with the closest reference name.
    """
    matched, unmatched = match_stations(["NANTE"], make_reference())
    assert len(matched) == 0
    assert unmatched.loc[0, "gare"] == "NANTE"
    assert "Nantes" in unmatched.loc[0, "candidats"]
