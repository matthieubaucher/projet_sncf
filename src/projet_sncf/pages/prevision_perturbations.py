"""Page Streamlit « Prévision des perturbations ».

Pour chaque liaison TGV, la page affiche le risque qu'un mois soit **perturbé** : plus de
20 % des trains prévus annulés ou arrivés en retard.

L'assureur choisit le mois :

- le **mois prochain** : la vraie prévision ;
- un **mois passé** de la période de test (2025 et après) : ce que le modèle avait prévu,
  comparé à ce qui s'est réellement passé.

Les prévisions sont produites par le notebook ``poc/analyse_amy/notebooks/prevision.ipynb``
(dossier ``resultats/``) ; l'historique vient de
:func:`projet_sncf.database.dataloader.get_dataframe`.

Lancer la page seule, depuis la racine du projet :
``streamlit run src/projet_sncf/pages/prevision_perturbations.py``
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RACINE = Path(__file__).resolve().parents[3]
DOSSIER_RESULTATS = RACINE / "poc" / "analyse_amy" / "resultats"

CLE_LIAISON = ["Gare de départ", "Gare d'arrivée", "Service"]
SEUIL_PERTURBATION = 0.20

COL_PREVUES = "Nombre de circulations prévues"
COL_ANNULES = "Nombre de trains annulés"
COL_RETARDS = "Nombre de trains en retard à l'arrivée"

#: Colonnes des causes de retard et leur nom court.
CAUSES = {
    "Prct retard pour causes externes": "Causes externes (météo, obstacles…)",
    "Prct retard pour cause infrastructure": "Infrastructure (voies, signalisation)",
    "Prct retard pour cause gestion trafic": "Gestion du trafic",
    "Prct retard pour cause matériel roulant": "Matériel roulant",
    "Prct retard pour cause gestion en gare et réutilisation de matériel": "Gestion en gare",
    "Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)":
        "Voyageurs (affluence, correspondances)",
}

VERT, ORANGE, ROUGE = "#2e7d32", "#f9a825", "#c62828"


# --- calculs (sans Streamlit, testables) ------------------------------------------------

def charger_previsions(dossier=DOSSIER_RESULTATS):
    """Rassemble la prévision du mois prochain et celles des mois de test.

    Args:
        dossier (str | pathlib.Path): Dossier contenant ``predictions_liaisons.csv`` et
            ``predictions_test.csv``.

    Returns:
        pandas.DataFrame: Une ligne par liaison et par mois prévu, avec ``proba_perturbation``,
        ``prevision``, ``realite`` (vide pour le mois prochain), ``taux_reel`` et une colonne
        ``liaison`` lisible (« DÉPART → ARRIVÉE »).
    """
    dossier = Path(dossier)
    futur = pd.read_csv(dossier / "predictions_liaisons.csv", parse_dates=["mois_prevu"])
    test = pd.read_csv(dossier / "predictions_test.csv", parse_dates=["Date"])
    test = test.rename(columns={"Date": "mois_prevu", "prediction_foret": "prevision",
                                "taux_perturbation": "taux_reel"})
    colonnes = CLE_LIAISON + ["mois_prevu", "proba_perturbation", "prevision"]
    previsions = pd.concat([futur[colonnes], test[colonnes + ["realite", "taux_reel"]]], ignore_index=True)
    previsions["liaison"] = previsions["Gare de départ"] + " → " + previsions["Gare d'arrivée"]
    return previsions


def mois_disponibles(previsions):
    """Liste les mois que l'on peut choisir, du plus récent au plus ancien.

    Args:
        previsions (pandas.DataFrame): Tableau renvoyé par :func:`charger_previsions`.

    Returns:
        list[pandas.Timestamp]: Les mois prévus ; le premier est le mois prochain.
    """
    return sorted(previsions["mois_prevu"].unique(), reverse=True)


def previsions_du_mois(previsions, mois, service="Toutes"):
    """Garde les prévisions d'un mois, triées de la liaison la plus risquée à la moins risquée.

    Args:
        previsions (pandas.DataFrame): Tableau renvoyé par :func:`charger_previsions`.
        mois (pandas.Timestamp): Mois prévu.
        service (str): ``"Toutes"``, ``"National"`` ou ``"International"``.

    Returns:
        pandas.DataFrame: Les prévisions du mois.
    """
    vue = previsions[previsions["mois_prevu"] == mois]
    if service != "Toutes":
        vue = vue[vue["Service"] == service]
    return vue.sort_values("proba_perturbation", ascending=False).reset_index(drop=True)


def historique_liaisons(df):
    """Calcule, pour chaque liaison et chaque mois, le taux de perturbation et les causes de retard.

    Taux = (trains annulés + trains en retard à l'arrivée) / circulations prévues.

    Args:
        df (pandas.DataFrame): Données nettoyées, renvoyées par ``get_dataframe()``.

    Returns:
        pandas.DataFrame: Les colonnes de :data:`CLE_LIAISON`, ``Date``, ``taux``, le nombre de
        trains en retard et les colonnes de :data:`CAUSES`.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"Gare de départ": ["A"], "Gare d'arrivée": ["B"], "Service": ["National"],
        ...                    "Date": pd.to_datetime(["2025-01-01"]), COL_PREVUES: [100],
        ...                    COL_ANNULES: [5], COL_RETARDS: [20]})
        >>> float(historique_liaisons(df)["taux"].iloc[0])
        0.25
    """
    colonnes_causes = [c for c in CAUSES if c in df.columns]
    historique = df[CLE_LIAISON + ["Date", COL_RETARDS] + colonnes_causes].copy()
    for col in ["Gare de départ", "Gare d'arrivée"]:
        historique[col] = historique[col].astype(str)
    historique["taux"] = (df[COL_ANNULES] + df[COL_RETARDS]) / df[COL_PREVUES]
    return historique.sort_values("Date").reset_index(drop=True)


def _filtrer_liaison(historique, depart, arrivee, service):
    return historique[(historique["Gare de départ"] == depart) & (historique["Gare d'arrivée"] == arrivee)
                      & (historique["Service"] == service)].set_index("Date")


def indicateurs_liaison(historique, depart, arrivee, service, mois_prevu):
    """Résume l'historique d'une liaison avant le mois prévu.

    Args:
        historique (pandas.DataFrame): Tableau renvoyé par :func:`historique_liaisons`.
        depart (str): Gare de départ.
        arrivee (str): Gare d'arrivée.
        service (str): ``"National"`` ou ``"International"``.
        mois_prevu (pandas.Timestamp): Mois prévu.

    Returns:
        dict: Le taux du mois dernier, la moyenne des 12 derniers mois et le taux du même mois
        l'an dernier (``None`` si le mois est absent).
    """
    taux = _filtrer_liaison(historique, depart, arrivee, service)["taux"]
    passe = taux[taux.index < mois_prevu]
    douze_mois = passe[passe.index >= mois_prevu - pd.DateOffset(months=12)]
    return {
        "mois_dernier": taux.get(mois_prevu - pd.DateOffset(months=1)),
        "moyenne_12_mois": douze_mois.mean() if len(douze_mois) else None,
        "an_dernier": taux.get(mois_prevu - pd.DateOffset(months=12)),
    }


def causes_du_mois(historique, depart, arrivee, service, mois):
    """Donne la répartition des causes de retard d'une liaison pour un mois.

    Args:
        historique (pandas.DataFrame): Tableau renvoyé par :func:`historique_liaisons`.
        depart (str): Gare de départ.
        arrivee (str): Gare d'arrivée.
        service (str): ``"National"`` ou ``"International"``.
        mois (pandas.Timestamp): Mois voulu.

    Returns:
        tuple[str, pandas.Series | None]: L'état (``"ok"``, ``"aucun retard"``,
        ``"non renseignées"`` ou ``"mois absent"``) et, si l'état est ``"ok"``, la part de chaque
        cause (en %), de la plus fréquente à la moins fréquente, sans les causes à 0.

    Example:
        >>> import pandas as pd
        >>> h = pd.DataFrame({"Gare de départ": ["A"], "Gare d'arrivée": ["B"], "Service": ["National"],
        ...                   "Date": pd.to_datetime(["2025-01-01"]), COL_RETARDS: [10]})
        >>> for cause in CAUSES:
        ...     h[cause] = 0.0
        >>> causes_du_mois(h, "A", "B", "National", pd.Timestamp("2025-01-01"))[0]
        'non renseignées'
    """
    liaison = _filtrer_liaison(historique, depart, arrivee, service)
    if mois not in liaison.index:
        return "mois absent", None
    ligne = liaison.loc[mois]
    if ligne[COL_RETARDS] == 0:
        return "aucun retard", None
    parts = pd.to_numeric(ligne[[c for c in CAUSES if c in liaison.columns]], errors="coerce")
    if parts.isna().all() or parts.fillna(0).sum() == 0:
        return "non renseignées", None
    parts = parts.rename(CAUSES).fillna(0)
    return "ok", parts[parts > 0].sort_values(ascending=False)


def niveau_risque(proba):
    """Traduit une probabilité de perturbation en niveau de risque lisible.

    Args:
        proba (float): Probabilité de perturbation, entre 0 et 1.

    Returns:
        tuple[str, str]: Le libellé du niveau et sa couleur.

    Example:
        >>> niveau_risque(0.8)[0]
        'Élevé'
    """
    if proba >= 0.65:
        return "Élevé", ROUGE
    if proba >= 0.35:
        return "Moyen", ORANGE
    return "Faible", VERT


def _pourcent(valeur):
    return "–" if valeur is None or pd.isna(valeur) else f"{valeur:.0%}"


def _libelle_mois(mois, premier):
    texte = pd.Timestamp(mois).strftime("%m/%Y")
    return f"{texte} : mois prochain" if premier else f"{texte} : mois passé (comparer à la réalité)"


# --- affichage ----------------------------------------------------------------------------

def _graphique_classement(vue, nombre=15):
    top = vue.head(nombre).iloc[::-1]
    couleurs = [niveau_risque(p)[1] for p in top["proba_perturbation"]]
    textes = [f"{p:.0%}" for p in top["proba_perturbation"]]
    if top["realite"].notna().any():
        textes = [f"{t} · réel : {r}" for t, r in zip(textes, top["realite"])]
    fig = go.Figure(go.Bar(
        x=top["proba_perturbation"], y=top["liaison"], orientation="h", marker_color=couleurs,
        text=textes, textposition="outside",
        hovertemplate="%{y}<br>Probabilité : %{x:.0%}<extra></extra>",
    ))
    fig.add_vline(x=0.5, line_dash="dot", line_color="grey",
                  annotation_text="seuil « Perturbé »", annotation_position="top")
    fig.update_layout(xaxis=dict(tickformat=".0%", range=[0, 1.35], title="Probabilité de perturbation"),
                      height=max(350, 28 * len(top)), margin=dict(l=10, r=10, t=30, b=10))
    return fig


def _graphique_historique(historique, mois_prevu):
    fig = go.Figure(go.Scatter(
        x=historique.index, y=historique["taux"], mode="lines+markers",
        line=dict(color="#1565c0", width=2), marker=dict(size=5),
        hovertemplate="%{x|%m/%Y} : %{y:.0%}<extra></extra>",
    ))
    fig.add_hline(y=SEUIL_PERTURBATION, line_dash="dash", line_color=ROUGE,
                  annotation_text="20 % : mois perturbé", annotation_position="top left")
    fig.add_vline(x=mois_prevu, line_dash="dot", line_color="grey",
                  annotation_text="mois prévu", annotation_position="top left")
    fig.update_layout(title=dict(text="Taux de perturbation de la liaison, mois par mois", x=0, xanchor="left"),
                      yaxis=dict(tickformat=".0%", title="Taux de perturbation", rangemode="tozero"),
                      height=380, margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
    return fig


def _afficher_causes(titre, etat, parts):
    st.markdown(f"**{titre}**")
    if etat == "ok":
        st.markdown("\n".join(f"- {cause} : **{part:.0f} %**" for cause, part in parts.items()))
    elif etat == "aucun retard":
        st.markdown("Aucun train en retard ce mois-là.")
    elif etat == "mois absent":
        st.markdown("Pas de données pour ce mois.")
    else:
        st.markdown("Les causes n'étaient pas renseignées.")


def afficher_page(previsions, historique):
    """Affiche la page « Prévision des perturbations ».

    Args:
        previsions (pandas.DataFrame): Prévisions, renvoyées par :func:`charger_previsions`.
        historique (pandas.DataFrame): Historique, renvoyé par :func:`historique_liaisons`.
    """
    st.title("Prévision des perturbations")
    st.caption("Un mois est dit **perturbé** quand plus de 20 % des trains prévus sont annulés "
               "ou arrivent en retard. La probabilité est donnée par un modèle d'apprentissage "
               "entraîné sur l'historique de chaque liaison.")

    # Choix du mois et du type de liaison
    mois_liste = mois_disponibles(previsions)
    choix_gauche, choix_droite = st.columns([2, 1])
    mois = choix_gauche.selectbox("Mois à prévoir", mois_liste,
                                  format_func=lambda m: _libelle_mois(m, m == mois_liste[0]))
    service = choix_droite.radio("Liaisons", ["Toutes", "National", "International"], horizontal=True)
    st.caption("Le modèle a besoin des données du mois précédent : on ne peut pas prévoir plus loin "
               "que le mois prochain. Les mois passés montrent ce qu'il avait prévu, sans les avoir "
               "vus pendant son apprentissage, à côté de ce qui s'est réellement passé.")
    vue = previsions_du_mois(previsions, mois, service)
    passe = vue["realite"].notna().any()

    # Chiffres clés, chacun dans une carte
    perturbees = int((vue["prevision"] == "Perturbé").sum())
    if passe:
        reelles = int((vue["realite"] == "Perturbé").sum())
        justes = int((vue["prevision"] == vue["realite"]).sum())
        cartes = [
            ("Liaisons annoncées perturbées", f"{perturbees} / {len(vue)}", "d'après le modèle"),
            ("Liaisons réellement perturbées", f"{reelles} / {len(vue)}", "ce qui s'est passé"),
            ("Prévisions justes", f"{justes / len(vue):.0%}", f"{justes} liaisons sur {len(vue)}"),
        ]
    else:
        plus_risquee = vue.iloc[0]
        cartes = [
            ("Liaisons annoncées perturbées", f"{perturbees} / {len(vue)}", "probabilité supérieure à 50 %"),
            ("Liaisons annoncées normales", f"{len(vue) - perturbees} / {len(vue)}", "probabilité inférieure à 50 %"),
            ("Liaison la plus à risque", f"{plus_risquee['proba_perturbation']:.0%}",
             f"{plus_risquee['liaison']} ({plus_risquee['Service']})"),
        ]
    for colonne, (titre, valeur, detail) in zip(st.columns(3), cartes):
        with colonne.container(border=True):
            st.metric(titre, valeur)
            st.caption(detail)

    # Classement
    st.subheader("Les liaisons les plus à risque")
    st.plotly_chart(_graphique_classement(vue), width="stretch")
    with st.expander("Voir toutes les liaisons"):
        colonnes_tableau = {"liaison": "Liaison", "Service": "Service",
                            "proba_perturbation": "Probabilité", "prevision": "Prévision"}
        if passe:
            colonnes_tableau["realite"] = "Réalité"
        tableau = vue[list(colonnes_tableau)].rename(columns=colonnes_tableau)
        st.dataframe(tableau, hide_index=True, width="stretch",
                     column_config={"Probabilité": st.column_config.ProgressColumn(
                         format="percent", min_value=0, max_value=1)})

    # Zoom sur une liaison
    st.subheader("Zoom sur une liaison")
    noms = vue["liaison"] + " (" + vue["Service"] + ")"
    choix = st.selectbox("Choisir une liaison", noms)
    ligne = vue[noms == choix].iloc[0]
    depart, arrivee, service_liaison = ligne["Gare de départ"], ligne["Gare d'arrivée"], ligne["Service"]
    niveau, couleur = niveau_risque(ligne["proba_perturbation"])
    reel = ""
    if passe:
        verdict = "prévision juste ✓" if ligne["prevision"] == ligne["realite"] else "prévision fausse ✗"
        reel = (f"<div style='margin-top:0.4rem'>Réalité : <b>{ligne['realite']}</b> "
                f"({_pourcent(ligne['taux_reel'])} de trains perturbés) · {verdict}</div>")

    gauche, droite = st.columns([1, 2])
    with gauche:
        st.markdown(
            f"<div style='border-left:6px solid {couleur};padding:0.5rem 1rem;margin-bottom:1rem'>"
            f"<div style='font-size:0.9rem'>Prévision pour {mois.strftime('%m/%Y')}</div>"
            f"<div style='font-size:1.8rem;font-weight:600'>{ligne['prevision']}</div>"
            f"<div>Probabilité : <b>{ligne['proba_perturbation']:.0%}</b> · risque <b>{niveau.lower()}</b></div>"
            f"{reel}</div>", unsafe_allow_html=True)
        ind = indicateurs_liaison(historique, depart, arrivee, service_liaison, mois)
        st.markdown(f"- Mois dernier : **{_pourcent(ind['mois_dernier'])}** de trains perturbés\n"
                    f"- Moyenne sur 12 mois : **{_pourcent(ind['moyenne_12_mois'])}**\n"
                    f"- Même mois l'an dernier : **{_pourcent(ind['an_dernier'])}**")
    with droite:
        st.plotly_chart(_graphique_historique(_filtrer_liaison(historique, depart, arrivee, service_liaison),
                                              mois), width="stretch")

    st.subheader("D'où venaient les retards ?")
    mois_dernier = mois - pd.DateOffset(months=1)
    an_dernier = mois - pd.DateOffset(months=12)
    cause_gauche, cause_droite = st.columns(2)
    with cause_gauche:
        _afficher_causes(f"Mois dernier ({mois_dernier.strftime('%m/%Y')})",
                         *causes_du_mois(historique, depart, arrivee, service_liaison, mois_dernier))
    with cause_droite:
        _afficher_causes(f"Même mois l'an dernier ({an_dernier.strftime('%m/%Y')})",
                         *causes_du_mois(historique, depart, arrivee, service_liaison, an_dernier))


def main():
    """Charge les données et affiche la page."""
    from projet_sncf.database.dataloader import get_dataframe

    st.set_page_config(page_title="Prévision des perturbations", layout="wide")
    previsions = st.cache_data(charger_previsions)()
    historique = st.cache_data(lambda: historique_liaisons(get_dataframe()))()
    afficher_page(previsions, historique)


if __name__ == "__main__":
    main()
