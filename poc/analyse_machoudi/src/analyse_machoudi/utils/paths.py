import os
import glob
import logging

from analyse_machoudi.constants import DATA_DIR, DEFAULT_PATTERN

logger = logging.getLogger(__name__)


def get_data_path(data_dir: str = DATA_DIR, pattern: str = DEFAULT_PATTERN) -> str:
    """Return the path of the raw SNCF regularity CSV file

    Args:
        data_dir (str, optional): _description_. Defaults to DATA_DIR.
        pattern (str, optional): _description_. Defaults to DEFAULT_PATTERN.

    Returns:
        str: _description_
    """

    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Data folder not found: {data_dir}")
    files = glob.glob(os.path.join(data_dir, pattern))
    if not files:
        raise FileNotFoundError(f"No file matching {pattern} in {data_dir}")
    logger.info("Found data file: %s", files[0])
    return files[0]
