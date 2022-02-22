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
    formatter = logging.Formatter(fmt="%(levelname)s:%(name)s: %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(log_name)
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger
