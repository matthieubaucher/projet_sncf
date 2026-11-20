"""Tests unitaires de la page d'analyse de saisonnalité."""

import pandas as pd
import pytest

from projet_sncf.pages import saisonnalite as page


@pytest.fixture
def donnees_brutes():
    return pd.DataFrame({
        "Gare de départ": ["Paris"],
        "Gare d'arrivée": ["Lyon"],
        "Année": [2024],
        "Mois": [6],
        "Nombre de trains en retard au départ": [10],
        "Nombre de trains en retard à l'arrivée": [8],
    })


def test_load_monthly_data_renomme_les_colonnes(monkeypatch, donnees_brutes):
    monkeypatch.setattr(page, "get_dataframe", lambda: donnees_brutes)
    page.load_monthly_data.clear()

    data = page.load_monthly_data()

    assert data.loc[0, "gare_depart"] == "Paris"
    assert data.loc[0, "gare_arrive"] == "Lyon"
    assert data.loc[0, "annee"] == 2024
    assert data.loc[0, "mois"] == 6
    assert data.loc[0, "nb_retard_depart"] == 10
    assert data.loc[0, "nb_retard_arrive"] == 8
    assert "Gare de départ" not in data.columns


@pytest.mark.parametrize(
    ("analysis", "metric", "route", "month", "function_name", "expected_args"),
    [
        ("Évolution mensuelle", "Retards", ("Paris", "Lyon"), 6,
         "plot_monthly_lateness", ("Paris", "Lyon", 6)),
        ("Évolution mensuelle", "Retards", ("Paris", "Lyon"), None,
         "plot_monthly_lateness_all", ("Paris", "Lyon")),
        ("Évolution mensuelle", "Annulations", ("Paris", "Lyon"), 6,
         "plot_monthly_annulations", ("Paris", "Lyon", 6)),
        ("Évolution mensuelle", "Annulations", ("Paris", "Lyon"), None,
         "plot_month_annulations_all", ("Paris", "Lyon")),
        ("Heatmap saisonnière", "Retards", ("Paris", "Lyon"), None,
         "plot_heatmap_delay", ("Paris", "Lyon")),
        ("Heatmap saisonnière", "Retards", None, None,
         "plot_heatmap_global", ()),
        ("Heatmap saisonnière", "Annulations", ("Paris", "Lyon"), None,
         "plot_heatmap_annulations", ("Paris", "Lyon")),
        ("Heatmap saisonnière", "Annulations", None, None,
         "plot_heatmap_annulations_global", ()),
    ],
)
def test_build_plot_aiguille_vers_le_bon_graphique(
    monkeypatch, analysis, metric, route, month, function_name, expected_args
):
    data = pd.DataFrame()
    figure = object()
    calls = []

    def fake_plot(*args):
        calls.append(args)
        return figure

    monkeypatch.setattr(page, function_name, fake_plot)

    result = page.build_plot(data, analysis, metric, route, month)

    assert result is figure
    assert calls == [(data, *expected_args)]


def test_build_plot_exige_un_trajet_pour_une_evolution_mensuelle():
    with pytest.raises(ValueError, match="trajet doit être sélectionné"):
        page.build_plot(pd.DataFrame(), "Évolution mensuelle", "Retards", None, 6)