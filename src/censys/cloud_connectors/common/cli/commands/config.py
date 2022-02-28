"""Censys Cloud Connectors config command."""
import argparse
import contextlib
import importlib

from pydantic import ValidationError
from PyInquirer import prompt

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
    questions = [
        {
            "type": "list",
            "name": "platform",
            "message": "Select a platform",
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
    platform_name = answers["platform"]
    platform_setup_cls = importlib.import_module(
        f"censys.cloud_connectors.{platform_name}"
    ).__platform_setup__

    settings = Settings()
    with contextlib.suppress(FileNotFoundError):
        settings.read_platforms_config_file()
    try:
        platform_setup = platform_setup_cls(settings)
        platform_setup.setup()
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
        settings.write_platforms_config_file()
        print(f"Successfully saved settings to {settings.platforms_config_file}")


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
