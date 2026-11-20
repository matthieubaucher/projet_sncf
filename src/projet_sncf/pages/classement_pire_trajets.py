"""Page de classement des trajets selon leurs retards ou leurs annulations."""

import textwrap

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

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
    """Charge les données mensuelles nettoyées de la SNCF."""
    return get_dataframe()


def construire_graphique_classement(
    classement: pd.DataFrame,
    titre_valeur: str,
    valeur_absolue: bool,
    mode_sombre: bool = False,
) -> go.Figure:
    """Construit les barres et joint les statistiques nécessaires à l'infobulle."""
    trajets = classement["trajet"].tolist()
    libelles = []
    for trajet in trajets:
        depart, arrivee = trajet.split(" → ", maxsplit=1)
        lignes_depart = textwrap.wrap(depart, width=25) or [depart]
        lignes_arrivee = textwrap.wrap(arrivee, width=25) or [arrivee]
        libelles.append(
            "<br>".join(
                [*lignes_depart, f"→ {lignes_arrivee[0]}", *lignes_arrivee[1:]]
            )
        )
    couleur_texte = "#f2f3f5" if mode_sombre else "#20242b"
    couleur_grille = "#3a3f49" if mode_sombre else "#d8dbe0"
    figure = go.Figure(
        go.Bar(
            x=classement["valeur"],
            y=classement["trajet"],
            orientation="h",
            marker_color="#c43d4d",
            customdata=classement[
                ["trains_concernes", "circulations_prevues", "taux"]
            ].to_numpy(),
            hoverinfo="none",
        )
    )
    figure.update_layout(
        template="plotly_dark" if mode_sombre else "plotly_white",
        height=max(420, 42 * len(classement) + 100),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": couleur_texte},
        xaxis_title=titre_valeur,
        yaxis_title=None,
        yaxis={
            "autorange": "reversed",
            "automargin": True,
            "tickmode": "array",
            "tickvals": trajets,
            "ticktext": libelles,
            "tickfont": {"color": couleur_texte},
        },
        xaxis={
            "tickformat": "," if valeur_absolue else "%",
            "gridcolor": couleur_grille,
            "zerolinecolor": couleur_grille,
        },
        margin={"l": 220, "r": 20, "t": 20, "b": 60},
    )
    return figure


