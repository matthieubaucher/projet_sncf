"""Unit tests of the regularity indicator."""

import numpy as np
import pandas as pd
import pytest

from projet_sncf.business.analysis.constants import (
    COL_ARRIVAL,
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_DEPARTURE,
    COL_SCHEDULED,
    COL_SERVICE,
)
from projet_sncf.business.analysis.regularity import compute_regularity, worst_months_share


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


def test_uniform_disruptions_give_the_share_of_worst_months():
    """Check the share when every month has the same disruptions.

    Returns:
        None: Passes if the 3 worst months out of 30 (10 %) hold 10 % of the
        disruptions.
    """
    disruptions = pd.Series([10] * 30)
    rates = disruptions / 1000
    assert worst_months_share(disruptions, rates, min_months=24) == pytest.approx(0.1)


def test_concentrated_disruptions_give_a_high_share():
    """Check the share when three months hold most of the disruptions.

    Returns:
        None: Passes if the share is 300 / 327 for 27 months of 1 and 3 months of 100.
    """
    disruptions = pd.Series([1] * 27 + [100] * 3)
    rates = disruptions / 1000
    assert worst_months_share(disruptions, rates, min_months=24) == pytest.approx(
        300 / 327
    )


def test_number_of_worst_months_is_rounded_up():
    """Check that the number of worst months is rounded up.

    Returns:
        None: Passes if 25 months give 3 worst months (ceil of 2.5), so 3 / 28
        of the disruptions for 3 months of 10 and 22 months of 1.
    """
    disruptions = pd.Series([10] * 3 + [1] * 22)
    rates = disruptions / 1000
    assert worst_months_share(disruptions, rates, min_months=24) == pytest.approx(
        30 / 52
    )


def test_share_is_nan_when_too_short_or_without_disruption():
    """Check the two cases without a value.

    Returns:
        None: Passes if 23 months and a series of zeros both give NaN.
    """
    short = pd.Series([5] * 23)
    assert np.isnan(worst_months_share(short, short / 1000, min_months=24))
    zeros = pd.Series([0] * 30)
    assert np.isnan(worst_months_share(zeros, zeros / 1000, min_months=24))


def test_regularity_columns_and_index():
    """Check the output format.

    Returns:
        None: Passes if there is one row per liaison, indexed by the liaison key,
        with the two expected columns.
    """
    df = pd.concat(
        [make_liaison([10] * 30, station="B"), make_liaison([10] * 30, station="C")]
    )
    result = compute_regularity(df)
    assert list(result.columns) == ["pires_mois_tous", "pires_mois_hors_chocs"]
    assert len(result) == 2
    assert result.index.names == [COL_DEPARTURE, COL_ARRIVAL, COL_SERVICE]


def test_removing_a_shock_month_lowers_the_share():
    """Check the effect of the shock months.

    Returns:
        None: Passes if the share without the shock month is lower than with it,
        and equal to the share computed on the data without that row.
    """
    delayed = [10] * 35 + [500]
    df = make_liaison(delayed)
    shock = pd.DatetimeIndex(["2024-12-01"])
    result = compute_regularity(df, shock_months=shock).iloc[0]
    assert result["pires_mois_hors_chocs"] < result["pires_mois_tous"]
    expected = compute_regularity(df.iloc[:-1]).iloc[0]["pires_mois_tous"]
    assert result["pires_mois_hors_chocs"] == pytest.approx(expected)


def test_liaison_too_short_after_removing_shocks_is_nan():
    """Check the minimum number of months after the removal of shocks.

    Returns:
        None: Passes if a 24-month liaison with one shock month has a value with all
        months and NaN without the shock month.
    """
    df = make_liaison([10] * 23 + [500])
    shock = pd.DatetimeIndex(["2023-12-01"])
    result = compute_regularity(df, shock_months=shock).iloc[0]
    assert not np.isnan(result["pires_mois_tous"])
    assert np.isnan(result["pires_mois_hors_chocs"])


def test_missing_column_raises_key_error():
    """Check the error raised when the service column is absent.

    Returns:
        None: Passes if a KeyError mentioning the missing columns is raised.
    """
    df = make_liaison([10] * 30).drop(columns=[COL_SERVICE])
    with pytest.raises(KeyError, match="Colonnes manquantes"):
        compute_regularity(df)
