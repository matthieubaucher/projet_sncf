"""Page Streamlit « Prévision des perturbations ».

Pour chaque liaison TGV, la page affiche le risque qu'un mois soit
**perturbé** : plus de 20 % des trains prévus annulés ou arrivés en retard.

L'assureur choisit le mois :

- le **mois prochain** : la vraie prévision ;
- un **mois passé** de la période de test (2025 et après) : ce que le modèle
  avait prévu, comparé à ce qui s'est réellement passé.

Les prévisions sont produites par le notebook ``notebooks/03_prevision.ipynb``,
qui les écrit dans ``data/predictions/`` ; l'historique vient
de :func:`projet_sncf.database.dataloader.get_dataframe`.

La fonction à appeler depuis l'application est :func:`page_prevision`.
Pour lancer la page seule, depuis la racine du projet ::

    streamlit run src/projet_sncf/pages/prevision_perturbations.py
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RACINE = Path(__file__).resolve().parents[3]
DOSSIER_RESULTATS = RACINE / "data" / "predictions"

CLE_LIAISON = ["Gare de départ", "Gare d'arrivée", "Service"]
SEUIL_PERTURBATION = 0.20

COL_PREVUES = "Nombre de circulations prévues"
COL_ANNULES = "Nombre de trains annulés"
COL_RETARDS = "Nombre de trains en retard à l'arrivée"

#: Colonnes des causes de retard et leur nom court.
CAUSES = {
    "Prct retard pour causes externes": "Causes externes (météo, obstacles…)",
    "Prct retard pour cause infrastructure": (
        "Infrastructure (voies, signalisation)"
    ),
    "Prct retard pour cause gestion trafic": "Gestion du trafic",
    "Prct retard pour cause matériel roulant": "Matériel roulant",
    "Prct retard pour cause gestion en gare et réutilisation de matériel": (
        "Gestion en gare"
    ),
    (
        "Prct retard pour cause prise en compte voyageurs "
        "(affluence, gestions PSH, correspondances)"
    ): "Voyageurs (affluence, correspondances)",
}

VERT, ORANGE, ROUGE = "#2e7d32", "#f9a825", "#c62828"


# --- calculs (sans Streamlit, testables)
# ------------------------------------------------


def charger_previsions(
    dossier: str | Path = DOSSIER_RESULTATS,
) -> pd.DataFrame:
    """Rassemble la prévision du mois prochain et celles des mois de test.

    Args:
        dossier (str | pathlib.Path): Dossier contenant
            ``predictions_liaisons.csv`` et ``predictions_test.csv``.

    Returns:
        pandas.DataFrame: Une ligne par liaison et par mois prévu, avec
            ``proba_perturbation``, ``prevision``, ``realite`` (vide pour le
            mois prochain), ``taux_reel`` et une colonne ``liaison`` lisible
            (« DÉPART → ARRIVÉE »).
    """
    dossier = Path(dossier)
    futur = pd.read_csv(
        dossier / "predictions_liaisons.csv", parse_dates=["mois_prevu"]
    )
    test = pd.read_csv(dossier / "predictions_test.csv", parse_dates=["Date"])
    test = test.rename(
        columns={
            "Date": "mois_prevu",
            "prediction_foret": "prevision",
            "taux_perturbation": "taux_reel",
        }
    )
    colonnes = CLE_LIAISON + ["mois_prevu", "proba_perturbation", "prevision"]
    previsions = pd.concat(
        [futur[colonnes], test[colonnes + ["realite", "taux_reel"]]],
        ignore_index=True,
    )
    previsions["liaison"] = (
        previsions["Gare de départ"] + " → " + previsions["Gare d'arrivée"]
    )
    return previsions


def mois_disponibles(previsions: pd.DataFrame) -> list[pd.Timestamp]:
    """Liste les mois que l'on peut choisir, du plus récent au plus ancien.

    Args:
        previsions (pandas.DataFrame): Tableau renvoyé
            par :func:`charger_previsions`.

    Returns:
        list[pandas.Timestamp]: Les mois prévus ; le premier est le mois
            prochain.
    """
    return sorted(previsions["mois_prevu"].unique(), reverse=True)


def previsions_du_mois(
    previsions: pd.DataFrame, mois: pd.Timestamp, service: str = "Toutes"
) -> pd.DataFrame:
    """Garde les prévisions d'un mois, de la plus risquée à la moins.

    Args:
        previsions (pandas.DataFrame): Tableau renvoyé
            par :func:`charger_previsions`.
        mois (pandas.Timestamp): Mois prévu.
        service (str): ``"Toutes"``, ``"National"`` ou ``"International"``.

    Returns:
        pandas.DataFrame: Les prévisions du mois.
    """
    vue = previsions[previsions["mois_prevu"] == mois]
    if service != "Toutes":
        vue = vue[vue["Service"] == service]
    return vue.sort_values("proba_perturbation", ascending=False).reset_index(
        drop=True
    )


def historique_liaisons(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule le taux de perturbation et les causes, par liaison et mois.

    Calcule, pour chaque liaison et chaque mois, le taux de perturbation et les
    causes de retard.

    Taux = (trains annulés + trains en retard à l'arrivée) / circulations
    prévues.

    Args:
        df (pandas.DataFrame): Données nettoyées, renvoyées par
            ``get_dataframe()``.

    Returns:
        pandas.DataFrame: Les colonnes de :data:`CLE_LIAISON`, ``Date``,
            ``taux``, le nombre de trains en retard et les colonnes
            de :data:`CAUSES`.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "Gare de départ": ["A"],
        ...     "Gare d'arrivée": ["B"],
        ...     "Service": ["National"],
        ...     "Date": pd.to_datetime(["2025-01-01"]),
        ...     COL_PREVUES: [100],
        ...     COL_ANNULES: [5],
        ...     COL_RETARDS: [20],
        ... })
        >>> float(historique_liaisons(df)["taux"].iloc[0])
        0.25
    """
    colonnes_causes = [c for c in CAUSES if c in df.columns]
    historique = df[
        CLE_LIAISON + ["Date", COL_RETARDS] + colonnes_causes
    ].copy()
    for col in ["Gare de départ", "Gare d'arrivée"]:
        historique[col] = historique[col].astype(str)
    historique["taux"] = (df[COL_ANNULES] + df[COL_RETARDS]) / df[COL_PREVUES]
    return historique.sort_values("Date").reset_index(drop=True)


