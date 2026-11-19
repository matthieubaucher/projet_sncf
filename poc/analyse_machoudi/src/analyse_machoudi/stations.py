"""Coordinates of the stations of the liaisons dataset.

French stations are matched by name with the "Gares de voyageurs" dataset
(SNCF Gares & Connexions, ODbL). Foreign stations and names that do not match are
given by hand in ``MANUAL_COORDINATES`` and ``ALIASES``.
"""

import difflib
import logging
import re
import unicodedata
import pandas as pd

logger = logging.getLogger(__name__)

# Foreign stations, not in the French reference. Approximate coordinates (latitude, longitude)
MANUAL_COORDINATES = {
    "BARCELONA": (41.3791, 2.1403),
    "FRANCFORT": (50.1071, 8.6628),
    "GENEVE": (46.2102, 6.1424),
    "LAUSANNE": (46.5170, 6.6293),
    "MADRID": (40.4065, -3.6892),
    "STUTTGART": (48.7840, 9.1816),
    "ZURICH": (47.3779, 8.5403),
}

# Name of the dataset
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
    "PARIS VAUGIRARD": "Paris Montparnasse",  # annexe, absente de la référence
    "VALENCE ALIXAN TGV": "Valence TGV Rhône-Alpes Sud",
}

NUMBER_OF_CANDIDATES = 3
MATCH_CUTOFF = 0.6


def normalize_name(name: str) -> str:
    """Put a station name in a form that does not depend on spelling.

    Args:
        name (str): Station name, in any case, with or without accents and hyphens.

    Returns:
        str: Upper case, without accents, hyphens or apostrophes, with ``ST`` and
        ``STE`` written ``SAINT`` and ``SAINTE``.
    """
    text = unicodedata.normalize("NFKD", name)
    text = "".join(c for c in text if not unicodedata.combining(c)).upper()
    text = re.sub(r"[-'’.,]", " ", text)
    text = re.sub(r"\bSTE\b", "SAINTE", text)
    text = re.sub(r"\bST\b", "SAINT", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_position(position: str) -> tuple[float, float]:
    """Read a "latitude, longitude" string.

    Args:
        position (str): Position as written in the reference, e.g. "49.68, 1.77".

    Returns:
        tuple[float, float]: Latitude and longitude. (NaN, NaN) if the text is empty
        or malformed.
    """
    try:
        latitude, longitude = str(position).split(",")
        return float(latitude), float(longitude)
    except ValueError:
        return float("nan"), float("nan")


def match_stations(
    names: list[str], reference: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Find the coordinates of each station.

    Order of the rules: manual coordinates, alias, then equal normalized name.

    Args:
        names (list[str]): Station names of the liaisons dataset.
        reference (pd.DataFrame): The "Gares de voyageurs" dataset, with the columns
            ``Nom_Gare`` and ``Position géographique``.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: The matched stations, with the columns
        ``gare``, ``latitude``, ``longitude``, ``source``, ``nom_reference``; and the
        stations without match, with the columns ``gare`` and ``candidats``.
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
