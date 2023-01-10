"""Logger for the Cloud Connector."""
import logging
from typing import Optional


def get_logger(
    log_name: Optional[str] = "cloud_connector", level: str = "INFO"
) -> logging.Logger:
    """Returns a custom logger.

    Args:
        log_name (str): Optional; The custom logger's name.
        level (str): Optional; The desired log level.
            Options are [CRITICAL, ERROR, WARNING, INFO, DEBUG].

    Returns:
        logger: A logger configured with the provided logging settings.
    """
    logger = logging.getLogger(log_name)
    if not logger.hasHandlers():
        formatter = logging.Formatter(fmt="%(levelname)s:%(name)s: %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)

    return logger
