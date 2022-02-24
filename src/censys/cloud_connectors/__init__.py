"""Censys Cloud Connectors."""

__copyright__ = "Copyright 2022 Censys, Inc."

import os.path
from typing import List


def get_connectors(
    ignore_prefix: str = "__", exclude_dirs: List[str] = ["common"]
) -> List[str]:
    """Get a list of all connectors.

    Args:
        ignore_prefix (str): Ignore connectors that start with this prefix.
        exclude_dirs (List[str]): A list of directories to exclude.

    Returns:
        List[str]: A list of connector names.
    """
    return [
        os.path.splitext(os.path.basename(x))[0]
        for x in os.listdir(os.path.dirname(__file__))
        if os.path.isdir(os.path.join(os.path.dirname(__file__), x))
        and x not in exclude_dirs
        and not x.startswith(ignore_prefix)
    ]


__connectors__ = get_connectors()
__all__ = __connectors__
