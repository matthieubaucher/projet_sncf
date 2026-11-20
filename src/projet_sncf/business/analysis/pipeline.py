"""Chaîne complète : du jeu de données mensuel nettoyé au tableau de fiabilité."""

# Imports
import logging
import pandas as pd

from projet_sncf.business.analysis.constants import FINAL_COLUMNS, MIN_MONTHS
from projet_sncf.business.analysis.indicators import (
    compute_cause_profile,
    compute_indicators,
)
from projet_sncf.business.analysis.regularity import compute_regularity
from projet_sncf.business.analysis.score import compute_score, dominant_cause
from projet_sncf.business.analysis.seasonality import compute_seasonality
from projet_sncf.business.analysis.shocks import (
    compute_national_rates,
    detect_shock_months,
)

# Constants
logger = logging.getLogger(__name__)


# Functions
def build_reliability_table(
    df: pd.DataFrame, min_months: int = MIN_MONTHS
) -> pd.DataFrame:
    """Construit le tableau de fiabilité, une ligne par liaison.

    Les étapes : indicateurs, causes de retard, mois de choc nationaux,
    saisonnalité, régularité, puis score, confiance et tier.

    Args:
        df (pd.DataFrame): Données mensuelles nettoyées, une ligne par liaison et par
            mois. La colonne `Service` doit rester, elle fait partie de la clé.
        min_months (int): Nombre minimal de mois pour un score fiable.

    Returns:
        pd.DataFrame: Une ligne par liaison, indexé par (départ, arrivée, service),
        trié par score croissant. Colonnes de `FINAL_COLUMNS`.

    Raises:
        KeyError: Si une colonne nécessaire manque.
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
