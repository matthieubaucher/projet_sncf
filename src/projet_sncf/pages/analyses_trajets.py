"""Page regroupant l'analyse saisonnière et le classement des trajets perturbés."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from projet_sncf.database.dataloader import get_dataframe
from projet_sncf.pages import classement_pire_trajets, saisonnalite
from projet_sncf.utils.evolution_causes import (
    CAUSES_PERTURBATION,
    calculer_evolution_causes,
)


VUE_SAISONNALITE = "Saisonnalité"
VUE_CLASSEMENT = "Classement des pires trajets"
VUE_CAUSES = "Évolution des causes"
TOUTES_LES_LIGNES = "Toutes les lignes"
NOMS_MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


@st.cache_data
def charger_donnees_causes() -> pd.DataFrame:
    """Charge les données mensuelles nettoyées de la SNCF pour l'analyse des causes."""
    return get_dataframe()


def raccourcir_intitules_causes(evolution: pd.DataFrame) -> pd.DataFrame:
    """Remplace les noms bruts des colonnes de causes par des libellés courts."""
    resultat = evolution.copy()
    intitules = resultat["cause"].replace(CAUSES_PERTURBATION)
    resultat["cause"] = intitules.str.replace("Prct retard pour ", "", regex=False)
    return resultat


def construire_graphique_causes(
    evolution: pd.DataFrame,
    titre: str = "Évolution des causes de retard",
) -> go.Figure:
    """Construit un graphique dont la légende isole une cause au double-clic."""
    figure = go.Figure()
    for cause, serie in evolution.groupby("cause", sort=False):
        figure.add_trace(
            go.Scatter(
                x=serie["mois"],
                y=serie["pourcentage"],
                name=cause,
                mode="lines+markers",
                hovertemplate=(
                    "%{x|%B %Y}<br>%{y:.1%}<extra>%{fullData.name}</extra>"
                ),
            )
        )

    figure.update_layout(
        height=420,
        title=titre,
        xaxis_title="Mois",
        yaxis_title="Part des retards à l'arrivée",
        yaxis={"tickformat": ".0%", "range": [0, 1]},
        legend={
            "title": "Cause",
            "itemclick": "toggle",
            "itemdoubleclick": "toggleothers",
        },
        margin={"l": 70, "r": 20, "t": 20, "b": 60},
    )
    return figure


def afficher_evolution_causes(donnees: pd.DataFrame | None = None) -> None:
    """Affiche l'évolution mensuelle pondérée des causes sur la période choisie."""
    if donnees is None:
        donnees = charger_donnees_causes()

    dates = pd.to_datetime(donnees["Date"], errors="coerce").dropna()
    if dates.empty:
        st.info("Aucune date exploitable dans les données.")
        return

    premier_mois = dates.min().to_period("M").to_timestamp().date()
    dernier_mois = dates.max().to_period("M").to_timestamp().date()
    options_mois = pd.date_range(premier_mois, dernier_mois, freq="MS").date.tolist()
    periode = st.select_slider(
        "Période des causes",
        options=options_mois,
        value=(premier_mois, dernier_mois),
        format_func=lambda mois: f"{NOMS_MOIS[mois.month - 1]} {mois.year}",
        key="periode_causes",
    )
    trajets = sorted(
        set(zip(
            donnees["Gare de départ"].astype(str),
            donnees["Gare d'arrivée"].astype(str),
        ))
    )
    options_trajets = [TOUTES_LES_LIGNES] + [
        f"{depart} -> {arrivee}" for depart, arrivee in trajets
    ]
    trajet_choisi = st.selectbox("Trajet", options_trajets, key="trajet_causes")
    if trajet_choisi == TOUTES_LES_LIGNES:
        gare_depart = gare_arrivee = None
        titre = "Évolution des causes de retard - Toutes les lignes"
    else:
        gare_depart, gare_arrivee = trajet_choisi.split(" -> ", maxsplit=1)
        titre = f"Évolution des causes de retard - {trajet_choisi}"

    evolution = calculer_evolution_causes(
        donnees,
        *periode,
        gare_depart=gare_depart,
        gare_arrivee=gare_arrivee,
    )
    if evolution.empty:
        st.info("Aucun retard exploitable pour cette période.")
        return
    evolution = raccourcir_intitules_causes(evolution)

    chart = construire_graphique_causes(evolution, titre)
    st.plotly_chart(chart, width="stretch")


def afficher_vue(vue: str) -> None:
    """Affiche la vue d'analyse sélectionnée."""
    if vue == VUE_SAISONNALITE:
        saisonnalite.main()
    elif vue == VUE_CLASSEMENT:
        classement_pire_trajets.main()
    elif vue == VUE_CAUSES:
        afficher_evolution_causes()


def main() -> None:
    """Permet de passer de la saisonnalité au classement des trajets."""
    vue = st.segmented_control(
        "Analyse",
        options=[VUE_SAISONNALITE, VUE_CLASSEMENT, VUE_CAUSES],
        default=VUE_SAISONNALITE,
    )
    if vue is not None:
        afficher_vue(vue)


if __name__ == "__main__":
    main()