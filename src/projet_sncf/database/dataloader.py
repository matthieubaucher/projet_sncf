"""Chargement des données de régularité mensuelle des TGV.

Un seul appel à :func:`get_dataframe` renvoie les données chargées, nettoyées
(avec :func:`projet_sncf.database.nettoyage.nettoyer`) et complétées par des colonnes utiles
aux analyses.

Les valeurs impossibles sont remplacées par NaN au lieu de supprimer la ligne : chaque
modèle écarte lui-même les lignes dont il ne peut pas se servir.
"""

import logging
from pathlib import Path

import pandas as pd

from projet_sncf.database.nettoyage import nettoyer

logger = logging.getLogger(__name__)

DATA_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "regularite-mensuelle-tgv-aqst.csv"
)

#: Températures moyennes en France, de janvier à décembre (colonne ``Saison``).
TEMPERATURES_MOYENNES = [5, 6, 9, 12, 16, 20, 23, 23, 20, 15, 10, 6]

#: Colonnes de comptage à rapporter au nombre de circulations prévues.
COLONNES_RETARD = [
    "Nombre de trains en retard à l'arrivée",
    "Nombre trains en retard > 15min",
    "Nombre trains en retard > 30min",
    "Nombre trains en retard > 60min",
]

COL_PREVUES = "Nombre de circulations prévues"

#: Premier mois des données : la colonne ``Temps`` compte les mois depuis cette date.
ORIGINE_DU_TEMPS = pd.Timestamp("2018-01-01")


def get_dataframe():
    """Charge, nettoie et complète les données.

    Returns:
        pandas.DataFrame: Les données prêtes pour les analyses.
    """
    df = get_initial_dataframe()
    df, _ = nettoyer(df)
    df = typer_gares(df)
    df = add_usefull_column(df)
    return df


def get_initial_dataframe():
    """Lit le fichier CSV brut de l'AQST.

    Returns:
        pandas.DataFrame: Les données brutes, sans aucune modification.
    """
    return pd.read_csv(DATA_PATH, sep=";")


def typer_gares(df):
    """Met les colonnes de gares au type ``category``, plus léger en mémoire.

    Args:
        df (pandas.DataFrame): Données avec les colonnes ``Gare de départ`` et ``Gare d'arrivée``.

    Returns:
        pandas.DataFrame: Une copie des données avec les gares en ``category``.

    Example:
        >>> import pandas as pd
        >>> df = typer_gares(pd.DataFrame({"Gare de départ": ["PARIS"], "Gare d'arrivée": ["LYON"]}))
        >>> str(df["Gare de départ"].dtype)
        'category'
    """
    df = df.copy()
    df["Gare de départ"] = df["Gare de départ"].astype("category")
    df["Gare d'arrivée"] = df["Gare d'arrivée"].astype("category")
    return df


def get_temps(annee, mois):
    """Compte le nombre de mois écoulés depuis :data:`ORIGINE_DU_TEMPS`.

    Args:
        annee (int | pandas.Series): Année.
        mois (int | pandas.Series): Mois (1 à 12).

    Returns:
        int | pandas.Series: Le nombre de mois depuis janvier 2018.

    Example:
        >>> get_temps(2019, 7)
        18
    """
    return (annee - ORIGINE_DU_TEMPS.year) * 12 + (mois - ORIGINE_DU_TEMPS.month)


def add_usefull_column(df):
    """Ajoute des colonnes utiles aux analyses.

    Colonnes ajoutées :

    - ``Temps`` : nombre de mois depuis janvier 2018 ;
    - ``Mois`` : mois de l'année (1 à 12) ;
    - ``Saison`` : température moyenne en France pour ce mois ;
    - ``prct <colonne>`` : chaque colonne de :data:`COLONNES_RETARD` divisée par le nombre
      de circulations prévues ;
    - ``prct annulation`` : trains annulés divisés par le nombre de circulations prévues.

    Aucune ligne n'est supprimée : un pourcentage vaut NaN quand la valeur d'origine a été
    jugée impossible par le nettoyage.

    Args:
        df (pandas.DataFrame): Données nettoyées, avec ``Date`` au format date.

    Returns:
        pandas.DataFrame: Une copie des données avec les nouvelles colonnes.
    """
    df_augmented = df.copy()

    # Temps : nombre de mois depuis janvier 2018 (voir get_temps)
    df_augmented["Temps"] = get_temps(df_augmented["Date"].dt.year, df_augmented["Date"].dt.month).astype("int16")

    # Mois et saison (température moyenne du mois)
    df_augmented["Mois"] = df_augmented["Date"].dt.month.astype("int8")
    saison = {mois: temperature for mois, temperature in enumerate(TEMPERATURES_MOYENNES, start=1)}
    df_augmented["Saison"] = df_augmented["Mois"].map(saison).astype("int8")

    # Pourcentages de retard et d'annulation
    for colonne in COLONNES_RETARD:
        df_augmented[f"prct {colonne}"] = df_augmented[colonne] / df_augmented[COL_PREVUES]
    df_augmented["prct annulation"] = df_augmented["Nombre de trains annulés"] / df_augmented[COL_PREVUES]

    logger.info("Colonnes utiles ajoutées : %d lignes", len(df_augmented))
    return df_augmented


def get_axes():
    """Liste les liaisons des données, sans tenir compte du sens.

    Une liaison A → B et la liaison B → A ne forment qu'un seul axe.

    Returns:
        list[tuple[str, str]]: Les paires de gares, chacune triée par ordre alphabétique.
    """
    df = get_dataframe()
    axes = (
        df[["Gare de départ", "Gare d'arrivée"]]
        .drop_duplicates()
        .apply(sorted, axis=1, result_type="expand")
        .drop_duplicates()
    )
    return list(axes.itertuples(index=False, name=None))
