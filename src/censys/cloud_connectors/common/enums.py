"""Enums for Cloud Connectors."""
from enum import Enum


class ProviderEnum(str, Enum):
    """Providers supported by Censys."""

    AWS = "AWS"
    AZURE = "Azure"
    GCP = "GCP"

    def __str__(self) -> str:
        """Gets the string representation of the provider.

        Returns:
            str: The string representation of the provider.
        """
        return self.value

    def label(self) -> str:
        """Gets the label of the provider.

        Returns:
            str: The label of the provider.
        """
        return self.name

    def module_path(self) -> str:
        """Gets the module path of the provider.

        Returns:
            str: The module path of the provider.
        """
        return f"censys.cloud_connectors.{self.name.lower()}"
