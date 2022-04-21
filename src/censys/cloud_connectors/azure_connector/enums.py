"""Enums for Azure."""
from enum import Enum


class AzureResourceTypes(str, Enum):
    """Azure resource types."""

    PUBLIC_IP_ADDRESSES = "Microsoft.Network/publicIPAddresses"
    CONTAINER_GROUPS = "Microsoft.ContainerInstance/containerGroups"
    SQL_SERVERS = "Microsoft.Sql/servers"
    DNS_ZONES = "Microsoft.Network/dnszones"
    STORAGE_ACCOUNTS = "Microsoft.Storage/storageAccounts"