def _filtrer_liaison(
    historique: pd.DataFrame, depart: str, arrivee: str, service: str
) -> pd.DataFrame:
    """Garde les lignes d'une liaison (départ, arrivée, service)."""
    return historique[
        (historique["Gare de départ"] == depart)
        & (historique["Gare d'arrivée"] == arrivee)
        & (historique["Service"] == service)
    ].set_index("Date")


def indicateurs_liaison(
    historique: pd.DataFrame,
    depart: str,
    arrivee: str,
    service: str,
    mois_prevu: pd.Timestamp,
) -> dict[str, float | None]:
    """Résume l'historique d'une liaison avant le mois prévu.

    Args:
        historique (pandas.DataFrame): Tableau renvoyé
            par :func:`historique_liaisons`.
        depart (str): Gare de départ.
        arrivee (str): Gare d'arrivée.
        service (str): ``"National"`` ou ``"International"``.
        mois_prevu (pandas.Timestamp): Mois prévu.

    Returns:
        dict: Le taux du mois dernier, la moyenne des 12 derniers mois et le
            taux du même mois l'an dernier (``None`` si le mois est absent).
    """
    taux = _filtrer_liaison(historique, depart, arrivee, service)["taux"]
    passe = taux[taux.index < mois_prevu]
    douze_mois = passe[passe.index >= mois_prevu - pd.DateOffset(months=12)]
    return {
        "mois_dernier": taux.get(mois_prevu - pd.DateOffset(months=1)),
        "moyenne_12_mois": douze_mois.mean() if len(douze_mois) else None,
        "an_dernier": taux.get(mois_prevu - pd.DateOffset(months=12)),
    }


def causes_du_mois(
    historique: pd.DataFrame,
    depart: str,
    arrivee: str,
    service: str,
    mois: pd.Timestamp,
) -> tuple[str, pd.Series | None]:
    """Donne la répartition des causes de retard d'une liaison pour un mois.

    Args:
        historique (pandas.DataFrame): Tableau renvoyé
            par :func:`historique_liaisons`.
        depart (str): Gare de départ.
        arrivee (str): Gare d'arrivée.
        service (str): ``"National"`` ou ``"International"``.
        mois (pandas.Timestamp): Mois voulu.

    Returns:
        tuple[str, pandas.Series | None]: L'état (``"ok"``, ``"aucun retard"``,
            ``"non renseignées"`` ou ``"mois absent"``) et, si l'état est
            ``"ok"``, la part de chaque cause (en %), de la plus fréquente à la
            moins fréquente, sans les causes à 0.

    Example:
        >>> import pandas as pd
        >>> h = pd.DataFrame({
        ...     "Gare de départ": ["A"],
        ...     "Gare d'arrivée": ["B"],
        ...     "Service": ["National"],
        ...     "Date": pd.to_datetime(["2025-01-01"]),
        ...     COL_RETARDS: [10],
        ... })
        >>> for cause in CAUSES:
        ...     h[cause] = 0.0
        >>> mois = pd.Timestamp("2025-01-01")
        >>> causes_du_mois(h, "A", "B", "National", mois)[0]
        'non renseignées'
    """
    liaison = _filtrer_liaison(historique, depart, arrivee, service)
    if mois not in liaison.index:
        return "mois absent", None
    ligne = liaison.loc[mois]
    if ligne[COL_RETARDS] == 0:
        return "aucun retard", None
    parts = pd.to_numeric(
        ligne[[c for c in CAUSES if c in liaison.columns]], errors="coerce"
    )
    if parts.isna().all() or parts.fillna(0).sum() == 0:
        return "non renseignées", None
    parts = parts.rename(CAUSES).fillna(0)
    return "ok", parts[parts > 0].sort_values(ascending=False)


def niveau_risque(proba: float) -> tuple[str, str]:
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


# --- phrases d'interprétation (sans Streamlit, testables)
# --------------------------------------------------------

#: Écart (en points de pourcentage) en dessous duquel deux taux sont
#: considérés comme proches.
ECART_PROCHE = 0.02

MOIS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
    "août", "septembre", "octobre", "novembre", "décembre",
]


def nom_mois(mois: pd.Timestamp) -> str:
    """Écrit un mois en toutes lettres, en français.

    Args:
        mois (pandas.Timestamp): Le mois.

    Returns:
        str: Par exemple ``"octobre 2026"``.

    Example:
        >>> nom_mois(pd.Timestamp("2026-10-01"))
        'octobre 2026'
    """
    mois = pd.Timestamp(mois)
    return f"{MOIS_FR[mois.month - 1]} {mois.year}"


def chances(proba: float) -> str:
    """Écrit une probabilité en « chances sur 100 ».

    On évite ainsi de l'écrire en %, pour ne pas la confondre avec la part des
    trains perturbés.

    Args:
        proba (float): Probabilité, entre 0 et 1.

    Returns:
        str: Par exemple ``"67 chances sur 100"``.

    Example:
        >>> chances(0.666)
        '67 chances sur 100'
    """
    return f"{round(proba * 100)} chances sur 100"


def phrase_prevision(liaison: str, mois: pd.Timestamp, proba: float) -> str:
    """Explique la prévision en une phrase.

    Args:
        liaison (str): Liaison lisible, par exemple ``"PARIS LYON → NICE"``.
        mois (pandas.Timestamp): Mois prévu.
        proba (float): Probabilité de perturbation, entre 0 et 1.

    Returns:
        str: La phrase, en Markdown.

    Example:
        >>> phrase_prevision("A → B", pd.Timestamp("2026-10-01"), 0.67)
        'Il y a **67 chances sur 100** que, en octobre 2026, plus de **20 % des trains** A → B soient annulés ou arrivent en retard.'
    """  # noqa: E501
    return (
        f"Il y a **{chances(proba)}** que, en {nom_mois(mois)}, plus de "
        f"**{_part(SEUIL_PERTURBATION)} des trains** {liaison} soient annulés "
        "ou arrivent en retard."
    )


def _position_seuil(taux: float) -> str:
    """Situe un taux par rapport au seuil de 20 %, en Markdown."""
    return (
        "**au-dessus** du seuil de 20 %"
        if taux > SEUIL_PERTURBATION
        else "sous le seuil de 20 %"
    )


def _part(taux: float) -> str:
    """Écrit un taux en pourcentage, par exemple ``"24 %"``."""
    return f"{taux:.0%}".replace("%", " %")


