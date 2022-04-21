"""Azure Cloud Connector."""
import contextlib
from typing import Callable, Optional

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
)
from azure.identity import ClientSecretCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient
from msrest.serialization import Model as AzureModel

from censys.cloud_connectors.common.cloud_asset import AzureContainerAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .enums import AzureResourceTypes
from .settings import AzureSpecificSettings


class AzureCloudConnector(CloudConnector):
    """Azure Cloud Connector."""

    provider = ProviderEnum.AZURE
    subscription_id: str
    credentials: ClientSecretCredential
    provider_settings: AzureSpecificSettings

    seed_scanners: dict[AzureResourceTypes, Callable[[], None]]
    cloud_asset_scanners: dict[AzureResourceTypes, Callable[[], None]]

    def __init__(self, settings: Settings):
        """Initialize Azure Cloud Connector.

        Args:
            settings (Settings): Settings.
        """
        super().__init__(settings)
        self.seed_scanners = {
            AzureResourceTypes.PUBLIC_IP_ADDRESSES: self.get_ip_addresses,
            AzureResourceTypes.CONTAINER_GROUPS: self.get_clusters,
            AzureResourceTypes.SQL_SERVERS: self.get_sql_servers,
            AzureResourceTypes.DNS_ZONES: self.get_dns_records,
        }
        self.cloud_asset_scanners = {
            AzureResourceTypes.STORAGE_ACCOUNTS: self.get_storage_containers,
        }

    def scan(self):
        """Scan Azure."""
        with contextlib.suppress(ClientAuthenticationError):
            super().scan()

    def scan_all(self):
        """Scan all Azure Subscriptions."""
        provider_settings: dict[
            tuple, AzureSpecificSettings
        ] = self.settings.providers.get(self.provider, {})
        for provider_setting in provider_settings.values():
            self.provider_settings = provider_setting
            self.credentials = ClientSecretCredential(
                tenant_id=provider_setting.tenant_id,
                client_id=provider_setting.client_id,
                client_secret=provider_setting.client_secret,
            )
            for subscription_id in self.provider_settings.subscription_id:
                self.logger.info(f"Scanning Azure Subscription {subscription_id}")
                self.subscription_id = subscription_id
                self.scan()

    def format_label(self, asset: AzureModel) -> str:
        """Format Azure asset label.

        Args:
            asset (AzureModel): Azure asset.

        Returns:
            str: Formatted label.

        Raises:
            ValueError: If asset has no location.
        """
        asset_location: Optional[str] = getattr(asset, "location", None)
        if not asset_location:
            raise ValueError("Asset has no location.")
        return f"{self.label_prefix}{self.subscription_id}/{asset_location}"

    def get_ip_addresses(self):
        """Get Azure IP addresses."""
        network_client = NetworkManagementClient(self.credentials, self.subscription_id)
        for asset in network_client.public_ip_addresses.list_all():
            asset_dict = asset.as_dict()
            if ip_address := asset_dict.get("ip_address"):
                self.add_seed(IpSeed(value=ip_address, label=self.format_label(asset)))

    def get_clusters(self):
        """Get Azure clusters."""
        container_client = ContainerInstanceManagementClient(
            self.credentials, self.subscription_id
        )
        for asset in container_client.container_groups.list():
            asset_dict = asset.as_dict()
            if (
                (ip_address_dict := asset_dict.get("ip_address"))
                and (ip_address_dict.get("type") == "Public")
                and (ip_address := ip_address_dict.get("ip"))
            ):
                self.add_seed(IpSeed(value=ip_address, label=self.format_label(asset)))
                if domain := ip_address_dict.get("fqdn"):
                    self.add_seed(
                        DomainSeed(value=domain, label=self.format_label(asset))
                    )

    def get_sql_servers(self):
        """Get Azure SQL servers."""
        sql_client = SqlManagementClient(self.credentials, self.subscription_id)

        for asset in sql_client.servers.list():
            asset_dict = asset.as_dict()
            if (
                domain := asset_dict.get("fully_qualified_domain_name")
            ) and asset_dict.get("public_network_access") == "Enabled":
                self.add_seed(DomainSeed(value=domain, label=self.format_label(asset)))

    def get_dns_records(self):
        """Get Azure DNS records."""
        dns_client = DnsManagementClient(self.credentials, self.subscription_id)

        try:
            zones = list(dns_client.zones.list())
        except HttpResponseError as error:
            # TODO: Better error handling here
            self.logger.error(
                f"Failed to get Azure DNS records: {error.message}", exc_info=True
            )
            return

        for zone in zones:
            zone_dict = zone.as_dict()
            # TODO: Do we need to check if zone is public? (ie. do we care?)
            if zone_dict.get("zone_type") != "Public":  # pragma: no cover
                continue
            zone_resource_group = zone_dict.get("id").split("/")[4]
            for asset in dns_client.record_sets.list_all_by_dns_zone(
                zone_resource_group, zone_dict.get("name")
            ):
                asset_dict = asset.as_dict()
                if domain := asset_dict.get("fqdn"):
                    self.add_seed(
                        DomainSeed(value=domain, label=self.format_label(zone))
                    )
                    if a_records := asset_dict.get("a_records"):
                        for a_record in a_records:
                            if ip := a_record.get("ipv4_address"):
                                self.add_seed(
                                    IpSeed(value=ip, label=self.format_label(zone))
                                )
                    if (cname_record := asset_dict.get("cname_record")) and (
                        cname := cname_record.get("cname")
                    ):
                        self.add_seed(
                            DomainSeed(value=cname, label=self.format_label(zone))
                        )

    def get_seeds(self):
        """Get Azure seeds."""
        for seed_type, seed_scanner in self.seed_scanners.items():
            if (
                self.provider_settings.ignore
                and seed_type in self.provider_settings.ignore
            ):
                self.logger.debug(f"Skipping {seed_type}")
                continue
            self.logger.debug(f"Scanning {seed_type}")
            seed_scanner()

    def get_storage_containers(self):
        """Get Azure containers."""
        storage_client = StorageManagementClient(self.credentials, self.subscription_id)

        for account in storage_client.storage_accounts.list():
            bucket_client = BlobServiceClient(
                f"https://{account.name}.blob.core.windows.net/", self.credentials
            )
            account_dict = account.as_dict()
            if custom_domain := account_dict.get("custom_domain"):
                self.add_seed(
                    DomainSeed(
                        value=custom_domain.get("name"),
                        label=self.format_label(account),
                    )
                )
            uid = f"{self.subscription_id}/{self.credentials._tenant_id}/{account.name}"
            for container in bucket_client.list_containers():
                try:
                    container_client = bucket_client.get_container_client(container)
                    container_url = container_client.url
                    self.add_cloud_asset(
                        AzureContainerAsset(
                            value=container_url,
                            uid=uid,
                            scan_data={
                                "accountNumber": self.subscription_id,
                                "publicAccess": container.public_access,
                                "location": account.location,
                            },
                        )
                    )
                except ServiceRequestError as error:  # pragma: no cover
                    self.logger.error(
                        f"Failed to get Azure container {container} for {account.name}: {error.message}",
                        exc_info=True,
                    )

    def get_cloud_assets(self):
        """Get Azure cloud assets."""
        for cloud_asset_type, cloud_asset_scanner in self.cloud_asset_scanners.items():
            if (
                self.provider_settings.ignore
                and cloud_asset_type in self.provider_settings.ignore
            ):
                self.logger.debug(f"Skipping {cloud_asset_type}")
                continue
            self.logger.debug(f"Scanning {cloud_asset_type}")
            cloud_asset_scanner()
