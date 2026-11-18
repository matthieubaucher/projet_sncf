"""Reliability map page."""

# Imports
import json
import math
from pathlib import Path
import pandas as pd
import pydeck as pdk
import streamlit as st

from projet_sncf.business.map_sncf import (
    CONFIDENCE_LOW,
    MODE_EACH_DIRECTION,
    MODE_WORST_DIRECTION,
    PARIS_GROUP,
    TIER_COLORS,
    TIER_LESS,
    TIER_MIDDLE,
    TIER_MORE,
    disruption_frequency,
    display_name,
    filter_links,
    insurer_reading,
    least_reliable,
    link_details,
    prepare_links,
    pure_premium,
    station_options,
    station_points,
    summary_metrics,
)

# Constants
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "map"
SCORES_FILE = DATA_DIR / "scores_liaisons.csv"
STATIONS_FILE = DATA_DIR / "stations_coordonnees.csv"
NETWORK_FILE = DATA_DIR / "reseau_ferre_simplifie.json"
ROUTES_FILE = DATA_DIR / "trajets_liaisons.json"  # optional

TIERS = [TIER_MORE, TIER_MIDDLE, TIER_LESS]
ALL_STATIONS = "Toutes les gares"
DEFAULT_INDEMNITY = 30.0  # euros
NETWORK_WIDTH = 1.5
LABEL_SIZE = 14
LABEL_OUTLINE = 5
# colors for light and dark mode
THEME_COLORS = {
    "light": {
        "network": [105, 118, 135, 230],
        "label": [15, 15, 15, 255],
        "outline": [255, 255, 255, 255],
        "halo": [30, 30, 30, 255],
    },
    "dark": {
        "network": [150, 162, 180, 220],
        "label": [240, 240, 240, 255],
        "outline": [20, 20, 20, 255],
        "halo": [255, 255, 255, 255],
    },
}
CAUSE_COLOR = "#5f6b7a"
MAP_KEY = "reliability_map"
NETWORK_LAYER, HALO_LAYER, LINKS_LAYER, POINTS_LAYER, LABELS_LAYER = (
    "reseau",
    "selection",
    "liaisons",
    "gares",
    "noms",
)
INTRO_TEXT = (
    "Cet outil aide un assureur à repérer les liaisons TGV les plus intéressantes à couvrir. "
    "Chaque trait est une liaison, colorée selon sa fiabilité historique : plus elle est fiable, "
    "moins il y a de trajets annulés ou en retard à indemniser.\n\n"
    "**Comment l'utiliser :** cliquez sur une liaison pour lire sa recommandation, puis "
    "**simulez sa prime** en réglant l'indemnité moyenne dans la barre latérale à gauche."
)
METHOD_TEXT = (
    "- **Score de fiabilité** : 100 moins la part des trains prévus annulés ou en retard à "
    "l'arrivée, observée sur l'historique des données de régularité mensuelle des TGV.\n"
    "- **Prime pure estimée** : taux de perturbation observé sur la liaison × indemnité choisie. "
    "C'est le coût moyen attendu par trajet, si le passé se répète.\n"
    "- **Limites** : la durée des retards, les frais, la marge et le prix du billet ne sont pas "
    "pris en compte. Un score reposant sur moins de 24 mois est à confirmer."
)
MAP_HEIGHT = 640
VIEW = {"latitude": 46.4, "longitude": 2.6, "zoom": 4.7}
TOOLTIP = {
    "html": (
        "<b>{titre}</b><br/>Score : {score_txt}<br/>Niveau : {tiers}"
        "<br/>Historique : {mois_txt}"
        "<br/>Taux de perturbation : {perturbation_txt}"
        "<br/>Cause dominante des retards : {cause_txt}"
    ),
    "style": {"backgroundColor": "white", "color": "#222", "fontSize": "13px"},
}


# Functions
@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, list, dict]:
    """Read the data files."""
    scores = pd.read_csv(SCORES_FILE)
    stations = pd.read_csv(STATIONS_FILE, sep=";")
    with open(NETWORK_FILE, encoding="utf-8") as file:
        network = json.load(file)
    routes = {}
    if ROUTES_FILE.exists():
        with open(ROUTES_FILE, encoding="utf-8") as file:
            routes = json.load(file)
    return scores, stations, network, routes


def legend() -> str:
    """Color legend, as HTML."""
    items = []
    for tier, text in [
        (TIER_MORE, "Plus fiable"),
        (TIER_MIDDLE, "Intermédiaire"),
        (TIER_LESS, "Moins fiable"),
    ]:
        red, green, blue = TIER_COLORS[tier]
        items.append(
            f'<span style="color:rgb({red},{green},{blue});font-size:1.3em">●</span> {text}'
        )
    return " &nbsp;&nbsp; ".join(items)


def current_theme() -> str:
    """Dark or light mode."""
    try:
        theme = st.context.theme.type
    except Exception:  # old Streamlit version
        theme = None
    return "dark" if theme == "dark" else "light"


