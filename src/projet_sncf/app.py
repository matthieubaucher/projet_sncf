"""Point d'entrée de l'application : le menu qui regroupe les pages."""

# Imports
from pathlib import Path
import streamlit as st

# Constants
BASE_DIR = Path(__file__).resolve().parent
PAGES_DIR = BASE_DIR / "pages"

## Icône train-front trouvée sur le site de Lucide (licence ISC)
ICON_FILE = BASE_DIR / "assets" / "train.svg"

LOGO_COLOR = "#f09600"


def build_logo() -> str:
    """Assemble le logo : l'icône de train du fichier SVG et le nom de l'application.

    Returns:
        str: Le logo au format SVG, prêt pour `st.logo`.
    """

    icon = ICON_FILE.read_text(encoding="utf-8")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="36" '
        'viewBox="0 0 200 36">'
        f'<g transform="translate(2 3) scale(1.25)">{icon}</g>'
        f'<text x="40" y="25" fill="{LOGO_COLOR}" font-family="sans-serif" '
        'font-size="21" font-weight="700">RailInsight</text>'
        "</svg>"
    )


def build_pages() -> dict:
    """Range les pages par thème, pour le menu de la barre latérale.

    Returns:
        dict: Le nom de chaque section et la liste de ses pages.
    """
    # Icônes du menu,mmaterial Symbols de  Streamlit
    return {
        "Général": [
            st.Page(
                PAGES_DIR / "home.py",
                title="Accueil",
                icon=":material/home:",
                default=True,
            ),
            st.Page(
                PAGES_DIR / "reliability_map.py",
                title="Carte interactive",
                icon=":material/map:",
            ),
        ],
        "Analyses": [
            st.Page(
                PAGES_DIR / "analyses_trajets.py",
                title="Analyse des perturbations",
                icon=":material/bar_chart:",
            ),
        ],
        "Prévisions": [
            st.Page(
                PAGES_DIR / "prediction_retard.py",
                title="Simulation de retard",
                icon=":material/timer:",
            ),
            st.Page(
                PAGES_DIR / "prevision_perturbations.py",
                title="Prévision des perturbations",
                icon=":material/query_stats:",
            ),
            st.Page(
                PAGES_DIR / "clustering_lignes.py",
                title="Clustering des modèles",
                icon=":material/hub:",
            ),
        ],
    }


def run_app() -> None:
    """Lance l'application : logo en haut, menu groupé, puis la page choisie."""
    st.logo(build_logo(), size="large")
    page = st.navigation(build_pages(), position="sidebar")
    st.sidebar.caption("Données : SNCF Open Data")
    page.run()


if __name__ == "__main__":
    run_app()
