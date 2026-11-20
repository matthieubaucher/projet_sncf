"""Page d'accueil."""

# Imports
import logging
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

from projet_sncf.business.map.home_kpis import TIERS, home_metrics, tier_counts
from projet_sncf.business.map.map_sncf import TIER_COLORS
from projet_sncf.business.analysis.reliability import get_reliability_table

# Constants
logger = logging.getLogger(__name__)

INTRO_TEXT = (
    "**Cher assureur,** RailInsight note la fiabilité de chaque liaison TGV à partir "
    "de l'historique des retards et des annulations. "
    "Visualisez les risques et les indicateurs de chaque liaison "
    "pour calibrer au mieux la prime d'assurance."
)

MAP_HINT = (
    "Ouvrez la page **Carte interactive** dans le menu pour explorer "
    "les liaisons et simuler une prime."
)


# Functions
@st.cache_data
def load_scores() -> pd.DataFrame:
    """Charge le tableau de fiabilité, gardé en cache par Streamlit.

    Returns:
        pd.DataFrame: Une ligne par liaison, voir `get_reliability_table`.
    """
    return get_reliability_table()


def hex_color(tier: str) -> str:
    """Donne la couleur d'un niveau au format hexadécimal.

    Args:
        tier (str): Niveau de fiabilité, une clé de `TIER_COLORS`.

    Returns:
        str: La couleur, par exemple "#d63031".
    """
    return "#{:02x}{:02x}{:02x}".format(*TIER_COLORS[tier])


def main() -> None:
    """Dessine la page d'accueil.

    Si les scores ne se chargent pas, la page affiche une erreur et s'arrête.

    Returns:
        None: La page est affichée par Streamlit.
    """
    try:
        st.set_page_config(page_title="Accueil", layout="wide")
    except st.errors.StreamlitAPIException:
        pass

    st.title("RailInsight")
    st.caption("Fiabilité des liaisons ferroviaires")
    st.markdown(INTRO_TEXT)
    st.info(MAP_HINT)

    try:
        scores = load_scores()
    except (FileNotFoundError, ValueError, KeyError) as error:
        logger.error("Chargement des scores impossible : %s", error)
        st.error(f"Impossible de charger les scores : {error}")
        st.stop()
    metrics = home_metrics(scores)

    columns = st.columns(4)
    columns[0].metric("Liaisons analysées", metrics["liaisons"])
    columns[1].metric("Liaisons à faible risque", metrics["plus_fiables"])
    columns[2].metric(
        "Perturbation moyenne", f"{100 * metrics['taux_perturbation']:.1f} %"
    )
    columns[3].metric("Historique couvert", f"{metrics['mois']} mois")

    st.subheader("Répartition des liaisons par niveau")
    counts = tier_counts(scores)
    chart = (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            x=alt.X("Niveau", sort=TIERS, axis=alt.Axis(labelAngle=0), title=None),
            y=alt.Y("Liaisons", title=None),
            color=alt.Color(
                "Niveau",
                scale=alt.Scale(domain=TIERS, range=[hex_color(t) for t in TIERS]),
                legend=None,
            ),
            tooltip=["Niveau", "Liaisons"],
        )
    )
    st.altair_chart(chart.properties(height=280), use_container_width=True)

    st.caption("Données : SNCF Open Data. Réseau ferré : SNCF Réseau (ODbL).")


# Main program
main()
