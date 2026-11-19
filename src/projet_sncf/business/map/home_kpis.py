"""Numbers for the home page. No Streamlit in here."""

# Imports
import pandas as pd

from projet_sncf.business.map.map_sncf import TIER_LESS, TIER_MIDDLE, TIER_MORE

# Constants
TIERS = [TIER_MORE, TIER_MIDDLE, TIER_LESS]


# Functions
def home_metrics(scores: pd.DataFrame) -> dict:
    """The four numbers shown on the home page."""
    return {
        "liaisons": len(scores),
        "plus_fiables": int((scores["tiers"] == TIER_MORE).sum()),
        "taux_perturbation": (
            float(scores["taux_perturbation"].mean()) if len(scores) else 0.0
        ),
        "mois": int(scores["mois"].max()) if len(scores) else 0,
    }


def tier_counts(scores: pd.DataFrame) -> pd.DataFrame:
    """Number of liaisons by tier, in a fixed order."""
    counts = scores["tiers"].value_counts()
    return pd.DataFrame(
        {"Niveau": TIERS, "Liaisons": [int(counts.get(tier, 0)) for tier in TIERS]}
    )
