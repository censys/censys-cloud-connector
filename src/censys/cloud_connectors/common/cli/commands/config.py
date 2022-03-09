"""Censys Cloud Connectors config command."""
import argparse
import contextlib
import importlib

from InquirerPy import prompt
from pydantic import ValidationError

from censys.cloud_connectors import __connectors__
from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.settings import Settings


def cli_config(_: argparse.Namespace):
    """Configure Censys Cloud Connectors.

    Args:
        _ (argparse.Namespace): Namespace.

    Raises:
        KeyboardInterrupt: If the user cancels the prompt.
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

    questions = [
        {
            "type": "list",
            "name": "provider",
            "message": "Select a provider",
            "choices": [
                {
                    "name": c.capitalize(),
                    "value": c,
                }
                for c in __connectors__
            ],
        }
    ]
    answers = prompt(questions)
    if not answers:  # pragma: no cover
        raise KeyboardInterrupt
    provider_name = answers["provider"]
    provider_setup_cls = importlib.import_module(
        f"censys.cloud_connectors.{provider_name}"
    ).__provider_setup__

    with contextlib.suppress(FileNotFoundError):
        settings.read_providers_config_file()
    try:
        provider_setup = provider_setup_cls(settings)
        provider_setup.setup()
    except ValidationError as e:  # pragma: no cover
        logger.error(e)
        return
    questions = [
        {
            "type": "confirm",
            "name": "save",
            "message": "Save settings?",
        }
    ]
    answers = prompt(questions)
    if not answers:  # pragma: no cover
        raise KeyboardInterrupt
    if answers.get("save", False):
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
    config_parser.set_defaults(func=cli_config)