def construire_html_graphique(figure: go.Figure, mode_sombre: bool = False) -> str:
    """Ajoute au graphique Plotly une infobulle contenant un camembert."""
    script_survol = """
const graphique = document.getElementById('{plot_id}');
const conteneur = graphique.parentElement;
document.body.style.margin = '0';
document.body.style.background = 'transparent';
conteneur.style.position = 'relative';
const infobulle = document.createElement('div');
infobulle.style.cssText = 'display:none;position:absolute;z-index:10;width:300px;padding:14px;border:1px solid __BORDURE__;background:__FOND__;color:__TEXTE__;border-radius:10px;box-shadow:0 6px 24px #0008;font:14px sans-serif;pointer-events:none;';
conteneur.appendChild(infobulle);
const nombre = new Intl.NumberFormat('fr-FR');
const pourcentage = new Intl.NumberFormat('fr-FR', {style:'percent',maximumFractionDigits:1});
graphique.on('plotly_hover', (evenement) => {
    const point = evenement.points[0];
    const [concernes, prevues, taux] = point.customdata;
    const part = prevues > 0 ? Math.max(0, Math.min(concernes / prevues, 1)) : 0;
    infobulle.replaceChildren();
    const titre = document.createElement('div');
    titre.textContent = point.y;
    titre.style.cssText = 'font-weight:600;margin-bottom:10px;';
    infobulle.appendChild(titre);
    const contenu = document.createElement('div');
    contenu.style.cssText = 'display:flex;align-items:center;gap:14px;';
    const camembert = document.createElement('div');
    camembert.style.cssText = `width:82px;height:82px;flex:none;border-radius:50%;background:conic-gradient(#c43d4d 0 ${part * 100}%,#596273 ${part * 100}% 100%);`;
    contenu.appendChild(camembert);
    const details = document.createElement('div');
    details.style.cssText = 'display:grid;gap:6px;';
    const tauxLigne = document.createElement('div');
    tauxLigne.textContent = `Part des circulations prévues : ${pourcentage.format(taux)}`;
    const trainsLigne = document.createElement('div');
    trainsLigne.textContent = `Trains concernés : ${nombre.format(concernes)}`;
    const prevuesLigne = document.createElement('div');
    prevuesLigne.textContent = `Circulations prévues : ${nombre.format(prevues)}`;
    details.append(tauxLigne, trainsLigne, prevuesLigne);
    contenu.appendChild(details);
    infobulle.appendChild(contenu);
    const rectangle = conteneur.getBoundingClientRect();
    const souris = evenement.event;
    const x = souris ? souris.clientX - rectangle.left + 14 : 14;
    const y = souris ? souris.clientY - rectangle.top + 14 : 14;
    infobulle.style.left = `${Math.max(8, Math.min(x, rectangle.width - 310))}px`;
    infobulle.style.top = `${Math.max(8, Math.min(y, rectangle.height - 150))}px`;
    infobulle.style.display = 'block';
});
graphique.on('plotly_unhover', () => { infobulle.style.display = 'none'; });
function envelopperTexte(texte, limite) {
    const lignes = [];
    let ligne = '';
    for (let mot of String(texte).split(/\\s+/)) {
        while (mot.length > limite) {
            if (ligne) { lignes.push(ligne); ligne = ''; }
            lignes.push(mot.slice(0, limite));
            mot = mot.slice(limite);
        }
        if (ligne && ligne.length + mot.length + 1 > limite) {
            lignes.push(ligne);
            ligne = mot;
        } else {
            ligne = ligne ? `${ligne} ${mot}` : mot;
        }
    }
    if (ligne) lignes.push(ligne);
    return lignes;
}
let derniereMiseEnPage = '';
function adapterGraphique() {
    const largeur = conteneur.clientWidth || document.documentElement.clientWidth;
    const caracteres = Math.max(14, Math.min(38, Math.floor((largeur - 310) / 8)));
    let nombreLignesMax = 1;
    const libelles = graphique.data[0].y.map((trajet) => {
        const [depart, arrivee] = String(trajet).split(' → ');
        if (arrivee === undefined) return trajet;
        const lignesDepart = envelopperTexte(depart, caracteres);
        const lignesArrivee = envelopperTexte(arrivee, caracteres);
        const lignes = [...lignesDepart, `→ ${lignesArrivee[0]}`, ...lignesArrivee.slice(1)];
        nombreLignesMax = Math.max(nombreLignesMax, lignes.length);
        return lignes.join('<br>');
    });
    const margeGauche = Math.min(300, Math.max(130, Math.round(largeur * 0.28)));
    const hauteur = Math.max(
        420,
        graphique.data[0].y.length * (25 + nombreLignesMax * 7) + 100,
    );
    const signature = `${caracteres}:${margeGauche}:${hauteur}`;
    if (signature === derniereMiseEnPage) return;
    derniereMiseEnPage = signature;
    Plotly.relayout(graphique, {
        'yaxis.ticktext': libelles,
        'margin.l': margeGauche,
        height: hauteur,
    }).then(() => {
        Plotly.Plots.resize(graphique);
        window.parent.postMessage({
            isStreamlitMessage: true,
            type: 'streamlit:setFrameHeight',
            height: hauteur,
        }, '*');
    });
}
new ResizeObserver(adapterGraphique).observe(conteneur);
window.addEventListener('resize', adapterGraphique);
requestAnimationFrame(adapterGraphique);
"""
    script_survol = script_survol.replace(
        "__BORDURE__", "#484d57" if mode_sombre else "#d1d5db"
    )
    script_survol = script_survol.replace(
        "__FOND__", "#17191f" if mode_sombre else "#ffffff"
    )
    script_survol = script_survol.replace(
        "__TEXTE__", "#f2f3f5" if mode_sombre else "#20242b"
    )
    return figure.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        post_script=script_survol,
        config={"responsive": True, "displayModeBar": False},
    )


def render_page(data: pd.DataFrame) -> None:
    """Affiche les contrôles du classement et le graphique associé aux données."""
    st.subheader("Classement des trajets les plus perturbés")

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
    value_title = (
        "Nombre de trains concernés"
        if is_absolute
        else "Part des circulations prévues"
    )
    try:
        mode_sombre = st.context.theme.type == "dark"
    except Exception:
        mode_sombre = False
    figure = construire_graphique_classement(
        ranking,
        value_title,
        is_absolute,
        mode_sombre,
    )
    components.html(
        construire_html_graphique(figure, mode_sombre),
        height=figure.layout.height,
        scrolling=False,
    )


def main() -> None:
    """Charge les données et affiche la page."""
    try:
        render_page(load_data())
    except (FileNotFoundError, KeyError, ValueError) as error:
        st.error(f"Impossible de calculer le classement : {error}")


if __name__ == "__main__":
    main()