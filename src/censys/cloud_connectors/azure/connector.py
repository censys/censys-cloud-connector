"""Azure Cloud Connector."""
from typing import List

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
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .settings import AzureSpecificSettings


class AzureCloudConnector(CloudConnector):
    """Azure Cloud Connector."""

    platform = "azure"
    subscription_id: str
    credentials: ClientSecretCredential
    platform_settings: AzureSpecificSettings

    def __init__(self, settings: Settings):
        """Initialize Azure Cloud Connector.

        Args:
            settings (Settings): Settings.
        """
        super().__init__(self.platform, settings)

    def scan(self) -> None:
        """Scan Azure.

        Returns:
            None
        """
        try:
            return super().scan()
        except ClientAuthenticationError as error:
            self.logger.error(
                f"Authentication error for {self.platform} subscription {self.subscription_id}: {error}"
            )

    def scan_all(self):
        """Scan all Azure Subscriptions."""
        platform_settings: List[AzureSpecificSettings] = self.settings.platforms.get(
            self.platform, []
        )
        for platform_setting in platform_settings:
            # TODO: Add support for disabling specific cloud assets
            self.platform_settings = platform_setting
            self.credentials = ClientSecretCredential(
                tenant_id=platform_setting.tenant_id,
                client_id=platform_setting.client_id,
                client_secret=platform_setting.client_secret,
            )
            if not isinstance(self.platform_settings.subscription_id, list):
                self.platform_settings.subscription_id = [
                    self.platform_settings.subscription_id
                ]

            for subscription_id in self.platform_settings.subscription_id:
                self.subscription_id = subscription_id
                self.scan()

    def _format_label(self, asset: AzureModel):
        """Format Azure asset label.

        Args:
            asset (AzureModel): Azure asset.

        Returns:
            str: Formatted label.

        Raises:
            ValueError: If asset does not have a location.
        """
        if not hasattr(asset, "location"):
            raise ValueError("Asset does not have location.")
        return f"{self.label_prefix}{self.subscription_id}/{asset.location}"  # type: ignore

    def get_seeds(self):
        """Get Azure seeds."""
        self._get_ip_addresses()
        self._get_clusters()
        self._get_sql_servers()
        self._get_dns_records()

    def _get_ip_addresses(self):
        """Get Azure IP addresses."""
        network_client = NetworkManagementClient(self.credentials, self.subscription_id)
        for asset in network_client.public_ip_addresses.list_all():
            asset_dict = asset.as_dict()
            if ip_address := asset_dict.get("ip_address"):
                self.add_seed(IpSeed(value=ip_address, label=self._format_label(asset)))

    def _get_clusters(self):
        """Get Azure clusters."""
        container_client = ContainerInstanceManagementClient(
            self.credentials, self.subscription_id
        )
        for asset in container_client.container_groups.list():
            asset_dict = asset.as_dict()
            if (ip_address := asset_dict.get("ip_address")) and ip_address.get(
                "type"
            ) == "Public":
                self.add_seed(
                    IpSeed(value=ip_address.get("ip"), label=self._format_label(asset))
                )
                if domain := ip_address.get("fqdn"):
                    self.add_seed(
                        DomainSeed(value=domain, label=self._format_label(asset))
                    )

    def _get_sql_servers(self):
        """Get Azure SQL servers."""
        sql_client = SqlManagementClient(self.credentials, self.subscription_id)

        for asset in sql_client.servers.list():
            asset_dict = asset.as_dict()
            if (
                domain := asset_dict.get("fully_qualified_domain_name")
            ) and asset_dict.get("public_network_access") == "Enabled":
                self.add_seed(DomainSeed(value=domain, label=self._format_label(asset)))

    def _get_dns_records(self):
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
            if zone_dict.get("zone_type") != "Public":
                continue
            zone_resource_group = zone_dict.get("id").split("/")[4]
            for asset in dns_client.record_sets.list_all_by_dns_zone(
                zone_resource_group, zone_dict.get("name")
            ):
                asset_dict = asset.as_dict()
                if domain := asset_dict.get("fqdn"):
                    # TODO: Add support for CNAME records
                    self.add_seed(
                        DomainSeed(value=domain, label=self._format_label(zone))
                    )
                    if a_records := asset_dict.get("a_records"):
                        for a_record in a_records:
                            if ip := a_record.get("ipv4_address"):
                                self.add_seed(
                                    IpSeed(value=ip, label=self._format_label(zone))
                                )

    def get_cloud_assets(self):
        """Get Azure cloud assets."""
        self._get_storage_containers()

    def _get_storage_containers(self):
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
                        label=self._format_label(account),
                    )
                )
            for container in bucket_client.list_containers():
                try:
                    container_client = bucket_client.get_container_client(container)
                    container_url = container_client.url
                    self.add_cloud_asset(
                        AzureContainerAsset(
                            value=container_url,
                            uid=f"{self.subscription_id}/{self.credentials._tenant_id}/{account.name}",
                            scan_data={
                                "accountNumber": self.subscription_id,
                                "publicAccess": container.public_access,
                            },
                        )
                    )
                except ServiceRequestError as e:
                    self.logger.error(
                        f"Failed to get Azure container {container} for {account.name}: {e}"
                    )


__connector__ = AzureCloudConnector
