"""Seasonality of the delay rate of each liaison.

Seasonality is measured by the adjusted R² of the calendar month (January to
December) on the monthly delay rate: the share of the variation explained by the
time of year, corrected for the number of months observed.
"""

import logging

import numpy as np
import pandas as pd

from projet_sncf.business.analysis.constants import (
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_SCHEDULED,
    LIAISON_KEY,
    MIN_MONTHS,
)
from projet_sncf.business.analysis.indicators import _check_columns, filter_valid_rows

logger = logging.getLogger(__name__)


def adjusted_r2(rates: pd.Series, calendar_months: pd.Series, min_months: int) -> float:
    """Compute the adjusted R² of the calendar month on a series of rates.

    Args:
        rates (pd.Series): Monthly delay rates of one liaison. NaN values are ignored.
        calendar_months (pd.Series): Calendar month (1 to 12) of each rate, same index.
        min_months (int): Minimum number of months required.

    Returns:
        float: The adjusted R², or NaN if there are fewer than ``min_months``
        months, if the rate never varies, or if there are not more months than
        distinct calendar months.
    """
    y = rates.dropna()
    n = len(y)
    months = calendar_months.loc[y.index]
    k = months.nunique()
    total = ((y - y.mean()) ** 2).sum()
    if n < min_months or np.isclose(total, 0.0, atol=1e-12) or n <= k:
        return np.nan
    month_means = y.groupby(months).transform("mean")
    r2 = ((month_means - y.mean()) ** 2).sum() / total
    return 1 - (1 - r2) * (n - 1) / (n - k)


def compute_seasonality(
    df: pd.DataFrame,
    shock_months: pd.DatetimeIndex = pd.DatetimeIndex([]),
    min_months: int = MIN_MONTHS,
) -> pd.Series:
    """Compute the seasonality of the delay rate of each liaison.

    Shock months are removed first, so that a national event is not mistaken for a
    seasonal effect.

    Args:
        df (pd.DataFrame): Cleaned monthly data.
        shock_months (pd.DatetimeIndex): Months to exclude, see ``detect_shock_months``.
        min_months (int): Minimum number of months required for a liaison.

    Returns:
        pd.Series: ``saisonnalite``, one value per liaison indexed by
        ``LIAISON_KEY``. NaN for liaisons without enough months.

    Raises:
        KeyError: If a required column is missing.
    """
    _check_columns(df, LIAISON_KEY + [COL_DATE])
    valid = filter_valid_rows(df)
    valid[COL_DATE] = pd.to_datetime(valid[COL_DATE])
    valid = valid.loc[~valid[COL_DATE].isin(shock_months)].copy()

    ran = valid[COL_SCHEDULED] - valid[COL_CANCELLED]
    valid["taux_retard_mensuel"] = valid[COL_DELAYED] / ran.where(ran > 0)
    valid["mois_calendaire"] = valid[COL_DATE].dt.month

    results = {
        key: adjusted_r2(
            group["taux_retard_mensuel"], group["mois_calendaire"], min_months
        )
        for key, group in valid.groupby(LIAISON_KEY, observed=True)
    }
    seasonality = pd.Series(results, name="saisonnalite", dtype=float)
    seasonality.index.names = LIAISON_KEY
    logger.info(
        "Saisonnalité calculée : %d liaisons sur %d",
        seasonality.notna().sum(),
        len(seasonality),
    )
    return seasonality
