"""Tests du chargement des données (``projet_sncf.database.dataloader``).

Les premiers tests lisent le vrai fichier CSV (tests d'intégration). Les suivants utilisent un
petit tableau fabriqué à la main, pour vérifier chaque colonne ajoutée.
"""

import numpy as np
import pandas as pd

from projet_sncf.database.dataloader import (
    add_usefull_column,
    get_dataframe,
    get_initial_dataframe,
    typer_gares,
)
from projet_sncf.database.nettoyage import nettoyer

COLONNES_PRCT = [
    "prct Nombre de trains en retard à l'arrivée",
    "prct Nombre trains en retard > 15min",
    "prct Nombre trains en retard > 30min",
    "prct Nombre trains en retard > 60min",
    "prct annulation",
]


# --- get_dataframe : chargement et nettoyage en un seul appel ---------------------

def test_get_dataframe_charge_le_dataset():
    df = get_dataframe()

    # colonnes gardées ou supprimées
    assert "Service" in df.columns  # nécessaire pour définir une liaison
    assert "Commentaire annulations" not in df.columns
    assert "Commentaire retards au départ" not in df.columns
    assert "Commentaire retards à l'arrivée" not in df.columns

    # type Date
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])

    # catégories
    assert str(df["Gare de départ"].dtype) == "category"
    assert str(df["Gare d'arrivée"].dtype) == "category"

    # nombre de circulations valide
    assert (df["Nombre de circulations prévues"] > 0).all()

    # nouvelles colonnes bien créées et correctement
    for colonne in ["Temps", "Mois", "Saison"] + COLONNES_PRCT:
        assert colonne in df.columns
    assert (df["Temps"] >= 0).all()
    assert df["Mois"].between(1, 12).all()
    assert df["Saison"].between(-10, 30).all()
    # les NaN du nettoyage sont gardés : on vérifie seulement les valeurs remplies
    for colonne in COLONNES_PRCT:
        assert df[colonne].dropna().between(0, 1).all()


def test_get_dataframe_utilise_nettoyer():
    """Un seul appel renvoie exactement les lignes gardées par nettoyer()."""
    df = get_dataframe()
    df_propre, _ = nettoyer(get_initial_dataframe())
    assert len(df) == len(df_propre)
    pd.testing.assert_series_equal(
        df["Nombre trains en retard > 30min"], df_propre["Nombre trains en retard > 30min"]
    )


def test_get_dataframe_garde_les_nan_et_aucune_valeur_negative():
    df = get_dataframe()
    assert df["Nombre trains en retard > 30min"].isna().any()  # valeurs impossibles -> NaN
    assert not df.select_dtypes("number").lt(0).any().any()


def test_get_dataframe_ne_modifie_pas_les_comptages():
    df = get_dataframe()
    colonnes = ["Nombre de circulations prévues", "Nombre de trains annulés",
                "Nombre de trains en retard à l'arrivée"]
    assert not df[colonnes].isna().any().any()


# --- typer_gares et add_usefull_column, sur un petit tableau ------------------------

def petit_tableau():
    return pd.DataFrame({
        "Date": pd.to_datetime(["2018-01-01", "2019-07-01"]),
        "Gare de départ": ["PARIS LYON", "PARIS NORD"],
        "Gare d'arrivée": ["NICE VILLE", "LILLE"],
        "Nombre de circulations prévues": [200, 100],
        "Nombre de trains annulés": [10, 0],
        "Nombre de trains en retard à l'arrivée": [40, 25],
        "Nombre trains en retard > 15min": [20, 10],
        "Nombre trains en retard > 30min": [8, np.nan],  # NaN laissé par le nettoyage
        "Nombre trains en retard > 60min": [2, 1],
    })


def test_typer_gares():
    df = typer_gares(petit_tableau())
    assert str(df["Gare de départ"].dtype) == "category"
    assert str(df["Gare d'arrivée"].dtype) == "category"


def test_add_usefull_column_temps_mois_saison():
    df = add_usefull_column(petit_tableau())
    assert df["Temps"].tolist() == [0, 18]  # janvier 2018 = 0, juillet 2019 = 18 mois plus tard
    assert df["Mois"].tolist() == [1, 7]
    assert df["Saison"].tolist() == [5, 23]
    assert str(df["Temps"].dtype) == "int16"


def test_add_usefull_column_pourcentages():
    df = add_usefull_column(petit_tableau())
    assert df["prct annulation"].tolist() == [0.05, 0.0]
    assert df["prct Nombre de trains en retard à l'arrivée"].tolist() == [0.2, 0.25]
    assert df.loc[0, "prct Nombre trains en retard > 30min"] == 0.04


def test_add_usefull_column_ne_supprime_aucune_ligne():
    df = add_usefull_column(petit_tableau())
    assert len(df) == 2
    assert np.isnan(df.loc[1, "prct Nombre trains en retard > 30min"])


def test_add_usefull_column_ne_modifie_pas_les_donnees_d_origine():
    donnees = petit_tableau()
    add_usefull_column(donnees)
    assert "Temps" not in donnees.columns
