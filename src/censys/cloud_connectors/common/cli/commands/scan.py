"""Censys Cloud Connectors scan command."""
import argparse

from pydantic import ValidationError

from censys.cloud_connectors import __connectors__, __version__
from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.settings import Settings


def cli_scan(args: argparse.Namespace):
    """Scan with Censys Cloud Connectors.

    Args:
        args (argparse.Namespace): Namespace.

    """
    logger = get_logger(log_name="censys_cloud_connectors", level="INFO")

    logger.info("Censys Cloud Connectors Version: %s", __version__)

    try:
        settings = Settings()
    except ValidationError as e:  # pragma: no cover
        logger.error(e)
        return

    try:
        settings.read_providers_config_file(args.provider)
    except ValidationError as e:  # pragma: no cover
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
    config_parser.add_argument(
        "-p",
        "--provider",
        choices=__connectors__,
        help=f"specify one or more cloud service provider(s): {__connectors__}",
        metavar="PROVIDER",
        dest="provider",
        action="extend",
        nargs="+",
        default=None,
    )
    config_parser.set_defaults(func=cli_scan)
