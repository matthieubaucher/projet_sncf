"""Diagnostic de la qualité du jeu de données AQST.

Ce module regroupe les contrôles du notebook
``notebooks/02_exploration_nettoyage.ipynb`` (section 3) : valeurs manquantes,
doublons, valeurs impossibles et valeurs négatives, ainsi que les vérifications
faites après le nettoyage (section 4).

Les fonctions ne modifient jamais les données : elles comptent et renvoient des
tableaux.
"""

import logging

import pandas as pd

from projet_sncf.database.nettoyage import (
    COLONNES_COMMENTAIRES,
    verifier_colonnes,
)

logger = logging.getLogger(__name__)

COL_PREVUES = "Nombre de circulations prévues"
COL_ANNULES = "Nombre de trains annulés"
COL_RETARDS = "Nombre de trains en retard à l'arrivée"
COL_RETARD_30 = "Nombre trains en retard > 30min"
COL_RETARD_60 = "Nombre trains en retard > 60min"
COL_RETARD_MOYEN_15 = (
    "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)"
)

#: Textes qui représentent une valeur manquante sans être un vrai NaN.
VALEURS_VIDES = [
    "",
    " ",
    "NA",
    "N/A",
    "na",
    "n/a",
    "NULL",
    "null",
    "None",
    "none",
    "-",
    "NaN",
]

#: Clé d'une ligne sans le service : date, gare de départ, gare d'arrivée.
CLE_SANS_SERVICE = ["Date", "Gare de départ", "Gare d'arrivée"]


def compter_valeurs_manquantes(
    data: pd.DataFrame,
    exclure: list[str] | None = None,
    valeurs_vides: list[str] | None = None,
) -> int:
    """Compte les valeurs manquantes, faux vides compris.

    Les faux vides, comme « NA » ou « - », sont comptés comme manquants.

    Args:
        data (pandas.DataFrame): Données à contrôler.
        exclure (list[str] | None): Colonnes à ignorer. Par défaut, les
            colonnes commentaires.
        valeurs_vides (list[str] | None): Textes considérés comme vides. Par
            défaut :data:`VALEURS_VIDES`.

    Returns:
        int: Le nombre de valeurs manquantes.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"a": [1, None], "b": ["x", "NA"]})
        >>> compter_valeurs_manquantes(df)
        2
    """
    exclure = COLONNES_COMMENTAIRES if exclure is None else exclure
    valeurs_vides = VALEURS_VIDES if valeurs_vides is None else valeurs_vides
    colonnes = [c for c in data.columns if c not in exclure]
    faux_vides = data[colonnes].map(
        lambda x: isinstance(x, str) and x.strip() in valeurs_vides
    )
    return int((data[colonnes].isna() | faux_vides).sum().sum())


def chercher_doublons(
    data: pd.DataFrame, cle: list[str] | None = None
) -> tuple[dict[str, int | list[str]], pd.DataFrame]:
    """Cherche les lignes répétées, entièrement ou sur une clé.

    Args:
        data (pandas.DataFrame): Données à contrôler.
        cle (list[str] | None): Colonnes qui devraient identifier une ligne.
            Par défaut :data:`CLE_SANS_SERVICE`.

    Returns:
        tuple[dict, pandas.DataFrame]: Un résumé (lignes identiques, lignes en
            double sur la clé, mois et liaisons concernés, doublons restants si
            l'on ajoute le service) et les lignes en double sur la clé, triées.

    Raises:
        KeyError: Si une colonne de la clé est absente.
    """
    cle = CLE_SANS_SERVICE if cle is None else cle
    verifier_colonnes(data, cle)
    doublons = data[data.duplicated(cle, keep=False)].sort_values(cle)
    resume = {
        "Lignes entièrement identiques": int(data.duplicated().sum()),
        "Lignes en double sur la clé": len(doublons),
        "Mois concernés": sorted(doublons["Date"].unique().tolist()),
        "Liaisons concernées": doublons.groupby(cle[1:]).ngroups
        if len(cle) > 1
        else 0,
    }
    if "Service" in data.columns:
        resume["Doublons si l'on ajoute le service"] = int(
            data.duplicated(cle + ["Service"]).sum()
        )
    logger.info("Doublons sur la clé : %d lignes", len(doublons))
    return resume, doublons


def masques_valeurs_impossibles(data: pd.DataFrame) -> dict[str, pd.Series]:
    """Repère les valeurs impossibles d'après la définition de chaque colonne.

    Args:
        data (pandas.DataFrame): Données brutes de l'AQST.

    Returns:
        dict[str, pandas.Series]: Pour chaque contrôle, un masque booléen
            (``True`` = ligne en défaut).

    Raises:
        KeyError: Si une colonne nécessaire est absente.
    """
    verifier_colonnes(
        data,
        [
            COL_PREVUES,
            COL_ANNULES,
            COL_RETARDS,
            COL_RETARD_30,
            COL_RETARD_60,
            "Durée moyenne du trajet",
            "Retard moyen des trains en retard à l'arrivée",
            COL_RETARD_MOYEN_15,
        ],
    )
    prevues, annules = data[COL_PREVUES], data[COL_ANNULES]
    return {
        "Circulations prévues = 0": prevues == 0,
        "Durée moyenne du trajet = 0": data["Durée moyenne du trajet"] == 0,
        "Trains annulés > circulations prévues": annules > prevues,
        "Trains en retard > trains réellement circulés": data[COL_RETARDS]
        > prevues - annules,
        "Trains en retard > 30 min négatif": data[COL_RETARD_30] < 0,
        "Trains en retard > 60 min plus nombreux que > 30 min": data[
            COL_RETARD_60
        ]
        > data[COL_RETARD_30],
        "Retard moyen des trains en retard à l'arrivée négatif": data[
            "Retard moyen des trains en retard à l'arrivée"
        ]
        < 0,
        "Retard moyen des trains en retard > 15 min négatif": data[
            COL_RETARD_MOYEN_15
        ]
        < 0,
    }


