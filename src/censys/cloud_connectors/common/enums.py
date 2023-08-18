"""Enums for Cloud Connectors."""
from enum import Enum, EnumMeta


class CaseInsensitiveEnumMeta(EnumMeta):
    """Case insensitive enum metaclass."""

    def __getitem__(self, item):
        """Get enum by name.

        Args:
            item: Enum name.

        Returns:
            Enum value.
        """
        if isinstance(item, str):
            item = item.upper()
        return super().__getitem__(item)


class ProviderEnum(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """Cloud Service Providers (CSP) supported by Censys."""

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
        return f"censys.cloud_connectors.{self.name.lower()}_connector"


class EventTypeEnum(str, Enum, metaclass=CaseInsensitiveEnumMeta):
    """Event types supported by Censys."""

    SCAN_STARTED = "SCAN_STARTED"
    SCAN_FAILED = "SCAN_FAILED"
    SCAN_FINISHED = "SCAN_FINISHED"
    SEED_FOUND = "SEED_FOUND"
    CLOUD_ASSET_FOUND = "CLOUD_ASSET_FOUND"
    SEEDS_SUBMITTED = "SEEDS_SUBMITTED"
    CLOUD_ASSETS_SUBMITTED = "CLOUD_ASSETS_SUBMITTED"
    SEEDS_DELETED = "SEEDS_DELETED"
