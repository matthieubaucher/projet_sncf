"""Unit tests of the seasonality indicator."""

import numpy as np
import pandas as pd
import pytest

from analyse_machoudi.constants import (
    COL_ARRIVAL,
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_DEPARTURE,
    COL_SCHEDULED,
    COL_SERVICE,
)
from analyse_machoudi.seasonality import adjusted_r2, compute_seasonality


def make_liaison(delayed, start="2022-01", station="B", scheduled=1000):
    """Build one liaison with one row per month.

    Args:
        delayed (list[int]): Delayed trains of each month.
        start (str): First month, as "YYYY-MM".
        station (str): Arrival station, to tell liaisons apart.
        scheduled (int): Scheduled trains of each month.

    Returns:
        pd.DataFrame: The monthly data, without cancelled trains.
    """
    months = pd.period_range(start, periods=len(delayed), freq="M").astype(str)
    return pd.DataFrame(
        {
            COL_DEPARTURE: "A",
            COL_ARRIVAL: station,
            COL_SERVICE: "National",
            COL_DATE: months,
            COL_SCHEDULED: scheduled,
            COL_CANCELLED: 0,
            COL_DELAYED: delayed,
        }
    )


def test_adjusted_r2_is_one_for_a_perfect_seasonal_pattern():
    """Check the adjusted R² when the rate depends only on the calendar month.

    Returns:
        None: Passes if the value is 1 for four years of the same yearly pattern.
    """
    pattern = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10]
    rates = pd.Series(pattern * 4)
    months = pd.Series(list(range(1, 13)) * 4)
    assert adjusted_r2(rates, months, min_months=24) == pytest.approx(1.0)


def test_adjusted_r2_is_nan_below_the_minimum_number_of_months():
    """Check the minimum number of months.

    Returns:
        None: Passes if 23 months give NaN and 24 months give a number.
    """
    rates = pd.Series(np.arange(24) % 12 + np.arange(24) * 0.01)
    months = pd.Series(list(range(1, 13)) * 2)
    assert np.isnan(adjusted_r2(rates.iloc[:23], months.iloc[:23], min_months=24))
    assert not np.isnan(adjusted_r2(rates, months, min_months=24))


def test_adjusted_r2_is_nan_for_a_constant_rate():
    """Check a rate that never changes.

    Returns:
        None: Passes if the value is NaN (no variation to explain).
    """
    rates = pd.Series([0.1] * 24)
    months = pd.Series(list(range(1, 13)) * 2)
    assert np.isnan(adjusted_r2(rates, months, min_months=24))


def test_adjusted_r2_is_low_for_pure_noise():
    """Check the adjusted R² of a rate unrelated to the calendar month.

    Returns:
        None: Passes if the value is below 0.2.
    """
    rng = np.random.default_rng(0)
    rates = pd.Series(rng.normal(0.1, 0.02, 48))
    months = pd.Series(list(range(1, 13)) * 4)
    assert adjusted_r2(rates, months, min_months=24) < 0.2


def test_seasonality_one_value_per_liaison_and_nan_if_too_short():
    """Check the output shape and the handling of short liaisons.

    Returns:
        None: Passes if the long liaison has a value and the short one has NaN, both
        indexed by the liaison key.
    """
    pattern = [10, 20, 30, 40, 50, 60, 70, 60, 50, 40, 30, 20]
    df = pd.concat(
        [make_liaison(pattern * 3, station="B"), make_liaison(pattern, station="C")]
    )
    result = compute_seasonality(df)
    assert result.name == "saisonnalite"
    assert result.loc[("A", "B", "National")] == pytest.approx(1.0)
    assert np.isnan(result.loc[("A", "C", "National")])


def test_shock_months_are_removed_before_measuring_seasonality():
    """Check that shock months are left out of the computation.

    Returns:
        None: Passes if excluding a shock month gives the same value as deleting
        its row from the data.
    """
    rng = np.random.default_rng(1)
    df = make_liaison(list(rng.integers(80, 120, 36)))
    df.loc[10, COL_DELAYED] = 900
    shock = pd.DatetimeIndex(["2022-11-01"])
    expected = compute_seasonality(df.drop(index=10)).iloc[0]
    assert compute_seasonality(df, shock_months=shock).iloc[0] == pytest.approx(
        expected
    )
    assert compute_seasonality(df).iloc[0] != pytest.approx(expected)


def test_missing_column_raises_key_error():
    """Check the error raised when the date column is absent.

    Returns:
        None: Passes if a KeyError mentioning the missing columns is raised.
    """
    df = make_liaison([10] * 30).drop(columns=[COL_DATE])
    with pytest.raises(KeyError, match="Colonnes manquantes"):
        compute_seasonality(df)
