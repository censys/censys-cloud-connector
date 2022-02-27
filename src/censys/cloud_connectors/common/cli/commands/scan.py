"""Censys Cloud Connectors scan command."""
import argparse

from pydantic import ValidationError

from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.settings import Settings


def cli_scan(_: argparse.Namespace):
    """Scan with Censys Cloud Connectors.

    Args:
        _ (argparse.Namespace): Namespace.
    """
    logger = get_logger(log_name="censys_cloud_connectors", level="INFO")

    try:
        settings = Settings()
        settings.read_platforms_config_file()
    except ValidationError as e:
        logger.error(e)
        return

    settings.scan_all()


def include_cli(parent_parser: argparse._SubParsersAction):
    """Include this subcommand into the parent parser.

    Args:
        parent_parser (argparse._SubParsersAction): Parent parser.
    """
    config_parser = parent_parser.add_parser(
        "scan",
        description="Scan with Censys Cloud Connectors",
        help="scan with censys cloud connectors",
    )
    config_parser.set_defaults(func=cli_scan)
