"""Tableau de fiabilité des liaisons, calculé sur la période de l'analyse."""

import pandas as pd

from projet_sncf.business.analysis.constants import ANALYSIS_END, ANALYSIS_START
from projet_sncf.business.analysis.indicators import (
    compute_cause_profile,
    compute_indicators,
)
from projet_sncf.business.analysis.pipeline import build_reliability_table
from projet_sncf.database.dataloader import get_dataframe


def get_reliability_table() -> pd.DataFrame:
    """Calcule le tableau de fiabilité, une ligne par liaison.

    Les données sont chargées avec :func:`get_dataframe`, puis limitées aux mois
    de l'analyse (``ANALYSIS_START`` à ``ANALYSIS_END``). Aux colonnes du
    pipeline s'ajoutent les indicateurs (taux de perturbation, comptages) et les
    causes de retard, utilisés par la carte.

    Returns:
        pandas.DataFrame: Une ligne par liaison, triée par score croissant. Les
        gares de départ et d'arrivée et le service sont des colonnes.
    """
    df = get_dataframe()
    dates = pd.to_datetime(df["Date"])
    df = df[
        (dates >= pd.Timestamp(ANALYSIS_START)) & (dates <= pd.Timestamp(ANALYSIS_END))
    ]
    table = build_reliability_table(df)
    extra = compute_indicators(df).join(compute_cause_profile(df))
    extra = extra.drop(columns=[c for c in extra.columns if c in table.columns])
    return table.join(extra).reset_index()
