"""Score de fiabilité, confiance et niveau de chaque liaison."""

# Imports
import logging

import numpy as np
import pandas as pd

from projet_sncf.business.analysis.constants import (
    CONFIDENCE_ENOUGH,
    CONFIDENCE_LOW,
    MIN_MONTHS,
    TIER_LABELS,
)
from projet_sncf.business.analysis.indicators import _check_columns

# Constants
logger = logging.getLogger(__name__)


# Functions
def dominant_cause(profile: pd.DataFrame) -> pd.Series:
    """Renvoie la cause de retard principale de chaque liaison.

    Args:
        profile (pd.DataFrame): Résultat de `compute_cause_profile`.

    Returns:
        pd.Series: `cause_dominante`, le nom de la cause majoritaire.
        Les liaisons sans retard (tout NaN) sont écartées.
    """
    return profile.dropna(how="all").idxmax(axis=1).rename("cause_dominante")


def compute_tier_bounds(scores: pd.Series) -> tuple[float, float]:
    """Calcule les bornes qui séparent les trois tiers du score.

    Args:
        scores (pd.Series): Scores des liaisons de référence (assez de mois).

    Returns:
        tuple[float, float]: Les quantiles 1/3 et 2/3 de `scores`.
        NaN si `scores` est vide.
    """
    lower, upper = scores.quantile([1 / 3, 2 / 3])
    return lower, upper


def compute_score(
    table: pd.DataFrame, min_months: int = MIN_MONTHS
) -> pd.DataFrame:
    """Ajoute le score, la confiance et le tier à un tableau de liaisons.

    Le score vaut 100 * (1 - taux de perturbation). Les bornes des tiers sont
    les quantiles 1/3 et 2/3 du score, calculés sur les liaisons qui ont assez
    de mois.

    Args:
        table (pd.DataFrame): Une ligne par liaison, avec les colonnes
            `mois` et `taux_perturbation` (voir `compute_indicators`).
        min_months (int): Nombre minimal de mois pour un score fiable.

    Returns:
        pd.DataFrame: Une copie de `table` avec les colonnes `score` (de 0 à
        100), `confiance` et `tiers`. Le tiers vaut NaN si aucune liaison n'a
        assez de mois.

    Raises:
        KeyError: Si une colonne nécessaire manque.
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
    result["tiers"] = pd.Categorical(
        tiers, categories=TIER_LABELS, ordered=True
    )
    logger.info("Bornes des tiers : %.1f et %.1f", lower, upper)
    return result
