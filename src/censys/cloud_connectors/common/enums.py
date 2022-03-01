"""Platforms supported by Censys."""
from enum import Enum


class PlatformEnum(str, Enum):
    """Platforms supported by Censys."""

    AWS = "AWS"
    AZURE = "Azure"
    GCP = "GCP"

    def __str__(self) -> str:
        """Gets the string representation of the platform.

        Returns:
            str: The string representation of the platform.
        """
        return self.value

    def label(self) -> str:
        """Gets the label of the platform.

        Returns:
            str: The label of the platform.
        """
        return self.name

    def module_path(self) -> str:
        """Gets the module path of the platform.

        Returns:
            str: The module path of the platform.
        """
        return f"censys.cloud_connectors.{self.name.lower()}"
