"""Tableau de fiabilité des liaisons, calculé sur la période de l'analyse."""

# Imports
import logging

import pandas as pd

from projet_sncf.business.analysis.constants import ANALYSIS_END, ANALYSIS_START
from projet_sncf.business.analysis.indicators import (
    compute_cause_profile,
    compute_indicators,
)
from projet_sncf.business.analysis.pipeline import build_reliability_table
from projet_sncf.database.dataloader import get_dataframe

# Constants
logger = logging.getLogger(__name__)


# Functions
def get_reliability_table() -> pd.DataFrame:
    """Calcule le tableau de fiabilité, une ligne par liaison.

    Les données viennent de `get_dataframe`, limitées aux mois de l'analyse
    (de `ANALYSIS_START` à `ANALYSIS_END`). On ajoute aux colonnes du pipeline les
    indicateurs (taux de perturbation, comptages) et les causes de retard,
    utilisés par la carte.

    Returns:
        pd.DataFrame: Une ligne par liaison, triée par score croissant. Les gares
        de départ et d'arrivée et le service sont des colonnes.

    Raises:
        ValueError: Si aucune ligne ne tombe dans la période de l'analyse.
    """
    df = get_dataframe()
    dates = pd.to_datetime(df["Date"])
    df = df[
        (dates >= pd.Timestamp(ANALYSIS_START)) & (dates <= pd.Timestamp(ANALYSIS_END))
    ]
    if df.empty:
        message = f"Aucune donnée entre {ANALYSIS_START} et {ANALYSIS_END}."
        logger.error(message)
        raise ValueError(message)
    table = build_reliability_table(df)
    extra = compute_indicators(df).join(compute_cause_profile(df))
    extra = extra.drop(columns=[c for c in extra.columns if c in table.columns])
    return table.join(extra).reset_index()
