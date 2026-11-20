"""Page d'accueil."""

# Imports
import logging
<<<<<<< HEAD
=======

>>>>>>> 1c6e835 (test(CI): refactor du fichier home.py pour PEP8)
import altair as alt
import pandas as pd
import streamlit as st

from projet_sncf.business.analysis.reliability import get_reliability_table
from projet_sncf.business.map.home_kpis import TIERS, home_metrics, tier_counts
from projet_sncf.business.map.map_sncf import TIER_COLORS

# Constants
logger = logging.getLogger(__name__)

INTRO_TEXT = (
    "**Cher assureur,** RailInsight note la fiabilité de chaque liaison "
    "TGV à partir "
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


def ink_color(tier: str) -> str:
    """Choisit la couleur du texte posé sur la barre d'un niveau.

    Args:
        tier (str): Niveau de fiabilité, une clé de `TIER_COLORS`.

    Returns:
        str: Du blanc sur une barre foncée, du noir sur une barre claire.
    """
    red, green, blue = TIER_COLORS[tier]
    luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255
    return "#ffffff" if luminance < 0.5 else "#111111"


def tier_chart(counts: pd.DataFrame) -> alt.LayerChart:
    """Dessine les barres des niveaux, avec le nombre et la part de liaisons.

    Args:
        counts (pd.DataFrame): Une ligne par niveau, avec les colonnes `Niveau`
            et `Liaisons`.

    Returns:
        alt.LayerChart: Les barres colorées, et au-dessus de chacune son texte,
        par exemple « 54 liaisons · 37 % ».
    """
    total = counts["Liaisons"].sum()
    counts = counts.assign(
        Texte=[f"{n} liaisons · {100 * n / total:.0f} %" for n in counts["Liaisons"]],
        Encre=[ink_color(tier) for tier in counts["Niveau"]],
    )
    base = alt.Chart(counts).encode(
        x=alt.X("Niveau", sort=TIERS, axis=alt.Axis(labelAngle=0), title=None),
        # De la place au-dessus des barres pour écrire le texte
        y=alt.Y(
            "Liaisons",
            title="Nombre de liaisons",
            scale=alt.Scale(domain=[0, counts["Liaisons"].max() * 1.2]),
        ),
    )
    bars = base.mark_bar().encode(
        color=alt.Color(
            "Niveau",
            scale=alt.Scale(domain=TIERS, range=[hex_color(t) for t in TIERS]),
            legend=None,
        ),
        tooltip=["Niveau", "Liaisons"],
    )
    # Texte dans la barre : même rendu en mode clair et sombre
    labels = base.mark_text(dy=16, fontSize=14, fontWeight="bold").encode(
        text="Texte",
        color=alt.Color("Encre", scale=None),
    )
    return bars + labels


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
            x=alt.X(
                "Niveau", sort=TIERS, axis=alt.Axis(labelAngle=0), title=None
            ),
            y=alt.Y("Liaisons", title=None),
            color=alt.Color(
                "Niveau",
                scale=alt.Scale(
                    domain=TIERS, range=[hex_color(t) for t in TIERS]
                ),
                legend=None,
            ),
            tooltip=["Niveau", "Liaisons"],
        )
    )

    st.caption("Données : SNCF Open Data. Réseau ferré : SNCF Réseau (ODbL).")


# Main program
main()
