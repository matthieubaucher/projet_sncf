"""Tests unitaires des modules ``utils.exploration`` et ``utils.graphiques``."""

import matplotlib

matplotlib.use("Agg")  

import matplotlib.pyplot as plt  
import pandas as pd  
import pytest  
from utils.exploration import ( 
    CAUSES,
    circulations_par_annee,
    comparer_periodes,
    moyennes_par_periode,
    retards_par_cause,
)
from utils.graphiques import (  
    tracer_avant_apres,
    tracer_barres,
    tracer_evolution,
    tracer_matrices_confusion,
)


@pytest.fixture
def donnees():
    """Trois mois : mars et juin 2024 avec des trains, juin 2025 sans circulation."""
    df = pd.DataFrame({
        "Date": ["2024-03", "2024-06", "2025-06"],
        "Nombre de circulations prévues": [100, 200, 0],
        "Nombre de trains en retard à l'arrivée": [10, 40, 0],
    })
    for i, cause in enumerate(CAUSES):
        df[cause] = [50.0, 50.0, 0.0] if i < 2 else [0.0, 0.0, 0.0]
    return df


@pytest.fixture(autouse=True)
def fermer_figures():
    yield
    plt.close("all")


# --- exploration -----------------------------------------------------------------

def test_moyennes_par_periode():
    df = pd.DataFrame({"Date": ["2024-01", "2024-02", "2025-01"], "r": [80.0, 90.0, 100.0]})
    par_annee, par_mois = moyennes_par_periode(df, ["r"])
    assert par_annee["Année"].tolist() == [2024, 2025]
    assert par_mois["Mois"].tolist() == [1, 2]


def test_circulations_par_annee(donnees):
    resultat = circulations_par_annee(donnees)
    assert resultat.to_dict() == {"2024": 300, "2025": 0}
    assert resultat.index.name == "Année"


def test_retards_par_cause(donnees):
    resultat = retards_par_cause(donnees)
    assert resultat.index.tolist() == [3, 6]  # juin 2025 ignoré : aucun train prévu
    assert list(resultat.columns) == list(CAUSES.values())
    # mars : 10 retards dont 50 % « externes », pour 100 trains prévus -> 5 pour 100 trains
    assert resultat.loc[3, "externes"] == pytest.approx(5.0)
    assert resultat.loc[6, "externes"] == pytest.approx(10.0)
    assert resultat.loc[6, "matériel roulant"] == 0


def test_comparer_periodes(donnees):
    rapport = comparer_periodes(retards_par_cause(donnees), mois_etudies=(6,), mois_reference=(3,))
    assert rapport["externes"] == pytest.approx(2.0)
    assert rapport.is_monotonic_increasing or rapport.isna().any()


# --- graphiques --------------------------------------------------------------------

@pytest.mark.parametrize("horizontal", [False, True])
def test_tracer_barres(horizontal):
    fig = tracer_barres(pd.Series([1, 2], index=["a", "b"]), "Titre", horizontal=horizontal,
                        ligne_reference=1, ylim=(0, 3))
    ax = fig.axes[0]
    assert ax.get_title() == "Titre"
    assert len(ax.patches) == 2
    assert len(ax.lines) == 1  

def test_tracer_evolution():
    par_annee = pd.DataFrame({"Année": [2024, 2025], "a": [1, 2], "b": [3, 4]})
    par_mois = pd.DataFrame({"Mois": [1, 2], "a": [1, 2], "b": [3, 4]})
    fig = tracer_evolution(par_annee, par_mois, ["a", "b"])
    assert len(fig.axes) == 2
    assert all(len(ax.lines) == 2 for ax in fig.axes)


def test_tracer_matrices_confusion():
    fig = tracer_matrices_confusion([0, 1, 1, 0], [0, 1, 0, 0], "Exemple")
    assert fig._suptitle.get_text() == "Exemple"
    assert [ax.get_title() for ax in fig.axes] == ["Nombre de mois", "Part de chaque réalité"]


def test_tracer_avant_apres():
    avant = pd.DataFrame({"x": [1.0, -5.0, 3.0], "y": [2.0, 2.0, 2.0]})
    apres = pd.DataFrame({"x": [1.0, None, 3.0], "y": [2.0, 2.0, 2.0]})
    fig = tracer_avant_apres(avant, apres, ["x", "y"], "Avant / après")
    assert [ax.get_title() for ax in fig.axes] == ["x", "y"]
