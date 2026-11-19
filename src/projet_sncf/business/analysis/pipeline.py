"""Full pipeline: from the cleaned monthly dataset to the table of liaisons."""

import logging

import pandas as pd

from projet_sncf.business.analysis.constants import FINAL_COLUMNS, MIN_MONTHS
from projet_sncf.business.analysis.indicators import compute_cause_profile, compute_indicators
from projet_sncf.business.analysis.regularity import compute_regularity
from projet_sncf.business.analysis.score import compute_score, dominant_cause
from projet_sncf.business.analysis.seasonality import compute_seasonality
from projet_sncf.business.analysis.shocks import compute_national_rates, detect_shock_months

logger = logging.getLogger(__name__)


def build_reliability_table(
    df: pd.DataFrame, min_months: int = MIN_MONTHS
) -> pd.DataFrame:
    """Build the reliability table, one row per liaison.

    Steps: indicators, delay causes, national shock months, seasonality,
    regularity, then score, confidence and tier.

    Args:
        df (pd.DataFrame): Cleaned monthly data, one row per liaison and per month.
            The ``Service`` column must be kept, it is part of the liaison key.
        min_months (int): Minimum number of months for a reliable score.

    Returns:
        pd.DataFrame: One row per liaison, indexed by (departure, arrival, service),
        sorted by increasing score, with the columns of ``FINAL_COLUMNS``.

    Raises:
        KeyError: If a required column is missing.
    """
    indicators = compute_indicators(df)
    causes = compute_cause_profile(df)
    shock_months = detect_shock_months(compute_national_rates(df))
    seasonality = compute_seasonality(df, shock_months, min_months)
    regularity = compute_regularity(df, shock_months, min_months)

    table = indicators.join(seasonality).join(regularity)
    table["cause_dominante"] = dominant_cause(causes)
    table = compute_score(table, min_months)
    logger.info("Table de fiabilité construite : %d liaisons", len(table))
    return table[FINAL_COLUMNS].sort_values("score")
