"""Logger for the Cloud Connector."""
import logging
from typing import Optional


def get_logger(
    log_name: Optional[str] = "cloud_connector",
    level: str = "INFO",
    provider: str = "",
    **kwargs,
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

        formatter = logging.Formatter(
            # fmt="%(asctime)s:%(levelname)s:%(name)s: %(message)s"
            fmt="%(asctime)s:%(levelname)s:%(name)s:%(provider)s: %(message)s"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        logging.setLogRecordFactory(
            lambda *args, **kwargs: CustomLogRecord(*args, provider=provider, **kwargs)
        )
    logger.setLevel(level)

    return logger


# TODO: see if there is an easier way to do this (dont like the provider arg)
class CustomLogRecord(logging.LogRecord):
    def __init__(self, *args, provider: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.provider = provider