def lecture_historique(indicateurs: dict[str, float | None]) -> list[str]:
    """Interprète l'historique d'une liaison, par rapport au seuil de 20 %.

    Args:
        indicateurs (dict): Dictionnaire renvoyé
            par :func:`indicateurs_liaison`.

    Returns:
        list[str]: Une phrase par indicateur connu, puis une phrase sur la
        tendance (mois dernier comparé à la moyenne sur 12 mois).

    Example:
        >>> lecture_historique(
        ...     {"mois_dernier": 0.24, "moyenne_12_mois": None,
        ...      "an_dernier": None}
        ... )[0]
        'Le mois dernier, **24 %** des trains ont été perturbés : **au-dessus** du seuil de 20 %.'
    """  # noqa: E501
    dernier = indicateurs.get("mois_dernier")
    moyenne = indicateurs.get("moyenne_12_mois")
    an_dernier = indicateurs.get("an_dernier")
    phrases = []
    if dernier is not None and not pd.isna(dernier):
        phrases.append(
            f"Le mois dernier, **{_part(dernier)}** des trains ont été "
            f"perturbés : {_position_seuil(dernier)}."
        )
    if moyenne is not None and not pd.isna(moyenne):
        phrases.append(
            f"Sur les 12 derniers mois, **{_part(moyenne)}** en moyenne : "
            f"{_position_seuil(moyenne)}."
        )
    if an_dernier is not None and not pd.isna(an_dernier):
        phrases.append(
            f"Le même mois l'an dernier, **{_part(an_dernier)}** des trains "
            f"avaient été perturbés : {_position_seuil(an_dernier)}."
        )
    if (
        dernier is not None
        and moyenne is not None
        and not pd.isna(dernier)
        and not pd.isna(moyenne)
    ):
        if dernier > moyenne + ECART_PROCHE:
            tendance = "**plus perturbé** que d'habitude"
        elif dernier < moyenne - ECART_PROCHE:
            tendance = "**moins perturbé** que d'habitude"
        else:
            tendance = "dans la moyenne habituelle"
        phrases.append(f"Le mois dernier a donc été {tendance}.")
    if not phrases:
        phrases.append("Pas d'historique pour cette liaison avant ce mois.")
    return phrases


def phrase_bilan(
    proba: float, prevision: str, realite: str, taux_reel: float
) -> str:
    """Compare, pour un mois passé, la prévision et ce qui s'est passé.

    Args:
        proba (float): Probabilité de perturbation donnée par le modèle.
        prevision (str): ``"Perturbé"`` ou ``"Normal"``.
        realite (str): ``"Perturbé"`` ou ``"Normal"``.
        taux_reel (float): Part des trains réellement perturbés.

    Returns:
        str: La phrase, en Markdown.

    Example:
        >>> phrase_bilan(0.67, "Perturbé", "Perturbé", 0.31)
        'Le modèle donnait **67 chances sur 100**. En réalité, **31 %** des trains ont été perturbés : le mois a bien été perturbé, **la prévision était juste**.'
    """  # noqa: E501
    debut = (
        f"Le modèle donnait **{chances(proba)}**. En réalité, "
        f"**{_part(taux_reel)}** des trains ont été perturbés : "
    )
    if prevision == realite == "Perturbé":
        fin = "le mois a bien été perturbé, **la prévision était juste**."
    elif prevision == realite:
        fin = "le mois est resté normal, **la prévision était juste**."
    elif prevision == "Perturbé":
        fin = "le mois est resté normal, **c'était une fausse alerte**."
    else:
        fin = (
            "le mois a été perturbé alors que le modèle ne l'annonçait pas, "
            "**la perturbation a été manquée**."
        )
    return debut + fin


