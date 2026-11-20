"""Chiffres de la page d'accueil, sans Streamlit."""

# Imports
import pandas as pd

from projet_sncf.business.map.map_sncf import TIER_LESS, TIER_MIDDLE, TIER_MORE

# Constants
## Ordre d'affichage des niveaux
TIERS = [TIER_MORE, TIER_MIDDLE, TIER_LESS]


# Functions
def home_metrics(scores: pd.DataFrame) -> dict:
    """Calcule les quatre chiffres affichés sur la page d'accueil.

    Args:
        scores (pd.DataFrame): Tableau de fiabilité, une ligne par liaison, avec les
            colonnes `tiers`, `taux_perturbation` et `mois`.

    Returns:
        dict: Les clés `liaisons` (nombre de liaisons), `plus_fiables` (nombre de
        liaisons du niveau « plus fiable »), `taux_perturbation` (moyenne des taux
        des liaisons) et `mois` (plus grand nombre de mois d'une liaison). Les
        deux dernières valent 0 si le tableau est vide.
    """
    return {
        "liaisons": len(scores),
        "plus_fiables": int((scores["tiers"] == TIER_MORE).sum()),
        "taux_perturbation": (
            float(scores["taux_perturbation"].mean()) if len(scores) else 0.0
        ),
        "mois": int(scores["mois"].max()) if len(scores) else 0,
    }


def tier_counts(scores: pd.DataFrame) -> pd.DataFrame:
    """Compte les liaisons de chaque niveau, dans un ordre fixe.

    Args:
        scores (pd.DataFrame): Tableau de fiabilité avec la colonne `tiers`.

    Returns:
        pd.DataFrame: Une ligne par niveau, avec les colonnes `Niveau` et
        `Liaisons`. Un niveau sans liaison est compté 0.
    """
    counts = scores["tiers"].value_counts()
    return pd.DataFrame(
        {"Niveau": TIERS, "Liaisons": [int(counts.get(tier, 0)) for tier in TIERS]}
    )
