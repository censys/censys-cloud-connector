"""Interact with argparser."""
import argparse

from . import commands


def get_parser() -> argparse.ArgumentParser:
    """Gets ArgumentParser for CLI.

    Returns:
        argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        default=False,
        help="display version",
    )

    def print_help(_: argparse.Namespace):
        """Prints help."""
        parser.print_help()
        parser.exit()

    parser.set_defaults(func=print_help)

    subparsers = parser.add_subparsers()

    for command in commands.__dict__.values():
        try:
            include_func = command.include_cli
        except AttributeError:
            continue

        include_func(subparsers)

    return parser
