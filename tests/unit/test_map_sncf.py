"""Tests for the map data."""

# Imports
import pandas as pd
import pytest

from projet_sncf.business.map_sncf import (
    CONFIDENCE_LOW,
    MODE_EACH_DIRECTION,
    MODE_WORST_DIRECTION,
    NO_TIER_COLOR,
    TIER_COLORS,
    TIER_LESS,
    TIER_MIDDLE,
    TIER_MORE,
    PARIS_GROUP,
    build_curve,
    disruption_frequency,
    display_name,
    filter_links,
    insurer_reading,
    label_name,
    least_reliable,
    link_details,
    offset_path,
    prepare_links,
    pure_premium,
    route_key,
    station_options,
    station_points,
    summary_metrics,
)


# Test data
def make_scores():
    """Four liaisons: A-B, B-A, A-C (short history) and A-D (no coordinates)."""
    return pd.DataFrame(
        {
            "Gare de départ": ["A", "B", "A", "A"],
            "Gare d'arrivée": ["B", "A", "C", "D"],
            "Service": ["National", "National", "International", "National"],
            "mois": [105, 105, 12, 105],
            "taux_perturbation": [0.10, 0.20, 0.15, 0.05],
            "score": [90.0, 80.0, 85.0, 95.0],
            "tiers": [TIER_MORE, TIER_LESS, TIER_MIDDLE, TIER_MORE],
            "confiance": ["suffisante", "suffisante", CONFIDENCE_LOW, "suffisante"],
            "cause_dominante": ["Externes", "Infrastructure", None, "Externes"],
        }
    )


def make_stations():
    """Stations A, B and C. D has no coordinates."""
    return pd.DataFrame(
        {
            "gare": ["A", "B", "C"],
            "latitude": [48.0, 45.0, 43.0],
            "longitude": [2.0, 4.0, 5.0],
        }
    )


# Tests
def test_display_name_capitalizes_and_keeps_tgv_upper_case():
    """Small words in lower case, TGV in upper case."""
    assert display_name("AIX EN PROVENCE TGV") == "Aix en Provence TGV"
    assert display_name("LYON PART DIEU") == "Lyon Part Dieu"


def test_curve_starts_and_ends_at_the_stations():
    """A curve starts and ends at the stations."""
    curve = build_curve((2.0, 48.0), (4.0, 45.0))
    assert curve[0] == pytest.approx([2.0, 48.0])
    assert curve[-1] == pytest.approx([4.0, 45.0])


def test_a_liaison_and_its_return_trip_bend_on_opposite_sides():
    """The two directions bend on opposite sides."""
    forward = build_curve((0.0, 45.0), (4.0, 45.0), points=3)[1]
    backward = build_curve((4.0, 45.0), (0.0, 45.0), points=3)[1]
    assert backward[1] < 45.0 < forward[1]


def test_prepare_links_gives_one_curve_per_liaison_and_counts_unlocated_ones():
    """Three liaisons are kept, one has no coordinates."""
    links, unlocated = prepare_links(make_scores(), make_stations())
    assert len(links) == 3
    assert unlocated == 1
    assert len(links.iloc[0]["path"]) > 2


def test_tier_gives_the_color():
    """The color follows the tier."""
    links, _ = prepare_links(make_scores(), make_stations())
    by_title = links.set_index("titre")
    assert by_title.loc["A → B", "color"][:3] == list(TIER_COLORS[TIER_MORE])
    assert by_title.loc["B → A", "color"][:3] == list(TIER_COLORS[TIER_LESS])
    assert by_title.loc["A → C", "color"][:3] == list(TIER_COLORS[TIER_MIDDLE])


def test_missing_tier_is_gray_and_cause_is_replaced_by_a_text():
    """No tier gives gray, no cause gives a readable text."""
    scores = make_scores().iloc[[2]].copy()
    scores["tiers"] = None
    links, _ = prepare_links(scores, make_stations())
    assert links.iloc[0]["color"][:3] == list(NO_TIER_COLOR)
    assert links.iloc[0]["tiers"] == "non classé"
    assert "aucune" in links.iloc[0]["cause_txt"]


def test_worst_direction_keeps_one_curve_per_pair_with_the_lower_score():
    """A-B and B-A become one curve with the lower score."""
    links, _ = prepare_links(make_scores(), make_stations(), MODE_WORST_DIRECTION)
    pair = links[links["depart"].isin(["A", "B"]) & links["arrivee"].isin(["A", "B"])]
    assert len(pair) == 1
    assert pair.iloc[0]["score"] == 80.0
    assert "sens le moins bon" in pair.iloc[0]["titre"]


