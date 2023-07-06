"""Censys Cloud Connectors scan command."""
import argparse
from datetime import datetime
from typing import Optional

from pydantic import ValidationError

from censys.cloud_connectors import __version__
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.plugins import CloudConnectorPluginRegistry
from censys.cloud_connectors.common.settings import Settings


async def cli_scan(args: argparse.Namespace):
    """Scan with Censys Cloud Connectors.

    Args:
        args (argparse.Namespace): Namespace.

    """
    logger = get_logger(log_name="censys_cloud_connectors", level="INFO")

    logger.info("Censys Cloud Connectors Version: %s", __version__)

    try:
        settings = Settings(_env_file=".env")  # type: ignore
        CloudConnectorPluginRegistry.load_plugins(settings, logger)
    except ValidationError as e:  # pragma: no cover
        logger.error(e)
        return

    selected_providers: Optional[list[ProviderEnum]] = None
    if args.provider:
        selected_providers = [ProviderEnum[provider] for provider in args.provider]
    try:
        settings.read_providers_config_file(selected_providers)
    except ValidationError as e:  # pragma: no cover
        logger.error(e)
        return

    await settings.scan_all()

    logger.info(
        f"Finished scanning at time: {datetime.now().isoformat(' ', 'seconds')}."
    )


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
    provider_choices = [str(provider).lower() for provider in ProviderEnum]
    config_parser.add_argument(
        "-p",
        "--provider",
        choices=provider_choices,
        help=f"specify one or more cloud service provider(s): {provider_choices}",
        metavar="PROVIDER",
        dest="provider",
        action="extend",
        nargs="+",
        type=str.lower,
        default=None,
    )

    config_parser.set_defaults(func=cli_scan)
