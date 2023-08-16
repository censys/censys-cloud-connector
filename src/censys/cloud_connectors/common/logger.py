"""Logger for the Cloud Connector."""
import logging
from typing import Optional


def get_logger(
    log_name: Optional[str] = "cloud_connector", level: str = "INFO", **kwargs
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
            fmt="%(asctime)s:%(levelname)s:%(name)s: %(message)s"
            # fmt="%(asctime)s:%(levelname)s:%(name)s:%(provider)s: %(message)s"
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # TODO - add provider (AWS=account+region, GCP=org+project, AZURE=subid) to log record
        #
        # https://stackoverflow.com/a/57820456/19351735
        # old_factory = logging.getLogRecordFactory()
        # def record_factory(*args, **kwargs):
        #     record = old_factory(*args, **kwargs)
        #     provider = kwargs.get("provider", "")
        #     record.provider = provider
        #     return record

        # logging.setLogRecordFactory(record_factory)
    logger.setLevel(level)

    return logger
