"""Agrège les causes mensuelles de retard en proportions sur une période choisie."""

import pandas as pd


COLONNE_DATE = "Date"
COLONNE_RETARDS = "Nombre de trains en retard à l'arrivée"
COLONNE_GARE_DEPART = "Gare de départ"
COLONNE_GARE_ARRIVEE = "Gare d'arrivée"
CAUSES_PERTURBATION = {
    "Prct retard pour causes externes": "Causes externes",
    "Prct retard pour cause infrastructure": "Infrastructure",
    "Prct retard pour cause gestion trafic": "Gestion du trafic",
    "Prct retard pour cause matériel roulant": "Matériel roulant",
    "Prct retard pour cause gestion en gare et réutilisation de matériel": "Gestion en gare",
    "Prct retard pour cause prise en compte voyageurs (affluence, gestions PSH, correspondances)":
        "Voyageurs",
}
CAUSE_NON_RENSEIGNEE = "Causes non renseignées"


def calculer_evolution_causes(
    donnees: pd.DataFrame,
    debut: str | pd.Timestamp,
    fin: str | pd.Timestamp,
    *,
    gare_depart: str | None = None,
    gare_arrivee: str | None = None,
) -> pd.DataFrame:
    """Calcule les parts mensuelles des causes, pondérées par les retards à l'arrivée.

    Les parts manquantes sont regroupées dans ``Causes non renseignées`` afin que
    les proportions de chaque mois totalisent 1.
    """
    periode_debut = pd.Period(debut, freq="M")
    periode_fin = pd.Period(fin, freq="M")
    if periode_debut > periode_fin:
        raise ValueError("La période de début doit précéder ou égaler la période de fin.")
    if (gare_depart is None) != (gare_arrivee is None):
        raise ValueError("Les gares de départ et d'arrivée doivent être toutes deux précisées.")

    colonnes_requises = [COLONNE_DATE, COLONNE_RETARDS, *CAUSES_PERTURBATION]
    if gare_depart is not None:
        colonnes_requises.extend([COLONNE_GARE_DEPART, COLONNE_GARE_ARRIVEE])
    colonnes_manquantes = [colonne for colonne in colonnes_requises if colonne not in donnees]
    if colonnes_manquantes:
        raise KeyError(f"Colonnes manquantes : {', '.join(colonnes_manquantes)}")

    dates = pd.to_datetime(donnees[COLONNE_DATE], errors="coerce")
    mois = dates.dt.to_period("M")
    masque = mois.between(periode_debut, periode_fin)
    if gare_depart is not None and gare_arrivee is not None:
        masque &= donnees[COLONNE_GARE_DEPART].astype(str).eq(gare_depart)
        masque &= donnees[COLONNE_GARE_ARRIVEE].astype(str).eq(gare_arrivee)
    selection = donnees.loc[masque, [COLONNE_RETARDS, *CAUSES_PERTURBATION]].copy()
    selection["mois"] = mois.loc[masque].dt.to_timestamp()
    retards = pd.to_numeric(selection[COLONNE_RETARDS], errors="coerce").fillna(0).clip(lower=0)
    parts = selection[list(CAUSES_PERTURBATION)].apply(pd.to_numeric, errors="coerce").fillna(0)
    parts = parts.clip(lower=0).rename(columns=CAUSES_PERTURBATION)

    somme_parts = parts.sum(axis=1)
    depassement = somme_parts > 100
    parts.loc[depassement] = parts.loc[depassement].div(somme_parts[depassement], axis=0) * 100
    somme_parts = parts.sum(axis=1).clip(upper=100)

    contributions = parts.mul(retards / 100, axis=0)
    contributions[CAUSE_NON_RENSEIGNEE] = (100 - somme_parts) * retards / 100
    contributions["mois"] = selection["mois"]
    contributions["retards_attribues"] = retards

    par_mois = contributions.groupby("mois", observed=True).sum(numeric_only=True)
    total_retards = par_mois.pop("retards_attribues")
    evolution = par_mois.div(total_retards, axis=0)
    evolution = evolution.reset_index().melt(
        id_vars="mois", var_name="cause", value_name="pourcentage"
    )
    return evolution.sort_values(["mois", "cause"]).reset_index(drop=True)