"""Indicateurs par liaison, calculés à partir de la régularité mensuelle."""

# Imports
import logging
import pandas as pd

from projet_sncf.business.analysis.constants import (
    CAUSE_COLUMNS,
    COL_CANCELLED,
    COL_DATE,
    COL_DELAYED,
    COL_SCHEDULED,
    LIAISON_KEY,
)

# Constants
logger = logging.getLogger(__name__)


# Functions
def _check_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Vérifie que le DataFrame contient bien les colonnes demandées.

    Args:
        df (pd.DataFrame): Données à vérifier.
        columns (list[str]): Colonnes qui doivent être présentes.

    Raises:
        KeyError: Si au moins une colonne manque. Le message les liste toutes.
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"Colonnes manquantes : {missing}")


def filter_valid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Retire les lignes inutilisables du jeu de données.

    Une ligne est écartée si aucun train n'était prévu, si un des
    comptes est négatif ou si un des comptes est manquant.

    Args:
        df (pd.DataFrame): Données mensuelles, une ligne par liaison et par mois.

    Returns:
        pd.DataFrame: Une copie de `df` sans les lignes invalides.

    Raises:
        KeyError: Si une colonne de comptage manque.
    """
    counts = [COL_SCHEDULED, COL_CANCELLED, COL_DELAYED]
    _check_columns(df, counts)
    invalid = (
        (df[COL_SCHEDULED] == 0)
        | (df[counts] < 0).any(axis=1)
        | df[counts].isna().any(axis=1)
    )
    logger.info("Lignes écartées : %d sur %d", invalid.sum(), len(df))
    return df.loc[~invalid].copy()


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les taux d'annulation, de retard et de perturbation de chaque liaison.

    Le taux de retard se calcule sur les trains qui ont circulé (prévus moins
    annulés). Le taux de perturbation compte les trains annulés et en retard,
    rapportés aux trains prévus.

    Args:
        df (pd.DataFrame): Données mensuelles nettoyées.

    Returns:
        pd.DataFrame: Une ligne par liaison, indexé par `LIAISON_KEY`. Colonnes :
        `mois`, `prevues`, `annules`, `reelles`, `retards`, `taux_annulation`,
        `taux_retard` et `taux_perturbation`. Le taux de retard vaut NaN si aucun
        train n'a circulé.

    Raises:
        KeyError: Si une colonne nécessaire manque.
    """
    _check_columns(df, LIAISON_KEY + [COL_DATE])
    valid = filter_valid_rows(df)
    valid["circulations_reelles"] = valid[COL_SCHEDULED] - valid[COL_CANCELLED]

    indicators = valid.groupby(LIAISON_KEY, observed=True).agg(
        mois=(COL_DATE, "nunique"),
        prevues=(COL_SCHEDULED, "sum"),
        annules=(COL_CANCELLED, "sum"),
        reelles=("circulations_reelles", "sum"),
        retards=(COL_DELAYED, "sum"),
    )
    indicators["taux_annulation"] = indicators["annules"] / indicators["prevues"]
    indicators["taux_retard"] = indicators["retards"] / indicators["reelles"].where(
        indicators["reelles"] > 0
    )
    indicators["taux_perturbation"] = (
        indicators["annules"] + indicators["retards"]
    ) / indicators["prevues"]
    logger.info("Indicateurs calculés : %d liaisons", len(indicators))
    return indicators


def compute_cause_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule la part de chaque cause de retard pour chaque liaison, en pourcentage.

    Chaque pourcentage mensuel est converti en nombre de trains (pourcentage
    multiplié par les trains en retard). On additionne sur la période, puis on
    divise par le total.

    Args:
        df (pd.DataFrame): Données mensuelles nettoyées, avec les six colonnes de causes.

    Returns:
        pd.DataFrame: Une ligne par liaison et une colonne par cause (les noms
        courts de `CAUSE_COLUMNS`). Chaque ligne somme à 100. Elle vaut NaN si la
        liaison n'a aucun retard.

    Raises:
        KeyError: Si une colonne nécessaire manque.
    """
    _check_columns(df, LIAISON_KEY + list(CAUSE_COLUMNS))
    valid = filter_valid_rows(df)
    causes = list(CAUSE_COLUMNS)

    trains = valid[causes].mul(valid[COL_DELAYED], axis=0) / 100
    trains = pd.concat([valid[LIAISON_KEY], trains], axis=1)
    per_cause = trains.groupby(LIAISON_KEY, observed=True)[causes].sum()

    total = per_cause.sum(axis=1)
    profile = 100 * per_cause.div(total.where(total > 0), axis=0)
    logger.info("Profil des causes calculé : %d liaisons", len(profile))
    return profile.rename(columns=CAUSE_COLUMNS)
