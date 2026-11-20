"""Chemin du CSV brut de la régularité SNCF."""

# Imports
import glob
import logging
import os

from projet_sncf.business.analysis.constants import DATA_DIR, DEFAULT_PATTERN

# Constants
logger = logging.getLogger(__name__)


# Functions
def get_data_path(
    data_dir: str = DATA_DIR, pattern: str = DEFAULT_PATTERN
) -> str:
    """Renvoie le chemin du CSV brut de la régularité SNCF.

    Si plusieurs CSV correspondent au motif, on prend le premier trouvé.

    Args:
        data_dir (str): Dossier des données. Par défaut `DATA_DIR`.
        pattern (str): Motif du nom du CSV. Par défaut `DEFAULT_PATTERN`.

    Returns:
        str: Le chemin du CSV trouvé.

    Raises:
        FileNotFoundError: Si le dossier n'existe pas ou ne contient aucun
            CSV correspondant au motif.
    """
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Data folder not found: {data_dir}")
    files = glob.glob(os.path.join(data_dir, pattern))
    if not files:
        raise FileNotFoundError(f"No file matching {pattern} in {data_dir}")
    logger.info("Found data file: %s", files[0])
    return files[0]
