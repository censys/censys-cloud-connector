"""Censys Cloud Connectors config command."""
import argparse
import contextlib
import importlib
from typing import Any

from pydantic import ValidationError

from censys.cloud_connectors.common.cli.base import print, print_question, prompt
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.settings import Settings


def cli_config(args: argparse.Namespace):
    """Configure Censys Cloud Connectors.

    Args:
        args (argparse.Namespace): Namespace.
    """
    logger = get_logger(log_name="censys_cloud_connectors", level="INFO")

    try:
        settings = Settings()
    except ValidationError as e:
        error_str = str(e)
        print(error_str)
        if "censys_api_key" in error_str:
            print("Please ensure the CENSYS_API_KEY environment variable is set")
        return

    if args.provider is None:
        questions: list[dict[str, Any]] = [
            {
                "type": "list",
                "name": "provider",
                "message": "Select a provider:",
                "choices": [
                    {
                        "name": str(provider),
                        "value": provider,
                    }
                    for provider in ProviderEnum
                    # TODO: Remove this once AWS is supported
                    if provider != ProviderEnum.AWS
                ],
            }
        ]
        answers = prompt(questions)
        provider = answers["provider"]
    else:
        provider_name = args.provider
        provider = ProviderEnum[provider_name]
        print_question(f"Provider: [info]{provider}[/info]")

    provider_setup_cls = importlib.import_module(
        provider.module_path()
    ).__provider_setup__

    with contextlib.suppress(FileNotFoundError):
        settings.read_providers_config_file()
    try:
        provider_setup = provider_setup_cls(settings)
        provider_setup.setup()
    except ValidationError as e:  # pragma: no cover
        logger.error(e)
        return
    settings.write_providers_config_file()
    print(f"Successfully saved settings to {settings.providers_config_file}")


def include_cli(parent_parser: argparse._SubParsersAction):
    """Include this subcommand into the parent parser.

    Args:
        parent_parser (argparse._SubParsersAction): Parent parser.
    """
    config_parser = parent_parser.add_parser(
        "config",
        description="Configure Censys Cloud Connectors",
        help="configure censys cloud connectors",
    )
    provider_choices = [str(provider).lower() for provider in ProviderEnum]
    config_parser.add_argument(
        "-p",
        "--provider",
        choices=provider_choices,
        help=f"specify a cloud service provider: {provider_choices}",
        metavar="PROVIDER",
        dest="provider",
        nargs="?",
        type=str.lower,
        default=None,
    )
    config_parser.set_defaults(func=cli_config)
