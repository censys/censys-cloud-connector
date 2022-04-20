"""Main function for Google Scheduled Function."""
from typing import Any

from censys.cloud_connectors.common.cli import main as invoke_cli


def scan(event: dict, context: Any) -> None:
    """Scan the infrastructure.

    Args:
        event (dict): The dictionary with data specific to this type of event.
        context (Any): Metadata of triggering event.

    Raises:
        SystemExit: If the scan failed.
    """
    try:
        invoke_cli(["scan"])
    except SystemExit as e:
        if e.code != 0:
            raise