def percent(value: float | None, decimals: int = 1) -> str:
    """Format a share between 0 and 1 as a percentage."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n.d."
    return f"{100 * value:.{decimals}f} %"


def selected_link(state) -> dict | None:
    """The liaison clicked on the map, or None."""
    try:
        objects = state["selection"]["objects"].get(LINKS_LAYER, [])
    except (KeyError, TypeError, AttributeError):
        return None
    return objects[0] if objects else None


def show_details(scores: pd.DataFrame, selected: dict | None, indemnity: float) -> None:
    """Show the clicked liaison next to the map."""
    hint = "Cliquez sur une liaison de la carte pour voir si elle est intéressante à assurer."
    if selected is None:
        st.info(hint)
        return
    row, causes = link_details(
        scores, selected["depart"], selected["arrivee"], selected["service"]
    )
    if row is None:
        st.info(hint)
        return

    tier = row.get("tiers")
    red, green, blue = TIER_COLORS.get(tier, (150, 150, 150))
    st.markdown(f"#### {selected['titre']}")
    st.markdown(
        f'<span style="color:rgb({red},{green},{blue});font-size:1.3em">●</span> '
        f"{tier if isinstance(tier, str) else 'non classé'} · {row['Service']}",
        unsafe_allow_html=True,
    )
    kind, sentence = insurer_reading(tier if isinstance(tier, str) else None)
    getattr(st, kind)(sentence)
    st.write(disruption_frequency(row["taux_perturbation"]))
    st.metric(
        "Prime pure estimée",
        f"{pure_premium(row['taux_perturbation'], indemnity):.2f} € par trajet",
    )
    st.caption(
        f"{percent(row['taux_perturbation'])} de trajets perturbés sur {int(row['mois'])} mois "
        f"× {indemnity:.0f} € d'indemnité. Indicatif : hors frais et marge."
    )
    if row["confiance"] == CONFIDENCE_LOW:
        st.warning(f"Score à confirmer : seulement {int(row['mois'])} mois de données.")

    with st.expander("Détail du score"):
        st.metric("Score de fiabilité", f"{row['score']:.1f} / 100")
        st.write(f"**Historique :** {int(row['mois'])} mois")
        if "taux_annulation" in row:
            st.write(
                f"**Annulations :** {percent(row['taux_annulation'])} des trains prévus"
            )
        if "taux_retard" in row:
            st.write(
                f"**Retards à l'arrivée :** {percent(row['taux_retard'])} des trains circulés"
            )
        if "pires_mois_hors_chocs" in row:
            st.write(
                "**Concentration des perturbations :** "
                f"{percent(row['pires_mois_hors_chocs'])} dans les 10 % de pires mois "
                f"({percent(row.get('pires_mois_tous'))} avec les chocs nationaux)"
            )
        if "saisonnalite" in row:
            st.write(
                f"**Saisonnalité :** {row['saisonnalite']:.2f} (R² ajusté du mois)"
            )
        if not causes.empty:
            st.write("**Causes des retards (en %)**")
            chart = causes.round(1).rename_axis("Cause").reset_index(name="Part")
            st.bar_chart(
                chart,
                x="Cause",
                y="Part",
                sort="-Part",
                horizontal=True,
                color=CAUSE_COLOR,
                height=220,
            )
    st.caption(
        "Tracé sur les voies."
        if selected.get("trace") == "voie"
        else "Courbe entre les gares (hors réseau français)."
    )


def build_layers(
    network: list,
    shown: pd.DataFrame,
    points: pd.DataFrame,
    selected: dict | None,
    theme: str = "light",
) -> list:
    """Build the map layers, from bottom to top.

    Every layer needs an id for the selection. Text values are quoted twice,
    because pydeck reads them as JavaScript.
    """
    colors = THEME_COLORS[theme]
    layers = [
        pdk.Layer(
            "PathLayer",
            id=NETWORK_LAYER,
            data=pd.DataFrame({"path": network}),
            get_path="path",
            get_color=colors["network"],
            get_width=NETWORK_WIDTH,
            width_units="'pixels'",
        )
    ]
    if selected is not None:
        halo = shown[
            (shown["depart"] == selected["depart"])
            & (shown["arrivee"] == selected["arrivee"])
            & (shown["service"] == selected["service"])
        ]
        layers.append(
            pdk.Layer(
                "PathLayer",
                id=HALO_LAYER,
                data=halo,
                get_path="path",
                get_color=colors["halo"],
                get_width=7,
                width_units="'pixels'",
            )
        )
    layers += [
        pdk.Layer(
            "PathLayer",
            id=LINKS_LAYER,
            data=shown,
            get_path="path",
            get_color="color",
            get_width="width",
            width_units="'pixels'",
            pickable=True,
            auto_highlight=True,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            id=POINTS_LAYER,
            data=points,
            get_position="[lon, lat]",
            get_radius=4,
            radius_units="'pixels'",
            get_fill_color=[255, 255, 255, 255],
            get_line_color=[60, 60, 60, 255],
            stroked=True,
            line_width_min_pixels=1,
        ),
        pdk.Layer(
            "TextLayer",
            id=LABELS_LAYER,
            data=points[points["label"] != ""],
            get_position="[lon, lat]",
            get_text="label",
            get_size=LABEL_SIZE,
            get_color=colors["label"],
            get_pixel_offset=[0, -16],
            font_family="'Arial, sans-serif'",
            font_weight="'bold'",
            font_settings={"sdf": True},
            outline_width=LABEL_OUTLINE,
            outline_color=colors["outline"],
        ),
    ]
    return layers


def main() -> None:
    """Draw the page."""
    try:
        st.set_page_config(page_title="Carte de fiabilité", layout="wide")
    except st.errors.StreamlitAPIException:
        pass  # already set by the main app

    st.title("Carte de fiabilité des liaisons TGV")
    st.markdown(INTRO_TEXT)
    with st.expander("Méthode et limites"):
        st.markdown(METHOD_TEXT)

    missing = [
        f.name for f in (SCORES_FILE, STATIONS_FILE, NETWORK_FILE) if not f.exists()
    ]
    if missing:
        st.error(f"Fichiers manquants dans {DATA_DIR} : {', '.join(missing)}")
        st.stop()

    scores, stations, network, routes = load_data()

    with st.sidebar:
        st.header("Filtres")
        mode = st.radio(
            "Sens des liaisons",
            [MODE_WORST_DIRECTION, MODE_EACH_DIRECTION],
            help="« Le moins bon des deux sens » dessine un seul trait par paire de gares.",
        )
        links, unlocated = prepare_links(scores, stations, mode, routes)
        station = st.selectbox(
            "Gare",
            [ALL_STATIONS] + station_options(links),
            format_func=lambda s: (
                s if s in (ALL_STATIONS, PARIS_GROUP) else display_name(s)
            ),
        )
        services = st.multiselect(
            "Service",
            sorted(scores["Service"].unique()),
            default=sorted(scores["Service"].unique()),
        )
        tiers = st.multiselect("Niveau de fiabilité", TIERS, default=TIERS)
        low, high = float(math.floor(links["score"].min())), float(
            math.ceil(links["score"].max())
        )
        score_range = st.slider("Score de fiabilité", low, high, (low, high), step=0.5)
        st.header("Simulateur de prime")
        indemnity = st.number_input(
            "Indemnité moyenne par trajet perturbé (€)",
            min_value=0.0,
            value=DEFAULT_INDEMNITY,
            step=5.0,
            help="Montant que l'assureur verserait pour un trajet annulé ou en retard. À ajuster.",
        )

    shown = filter_links(
        links,
        services,
        tiers,
        station=None if station == ALL_STATIONS else station,
        score_range=score_range,
    )
    points = station_points(shown, stations, min_links_for_label=1)

    summary = summary_metrics(shown)
    if summary["liaisons"]:
        st.markdown(
            f"**{summary['liaisons']}** liaisons affichées · "
            f"**{summary['plus_fiables']}** à risque faible, à assurer en priorité · "
            f"**{summary['moins_fiables']}** à risque élevé"
        )
    else:
        st.markdown("**Aucune liaison ne correspond aux filtres.**")

    st.markdown(legend(), unsafe_allow_html=True)

    selected = selected_link(st.session_state.get(MAP_KEY))
    if (
        selected is not None
        and not (
            (shown["depart"] == selected["depart"])
            & (shown["arrivee"] == selected["arrivee"])
            & (shown["service"] == selected["service"])
        ).any()
    ):
        selected = None  # filtered out

    map_col, detail_col = st.columns([7, 3])
    with map_col:
        deck = pdk.Deck(
            layers=build_layers(network, shown, points, selected, current_theme()),
            initial_view_state=pdk.ViewState(**VIEW),
            map_provider=None,
            tooltip=TOOLTIP,
        )
        st.pydeck_chart(
            deck,
            height=MAP_HEIGHT,
            on_select="rerun",
            selection_mode="single-object",
            key=MAP_KEY,
        )
    with detail_col:
        show_details(scores, selected, indemnity)

    drawn_on_tracks = int((shown["trace"] == "voie").sum())
    st.caption(
        f"{len(shown)} liaisons affichées sur {len(links)} localisées, dont "
        f"{drawn_on_tracks} tracées sur les voies."
    )
    if unlocated:
        st.caption(
            f"{unlocated} liaisons ne sont pas dessinées, car l'une de leurs gares n'a pas de "
            "coordonnées (par exemple l'Italie, qui n'est pas une gare)."
        )
    if not routes:
        st.caption(
            "Fichier des tracés absent : toutes les liaisons sont dessinées en courbe."
        )

    with st.expander("Les 10 liaisons les moins fiables parmi celles affichées"):
        st.dataframe(least_reliable(shown, 10), hide_index=True)
    with st.expander("Voir toutes les liaisons affichées"):
        st.dataframe(least_reliable(shown, len(shown)), hide_index=True)


# Main program
main()
