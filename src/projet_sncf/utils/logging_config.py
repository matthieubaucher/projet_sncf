"""Configuration de la journalisation."""

# Imports
import logging

from projet_sncf.business.analysis.constants import LOG_FORMAT, LOG_LEVEL


# Functions
def setup_logging(level: str = LOG_LEVEL) -> None:
    """Configure le logger racine.

    Sans effet si le logger racine est déjà configuré.

    Args:
        level (str): Nom du niveau de journalisation, par exemple "INFO". Par défaut
            `LOG_LEVEL`.

    Returns:
        None: La configuration s'applique au logger racine.
    """
    logging.basicConfig(format=LOG_FORMAT, level=level)
