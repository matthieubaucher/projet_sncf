"""Regularity of the disruptions of each liaison."""

import logging
import math
import numpy as np
import pandas as pd

from analyse_machoudi.constants import (
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_SCHEDULED,
    LIAISON_KEY,
    MIN_MONTHS,
    WORST_MONTHS_SHARE,
)
from analyse_machoudi.indicators import _check_columns, filter_valid_rows

logger = logging.getLogger(__name__)


def worst_months_share(
    disruptions: pd.Series,
    rates: pd.Series,
    min_months: int = MIN_MONTHS,
    share: float = WORST_MONTHS_SHARE,
) -> float:
    """Compute the share of disruptions that falls in the worst months.

    The worst months are the ``ceil(share * n)`` months with the highest
    disruption rate.

    Args:
        disruptions (pd.Series): Cancelled plus delayed trains of each month.
        rates (pd.Series): Disruption rate of each month, same index.
        min_months (int): Minimum number of months required.
        share (float): Share of months considered as the worst ones.

    Returns:
        float: Share of the disruptions in the worst months, between 0 and 1. NaN if
        there are fewer than ``min_months`` months or no disruption at all.
    """
    total = disruptions.sum()
    if len(disruptions) < min_months or total == 0:
        return np.nan
    k = math.ceil(share * len(disruptions))
    worst = rates.nlargest(k).index
    return disruptions.loc[worst].sum() / total


def compute_regularity(
    df: pd.DataFrame,
    shock_months: pd.DatetimeIndex = pd.DatetimeIndex([]),
    min_months: int = MIN_MONTHS,
    share: float = WORST_MONTHS_SHARE,
) -> pd.DataFrame:
    """Compute the regularity of each liaison, with and without the shock months.

    Args:
        df (pd.DataFrame): Cleaned monthly data.
        shock_months (pd.DatetimeIndex): Months excluded from the second column,
            see ``detect_shock_months``.
        min_months (int): Minimum number of months required for a liaison.
        share (float): Share of months considered as the worst ones.

    Returns:
        pd.DataFrame: One row per liaison, indexed by ``LIAISON_KEY``, with the
        columns ``pires_mois_tous`` (all months) and ``pires_mois_hors_chocs``
        (shock months removed). NaN for liaisons without enough months.

    Raises:
        KeyError: If a required column is missing.
    """
    _check_columns(df, LIAISON_KEY + [COL_DATE])
    valid = filter_valid_rows(df).reset_index(drop=True)
    valid[COL_DATE] = pd.to_datetime(valid[COL_DATE])
    valid["perturbations"] = valid[COL_CANCELLED] + valid[COL_DELAYED]
    valid["taux"] = valid["perturbations"] / valid[COL_SCHEDULED]

    def share_for(group: pd.DataFrame, excluded=()) -> float:
        kept = group.loc[~group[COL_DATE].isin(excluded)]
        return worst_months_share(
            kept["perturbations"], kept["taux"], min_months, share
        )

    rows = {
        key: {
            "pires_mois_tous": share_for(group),
            "pires_mois_hors_chocs": share_for(group, shock_months),
        }
        for key, group in valid.groupby(LIAISON_KEY, observed=True)
    }
    regularity = pd.DataFrame.from_dict(
        rows,
        orient="index",
        columns=["pires_mois_tous", "pires_mois_hors_chocs"],
        dtype=float,
    )
    regularity.index = pd.MultiIndex.from_tuples(regularity.index, names=LIAISON_KEY)
    logger.info(
        "Régularité calculée : %d liaisons", regularity["pires_mois_tous"].notna().sum()
    )
    return regularity
