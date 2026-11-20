"""Tests du classement des trajets selon les retards et les taux d'annulation."""

import pandas as pd
import pytest

from projet_sncf.utils.route_ranking import (
    INDICATEUR_ANNULATIONS_ABSOLUES,
    INDICATEUR_ANNULATIONS_TAUX,
    INDICATEUR_RETARDS_ABSOLUS,
    INDICATEUR_RETARDS_TAUX,
    rank_worst_routes,
)


@pytest.fixture
def monthly_routes():
    return pd.DataFrame({
        "Date": pd.to_datetime([
            "2022-01-01", "2022-01-01", "2023-01-01", "2023-01-01", "2024-01-01",
            "2022-01-01", "2023-01-01",
        ]),
        "Gare de départ": ["A", "C", "A", "C", "A", "E", "E"],
        "Gare d'arrivée": ["B", "D", "B", "D", "B", "F", "F"],
        "Nombre de circulations prévues": [100, 100, 100, 100, 50, 1000, 1000],
        "Nombre de trains en retard à l'arrivée": [20, 50, 30, 10, 5, 100, 100],
        "Nombre de trains annulés": [10, 5, 30, 5, 1, 1, 1],
    })


def test_rank_worst_routes_by_delay_sums_counts_and_planned_services(monthly_routes):
    ranking = rank_worst_routes(monthly_routes, 2022, 2023, INDICATEUR_RETARDS_TAUX)

    assert ranking["trajet"].tolist() == ["C → D", "A → B", "E → F"]
    assert ranking["taux"].tolist() == pytest.approx([0.30, 0.25, 0.10])
    assert ranking.loc[0, "trains_concernes"] == 60
    assert ranking.loc[0, "circulations_prevues"] == 200


def test_rank_worst_routes_by_cancellations(monthly_routes):
    ranking = rank_worst_routes(monthly_routes, 2022, 2023, INDICATEUR_ANNULATIONS_TAUX)

    assert ranking["trajet"].tolist() == ["A → B", "C → D", "E → F"]
    assert ranking["taux"].tolist() == pytest.approx([0.20, 0.05, 0.001])


def test_rank_worst_routes_by_absolute_delay_count(monthly_routes):
    ranking = rank_worst_routes(monthly_routes, 2022, 2023, INDICATEUR_RETARDS_ABSOLUS)

    assert ranking["trajet"].tolist() == ["E → F", "C → D", "A → B"]
    assert ranking["valeur"].tolist() == [200, 60, 50]


def test_rank_worst_routes_by_absolute_cancellation_count(monthly_routes):
    ranking = rank_worst_routes(monthly_routes, 2022, 2023, INDICATEUR_ANNULATIONS_ABSOLUES)

    assert ranking["trajet"].tolist() == ["A → B", "C → D", "E → F"]
    assert ranking["valeur"].tolist() == [40, 10, 2]


def test_rank_worst_routes_filters_inclusive_period_and_limit(monthly_routes):
    ranking = rank_worst_routes(monthly_routes, 2024, 2024, INDICATEUR_RETARDS_TAUX, limit=1)

    assert ranking["trajet"].tolist() == ["A → B"]
    assert ranking.loc[0, "taux"] == pytest.approx(0.10)


def test_rank_worst_routes_filters_months_inclusively():
    data = pd.DataFrame({
        "Date": pd.to_datetime(["2022-01-01", "2022-02-01", "2022-03-01"]),
        "Gare de départ": ["A", "A", "A"],
        "Gare d'arrivée": ["B", "B", "B"],
        "Nombre de circulations prévues": [100, 100, 100],
        "Nombre de trains en retard à l'arrivée": [10, 50, 20],
        "Nombre de trains annulés": [1, 2, 3],
    })

    ranking = rank_worst_routes(
        data, "2022-02", "2022-03", INDICATEUR_RETARDS_ABSOLUS
    )

    assert ranking.loc[0, "trains_concernes"] == 70
    assert ranking.loc[0, "circulations_prevues"] == 200
    assert ranking.loc[0, "valeur"] == 70


def test_rank_worst_routes_returns_empty_for_period_without_rows(monthly_routes):
    ranking = rank_worst_routes(monthly_routes, 2018, 2019, INDICATEUR_RETARDS_TAUX)

    assert ranking.empty


def test_graphique_classement_ajoute_une_infobulle_avec_camembert():
    from projet_sncf.pages.classement_pire_trajets import (
        construire_graphique_classement,
        construire_html_graphique,
    )

    classement = pd.DataFrame({
        "trajet": ["A → B"],
        "valeur": [0.2],
        "taux": [0.2],
        "trains_concernes": [20],
        "circulations_prevues": [100],
    })
    figure = construire_graphique_classement(
        classement,
        "Part des circulations prévues",
        False,
    )
    html = construire_html_graphique(figure)

    assert tuple(figure.data[0].customdata[0]) == (20, 100, 0.2)
    assert "plotly_hover" in html
    assert "conic-gradient" in html
    assert "Trains concernés" in html
    assert "Circulations prévues" in html
    assert "background:#ffffff" in html
    assert "ResizeObserver" in html
    assert "window.addEventListener('resize'" in html
    assert "streamlit:setFrameHeight" in html


def test_graphique_classement_adapte_le_theme_et_wrappe_les_trajets():
    from projet_sncf.pages.classement_pire_trajets import construire_graphique_classement

    trajet = "SAINT GERVAIS LES BAINS → PARIS MONTPARNASSE"
    classement = pd.DataFrame({
        "trajet": [trajet],
        "valeur": [20],
        "taux": [0.2],
        "trains_concernes": [20],
        "circulations_prevues": [100],
    })

    figure = construire_graphique_classement(
        classement,
        "Nombre de trains concernés",
        True,
        mode_sombre=True,
    )
    libelle = figure.layout.yaxis.ticktext[0]

    assert figure.layout.font.color == "#f2f3f5"
    assert "<br>" in libelle
    assert libelle.replace("<br>", "").replace("→", "").replace(" ", "") == (
        trajet.replace("→", "").replace(" ", "")
    )


def _render_ranking_page(data):
    from projet_sncf.pages.classement_pire_trajets import render_page

    render_page(data)


def test_route_ranking_page_shows_period_slider_and_chart(monthly_routes):
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_function(_render_ranking_page, args=(monthly_routes,)).run()

    assert not app.exception
    assert app.select_slider[0].value == (
        pd.Timestamp("2022-01-01").date(),
        pd.Timestamp("2024-01-01").date(),
    )
    for metric_index in range(4):
        app.selectbox[0].select_index(metric_index).run()
        assert not app.exception


@pytest.mark.parametrize(
    ("start_period", "end_period", "metric", "limit", "message"),
    [
        ("2023-02", "2023-01", INDICATEUR_RETARDS_TAUX, 10, "période de début"),
        (2022, 2023, "Inconnu", 10, "Indicateur inconnu"),
        (2022, 2023, INDICATEUR_RETARDS_TAUX, 0, "limite"),
    ],
)
def test_rank_worst_routes_validates_arguments(
    monthly_routes, start_period, end_period, metric, limit, message
):
    with pytest.raises(ValueError, match=message):
        rank_worst_routes(monthly_routes, start_period, end_period, metric, limit)