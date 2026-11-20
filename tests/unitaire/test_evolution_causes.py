"""Tests de l'évolution mensuelle des causes de perturbation."""

import pandas as pd
import pytest

from projet_sncf.utils.evolution_causes import (
    CAUSES_PERTURBATION,
    CAUSE_NON_RENSEIGNEE,
    calculer_evolution_causes,
)


@pytest.fixture
def donnees_causes():
    donnees = pd.DataFrame({
        "Date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01", "2024-02-01"]),
        "Nombre de trains en retard à l'arrivée": [10, 30, 10, 60],
        "Gare de départ": ["A", "A", "C", "A"],
        "Gare d'arrivée": ["B", "B", "D", "B"],
    })
    for colonne in CAUSES_PERTURBATION:
        donnees[colonne] = 0.0
    externe, infrastructure = list(CAUSES_PERTURBATION)[:2]
    donnees.loc[0, externe] = 100
    donnees.loc[1, infrastructure] = 100
    donnees.loc[3, [externe, infrastructure]] = [50, 50]
    return donnees


def _afficher_vue_causes(donnees):
    from projet_sncf.pages.analyses_trajets import afficher_evolution_causes

    afficher_evolution_causes(donnees)


def test_calculer_evolution_causes_pondere_par_les_retards(donnees_causes):
    evolution = calculer_evolution_causes(donnees_causes, "2024-01", "2024-02")
    janvier = evolution[evolution["mois"] == pd.Timestamp("2024-01-01")].set_index("cause")
    fevrier = evolution[evolution["mois"] == pd.Timestamp("2024-02-01")].set_index("cause")

    assert janvier.loc["Causes externes", "pourcentage"] == pytest.approx(0.20)
    assert janvier.loc["Infrastructure", "pourcentage"] == pytest.approx(0.60)
    assert janvier.loc[CAUSE_NON_RENSEIGNEE, "pourcentage"] == pytest.approx(0.20)
    assert janvier["pourcentage"].sum() == pytest.approx(1)
    assert fevrier.loc["Causes externes", "pourcentage"] == pytest.approx(0.50)
    assert fevrier.loc["Infrastructure", "pourcentage"] == pytest.approx(0.50)
    assert fevrier["pourcentage"].sum() == pytest.approx(1)


def test_vue_causes_affiche_le_selecteur_et_la_courbe(donnees_causes):
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_function(_afficher_vue_causes, args=(donnees_causes,)).run()

    assert not app.exception
    assert app.subheader[0].value == "Évolution des causes de perturbation"
    assert app.select_slider[0].value == (
        pd.Timestamp("2024-01-01").date(),
        pd.Timestamp("2024-02-01").date(),
    )
    assert app.selectbox[0].options == ["Toutes les lignes", "A -> B", "C -> D"]
    app.selectbox[0].select_index(1).run()
    assert not app.exception


def test_calculer_evolution_causes_filtre_les_mois_inclusivement(donnees_causes):
    evolution = calculer_evolution_causes(donnees_causes, "2024-02", "2024-02")

    assert evolution["mois"].unique().tolist() == [pd.Timestamp("2024-02-01")]


def test_calculer_evolution_causes_filtre_un_trajet(donnees_causes):
    evolution = calculer_evolution_causes(
        donnees_causes,
        "2024-01",
        "2024-01",
        gare_depart="A",
        gare_arrivee="B",
    ).set_index("cause")

    assert evolution.loc["Causes externes", "pourcentage"] == pytest.approx(0.25)
    assert evolution.loc["Infrastructure", "pourcentage"] == pytest.approx(0.75)
    assert evolution["pourcentage"].sum() == pytest.approx(1)


def test_calculer_evolution_causes_rejette_une_periode_inversee(donnees_causes):
    with pytest.raises(ValueError, match="période de début"):
        calculer_evolution_causes(donnees_causes, "2024-03", "2024-02")