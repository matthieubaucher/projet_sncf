"""Detection of the months when the whole network is hit by a shock."""

import logging
import pandas as pd

from analyse_machoudi.constants import (
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_SCHEDULED,
    MAD_TO_SIGMA,
    SHOCK_SIGMA,
)
from analyse_machoudi.indicators import filter_valid_rows

logger = logging.getLogger(__name__)


def compute_national_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the monthly rates of the whole network.

    Counts of all liaisons are summed before dividing, so that each train weighs the
    same.

    Args:
        df (pd.DataFrame): Cleaned monthly data.

    Returns:
        pd.DataFrame: One row per month, indexed by date, with the columns
        ``prevues``, ``annules``, ``reelles``, ``retards``, ``taux_annulation``,
        ``taux_retard`` and ``taux_perturbation``.

    Raises:
        KeyError: If a required column is missing.
    """
    if COL_DATE not in df.columns:
        raise KeyError(f"Colonnes manquantes : {[COL_DATE]}")
    valid = filter_valid_rows(df)
    valid[COL_DATE] = pd.to_datetime(valid[COL_DATE])
    valid["circulations_reelles"] = valid[COL_SCHEDULED] - valid[COL_CANCELLED]

    monthly = valid.groupby(COL_DATE).agg(
        prevues=(COL_SCHEDULED, "sum"),
        annules=(COL_CANCELLED, "sum"),
        reelles=("circulations_reelles", "sum"),
        retards=(COL_DELAYED, "sum"),
    )
    monthly["taux_annulation"] = monthly["annules"] / monthly["prevues"]
    monthly["taux_retard"] = monthly["retards"] / monthly["reelles"].where(
        monthly["reelles"] > 0
    )
    monthly["taux_perturbation"] = (monthly["annules"] + monthly["retards"]) / monthly[
        "prevues"
    ]
    return monthly


def compute_shock_threshold(monthly: pd.DataFrame, sigma: float = SHOCK_SIGMA) -> float:
    """Compute the disruption rate above which a month is a national shock.

    The threshold is ``median + sigma * s``, where ``s`` is the median absolute
    deviation multiplied by 1.4826.

    Args:
        monthly (pd.DataFrame): Output of ``compute_national_rates``.
        sigma (float): Number of robust standard deviations above the median.

    Returns:
        float: The threshold on ``taux_perturbation``.

    Raises:
        KeyError: If ``taux_perturbation`` is missing.
    """
    if "taux_perturbation" not in monthly.columns:
        raise KeyError("Colonnes manquantes : ['taux_perturbation']")
    rate = monthly["taux_perturbation"]
    median = rate.median()
    spread = MAD_TO_SIGMA * (rate - median).abs().median()
    return median + sigma * spread


def detect_shock_months(
    monthly: pd.DataFrame, sigma: float = SHOCK_SIGMA
) -> pd.DatetimeIndex:
    """Return the months whose national disruption rate is abnormally high.

    A month is a shock when its rate is strictly above the threshold of
    ``compute_shock_threshold``.

    Args:
        monthly (pd.DataFrame): Output of ``compute_national_rates``.
        sigma (float): Number of robust standard deviations above the median.

    Returns:
        pd.DatetimeIndex: The shock months, in chronological order.

    Raises:
        KeyError: If ``taux_perturbation`` is missing.
    """
    threshold = compute_shock_threshold(monthly, sigma)
    rate = monthly["taux_perturbation"]
    shocks = rate.index[rate > threshold]
    logger.info(
        "Seuil de choc : %.3f, %d mois sur %d", threshold, len(shocks), len(rate)
    )
    return shocks
