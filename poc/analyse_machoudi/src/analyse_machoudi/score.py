"""Reliability score of each liaison, its confidence level and its tier."""

import logging
import numpy as np
import pandas as pd

from analyse_machoudi.constants import (
    CONFIDENCE_ENOUGH,
    CONFIDENCE_LOW,
    MIN_MONTHS,
    TIER_LABELS,
)
from analyse_machoudi.indicators import _check_columns

logger = logging.getLogger(__name__)


def dominant_cause(profile: pd.DataFrame) -> pd.Series:
    """Return the main delay cause of each liaison.

    Args:
        profile (pd.DataFrame): Output of ``compute_cause_profile``.

    Returns:
        pd.Series: ``cause_dominante``, the name of the cause with the largest
        share. Liaisons without any delay (all NaN) are left out.
    """
    return profile.dropna(how="all").idxmax(axis=1).rename("cause_dominante")


def compute_tier_bounds(scores: pd.Series) -> tuple[float, float]:
    """Compute the bounds between the three tiers of the score.

    Args:
        scores (pd.Series): Scores of the reference liaisons (enough months).

    Returns:
        tuple[float, float]: The 1/3 and 2/3 quantiles of ``scores``. NaN if
        ``scores`` is empty.
    """
    lower, upper = scores.quantile([1 / 3, 2 / 3])
    return lower, upper


def compute_score(table: pd.DataFrame, min_months: int = MIN_MONTHS) -> pd.DataFrame:
    """Add the score, the confidence level and the tier to a table of liaisons.

    Args:
        table (pd.DataFrame): One row per liaison, with the columns ``mois`` and
            ``taux_perturbation`` (see ``compute_indicators``).
        min_months (int): Minimum number of months for a reliable score.

    Returns:
        pd.DataFrame: A copy of ``table`` with the columns ``score`` (0 to 100),
        ``confiance`` and ``tiers``. The tier bounds are the 1/3 and 2/3 quantiles
        of the score among the liaisons with enough months. The tier is NaN if no
        liaison has enough months.

    Raises:
        KeyError: If a required column is missing.
    """
    _check_columns(table, ["mois", "taux_perturbation"])
    result = table.copy()
    result["score"] = 100 * (1 - result["taux_perturbation"])
    enough = result["mois"] >= min_months
    result["confiance"] = np.where(enough, CONFIDENCE_ENOUGH, CONFIDENCE_LOW)

    lower, upper = compute_tier_bounds(result.loc[enough, "score"])
    tier = np.select(
        [result["score"] <= lower, result["score"] <= upper],
        TIER_LABELS[:2],
        default=TIER_LABELS[2],
    )
    tiers = pd.Series(tier, index=result.index).where(
        result["score"].notna() & ~np.isnan(lower)
    )
    result["tiers"] = pd.Categorical(tiers, categories=TIER_LABELS, ordered=True)
    logger.info("Bornes des tiers : %.1f et %.1f", lower, upper)
    return result