def tableau_controles(masques: dict[str, pd.Series]) -> pd.DataFrame:
    """Résume des masques de contrôle en nombre et en part de lignes.

    Args:
        masques (dict[str, pandas.Series]): Masques renvoyés
            par :func:`masques_valeurs_impossibles`.

    Returns:
        pandas.DataFrame: Pour chaque contrôle, le nombre de lignes en défaut
            et leur part (en %).

    Example:
        >>> import pandas as pd
        >>> masques = {"test": pd.Series([True, False, False, False])}
        >>> float(tableau_controles(masques).loc["test", "part (%)"])
        25.0
    """
    return pd.DataFrame(
        {
            "lignes": {
                nom: int(masque.sum()) for nom, masque in masques.items()
            },
            "part (%)": {
                nom: round(masque.mean() * 100, 2)
                for nom, masque in masques.items()
            },
        }
    )


def compter_inclusions(
    masques: dict[str, pd.Series], reference: str
) -> pd.DataFrame:
    """Compte les lignes de chaque contrôle comprises dans la référence.

    Compte, pour chaque contrôle, combien de ses lignes font aussi partie du
    contrôle de référence.

    Sert à montrer que plusieurs problèmes touchent les mêmes lignes.

    Args:
        masques (dict[str, pandas.Series]): Masques renvoyés
            par :func:`masques_valeurs_impossibles`.
        reference (str): Nom du contrôle de référence, par exemple
            ``"Circulations prévues = 0"``.

    Returns:
        pandas.DataFrame: Pour chaque autre contrôle, le nombre de lignes et le
            nombre inclus dans la référence.

    Raises:
        KeyError: Si la référence n'est pas un des contrôles.
    """
    if reference not in masques:
        raise KeyError(f"Contrôle inconnu : {reference!r}")
    ref = masques[reference]
    return pd.DataFrame(
        {
            nom: {
                "lignes": int(m.sum()),
                f"dont « {reference} »": int((m & ref).sum()),
            }
            for nom, m in masques.items()
            if nom != reference
        }
    ).T


def negatifs_par_annee(
    data: pd.DataFrame, colonnes: list[str]
) -> pd.DataFrame:
    """Compte les valeurs négatives de chaque colonne, par année.

    Args:
        data (pandas.DataFrame): Données brutes, avec ``Date`` au format
            ``AAAA-MM``.
        colonnes (list[str]): Colonnes à examiner.

    Returns:
        pandas.DataFrame: Le nombre de valeurs négatives, une ligne par année
            et une colonne par colonne examinée.
    """
    annee = data["Date"].astype(str).str[:4]
    resultat = pd.DataFrame(
        {col: data[col].lt(0).groupby(annee).sum() for col in colonnes}
    )
    resultat.index.name = "Année"
    return resultat


def verifier_apres_nettoyage(df_propre: pd.DataFrame) -> pd.Series:
    """Vérifie qu'il ne reste aucune valeur impossible après le nettoyage.

    Args:
        df_propre (pandas.DataFrame): Données renvoyées
            par :func:`projet_sncf.database.nettoyage.nettoyer`.

    Returns:
        pandas.Series: Pour chaque contrôle, le nombre de lignes en défaut.
            Toutes les valeurs doivent être nulles.
    """
    prevues, annules = df_propre[COL_PREVUES], df_propre[COL_ANNULES]
    return pd.Series(
        {
            "Circulations prévues = 0": int((prevues == 0).sum()),
            "Durée moyenne du trajet = 0": int(
                (df_propre["Durée moyenne du trajet"] == 0).sum()
            ),
            "Trains annulés > circulations prévues": int(
                (annules > prevues).sum()
            ),
            "Trains en retard > trains circulés": int(
                (df_propre[COL_RETARDS] > prevues - annules).sum()
            ),
            "Valeurs négatives (toutes colonnes numériques)": int(
                df_propre.select_dtypes("number").lt(0).sum().sum()
            ),
            "Trains en retard > 60 min plus nombreux que > 30 min": int(
                (df_propre[COL_RETARD_60] > df_propre[COL_RETARD_30]).sum()
            ),
            "NaN dans prévues, annulés et retards à l'arrivée": int(
                df_propre[[COL_PREVUES, COL_ANNULES, COL_RETARDS]]
                .isna()
                .sum()
                .sum()
            ),
        },
        name="lignes",
    )
