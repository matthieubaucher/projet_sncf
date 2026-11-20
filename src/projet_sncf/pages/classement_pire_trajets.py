"""Page ranking routes with the highest delay or cancellation rates."""

import altair as alt
import pandas as pd
import streamlit as st

from projet_sncf.database.dataloader import get_dataframe
from projet_sncf.utils.route_ranking import rank_worst_routes


INDICATEUR_RETARDS_TAUX = "Retards à l'arrivée (taux)"
INDICATEUR_RETARDS_ABSOLUS = "Retards à l'arrivée (valeur absolue)"
INDICATEUR_ANNULATIONS_TAUX = "Annulations (taux)"
INDICATEUR_ANNULATIONS_ABSOLUES = "Annulations (valeur absolue)"
INDICATEURS_ABSOLUS = frozenset({INDICATEUR_RETARDS_ABSOLUS, INDICATEUR_ANNULATIONS_ABSOLUES})
NOMS_MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load cleaned SNCF monthly data."""
    return get_dataframe()


def render_page(data: pd.DataFrame) -> None:
    """Render route ranking controls and chart for the supplied data."""
    st.title("Classement des trajets les plus perturbés")

    dates = pd.to_datetime(data["Date"], errors="coerce").dropna()
    if dates.empty:
        st.info("Aucune date exploitable dans les données.")
        return

    premier_mois = dates.min().to_period("M").to_timestamp().date()
    dernier_mois = dates.max().to_period("M").to_timestamp().date()
    options_mois = pd.date_range(premier_mois, dernier_mois, freq="MS").date.tolist()
    periode = st.select_slider(
        "Période",
        options=options_mois,
        value=(premier_mois, dernier_mois),
        format_func=lambda mois: f"{NOMS_MOIS[mois.month - 1]} {mois.year}",
    )
    metric = st.selectbox(
        "Classer par",
        [
            INDICATEUR_RETARDS_TAUX,
            INDICATEUR_RETARDS_ABSOLUS,
            INDICATEUR_ANNULATIONS_TAUX,
            INDICATEUR_ANNULATIONS_ABSOLUES,
        ],
    )
    limit = st.slider("Nombre de trajets", min_value=5, max_value=20, value=10)

    ranking = rank_worst_routes(data, *periode, metric, limit)
    if ranking.empty:
        st.info("Aucune donnée exploitable pour cette période.")
        return

    is_absolute = metric in INDICATEURS_ABSOLUS
    value_format = "," if is_absolute else "%"
    value_title = (
        "Nombre de trains concernés"
        if is_absolute
        else "Part des circulations prévues"
    )
    value_tooltip_format = ",.0f" if is_absolute else ".1%"
    chart = (
        alt.Chart(ranking)
        .mark_bar(color="#c43d4d")
        .encode(
            x=alt.X("valeur:Q", title=value_title, axis=alt.Axis(format=value_format)),
            y=alt.Y("trajet:N", title=None, sort="-x"),
            tooltip=[
                alt.Tooltip("trajet:N", title="Trajet"),
                alt.Tooltip("valeur:Q", title=value_title, format=value_tooltip_format),
                alt.Tooltip("trains_concernes:Q", title="Trains concernés", format=","),
                alt.Tooltip("circulations_prevues:Q", title="Circulations prévues", format=","),
            ],
        )
        .properties(height=max(260, 30 * len(ranking)))
    )
    st.altair_chart(chart, width="stretch")


def main() -> None:
    """Load the data and display the page."""
    try:
        render_page(load_data())
    except (FileNotFoundError, KeyError, ValueError) as error:
        st.error(f"Impossible de calculer le classement : {error}")


if __name__ == "__main__":
    main()