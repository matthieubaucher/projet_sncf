"""Saisonnalité du taux de retard de chaque liaison.

Mesurée avec le R² ajusté du mois calendaire sur le taux mensuel.
"""

# Imports
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
from projet_sncf.business.analysis.indicators import (
    _check_columns,
    filter_valid_rows,
)

# Constants
logger = logging.getLogger(__name__)


# Functions
def adjusted_r2(
    rates: pd.Series, calendar_months: pd.Series, min_months: int
) -> float:
    """Calcule le R² ajusté du mois calendaire sur une série de taux.

    Args:
        rates (pd.Series): Taux de retard mensuels d'une liaison.
            Les NaN sont ignorés.
        calendar_months (pd.Series): Mois calendaire (1 à 12) de chaque taux,
            avec le même index.
        min_months (int): Nombre minimal de mois exigé.

    Returns:
        float: Le R² ajusté. NaN s'il y a moins de `min_months` mois, si le
        taux ne varie jamais ou s'il n'y a pas plus de mois que de mois
        calendaires distincts.
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
    """Calcule la saisonnalité du taux de retard de chaque liaison.

    Les mois de choc sont retirés pour ne pas confondre un événement national
    avec un effet de saison.

    Args:
        df (pd.DataFrame): Données mensuelles nettoyées.
        shock_months (pd.DatetimeIndex): Mois à exclure, voir
            `detect_shock_months`.
        min_months (int): Nombre minimal de mois exigé pour une liaison.

    Returns:
        pd.Series: `saisonnalite`, une valeur par liaison, indexée par
        `LIAISON_KEY`. NaN pour les liaisons avec trop peu de mois.

    Raises:
        KeyError: Si une colonne nécessaire manque.
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