def taux_par_niveau(previsions: pd.DataFrame) -> dict[str, float]:
    """Mesure, par niveau de risque, la part de mois vraiment perturbés.

    Le calcul utilise les mois passés, où la réalité est connue.

    Args:
        previsions (pandas.DataFrame): Tableau renvoyé
            par :func:`charger_previsions`.

    Returns:
        dict[str, float]: Pour ``"Faible"``, ``"Moyen"`` et ``"Élevé"``, la
        part des mois réellement perturbés (absent si aucun mois connu).

    Example:
        >>> p = pd.DataFrame({
        ...     "proba_perturbation": [0.9, 0.8, 0.1],
        ...     "realite": ["Perturbé", "Normal", "Normal"],
        ... })
        >>> taux_par_niveau(p)
        {'Élevé': 0.5, 'Faible': 0.0}
    """
    passe = previsions.dropna(subset=["realite"])
    niveaux = passe["proba_perturbation"].map(lambda p: niveau_risque(p)[0])
    perturbes = passe["realite"].eq("Perturbé")
    parts = perturbes.groupby(niveaux, sort=False).mean()
    return {str(niveau): float(part) for niveau, part in parts.items()}


def phrase_confiance(niveau: str, taux: dict[str, float]) -> str:
    """Dit à quel point on peut se fier à un niveau de risque.

    Args:
        niveau (str): ``"Faible"``, ``"Moyen"`` ou ``"Élevé"``.
        taux (dict[str, float]): Dictionnaire renvoyé
            par :func:`taux_par_niveau`.

    Returns:
        str: La phrase, ou une chaîne vide si le niveau n'a pas de mois
        passé.

    Example:
        >>> phrase_confiance("Élevé", {"Élevé": 0.7})
        'Par le passé, quand le risque était **élevé**, le mois a vraiment été perturbé **7 fois sur 10**.'
    """  # noqa: E501
    if niveau not in taux:
        return ""
    return (
        f"Par le passé, quand le risque était **{niveau.lower()}**, le mois "
        f"a vraiment été perturbé **{round(taux[niveau] * 10)} fois sur 10**."
    )


def _md(texte: str) -> None:
    """Affiche du Markdown sans couper « 20 % » en fin de ligne."""
    st.markdown(texte.replace(" %", "\u00a0%"))


def _libelle_mois(mois: pd.Timestamp, premier: bool) -> str:
    """Libellé d'un mois, par exemple « 10/2026 : mois prochain »."""
    texte = pd.Timestamp(mois).strftime("%m/%Y")
    return (
        f"{texte} : mois prochain"
        if premier
        else f"{texte} : mois passé (comparer à la réalité)"
    )


# --- affichage
# ----------------------------------------------------------------------------


