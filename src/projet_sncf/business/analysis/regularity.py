"""Régularité des perturbations de chaque liaison."""

# Imports
import logging
import math

import numpy as np
import pandas as pd

from projet_sncf.business.analysis.constants import (
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_SCHEDULED,
    LIAISON_KEY,
    MIN_MONTHS,
    WORST_MONTHS_SHARE,
)
from projet_sncf.business.analysis.indicators import (
    _check_columns,
    filter_valid_rows,
)

# Constants
logger = logging.getLogger(__name__)


# Functions
def worst_months_share(
    disruptions: pd.Series,
    rates: pd.Series,
    min_months: int = MIN_MONTHS,
    share: float = WORST_MONTHS_SHARE,
) -> float:
    """Calcule la part des perturbations qui tombe dans les pires mois.

    Les pires mois sont les `ceil(share * n)` mois aux taux de perturbation
    les plus hauts.

    Args:
        disruptions (pd.Series): Trains annulés et trains en retard
            de chaque mois.
        rates (pd.Series): Taux de perturbation de chaque mois, même index.
        min_months (int): Nombre minimal de mois exigé.
        share (float): Part de mois comptés comme les pires.

    Returns:
        float: Part des perturbations dans les pires mois, entre 0 et 1.
        NaN s'il y a moins de `min_months` mois ou aucune perturbation.
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
    """Calcule la régularité de chaque liaison, avec et sans les mois de choc.

    Args:
        df (pd.DataFrame): Données mensuelles nettoyées.
        shock_months (pd.DatetimeIndex): Mois exclus pour la deuxième
            colonne, voir `detect_shock_months`.
        min_months (int): Nombre minimal de mois exigé pour une liaison.
        share (float): Part de mois comptés comme les pires.

    Returns:
        pd.DataFrame: Une ligne par liaison, indexée par `LIAISON_KEY`.
        Colonnes `pires_mois_tous` (tous les mois) et
        `pires_mois_hors_chocs` (sans les mois de choc). NaN pour les
        liaisons qui n'ont pas assez de mois.

    Raises:
        KeyError: Si une colonne nécessaire manque.
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
    regularity.index = pd.MultiIndex.from_tuples(
        regularity.index, names=LIAISON_KEY
    )
    logger.info(
        "Régularité calculée : %d liaisons",
        regularity["pires_mois_tous"].notna().sum(),
    )
    return regularity
