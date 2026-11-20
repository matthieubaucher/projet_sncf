"""Coordonnées des gares du jeu de données des liaisons.

Les gares françaises sont retrouvées par leur nom dans le jeu de données
« Gares de voyageurs » (SNCF Gares & Connexions, ODbL).
"""

# Imports
import difflib
import logging
import re
import unicodedata

import pandas as pd

# Constants
logger = logging.getLogger(__name__)

# Si des gares étrangères, absentes de la référence alors on définit des coordonnées approximatives (latitude, longitude)
MANUAL_COORDINATES = {
    "BARCELONA": (41.3791, 2.1403),
    "FRANCFORT": (50.1071, 8.6628),
    "GENEVE": (46.2102, 6.1424),
    "LAUSANNE": (46.5170, 6.6293),
    "MADRID": (40.4065, -3.6892),
    "STUTTGART": (48.7840, 9.1816),
    "ZURICH": (47.3779, 8.5403),
}

# Nom de la gare dans la référence, quand il diffère
ALIASES = {
    "BELLEGARDE (AIN)": "Bellegarde-sur-Valserine",
    "DIJON VILLE": "Dijon",
    "LA ROCHELLE VILLE": "La Rochelle",
    "LE CREUSOT MONTCEAU MONTCHANIN": "Le Creusot - Montceau-les-Mines - Montchanin TGV",
    "LILLE": "Lille Flandres",
    "MACON LOCHE": "Mâcon Loché TGV",
    "MARNE LA VALLEE": "Marne-la-Vallée - Chessy",
    "MONTPELLIER": "Montpellier Saint-Roch",
    "MULHOUSE VILLE": "Mulhouse",
    "NICE VILLE": "Nice",
    "PARIS LYON": "Paris Gare de Lyon",
    "PARIS NORD": "Paris Gare du Nord",
    # Annexe, absente de la référence
    "PARIS VAUGIRARD": "Paris Montparnasse",
    "VALENCE ALIXAN TGV": "Valence TGV Rhône-Alpes Sud",
}

NUMBER_OF_CANDIDATES = 3
MATCH_CUTOFF = 0.6


# Functions
def normalize_name(name: str) -> str:
    """Met un nom de gare sous une forme qui ne dépend pas de l'écriture.

    Args:
        name (str): Nom de la gare, en majuscules ou non, avec ou sans accents et
            tirets.

    Returns:
        str: Le nom en majuscules, sans accents, tirets ni apostrophes, avec `ST` et
        `STE` écrits `SAINT` et `SAINTE`.
    """
    text = unicodedata.normalize("NFKD", name)
    text = "".join(c for c in text if not unicodedata.combining(c)).upper()
    text = re.sub(r"[-'’.,]", " ", text)
    text = re.sub(r"\bSTE\b", "SAINTE", text)
    text = re.sub(r"\bST\b", "SAINT", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_position(position: str) -> tuple[float, float]:
    """Lit un texte de la forme « latitude, longitude ».

    Args:
        position (str): Position écrite comme dans la référence, par exemple
            "49.68, 1.77".

    Returns:
        tuple[float, float]: La latitude et la longitude. (NaN, NaN) si le texte est
        vide ou mal formé.
    """
    try:
        latitude, longitude = str(position).split(",")
        return float(latitude), float(longitude)
    except ValueError:
        return float("nan"), float("nan")


def match_stations(
    names: list[str], reference: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Trouve les coordonnées de chaque gare.

    Les règles s'appliquent dans cet ordre : coordonnées manuelles, alias, puis nom
    normalisé identique.

    Args:
        names (list[str]): Noms des gares du jeu de données des liaisons.
        reference (pd.DataFrame): Le jeu de données « Gares de voyageurs », avec les
            colonnes `Nom_Gare` et `Position géographique`.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Les gares trouvées, avec les colonnes
        `gare`, `latitude`, `longitude`, `source` et `nom_reference`, puis les gares
        sans correspondance, avec les colonnes `gare` et `candidats`.
    """
    reference = reference.copy()
    reference["cle"] = reference["Nom_Gare"].map(normalize_name)
    by_key = reference.drop_duplicates("cle").set_index("cle")
    matched, unmatched = [], []

    for name in names:
        if name in MANUAL_COORDINATES:
            latitude, longitude = MANUAL_COORDINATES[name]
            matched.append((name, latitude, longitude, "manuel", ""))
            continue
        key = normalize_name(ALIASES.get(name, name))
        if key in by_key.index:
            row = by_key.loc[key]
            latitude, longitude = parse_position(row["Position géographique"])
            matched.append(
                (name, latitude, longitude, "gares-voyageurs", row["Nom_Gare"])
            )
        else:
            close = difflib.get_close_matches(
                key, by_key.index, NUMBER_OF_CANDIDATES, MATCH_CUTOFF
            )
            unmatched.append((name, " | ".join(by_key.loc[close, "Nom_Gare"])))

    matched_df = pd.DataFrame(
        matched, columns=["gare", "latitude", "longitude", "source", "nom_reference"]
    )
    unmatched_df = pd.DataFrame(unmatched, columns=["gare", "candidats"])
    logger.info("Gares localisées : %d sur %d", len(matched_df), len(names))
    return matched_df, unmatched_df
