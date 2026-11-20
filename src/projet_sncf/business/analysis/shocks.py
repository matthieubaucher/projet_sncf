"""Détection des mois où tout le réseau subit un choc."""

# Imports
import logging
import pandas as pd

from projet_sncf.business.analysis.constants import (
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_SCHEDULED,
    MAD_TO_SIGMA,
    SHOCK_SIGMA,
)
from projet_sncf.business.analysis.indicators import filter_valid_rows

# Constants
logger = logging.getLogger(__name__)


# Functions
def compute_national_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les taux mensuels de l'ensemble du réseau.

    On additionne d'abord les trains de toutes les liaisons, puis on divise.
    Chaque train pèse donc le même poids.

    Args:
        df (pd.DataFrame): Données mensuelles nettoyées.

    Returns:
        pd.DataFrame: Une ligne par mois, indexé par la date. Colonnes : `prevues`,
        `annules`, `reelles`, `retards`, `taux_annulation`, `taux_retard` et
        `taux_perturbation`.

    Raises:
        KeyError: Si une colonne nécessaire manque.
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
    """Calcule le taux de perturbation à partir duquel un mois est un choc national.

    Le seuil vaut `médiane + sigma * s`, où `s` est la déviation absolue médiane
    (MAD) multipliée par 1,4826.

    Args:
        monthly (pd.DataFrame): Résultat de `compute_national_rates`.
        sigma (float): Nombre d'écarts-types robustes au-dessus de la médiane.

    Returns:
        float: Le seuil, exprimé sur `taux_perturbation`.

    Raises:
        KeyError: Si `taux_perturbation` manque.
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
    """Renvoie les mois dont le taux de perturbation national est anormalement haut.

    Un mois est un choc quand son taux dépasse strictement le seuil de
    `compute_shock_threshold`.

    Args:
        monthly (pd.DataFrame): Résultat de `compute_national_rates`.
        sigma (float): Nombre d'écarts-types robustes au-dessus de la médiane.

    Returns:
        pd.DatetimeIndex: Les mois de choc, dans l'ordre chronologique.

    Raises:
        KeyError: Si `taux_perturbation` manque.
    """
    threshold = compute_shock_threshold(monthly, sigma)
    rate = monthly["taux_perturbation"]
    shocks = rate.index[rate > threshold]
    logger.info(
        "Seuil de choc : %.3f, %d mois sur %d", threshold, len(shocks), len(rate)
    )
    return shocks
