"""Analyses du notebook d'exploration.

Contexte national, trafic et causes de retard.

Ce module regroupe les calculs des sections 1 et 2 du notebook
``notebooks/exploration_nettoyage.ipynb``. Les fonctions renvoient des
tableaux ; les graphiques sont tracés avec :mod:`projet_sncf.utils.graphiques`.
"""

import pandas as pd

COL_PREVUES = "Nombre de circulations prévues"
COL_RETARDS = "Nombre de trains en retard à l'arrivée"

#: Colonnes de causes de retard et leur nom court.
CAUSES = {
    "Prct retard pour causes externes": "externes",
    "Prct retard pour cause infrastructure": "infrastructure",
    "Prct retard pour cause gestion trafic": "gestion du trafic",
    "Prct retard pour cause matériel roulant": "matériel roulant",
    "Prct retard pour cause gestion en gare et réutilisation de matériel": (
        "gestion en gare"
    ),
    (
        "Prct retard pour cause prise en compte voyageurs "
        "(affluence, gestions PSH, correspondances)"
    ): "voyageurs (affluence)",
}


def moyennes_par_periode(
    data_regularite: pd.DataFrame, variables: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcule la moyenne des indicateurs par année et par mois.

    Les indicateurs nationaux sont moyennés par année, puis par mois de
    l'année.

    Args:
        data_regularite (pandas.DataFrame): Fichier national, avec une colonne
            ``Date``.
        variables (list[str]): Indicateurs à moyenner, par exemple
            ``["Régularité composite"]``.

    Returns:
        tuple[pandas.DataFrame, pandas.DataFrame]: Les moyennes par année
            (colonne ``Année``) et par mois (colonne ``Mois``).

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "Date": ["2024-01", "2024-02", "2025-01"],
        ...     "r": [80.0, 90.0, 100.0],
        ... })
        >>> par_annee, par_mois = moyennes_par_periode(df, ["r"])
        >>> par_annee["r"].tolist(), par_mois["r"].tolist()
        ([85.0, 100.0], [90.0, 90.0])
    """
    dates = pd.to_datetime(data_regularite["Date"])
    par_annee = (
        data_regularite.groupby(dates.dt.year.rename("Année"))[variables]
        .mean()
        .reset_index()
    )
    par_mois = (
        data_regularite.groupby(dates.dt.month.rename("Mois"))[variables]
        .mean()
        .reset_index()
    )
    return par_annee, par_mois


def circulations_par_annee(data: pd.DataFrame) -> pd.Series:
    """Additionne les circulations prévues par année.

    Args:
        data (pandas.DataFrame): Données AQST, avec ``Date`` au format
            ``AAAA-MM``.

    Returns:
        pandas.Series: Le nombre de circulations prévues de chaque année.
    """
    resultat = data.groupby(data["Date"].astype(str).str[:4])[
        COL_PREVUES
    ].sum()
    resultat.index.name = "Année"
    return resultat


def retards_par_cause(data: pd.DataFrame) -> pd.DataFrame:
    """Calcule les retards par cause pour 100 trains prévus, par mois.

    Calcule, pour chaque mois de l'année, le nombre de retards par cause pour
    100 trains prévus.

    La part de chaque cause est multipliée par le nombre de trains en retard,
    pour obtenir un nombre de retards par cause, puis rapportée aux
    circulations prévues du même mois.

    Args:
        data (pandas.DataFrame): Données AQST brutes. Les lignes sans
            circulation prévue sont ignorées.

    Returns:
        pandas.DataFrame: Une ligne par mois (1 à 12), une colonne par cause.
    """
    avec_trains = data[data[COL_PREVUES] > 0]
    mois = pd.to_datetime(avec_trains["Date"]).dt.month.rename("Mois")
    retards = (
        avec_trains[list(CAUSES)].mul(avec_trains[COL_RETARDS], axis=0) / 100
    )
    retards.columns = list(CAUSES.values())
    return (
        retards.groupby(mois)
        .sum()
        .div(avec_trains.groupby(mois)[COL_PREVUES].sum(), axis=0)
        * 100
    )


def comparer_periodes(
    par_mois: pd.DataFrame,
    mois_etudies: tuple[int, ...] = (6, 7),
    mois_reference: tuple[int, ...] = (3, 4),
) -> pd.Series:
    """Compare les retards par cause de deux périodes de l'année.

    Args:
        par_mois (pandas.DataFrame): Tableau renvoyé
            par :func:`retards_par_cause`.
        mois_etudies (tuple[int]): Mois étudiés. Par défaut juin et juillet.
        mois_reference (tuple[int]): Mois de référence. Par défaut mars et
            avril.

    Returns:
        pandas.Series: Pour chaque cause, le rapport entre les deux périodes (1
            = autant de retards), trié par ordre croissant.

    Example:
        >>> import pandas as pd
        >>> par_mois = pd.DataFrame({"a": [1.0, 2.0]}, index=[3, 6])
        >>> float(comparer_periodes(par_mois, (6,), (3,))["a"])
        2.0
    """
    return (
        par_mois.loc[list(mois_etudies)].mean()
        / par_mois.loc[list(mois_reference)].mean()
    ).sort_values()
