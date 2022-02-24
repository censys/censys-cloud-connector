#!/usr/bin/env python3
"""Interact with the Censys Search API through the command line."""
from importlib.metadata import PackageNotFoundError
import sys

from .args import get_parser

try:
    from censys.cloud_connectors.common.version import __version__
except PackageNotFoundError:
    __version__ = "0.0.0"


def main():
    """Main cli function."""
    parser = get_parser()

    # Executes by subcommand
    args = parser.parse_args()

    if args.version:
        print(f"Censys Cloud Connectors Version: {__version__}")
        sys.exit(0)

    try:
        args.func(args)
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
