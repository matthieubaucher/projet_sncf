"""Home page."""

# Imports
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from projet_sncf.business.map.home_kpis import TIERS, home_metrics, tier_counts
from projet_sncf.business.map.map_sncf import TIER_COLORS

# Constants
SCORES_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "map" / "scores_liaisons.csv"
)

INTRO_TEXT = (
    "**Cher assureur,** RailInsight note la fiabilité de chaque liaison TGV à partir "
    "de l'historique des retards et des annulations. "
    "Vous voyez quelles liaisons assurer, lesquelles éviter, et vous simulez une prime."
)


# Functions
@st.cache_data
def load_scores() -> pd.DataFrame:
    """Read the scores."""
    return pd.read_csv(SCORES_FILE)


def hex_color(tier: str) -> str:
    """Color of a tier, as hex."""
    return "#{:02x}{:02x}{:02x}".format(*TIER_COLORS[tier])


def main() -> None:
    """Draw the page."""
    try:
        st.set_page_config(page_title="Accueil", layout="wide")
    except st.errors.StreamlitAPIException:
        pass  # already set by the main app

    st.title("RailInsight")
    st.caption("Fiabilité des liaisons ferroviaires")
    st.markdown(INTRO_TEXT)

    if not SCORES_FILE.exists():
        st.error(f"Fichier manquant : {SCORES_FILE.name}")
        return
    scores = load_scores()
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

    st.info(
        "Ouvrez la page **Carte** dans le menu pour voir les liaisons et simuler une prime."
    )
    st.caption("Données : SNCF Open Data. Réseau ferré : SNCF Réseau (ODbL).")


# Main program
main()
