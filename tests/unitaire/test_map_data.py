"""Lecture des JSON de la carte, sans Streamlit."""

# Imports
import json
import logging
from pathlib import Path

# Constants
logger = logging.getLogger(__name__)


# Functions
def read_json(path: Path, default: dict | list | None = None) -> dict | list:
    """Lit un JSON de la carte.

    Si le JSON est absent et qu'une valeur par défaut est donnée, on journalise un
    avertissement et on renvoie cette valeur. Sans valeur par défaut, l'absence est
    une erreur.

    Args:
        path (Path): Chemin du JSON.
        default (dict | list | None): Valeur à renvoyer si le JSON est absent.

    Returns:
        dict | list: Le contenu du JSON, ou `default` s'il est absent.

    Raises:
        FileNotFoundError: Si le JSON est absent et qu'il n'y a pas de valeur par défaut.
        ValueError: Si le JSON est illisible.
    """
    if not path.exists():
        if default is None:
            raise FileNotFoundError(f"Fichier manquant : {path}")
        logger.warning("Fichier absent, valeur par défaut utilisée : %s", path)
        return default
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON illisible : {path}") from error
