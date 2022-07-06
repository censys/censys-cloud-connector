"""Enums for Azure."""
from enum import Enum


class AzureResourceTypes(str, Enum):
    """Azure resource types."""

    PUBLIC_IP_ADDRESSES = "Microsoft.Network/publicIPAddresses"
    CONTAINER_GROUPS = "Microsoft.ContainerInstance/containerGroups"
    SQL_SERVERS = "Microsoft.Sql/servers"
    DNS_ZONES = "Microsoft.Network/dnszones"
    STORAGE_ACCOUNTS = "Microsoft.Storage/storageAccounts"


class AzureMessages(str, Enum):
    """Azure messages."""

    ERROR_FAILED_TO_VERIFY_SERVICE_PRINCIPAL = (
        "Failed to verify Azure Service Principal."
    )
    ERROR_NO_SUBSCRIPTIONS_SELECTED = "No subscriptions selected."
    ERROR_NO_SUBSCRIPTIONS_FOUND = "No subscriptions found."

    def __str__(self) -> str:
        """Get the string representation of the message.

        Returns:
            str: The string representation of the message.
        """
        return self.value
