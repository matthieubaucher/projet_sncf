"""Unit tests of the per-liaison indicators."""

import pandas as pd
import pytest

from projet_sncf.business.analysis.constants import (
    CAUSE_COLUMNS,
    COL_ARRIVAL,
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_DEPARTURE,
    COL_SCHEDULED,
    COL_SERVICE,
)
from projet_sncf.business.analysis.indicators import (
    compute_cause_profile,
    compute_indicators,
    filter_valid_rows,
)


def make_rows(rows):
    """Build a monthly DataFrame, one tuple per row.

    Args:
        rows (list[tuple]): Tuples (departure, arrival, service, month, scheduled,
            cancelled, delayed).

    Returns:
        pd.DataFrame: The monthly data, with every cause column set to 0.
    """
    df = pd.DataFrame(
        rows,
        columns=[
            COL_DEPARTURE,
            COL_ARRIVAL,
            COL_SERVICE,
            COL_DATE,
            COL_SCHEDULED,
            COL_CANCELLED,
            COL_DELAYED,
        ],
    )
    for cause in CAUSE_COLUMNS:
        df[cause] = 0.0
    return df


def test_rates_are_computed_on_sums_not_on_means():
    """Check that rates are computed on summed counts.

    Returns:
        None: Passes if the delay rate is 108 / 990 (sums), not the mean of the two
        monthly rates (0.15).
    """
    df = make_rows(
        [
            ("A", "B", "National", "2024-01", 100, 10, 18),
            ("A", "B", "National", "2024-02", 900, 0, 90),
        ]
    )
    result = compute_indicators(df).loc[("A", "B", "National")]
    assert result["mois"] == 2
    assert result["prevues"] == 1000
    assert result["reelles"] == 990
    assert result["taux_annulation"] == pytest.approx(10 / 1000)
    assert result["taux_retard"] == pytest.approx(108 / 990)
    assert result["taux_perturbation"] == pytest.approx(118 / 1000)


def test_service_separates_two_liaisons_with_the_same_stations():
    """Check that the service is part of the liaison key.

    Returns:
        None: Passes if the national and international rows of the same pair of
        stations give two separate liaisons.
    """
    df = make_rows(
        [
            ("A", "B", "National", "2025-07", 100, 0, 10),
            ("A", "B", "International", "2025-07", 50, 5, 5),
        ]
    )
    result = compute_indicators(df)
    assert len(result) == 2
    assert result.loc[("A", "B", "National"), "prevues"] == 100
    assert result.loc[("A", "B", "International"), "prevues"] == 50


def test_filter_drops_zero_scheduled_and_negative_counts():
    """Check which rows the minimal filter removes.

    Returns:
        None: Passes if only the valid row remains out of four (zero scheduled,
        negative cancelled and negative delayed are dropped).
    """
    df = make_rows(
        [
            ("A", "B", "National", "2024-01", 100, 0, 10),
            ("A", "B", "National", "2024-02", 0, 0, 0),
            ("A", "B", "National", "2024-03", 100, -1, 10),
            ("A", "B", "National", "2024-04", 100, 0, -5),
        ]
    )
    assert len(filter_valid_rows(df)) == 1


def test_filter_drops_rows_with_a_missing_count():
    """Check that a missing count removes the whole row.

    Returns:
        None: Passes if only the complete row remains out of four (a missing
        scheduled, cancelled or delayed count is dropped).
    """
    df = make_rows(
        [
            ("A", "B", "National", "2024-01", 100, 0, 10),
            ("A", "B", "National", "2024-02", None, 0, 10),
            ("A", "B", "National", "2024-03", 100, None, 10),
            ("A", "B", "National", "2024-04", 100, 0, None),
        ]
    )
    assert len(filter_valid_rows(df)) == 1


def test_missing_count_does_not_bias_the_rates():
    """Check the rates of a liaison with one incomplete month.

    Returns:
        None: Passes if the incomplete month counts for nothing, neither in the
        scheduled trains nor in the delayed trains.
    """
    df = make_rows(
        [
            ("A", "B", "National", "2024-01", 100, 0, 10),
            ("A", "B", "National", "2024-02", 100, 0, None),
        ]
    )
    result = compute_indicators(df).loc[("A", "B", "National")]
    assert result["prevues"] == 100
    assert result["taux_perturbation"] == pytest.approx(0.10)


def test_filter_does_not_modify_the_input():
    """Check that the filter works on a copy.

    Returns:
        None: Passes if the input DataFrame still has its invalid row afterwards.
    """
    df = make_rows([("A", "B", "National", "2024-01", 0, 0, 0)])
    filter_valid_rows(df)
    assert len(df) == 1


def test_delay_rate_is_nan_when_no_train_ran():
    """Check the delay rate of a liaison whose trains are all cancelled.

    Returns:
        None: Passes if the cancellation rate is 1 and the delay rate is NaN.
    """
    df = make_rows([("A", "B", "National", "2024-01", 10, 10, 0)])
    result = compute_indicators(df).loc[("A", "B", "National")]
    assert result["taux_annulation"] == 1
    assert pd.isna(result["taux_retard"])


def test_missing_column_raises_key_error():
    """Check the error raised when the service column is absent.

    Returns:
        None: Passes if a KeyError mentioning the missing columns is raised.
    """
    df = make_rows([("A", "B", "National", "2024-01", 10, 0, 1)]).drop(
        columns=[COL_SERVICE]
    )
    with pytest.raises(KeyError, match="Colonnes manquantes"):
        compute_indicators(df)


def test_cause_profile_is_weighted_by_delayed_trains():
    """Check that cause shares are weighted by the delayed trains of each month.

    Returns:
        None: Passes if the shares are 12.5, 12.5 and 75 percent, and sum to 100.
    """
    df = make_rows(
        [
            ("A", "B", "National", "2024-01", 500, 0, 100),
            ("A", "B", "National", "2024-02", 500, 0, 300),
        ]
    )
    external, infrastructure, traffic = list(CAUSE_COLUMNS)[:3]
    df.loc[0, [external, infrastructure]] = [50.0, 50.0]
    df.loc[1, traffic] = 100.0

    profile = compute_cause_profile(df).loc[("A", "B", "National")]
    assert profile["Externes"] == pytest.approx(12.5)
    assert profile["Infrastructure"] == pytest.approx(12.5)
    assert profile["Gestion du trafic"] == pytest.approx(75.0)
    assert profile.sum() == pytest.approx(100.0)


def test_cause_profile_is_nan_without_any_delay():
    """Check the cause profile of a liaison without any delay.

    Returns:
        None: Passes if every share is NaN.
    """
    df = make_rows([("A", "B", "National", "2024-01", 100, 0, 0)])
    profile = compute_cause_profile(df).loc[("A", "B", "National")]
    assert profile.isna().all()