def _graphique_classement(vue: pd.DataFrame, nombre: int = 15) -> go.Figure:
    """Barres des liaisons les plus à risque, colorées par niveau."""
    top = vue.head(nombre).iloc[::-1]
    couleurs = [niveau_risque(p)[1] for p in top["proba_perturbation"]]
    textes = [f"{p:.0%}" for p in top["proba_perturbation"]]
    if top["realite"].notna().any():
        textes = [f"{t} · réel : {r}" for t, r in zip(textes, top["realite"])]
    fig = go.Figure(
        go.Bar(
            x=top["proba_perturbation"],
            y=top["liaison"],
            orientation="h",
            marker_color=couleurs,
            text=textes,
            textposition="outside",
            hovertemplate="%{y}<br>Probabilité : %{x:.0%}<extra></extra>",
        )
    )
    fig.add_vline(
        x=0.5,
        line_dash="dot",
        line_color="grey",
        annotation_text="seuil « Perturbé »",
        annotation_position="top",
    )
    fig.update_layout(
        xaxis=dict(
            tickformat=".0%",
            range=[0, 1.35],
            title="Probabilité de perturbation",
        ),
        height=max(350, 28 * len(top)),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig


def _graphique_historique(
    historique: pd.DataFrame, mois_prevu: pd.Timestamp
) -> go.Figure:
    """Courbe du taux de perturbation d'une liaison, avec le seuil de 20 %."""
    fig = go.Figure(
        go.Scatter(
            x=historique.index,
            y=historique["taux"],
            mode="lines+markers",
            line=dict(color="#1565c0", width=2),
            marker=dict(size=5),
            hovertemplate="%{x|%m/%Y} : %{y:.0%}<extra></extra>",
        )
    )
    fig.add_hline(
        y=SEUIL_PERTURBATION,
        line_dash="dash",
        line_color=ROUGE,
        annotation_text="20 % : mois perturbé",
        annotation_position="top left",
    )
    fig.add_vline(
        x=mois_prevu,
        line_dash="dot",
        line_color="grey",
        annotation_text="mois prévu",
        annotation_position="top left",
    )
    fig.update_layout(
        title=dict(
            text="Taux de perturbation de la liaison, mois par mois",
            x=0,
            xanchor="left",
        ),
        yaxis=dict(
            tickformat=".0%", title="Taux de perturbation", rangemode="tozero"
        ),
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
    )
    return fig


def _afficher_causes(titre: str, etat: str, parts: pd.Series | None) -> None:
    """Affiche la part de chaque cause, ou pourquoi elle manque."""
    st.markdown(f"**{titre}**")
    if etat == "ok" and parts is not None:
        st.markdown(
            "\n".join(
                f"- {cause} : **{part:.0f} %**"
                for cause, part in parts.items()
            )
        )
    elif etat == "aucun retard":
        st.markdown("Aucun train en retard ce mois-là.")
    elif etat == "mois absent":
        st.markdown("Pas de données pour ce mois.")
    else:
        st.markdown("Les causes n'étaient pas renseignées.")


def afficher_page(previsions: pd.DataFrame, historique: pd.DataFrame) -> None:
    """Affiche la page « Prévision des perturbations ».

    Args:
        previsions (pandas.DataFrame): Prévisions, renvoyées
            par :func:`charger_previsions`.
        historique (pandas.DataFrame): Historique, renvoyé
            par :func:`historique_liaisons`.
    """
    st.title("Prévision des perturbations")
    st.caption(
        "Un mois est dit **perturbé** quand plus de 20 % des trains prévus "
        "sont annulés ou arrivent en retard. La probabilité est donnée par un "
        "modèle d'apprentissage entraîné sur l'historique de chaque liaison."
    )

    # Choix du mois et du type de liaison
    mois_liste = mois_disponibles(previsions)
    choix_gauche, choix_droite = st.columns([2, 1])
    mois = choix_gauche.selectbox(
        "Mois à prévoir",
        mois_liste,
        format_func=lambda m: _libelle_mois(m, m == mois_liste[0]),
    )
    service = choix_droite.radio(
        "Liaisons", ["Toutes", "National", "International"], horizontal=True
    )
    st.caption(
        "Le modèle a besoin des données du mois précédent : on ne peut pas "
        "prévoir plus loin que le mois prochain. Les mois passés montrent ce "
        "qu'il avait prévu, sans les avoir vus pendant son apprentissage, à "
        "côté de ce qui s'est réellement passé."
    )
    vue = previsions_du_mois(previsions, mois, service)
    passe = vue["realite"].notna().any()

    # Chiffres clés, chacun dans une carte
    perturbees = int((vue["prevision"] == "Perturbé").sum())
    if passe:
        reelles = int((vue["realite"] == "Perturbé").sum())
        justes = int((vue["prevision"] == vue["realite"]).sum())
        cartes = [
            (
                "Liaisons annoncées perturbées",
                f"{perturbees} / {len(vue)}",
                "d'après le modèle",
            ),
            (
                "Liaisons réellement perturbées",
                f"{reelles} / {len(vue)}",
                "ce qui s'est passé",
            ),
            (
                "Prévisions justes",
                f"{justes / len(vue):.0%}",
                f"{justes} liaisons sur {len(vue)}",
            ),
        ]
    else:
        plus_risquee = vue.iloc[0]
        cartes = [
            (
                "Liaisons annoncées perturbées",
                f"{perturbees} / {len(vue)}",
                "probabilité supérieure à 50 %",
            ),
            (
                "Liaisons annoncées normales",
                f"{len(vue) - perturbees} / {len(vue)}",
                "probabilité inférieure à 50 %",
            ),
            (
                "Liaison la plus à risque",
                f"{plus_risquee['proba_perturbation']:.0%}",
                f"{plus_risquee['liaison']} ({plus_risquee['Service']})",
            ),
        ]
    for colonne, (titre, valeur, detail) in zip(st.columns(3), cartes):
        with colonne.container(border=True):
            st.metric(titre, valeur)
            st.caption(detail)

    # Classement
    st.subheader("Les liaisons les plus à risque")
    st.plotly_chart(_graphique_classement(vue), width="stretch")
    with st.expander("Voir toutes les liaisons"):
        colonnes_tableau = {
            "liaison": "Liaison",
            "Service": "Service",
            "proba_perturbation": "Probabilité",
            "prevision": "Prévision",
        }
        if passe:
            colonnes_tableau["realite"] = "Réalité"
        tableau = vue[list(colonnes_tableau)].rename(columns=colonnes_tableau)
        st.dataframe(
            tableau,
            hide_index=True,
            width="stretch",
            column_config={
                "Probabilité": st.column_config.ProgressColumn(
                    format="percent", min_value=0, max_value=1
                )
            },
        )

    # Zoom sur une liaison
    st.subheader("Zoom sur une liaison")
    noms = vue["liaison"] + " (" + vue["Service"] + ")"
    choix = st.selectbox("Choisir une liaison", noms)
    ligne = vue[noms == choix].iloc[0]
    depart, arrivee, service_liaison = (
        ligne["Gare de départ"],
        ligne["Gare d'arrivée"],
        ligne["Service"],
    )
    proba = ligne["proba_perturbation"]
    niveau, couleur = niveau_risque(proba)

    gauche, droite = st.columns(2)
    with gauche, st.container(border=True):
        st.markdown(f"**Prévision du modèle pour {nom_mois(mois)}**")
        st.markdown(
            f"<div style='border-left:6px solid {couleur};"
            "padding:0.3rem 1rem;margin-bottom:0.6rem'>"
            "<div style='font-size:1.8rem;font-weight:600'>"
            f"{ligne['prevision']}</div>"
            f"<div><b>{chances(proba)}</b> · risque "
            f"<b>{niveau.lower()}</b></div></div>",
            unsafe_allow_html=True,
        )
        _md(phrase_prevision(ligne["liaison"], mois, proba))
        confiance_niveau = phrase_confiance(
            niveau, taux_par_niveau(previsions)
        )
        if confiance_niveau:
            st.caption(confiance_niveau)
        if passe:
            st.markdown("**Ce qui s'est réellement passé**")
            _md(
                phrase_bilan(
                    proba,
                    ligne["prevision"],
                    ligne["realite"],
                    ligne["taux_reel"],
                )
            )
    with droite, st.container(border=True):
        st.markdown("**Ce qui s'est passé avant sur cette liaison**")
        ind = indicateurs_liaison(
            historique, depart, arrivee, service_liaison, mois
        )
        _md("\n".join(f"- {p}" for p in lecture_historique(ind)))

    st.plotly_chart(
        _graphique_historique(
            _filtrer_liaison(historique, depart, arrivee, service_liaison),
            mois,
        ),
        width="stretch",
    )

    st.subheader("D'où venaient les retards ?")
    mois_dernier = mois - pd.DateOffset(months=1)
    an_dernier = mois - pd.DateOffset(months=12)
    cause_gauche, cause_droite = st.columns(2)
    with cause_gauche:
        _afficher_causes(
            f"Mois dernier ({mois_dernier.strftime('%m/%Y')})",
            *causes_du_mois(
                historique, depart, arrivee, service_liaison, mois_dernier
            ),
        )
    with cause_droite:
        _afficher_causes(
            f"Même mois l'an dernier ({an_dernier.strftime('%m/%Y')})",
            *causes_du_mois(
                historique, depart, arrivee, service_liaison, an_dernier
            ),
        )


@st.cache_data
def _previsions_en_cache() -> pd.DataFrame:
    """Charge les prévisions une seule fois (cache Streamlit)."""
    return charger_previsions()


@st.cache_data
def _historique_en_cache() -> pd.DataFrame:
    """Calcule l'historique des liaisons une seule fois (cache Streamlit)."""
    from projet_sncf.database.dataloader import get_dataframe

    return historique_liaisons(get_dataframe())


def page_prevision() -> None:
    """Affiche la page « Prévision des perturbations ».

    C'est la fonction appelée par l'application. Les données sont chargées une
    seule fois, puis gardées en mémoire par Streamlit.

    Example:
        Dans l'application principale::

            from projet_sncf.pages.prevision_perturbations import (
                page_prevision,
            )

            page = st.navigation(
                [st.Page(page_prevision, title="Prévision des perturbations")]
            )
            page.run()
    """
    afficher_page(_previsions_en_cache(), _historique_en_cache())


if __name__ == "__main__":
    st.set_page_config(page_title="Prévision des perturbations", layout="wide")
    page_prevision()