def test_filters_on_service_and_tier():
    """Each filter removes the right liaisons."""
    links, _ = prepare_links(make_scores(), make_stations(), MODE_EACH_DIRECTION)
    everything = ["National", "International"], [TIER_LESS, TIER_MIDDLE, TIER_MORE]
    assert len(filter_links(links, *everything)) == 3
    assert len(filter_links(links, ["National"], everything[1])) == 2
    assert len(filter_links(links, everything[0], [TIER_LESS])) == 1


def test_station_points_label_only_the_busiest_stations():
    """Only the busiest station gets a label."""
    links, _ = prepare_links(make_scores(), make_stations())
    points = station_points(links, make_stations(), min_links_for_label=3)
    assert set(points["gare"]) == {"A", "B", "C"}
    assert points.set_index("gare")["label"].to_dict() == {"A": "A", "B": "", "C": ""}


# track from A to B
TRACK_AB = [[2.0, 48.0], [3.0, 46.5], [4.0, 45.0]]


def test_route_key_is_the_same_in_both_directions():
    """Same key in both directions."""
    assert route_key("B", "A") == route_key("A", "B") == "A|B"


def test_routed_liaison_follows_the_track_in_both_directions():
    """A routed liaison follows the track, one without route is a curve."""
    links, _ = prepare_links(
        make_scores(), make_stations(), MODE_WORST_DIRECTION, routes={"A|B": TRACK_AB}
    )
    by_pair = links.set_index(["depart", "arrivee"])
    assert by_pair.loc[("B", "A"), "trace"] == "voie"
    assert by_pair.loc[("B", "A"), "path"] == TRACK_AB[::-1]
    assert by_pair.loc[("A", "C"), "trace"] == "courbe"


def test_each_direction_of_a_routed_liaison_is_shifted_to_its_right():
    """Each direction is shifted to its right."""
    track = [[2.0, 48.0], [2.0, 47.0], [2.0, 46.0], [2.0, 45.0]]
    links, _ = prepare_links(
        make_scores(), make_stations(), MODE_EACH_DIRECTION, routes={"A|B": track}
    )
    by_pair = links.set_index(["depart", "arrivee"])
    going_south = by_pair.loc[("A", "B"), "path"]
    going_north = by_pair.loc[("B", "A"), "path"]
    assert going_south[1][0] < 2.0 < going_north[1][0]
    assert going_south[0] == [2.0, 48.0]
    assert going_north[0] == [2.0, 45.0]


def test_offset_path_keeps_the_number_of_points_and_fades_out_at_the_ends():
    """The ends stay in place, the middle moves."""
    track = [[2.0, 48.0], [2.0, 47.0], [2.0, 46.0], [2.0, 45.0]]
    shifted = offset_path(track, distance=0.05)
    assert len(shifted) == 4
    assert shifted[0] == pytest.approx(track[0])
    assert shifted[-1] == pytest.approx(track[-1])
    assert abs(shifted[1][0] - 2.0) > 0.04


def test_worst_direction_is_not_shifted():
    """One path per pair is not shifted."""
    links, _ = prepare_links(
        make_scores(), make_stations(), MODE_WORST_DIRECTION, routes={"A|B": TRACK_AB}
    )
    pair = links[links["depart"].isin(["A", "B"]) & links["arrivee"].isin(["A", "B"])]
    assert pair.iloc[0]["path"] in (TRACK_AB, TRACK_AB[::-1])


def test_worst_scores_are_drawn_last_so_they_stay_visible_on_shared_tracks():
    """Worst scores come last, so they are drawn on top."""
    links, _ = prepare_links(make_scores(), make_stations())
    assert list(links["score"]) == sorted(links["score"], reverse=True)


def test_filter_on_one_station_and_on_the_paris_group():
    """Filter by station and by the Paris group."""
    scores = make_scores()
    scores.loc[2, "Gare de départ"] = "PARIS NORD"
    stations = pd.concat(
        [
            make_stations(),
            pd.DataFrame(
                {"gare": ["PARIS NORD"], "latitude": [48.9], "longitude": [2.3]}
            ),
        ],
        ignore_index=True,
    )
    links, _ = prepare_links(scores, stations)
    everything = ["National", "International"], [TIER_LESS, TIER_MIDDLE, TIER_MORE]
    assert len(filter_links(links, *everything, station="B")) == 2
    assert len(filter_links(links, *everything, station=PARIS_GROUP)) == 1
    assert PARIS_GROUP == station_options(links)[0]


