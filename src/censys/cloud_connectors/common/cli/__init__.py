#!/usr/bin/env python3
"""Interact with the Censys Search API through the command line."""
import sys
from typing import Optional

from censys.cloud_connectors import __version__

from . import commands
from .args import get_parser

__commands__ = commands.__all__
__all__ = ["__commands__"]


def main(manual_args: Optional[list[str]] = None):
    """Main cli function.

    Args:
        manual_args (Optional[list[str]]): Optional; The arguments to pass to the parser.
    """
    parser = get_parser()

    # Executes by subcommand
    args = parser.parse_args(manual_args)

    if args.version:
        print(f"Censys Cloud Connectors Version: {__version__}")
        sys.exit(0)

    try:
        args.func(args)
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
