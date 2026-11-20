"""Classe les trajets SNCF selon leurs taux de retard ou d'annulation."""

from datetime import date

import pandas as pd

COLONNE_DATE = "Date"
COLONNE_GARE_DEPART = "Gare de départ"
COLONNE_GARE_ARRIVEE = "Gare d'arrivée"
COLONNE_CIRCULATIONS_PREVUES = "Nombre de circulations prévues"
COLONNE_TRAINS_RETARD_ARRIVEE = "Nombre de trains en retard à l'arrivée"
COLONNE_TRAINS_ANNULES = "Nombre de trains annulés"

INDICATEUR_RETARDS_TAUX = "Retards à l'arrivée (taux)"
INDICATEUR_ANNULATIONS_TAUX = "Annulations (taux)"
INDICATEUR_RETARDS_ABSOLUS = "Retards à l'arrivée (valeur absolue)"
INDICATEUR_ANNULATIONS_ABSOLUES = "Annulations (valeur absolue)"
INDICATEURS_ABSOLUS = frozenset(
    {INDICATEUR_RETARDS_ABSOLUS, INDICATEUR_ANNULATIONS_ABSOLUES}
)
COLONNES_PAR_INDICATEUR = {
    INDICATEUR_RETARDS_TAUX: COLONNE_TRAINS_RETARD_ARRIVEE,
    INDICATEUR_ANNULATIONS_TAUX: COLONNE_TRAINS_ANNULES,
    INDICATEUR_RETARDS_ABSOLUS: COLONNE_TRAINS_RETARD_ARRIVEE,
    INDICATEUR_ANNULATIONS_ABSOLUES: COLONNE_TRAINS_ANNULES,
}


def rank_worst_routes(
    data: pd.DataFrame,
    start_period: int | str | date | pd.Period,
    end_period: int | str | date | pd.Period,
    metric: str,
    limit: int = 10,
) -> pd.DataFrame:
    """Renvoie les trajets les plus perturbés selon le critère choisi.

    Les taux correspondent au nombre de trains en retard ou annulés divisé
    par le nombre de circulations prévues sur la période. Les critères en
    valeur absolue classent les trajets selon le nombre total de trains
    concernés.
    """
    start_period = (
        pd.Period(year=start_period, month=1, freq="M")
        if isinstance(start_period, int)
        else pd.Period(start_period, freq="M")
    )
    end_period = (
        pd.Period(year=end_period, month=12, freq="M")
        if isinstance(end_period, int)
        else pd.Period(end_period, freq="M")
    )
    if start_period > end_period:
        raise ValueError(
            "La période de début doit précéder ou égaler la période de fin."
        )
    if metric not in COLONNES_PAR_INDICATEUR:
        raise ValueError(f"Indicateur inconnu : {metric}")
    if limit < 1:
        raise ValueError("La limite doit être supérieure ou égale à 1.")

    delayed_or_cancelled = COLONNES_PAR_INDICATEUR[metric]
    required_columns = [
        COLONNE_DATE,
        COLONNE_GARE_DEPART,
        COLONNE_GARE_ARRIVEE,
        COLONNE_CIRCULATIONS_PREVUES,
        delayed_or_cancelled,
    ]
    missing_columns = [
        column for column in required_columns if column not in data.columns
    ]
    if missing_columns:
        raise KeyError(f"Colonnes manquantes : {', '.join(missing_columns)}")

    months = pd.to_datetime(data[COLONNE_DATE], errors="coerce").dt.to_period(
        "M"
    )
    selected = data.loc[
        months.between(start_period, end_period), required_columns
    ].dropna()
    if selected.empty:
        return pd.DataFrame(
            columns=[
                "trajet",
                "taux",
                "valeur",
                "trains_concernes",
                "circulations_prevues",
            ]
        )

    grouped = selected.groupby(
        [COLONNE_GARE_DEPART, COLONNE_GARE_ARRIVEE], observed=True
    ).agg(
        trains_concernes=(delayed_or_cancelled, "sum"),
        circulations_prevues=(COLONNE_CIRCULATIONS_PREVUES, "sum"),
    )
    grouped = grouped[grouped["circulations_prevues"] > 0].copy()
    grouped["taux"] = (
        grouped["trains_concernes"] / grouped["circulations_prevues"]
    )
    grouped["trajet"] = [
        f"{departure} → {arrival}" for departure, arrival in grouped.index
    ]
    grouped["valeur"] = (
        grouped["trains_concernes"]
        if metric in INDICATEURS_ABSOLUS
        else grouped["taux"]
    )

    return (
        grouped.reset_index(drop=True)
        .sort_values(["valeur", "trajet"], ascending=[False, True])
        .head(limit)
        .reset_index(drop=True)
    )
