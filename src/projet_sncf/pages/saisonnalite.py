"""Page d'analyse des variations mensuelles et de la saisonnalité."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from projet_sncf.database.dataloader import get_dataframe
from projet_sncf.utils.month_variations import (
    plotMonthAnnulations,
    plotMonthAnnulationsAll,
    plotMonthlyLateness,
    plotMonthlyLatenessAll,
)
from projet_sncf.utils.saisonality_view import (
    plot_heatmap_annulations,
    plot_heatmap_annulations_global,
    plot_heatmap_delay,
    plot_heatmap_global,
)

ALL_ROUTES = "Tous les trajets"
MONTH_NAMES = [
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
]
COLUMN_RENAMES = {
    "Gare de départ": "gare_depart",
    "Gare d'arrivée": "gare_arrive",
    "Année": "annee",
    "Mois": "mois",
    "Nombre de trains en retard au départ": "nb_retard_depart",
    "Nombre de trains en retard à l'arrivée": "nb_retard_arrive",
}


@st.cache_data
def load_monthly_data() -> pd.DataFrame:
    """Load SNCF data with the column names expected by plotting helpers."""
    return get_dataframe().rename(columns=COLUMN_RENAMES)


def build_plot(
    data: pd.DataFrame,
    analysis: str,
    metric: str,
    route: tuple[str, str] | None,
    month: int | None = None,
):
    """Choose and build the plot matching the selected options."""
    if analysis == "Évolution mensuelle":
        if route is None:
            raise ValueError(
                "Un trajet doit être sélectionné pour l'évolution mensuelle."
            )
        if metric == "Retards":
            return (
                plotMonthlyLatenessAll(data, *route)
                if month is None
                else plotMonthlyLateness(data, *route, month)
            )
        return (
            plotMonthAnnulationsAll(data, *route)
            if month is None
            else plotMonthAnnulations(data, *route, month)
        )

    if metric == "Retards":
        return (
            plot_heatmap_global(data)
            if route is None
            else plot_heatmap_delay(data, *route)
        )
    return (
        plot_heatmap_annulations_global(data)
        if route is None
        else plot_heatmap_annulations(data, *route)
    )


def main(afficher_titre: bool = True) -> None:
    """Display monthly and seasonal plots."""
    if afficher_titre:
        st.subheader("Variations mensuelles et saisonnalité")

    try:
        data = load_monthly_data()
    except (FileNotFoundError, KeyError, ValueError) as error:
        st.error(f"Impossible de charger les données : {error}")
        return

    routes = sorted(
        set(
            zip(
                data["gare_depart"].astype(str),
                data["gare_arrive"].astype(str),
            )
        )
    )
    if not routes:
        st.info("Aucun trajet disponible dans les données.")
        return

    col_analysis, col_metric, col_route = st.columns([1, 1, 2])
    with col_analysis:
        analysis = st.selectbox(
            "Analyse", ["Évolution mensuelle", "Heatmap saisonnière"]
        )
    with col_metric:
        metric = st.selectbox("Indicateur", ["Retards", "Annulations"])
    with col_route:
        route_labels = [ALL_ROUTES] + [
            f"{departure} -> {arrival}" for departure, arrival in routes
        ]
        selected_route = st.selectbox("Trajet", route_labels)

    route = None
    if selected_route != ALL_ROUTES:
        departure, arrival = selected_route.split(" -> ", maxsplit=1)
        route = (departure, arrival)

    if analysis == "Évolution mensuelle":
        month = st.selectbox(
            "Mois",
            [None, *range(1, 13)],
            format_func=lambda value: (
                "Tous les mois" if value is None else MONTH_NAMES[value - 1]
            ),
        )
        if route is None:
            st.info(
                "Sélectionnez un trajet pour afficher son évolution mensuelle."
            )
            return
    else:
        month = None

    figure = build_plot(data, analysis, metric, route, month)
    st.pyplot(figure, use_container_width=True)
    plt.close(figure)


if __name__ == "__main__":
    main()
