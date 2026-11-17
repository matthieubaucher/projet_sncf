"""Unit tests of the national shock detection."""

import pandas as pd
import pytest

from analyse_machoudi.constants import (
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_SCHEDULED,
)
from analyse_machoudi.shocks import compute_national_rates, detect_shock_months


def make_months(delayed, scheduled=1000):
    """Build one liaison with one row per month, from January 2024.

    Args:
        delayed (list[int]): Delayed trains of each month.
        scheduled (int): Scheduled trains of each month.

    Returns:
        pd.DataFrame: The monthly data, without cancelled trains.
    """
    months = pd.period_range("2024-01", periods=len(delayed), freq="M").astype(str)
    return pd.DataFrame(
        {
            COL_DATE: months,
            COL_SCHEDULED: scheduled,
            COL_CANCELLED: 0,
            COL_DELAYED: delayed,
        }
    )


def test_national_rates_sum_all_liaisons_before_dividing():
    """Check that the counts of all liaisons are summed before dividing.

    Returns:
        None: Passes if the disruption rate is 60 / 400, the cancellation rate
        10 / 400 and the delay rate 50 / 390.
    """
    df = pd.DataFrame(
        {
            COL_DATE: ["2024-01", "2024-01"],
            COL_SCHEDULED: [100, 300],
            COL_CANCELLED: [10, 0],
            COL_DELAYED: [20, 30],
        }
    )
    month = compute_national_rates(df).loc[pd.Timestamp("2024-01-01")]
    assert month["taux_perturbation"] == pytest.approx(60 / 400)
    assert month["taux_annulation"] == pytest.approx(10 / 400)
    assert month["taux_retard"] == pytest.approx(50 / 390)


def test_national_rates_are_indexed_by_date_in_order():
    """Check the index of the national rates.

    Returns:
        None: Passes if the index is a DatetimeIndex in chronological order, even
        when the input rows are in reverse order.
    """
    df = make_months([10, 20, 30]).iloc[::-1]
    monthly = compute_national_rates(df)
    assert isinstance(monthly.index, pd.DatetimeIndex)
    assert monthly.index.is_monotonic_increasing


def test_one_extreme_month_is_a_shock():
    """Check that an isolated extreme month is detected.

    Returns:
        None: Passes if November 2024, with 500 delays against about 100 the other
        months, is the only shock.
    """
    monthly = compute_national_rates(
        make_months([100, 110, 90, 105, 95, 100, 108, 92, 100, 102, 500, 98])
    )
    shocks = detect_shock_months(monthly)
    assert list(shocks) == [pd.Timestamp("2024-11-01")]


def test_constant_series_has_no_shock():
    """Check a series where every month is identical.

    Returns:
        None: Passes if no month is a shock.
    """
    monthly = compute_national_rates(make_months([100] * 12))
    assert len(detect_shock_months(monthly)) == 0


def test_larger_sigma_keeps_fewer_months():
    """Check the effect of a very large threshold.

    Returns:
        None: Passes if no month is a shock when sigma is 100.
    """
    monthly = compute_national_rates(
        make_months([100, 110, 90, 105, 95, 100, 108, 92, 100, 102, 500, 98])
    )
    assert len(detect_shock_months(monthly, sigma=100)) == 0


def test_missing_date_column_raises_key_error():
    """Check the error raised when the date column is absent.

    Returns:
        None: Passes if a KeyError mentioning the missing columns is raised.
    """
    df = make_months([10, 20]).drop(columns=[COL_DATE])
    with pytest.raises(KeyError, match="Colonnes manquantes"):
        compute_national_rates(df)
