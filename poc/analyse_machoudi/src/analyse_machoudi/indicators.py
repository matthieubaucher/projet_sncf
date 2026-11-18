"""Per-liaison indicators computed from the monthly regularity dataset.

A liaison is a (departure, arrival, service) triplet. Rates are computed on sums,
never on averages of monthly rates.
"""

import logging
import pandas as pd

from analyse_machoudi.constants import (
    CAUSE_COLUMNS,
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_SCHEDULED,
    LIAISON_KEY,
)

logger = logging.getLogger(__name__)


def _check_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Check that a DataFrame contains the given columns.

    Args:
        df (pd.DataFrame): Data to check.
        columns (list[str]): Names of the columns that must be present.

    Raises:
        KeyError: If at least one column is missing. The message lists them.
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"Colonnes manquantes : {missing}")


def filter_valid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with no scheduled train, a negative count or a missing count.

    Args:
        df (pd.DataFrame): Monthly data, one row per liaison and per month.

    Returns:
        pd.DataFrame: A copy of ``df`` without the invalid rows.

    Raises:
        KeyError: If a count column is missing.
    """
    counts = [COL_SCHEDULED, COL_CANCELLED, COL_DELAYED]
    _check_columns(df, counts)
    invalid = (
        (df[COL_SCHEDULED] == 0)
        | (df[counts] < 0).any(axis=1)
        | df[counts].isna().any(axis=1)
    )
    logger.info("Lignes écartées : %d sur %d", invalid.sum(), len(df))
    return df.loc[~invalid].copy()


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the cancellation, delay and disruption rates of each liaison.

    The delay rate is taken over the trains that ran (scheduled minus cancelled).
    The disruption rate is cancelled plus delayed trains over scheduled trains.

    Args:
        df (pd.DataFrame): Cleaned monthly data.

    Returns:
        pd.DataFrame: One row per liaison, indexed by ``LIAISON_KEY``, with the
        columns ``mois``, ``prevues``, ``annules``, ``reelles``, ``retards``,
        ``taux_annulation``, ``taux_retard`` and ``taux_perturbation``.

    Raises:
        KeyError: If a required column is missing.
    """
    _check_columns(df, LIAISON_KEY + [COL_DATE])
    valid = filter_valid_rows(df)
    valid["circulations_reelles"] = valid[COL_SCHEDULED] - valid[COL_CANCELLED]

    indicators = valid.groupby(LIAISON_KEY, observed=True).agg(
        mois=(COL_DATE, "nunique"),
        prevues=(COL_SCHEDULED, "sum"),
        annules=(COL_CANCELLED, "sum"),
        reelles=("circulations_reelles", "sum"),
        retards=(COL_DELAYED, "sum"),
    )
    indicators["taux_annulation"] = indicators["annules"] / indicators["prevues"]
    indicators["taux_retard"] = indicators["retards"] / indicators["reelles"].where(
        indicators["reelles"] > 0
    )
    indicators["taux_perturbation"] = (
        indicators["annules"] + indicators["retards"]
    ) / indicators["prevues"]
    logger.info("Indicateurs calculés : %d liaisons", len(indicators))
    return indicators


def compute_cause_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the share of each delay cause for each liaison, in percent.

    Monthly percentages are converted into trains (percentage times delayed trains),
    summed over the period, then divided by the total.

    Args:
        df (pd.DataFrame): Cleaned monthly data with the six cause columns.

    Returns:
        pd.DataFrame: One row per liaison, one column per cause (short names of
        ``CAUSE_COLUMNS``). Rows sum to 100, or are NaN for a liaison without delay.

    Raises:
        KeyError: If a required column is missing.
    """
    _check_columns(df, LIAISON_KEY + list(CAUSE_COLUMNS))
    valid = filter_valid_rows(df)
    causes = list(CAUSE_COLUMNS)

    trains = valid[causes].mul(valid[COL_DELAYED], axis=0) / 100
    trains = pd.concat([valid[LIAISON_KEY], trains], axis=1)
    per_cause = trains.groupby(LIAISON_KEY, observed=True)[causes].sum()

    total = per_cause.sum(axis=1)
    profile = 100 * per_cause.div(total.where(total > 0), axis=0)
    logger.info("Profil des causes calculé : %d liaisons", len(profile))
    return profile.rename(columns=CAUSE_COLUMNS)
