"""Nettoyage du jeu de données « régularité mensuelle TGV » de l'AQST.

Ce module applique les règles de nettoyage décidées dans le notebook
``notebooks/exploration_nettoyage.ipynb`` (section 4), où chacune est
justifiée.

Chaque règle est une fonction séparée, qui peut être testée seule. La
fonction :func:`nettoyer` les enchaîne dans l'ordre et renvoie un rapport.

Les règles sont :

1. supprimer les colonnes commentaires (vides ou texte libre) ;
2. convertir la date et créer les colonnes ``Mois`` et ``Année`` ;
3. supprimer les lignes sans circulation prévue (aucun taux calculable) ;
4. remplacer par NaN le nombre de trains en retard de plus de 30 minutes
   lorsqu'il est négatif ou inférieur au nombre de plus de 60 minutes ;
5. remplacer par NaN les retards moyens négatifs.


"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

COL_DATE = "Date"
COL_PREVUES = "Nombre de circulations prévues"
COL_RETARD_30 = "Nombre trains en retard > 30min"
COL_RETARD_60 = "Nombre trains en retard > 60min"

COLONNES_COMMENTAIRES = [
    "Commentaire annulations",
    "Commentaire retards au départ",
    "Commentaire retards à l'arrivée",
]

#: Moyennes calculées sur les seuls trains en retard : une valeur négative est
#: impossible.
RETARDS_MOYENS_TRAINS_EN_RETARD = [
    "Retard moyen des trains en retard à l'arrivée",
    "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)",
]

#: Moyennes calculées sur tous les trains : une valeur négative est jugée non
#: fiable.
RETARDS_MOYENS_TOUS_LES_TRAINS = [
    "Retard moyen de tous les trains au départ",
    "Retard moyen de tous les trains à l'arrivée",
]

#: Colonnes indispensables au nettoyage.
COLONNES_REQUISES = [COL_DATE, COL_PREVUES, COL_RETARD_30, COL_RETARD_60]


def verifier_colonnes(df: pd.DataFrame, colonnes: list[str]) -> None:
    """Vérifie le type du tableau et la présence des colonnes.

    Vérifie qu'un tableau est un DataFrame et qu'il contient les colonnes
    demandées.

    Args:
        df (pandas.DataFrame): Tableau à vérifier.
        colonnes (list[str]): Noms des colonnes qui doivent être présentes.

    Raises:
        TypeError: Si ``df`` n'est pas un ``pandas.DataFrame``.
        KeyError: Si au moins une colonne est absente. Le message liste les
            colonnes manquantes.

    Example:
        >>> import pandas as pd
        >>> verifier_colonnes(pd.DataFrame({"a": [1]}), ["a"])
        >>> verifier_colonnes(pd.DataFrame({"a": [1]}), ["a", "b"])
        Traceback (most recent call last):
            ...
        KeyError: "Colonnes manquantes : ['b']"
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"Un pandas.DataFrame est attendu, pas {type(df).__name__}."
        )
    manquantes = [c for c in colonnes if c not in df.columns]
    if manquantes:
        raise KeyError(f"Colonnes manquantes : {manquantes}")


