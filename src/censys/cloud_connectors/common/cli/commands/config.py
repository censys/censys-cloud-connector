"""Censys Cloud Connectors config command."""
import argparse
import importlib
import contextlib

from pydantic import ValidationError
from PyInquirer import prompt

from censys.cloud_connectors import __connectors__
from censys.cloud_connectors.common.settings import Settings


def cli_config(_: argparse.Namespace):
    """Configure Censys Cloud Connectors.

    Args:
        _ (argparse.Namespace): Namespace.

    Raises:
        KeyboardInterrupt: If the user cancels the prompt.
    """
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
    if answers == {}:
        raise KeyboardInterrupt
    platform_name = answers["platform"]
    platform_setup_func = importlib.import_module(
        f"censys.cloud_connectors.{platform_name}.platform_setup"
    ).main

    settings = Settings()
    with contextlib.suppress(FileNotFoundError):
        settings.read_platforms_config_file()
    try:
        platform_setup_func(settings)
    except ValidationError as e:
        print(e)
        return
    questions = [
        {
            "type": "confirm",
            "name": "save",
            "message": "Save settings?",
        }
    ]
    answers = prompt(questions)
    if answers == {}:
        raise KeyboardInterrupt
    if answers["save"]:
        settings.write_platforms_config_file()
        print(f"Successfully saved settings to {settings.platforms_config_file}")


def include(parent_parser: argparse._SubParsersAction):
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
