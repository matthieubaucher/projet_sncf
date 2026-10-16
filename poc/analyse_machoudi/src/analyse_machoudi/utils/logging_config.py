import logging

from analyse_machoudi.constants import LOG_FORMAT, LOG_LEVEL


def setup_logging(level: str = LOG_LEVEL) -> None:
    """Configure the root logger

    Args:
        level (str, optional): Logginng level name. Defaults to LOG_LEVEL.
    """
    logging.basicConfig(format=LOG_FORMAT, level=level)