def supprimer_commentaires(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Supprime les colonnes commentaires présentes dans le tableau.

    Les commentaires sur les annulations et les retards au départ sont toujours
    vides ; ceux sur les retards à l'arrivée sont du texte libre, inexploitable
    dans un calcul. Les colonnes absentes sont ignorées, ce qui permet
    d'appeler la fonction sur des données déjà nettoyées.

    Args:
        df (pandas.DataFrame): Données à nettoyer.

    Returns:
        tuple[pandas.DataFrame, int]: Les données sans les colonnes
            commentaires, et le nombre de colonnes supprimées.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame(
        ...     {"Commentaire annulations": [None], "Date": ["2024-01"]}
        ... )
        >>> sans_commentaires, n = supprimer_commentaires(df)
        >>> list(sans_commentaires.columns), n
        (['Date'], 1)
    """
    presentes = [c for c in COLONNES_COMMENTAIRES if c in df.columns]
    logger.info("Colonnes commentaires supprimées : %d", len(presentes))
    return df.drop(columns=presentes), len(presentes)


def ajouter_variables_temps(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit ``Date`` et ajoute les colonnes ``Mois`` et ``Année``.

    Convertit la colonne ``Date`` en date et ajoute les colonnes ``Mois`` et
    ``Année``.

    Args:
        df (pandas.DataFrame): Données contenant une colonne ``Date`` au format
            ``AAAA-MM``.

    Returns:
        pandas.DataFrame: Les données avec ``Date`` au format date, et les
            colonnes ``Mois`` (1 à 12) et ``Année``.

    Raises:
        KeyError: Si la colonne ``Date`` est absente.
        ValueError: Si une date ne peut pas être lue.

    Example:
        >>> import pandas as pd
        >>> df = ajouter_variables_temps(pd.DataFrame({"Date": ["2024-07"]}))
        >>> int(df.loc[0, "Mois"]), int(df.loc[0, "Année"])
        (7, 2024)
    """
    verifier_colonnes(df, [COL_DATE])
    df = df.copy()
    df[COL_DATE] = pd.to_datetime(df[COL_DATE])
    df["Mois"] = df[COL_DATE].dt.month
    df["Année"] = df[COL_DATE].dt.year
    return df


def supprimer_lignes_sans_circulation(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    """Supprime les lignes sans circulation prévue.

    Une ligne est supprimée si son nombre de circulations prévues est nul ou
    négatif : aucun taux ne peut alors être calculé.

    Aucun taux ne peut être calculé sur ces lignes. Elles regroupent aussi,
    dans les données de l'AQST, les durées de trajet nulles et les lignes où
    les annulations ou les retards dépassent le nombre de trains prévus.

    Args:
        df (pandas.DataFrame): Données contenant la colonne ``Nombre de
            circulations prévues``.

    Returns:
        tuple[pandas.DataFrame, int]: Les données sans ces lignes, et le nombre
            de lignes supprimées.

    Raises:
        KeyError: Si la colonne des circulations prévues est absente.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"Nombre de circulations prévues": [100, 0, 50]})
        >>> gardees, n = supprimer_lignes_sans_circulation(df)
        >>> len(gardees), n
        (2, 1)
    """
    verifier_colonnes(df, [COL_PREVUES])
    sans_circulation = df[COL_PREVUES] <= 0
    n = int(sans_circulation.sum())
    logger.info("Lignes sans circulation prévue supprimées : %d", n)
    return df.loc[~sans_circulation].copy(), n


def invalider_retards_30_min(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Met à NaN les nombres de retards de plus de 30 min impossibles.

    Remplace par NaN les nombres de trains en retard de plus de 30 minutes
    impossibles.

    Une valeur est impossible si elle est négative (un nombre de trains ne peut
    pas l'être) ou si elle est inférieure au nombre de trains en retard de plus
    de 60 minutes (un train en retard de plus de 60 minutes l'est aussi de plus
    de 30 minutes).

    Args:
        df (pandas.DataFrame): Données contenant les colonnes ``Nombre trains
            en retard > 30min`` et ``Nombre trains en retard > 60min``.

    Returns:
        tuple[pandas.DataFrame, int]: Les données corrigées, et le nombre de
            cases remplacées.

    Raises:
        KeyError: Si l'une des deux colonnes est absente.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"Nombre trains en retard > 30min": [5, -2, 1],
        ...                    "Nombre trains en retard > 60min": [2, 0, 3]})
        >>> corrige, n = invalider_retards_30_min(df)
        >>> corrige["Nombre trains en retard > 30min"].tolist(), n
        ([5.0, nan, nan], 2)
    """
    verifier_colonnes(df, [COL_RETARD_30, COL_RETARD_60])
    df = df.copy()
    invalide = (df[COL_RETARD_30] < 0) | (
        df[COL_RETARD_60] > df[COL_RETARD_30]
    )
    n = int(invalide.sum())
    df[COL_RETARD_30] = df[COL_RETARD_30].astype(float)
    df.loc[invalide, COL_RETARD_30] = np.nan
    logger.info("Cases « > 30 min » remplacées par NaN : %d", n)
    return df, n


def invalider_retards_moyens_negatifs(
    df: pd.DataFrame, colonnes: list[str] | None = None
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Remplace par NaN les retards moyens négatifs.

    Pour les moyennes calculées sur les seuls trains en retard, une valeur
    négative est impossible. Pour celles calculées sur tous les trains, une
    valeur négative pourrait venir de trains en avance, mais la documentation
    de l'AQST ne permet pas de la distinguer d'une erreur : elle est jugée non
    fiable.

    Args:
        df (pandas.DataFrame): Données à corriger.
        colonnes (list[str] | None): Colonnes à traiter. Par défaut, les quatre
            colonnes de retard moyen concernées (trains en retard et tous les
            trains).

    Returns:
        tuple[pandas.DataFrame, dict[str, int]]: Les données corrigées, et le
            nombre de cases remplacées pour chaque colonne.

    Raises:
        KeyError: Si l'une des colonnes est absente.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"r": [3.0, -1.5, 0.0]})
        >>> corrige, n = invalider_retards_moyens_negatifs(df, ["r"])
        >>> corrige["r"].tolist(), n
        ([3.0, nan, 0.0], {'r': 1})
    """
    if colonnes is None:
        colonnes = (
            RETARDS_MOYENS_TRAINS_EN_RETARD + RETARDS_MOYENS_TOUS_LES_TRAINS
        )
    verifier_colonnes(df, colonnes)
    df = df.copy()
    remplacees = {}
    for col in colonnes:
        negatif = df[col] < 0
        remplacees[col] = int(negatif.sum())
        df.loc[negatif, col] = np.nan
        logger.info(
            "Cases « %s » remplacées par NaN : %d", col, remplacees[col]
        )
    return df, remplacees


def nettoyer(data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Applique toutes les règles de nettoyage.

    Renvoie les données nettoyées et un rapport des changements.

    Les données d'origine ne sont pas modifiées. Les règles sont appliquées
    dans cet ordre : suppression des commentaires, variables de temps,
    suppression des lignes sans circulation, invalidation des retards de plus
    de 30 minutes impossibles, invalidation des retards moyens négatifs.

    Args:
        data (pandas.DataFrame): Données brutes de l'AQST, lues avec
            ``pd.read_csv(..., sep=";")``.

    Returns:
        tuple[pandas.DataFrame, dict]: Les données nettoyées (index remis à
            zéro), et un rapport qui contient :

        - ``lignes_initiales`` et ``lignes_finales`` : nombre de lignes avant
          et après ;
        - ``colonnes_supprimees`` : nombre de colonnes commentaires
          supprimées ;
        - ``lignes_sans_circulation_supprimees`` : nombre de lignes
          supprimées ;
        - ``NaN : <colonne>`` : nombre de cases remplacées par NaN dans chaque
          colonne ;
        - ``cases_mises_a_nan`` : total des cases remplacées par NaN.

    Raises:
        TypeError: Si ``data`` n'est pas un ``pandas.DataFrame``.
        KeyError: Si une colonne nécessaire au nettoyage est absente.

    Example:
        >>> import pandas as pd
        >>> data = pd.DataFrame({
        ...     "Date": ["2024-01", "2024-02"],
        ...     "Nombre de circulations prévues": [100, 0],
        ...     "Nombre trains en retard > 30min": [-3, 0],
        ...     "Nombre trains en retard > 60min": [1, 0],
        ...     "Retard moyen des trains en retard à l'arrivée": [12.0, 0.0],
        ...     "Retard moyen trains en retard > 15 "
        ...     "(si liaison concurrencée par vol)": [30.0, 0.0],
        ...     "Retard moyen de tous les trains au départ": [-0.5, 0.0],
        ...     "Retard moyen de tous les trains à l'arrivée": [2.0, 0.0],
        ... })
        >>> df_propre, rapport = nettoyer(data)
        >>> rapport["lignes_finales"], rapport["cases_mises_a_nan"]
        (1, 2)
    """
    colonnes_requises = (
        COLONNES_REQUISES
        + RETARDS_MOYENS_TRAINS_EN_RETARD
        + RETARDS_MOYENS_TOUS_LES_TRAINS
    )
    verifier_colonnes(data, colonnes_requises)
    logger.info("Début du nettoyage : %d lignes, %d colonnes", *data.shape)
    rapport = {"lignes_initiales": len(data)}

    df, rapport["colonnes_supprimees"] = supprimer_commentaires(data)
    df = ajouter_variables_temps(df)
    df, rapport["lignes_sans_circulation_supprimees"] = (
        supprimer_lignes_sans_circulation(df)
    )

    df, n_30 = invalider_retards_30_min(df)
    rapport[f"NaN : {COL_RETARD_30}"] = n_30

    df, n_moyens = invalider_retards_moyens_negatifs(df)
    for col, n in n_moyens.items():
        rapport[f"NaN : {col}"] = n

    rapport["lignes_finales"] = len(df)
    rapport["cases_mises_a_nan"] = n_30 + sum(n_moyens.values())
    logger.info(
        "Fin du nettoyage : %d lignes gardées, %d cases mises à NaN",
        rapport["lignes_finales"],
        rapport["cases_mises_a_nan"],
    )
    return df.reset_index(drop=True), rapport
