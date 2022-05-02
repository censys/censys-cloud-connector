"""Censys Cloud Connectors."""

__copyright__ = "Copyright 2022 Censys, Inc."

import os.path

try:  # pragma: no cover
    from importlib.metadata import version
except ImportError:  # pragma: no cover
    from importlib_metadata import version  # type: ignore

__version__: str = version("censys-cloud-connectors")


def get_connectors(ignore_prefix: str = "__") -> list[str]:
    """Get a list of all connectors.

    Args:
        ignore_prefix (str): Ignore connectors that start with this prefix.

    Returns:
        List[str]: A list of connector names.
    """
    excluded_dirs = ["common"]
    return [
        os.path.splitext(os.path.basename(x))[0]
        for x in os.listdir(os.path.dirname(__file__))
        if os.path.isdir(os.path.join(os.path.dirname(__file__), x))
        and x not in excluded_dirs
        and not x.startswith(ignore_prefix)
    ]


__all__ = ["__version__"] + get_connectors()