def test_filter_on_score_range_includes_the_bounds():
    """The bounds of the score range are included."""
    links, _ = prepare_links(make_scores(), make_stations())
    everything = ["National", "International"], [TIER_LESS, TIER_MIDDLE, TIER_MORE]
    kept = filter_links(links, *everything, score_range=(85.0, 90.0))
    assert sorted(kept["score"]) == [85.0, 90.0]


def test_label_name_shortens_stations_and_groups_paris():
    """Suffixes are removed, Paris stations become Paris."""
    assert label_name("PARIS MONTPARNASSE") == "Paris"
    assert label_name("MARSEILLE ST CHARLES") == "Marseille"
    assert label_name("LYON PART DIEU") == "Lyon"
    assert label_name("AIX EN PROVENCE TGV") == "Aix en Provence"
    assert label_name("NANTES") == "Nantes"


def test_labels_do_not_overlap_and_paris_is_labeled_once():
    """Paris is labeled once and close labels do not overlap."""
    stations = pd.DataFrame(
        {
            "gare": [
                "PARIS NORD",
                "PARIS EST",
                "PARIS LYON",
                "LILLE",
                "TOURCOING",
                "NANTES",
            ],
            "latitude": [48.88, 48.87, 48.84, 50.63, 50.72, 47.2],
            "longitude": [2.35, 2.36, 2.37, 3.07, 3.16, -1.54],
        }
    )
    rows = (
        [("PARIS NORD", "LILLE")] * 3
        + [("PARIS EST", "LILLE")] * 2
        + [("PARIS LYON", "NANTES")]
        + [("TOURCOING", "NANTES")]
    )
    links = pd.DataFrame(rows, columns=["depart", "arrivee"])
    points = station_points(links, stations, min_links_for_label=1).set_index("gare")
    labels = points["label"].to_dict()
    assert [name for name in labels.values() if name == "Paris"] == ["Paris"]
    assert labels["PARIS NORD"] == "Paris"
    assert labels["LILLE"] == "Lille"
    assert labels["TOURCOING"] == ""


def test_summary_metrics_counts_the_best_and_worst_tiers():
    """Counts of liaisons, best and worst tiers."""
    links, _ = prepare_links(make_scores(), make_stations())
    assert summary_metrics(links) == {
        "liaisons": 3,
        "plus_fiables": 1,
        "moins_fiables": 1,
    }
    assert summary_metrics(links.iloc[0:0]) == {
        "liaisons": 0,
        "plus_fiables": 0,
        "moins_fiables": 0,
    }


def test_insurer_reading_depends_on_the_tier():
    """Each tier has its own message."""
    assert insurer_reading(TIER_MORE)[0] == "success"
    assert "favorable à assurer" in insurer_reading(TIER_MORE)[1]
    assert insurer_reading(TIER_MIDDLE)[0] == "warning"
    assert insurer_reading(TIER_LESS)[0] == "error"
    assert insurer_reading(None)[0] == "info"


def test_disruption_frequency_says_one_trip_in_n():
    """12.5 % means one trip in 8."""
    assert "1 trajet sur 8" in disruption_frequency(0.125)
    assert "Aucune" in disruption_frequency(0.0)
    assert "Presque tous" in disruption_frequency(0.9)


def test_pure_premium_is_rate_times_indemnity():
    """10 % of 30 euros is 3 euros."""
    assert pure_premium(0.10, 30.0) == pytest.approx(3.0)
    assert pure_premium(0.0, 30.0) == 0.0


def test_least_reliable_starts_with_the_lowest_score():
    """Lowest scores come first."""
    links, _ = prepare_links(make_scores(), make_stations())
    table = least_reliable(links, count=2)
    assert list(table["Score"]) == [80.0, 85.0]


def test_link_details_gives_the_row_and_the_present_causes():
    """Missing causes are left out, an unknown liaison gives None."""
    scores = make_scores()
    scores["Externes"] = [60.0, 10.0, None, 30.0]
    scores["Infrastructure"] = [40.0, 90.0, None, 70.0]
    row, causes = link_details(scores, "B", "A", "National")
    assert row["score"] == 80.0
    assert causes.to_dict() == {"Externes": 10.0, "Infrastructure": 90.0}
    row, causes = link_details(scores, "A", "C", "International")
    assert causes.empty
    assert link_details(scores, "X", "Y", "National")[0] is None
