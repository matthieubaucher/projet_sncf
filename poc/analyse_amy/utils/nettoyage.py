import numpy as np
import pandas as pd

COL_PREVUES = "Nombre de circulations prévues"
COL_ANNULES = "Nombre de trains annulés"
COL_RETARDS_ARRIVEE = "Nombre de trains en retard à l'arrivée"
COL_RETARD_30 = "Nombre trains en retard > 30min"
COL_RETARD_60 = "Nombre trains en retard > 60min"

COLONNES_COMMENTAIRES = [
    "Commentaire annulations",
    "Commentaire retards au départ",
    "Commentaire retards à l'arrivée",
]

# Moyennes calculées sur les seuls trains en retard : une valeur négative est impossible
RETARDS_MOYENS_TRAINS_EN_RETARD = [
    "Retard moyen des trains en retard à l'arrivée",
    "Retard moyen trains en retard > 15 (si liaison concurrencée par vol)",
]

# Moyennes calculées sur tous les trains : une valeur négative est invraisemblable
RETARDS_MOYENS_TOUS_LES_TRAINS = [
    "Retard moyen de tous les trains au départ",
    "Retard moyen de tous les trains à l'arrivée",
]


def nettoyer(data):
    """
    Applique les règles de nettoyage et renvoie (données nettoyées, rapport).

    Règles :
    1. suppression des trois colonnes commentaires ;
    2. conversion de Date et création des colonnes Mois et Année ;
    3. suppression des lignes sans circulation prévue (aucun taux calculable) ;
    4. nombre de trains en retard > 30 min : NaN s'il est négatif ou inférieur au nombre > 60 min ;
    5. retards moyens négatifs (trains en retard et tous les trains) : NaN.

    Le rapport est un dictionnaire qui compte les lignes supprimées et les cases passées à NaN.
    Les données d'origine ne sont pas modifiées.
    """
    df = data.copy()
    rapport = {"lignes_initiales": len(df)}

    # 1. Colonnes commentaires
    commentaires = [c for c in COLONNES_COMMENTAIRES if c in df.columns]
    df = df.drop(columns=commentaires)
    rapport["colonnes_supprimees"] = len(commentaires)

    # 2. Variables de temps
    df["Date"] = pd.to_datetime(df["Date"])
    df["Mois"] = df["Date"].dt.month
    df["Année"] = df["Date"].dt.year

    # 3. Lignes sans circulation prévue
    sans_circulation = df[COL_PREVUES] <= 0
    rapport["lignes_sans_circulation_supprimees"] = int(sans_circulation.sum())
    df = df.loc[~sans_circulation].copy()

    # 4. Retards de plus de 30 minutes
    invalide_30 = (df[COL_RETARD_30] < 0) | (df[COL_RETARD_60] > df[COL_RETARD_30])
    rapport[f"NaN : {COL_RETARD_30}"] = int(invalide_30.sum())
    df.loc[invalide_30, COL_RETARD_30] = np.nan

    # 5. Retards moyens négatifs
    for col in RETARDS_MOYENS_TRAINS_EN_RETARD + RETARDS_MOYENS_TOUS_LES_TRAINS:
        negatif = df[col] < 0
        rapport[f"NaN : {col}"] = int(negatif.sum())
        df.loc[negatif, col] = np.nan

    rapport["lignes_finales"] = len(df)
    rapport["cases_mises_a_nan"] = sum(v for k, v in rapport.items() if k.startswith("NaN"))
    return df.reset_index(drop=True), rapport