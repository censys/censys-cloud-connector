"""Azure Cloud Connector."""
from collections.abc import Generator
from typing import Optional

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
from azure.mgmt.storage.models import StorageAccount
from azure.storage.blob import BlobServiceClient, ContainerProperties
from msrest.serialization import Model as AzureModel

from censys.cloud_connectors.common.cloud_asset import AzureContainerAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.context import SuppressValidationError
from censys.cloud_connectors.common.enums import EventTypeEnum, ProviderEnum
from censys.cloud_connectors.common.healthcheck import Healthcheck
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
        """Scan Azure Subscription."""
        with Healthcheck(
            self.settings,
            self.provider_settings,
            provider={"subscription_id": self.subscription_id},
            exception_map={
                ClientAuthenticationError: "PERMISSIONS",
            },
        ):
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
                try:
                    self.scan()
                except Exception as e:
                    self.logger.error(
                        f"Unable to scan Azure Subscription {subscription_id}. Error: {e}"
                    )
                    self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)
                self.subscription_id = None

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
                with SuppressValidationError():
                    ip_seed = IpSeed(value=ip_address, label=self.format_label(asset))
                    self.add_seed(ip_seed)

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
                with SuppressValidationError():
                    ip_seed = IpSeed(value=ip_address, label=self.format_label(asset))
                    self.add_seed(ip_seed)
                if domain := ip_address_dict.get("fqdn"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(
                            value=domain, label=self.format_label(asset)
                        )
                        self.add_seed(domain_seed)

    def get_sql_servers(self):
        """Get Azure SQL servers."""
        sql_client = SqlManagementClient(self.credentials, self.subscription_id)

        for asset in sql_client.servers.list():
            asset_dict = asset.as_dict()
            if (
                domain := asset_dict.get("fully_qualified_domain_name")
            ) and asset_dict.get("public_network_access") == "Enabled":
                with SuppressValidationError():
                    domain_seed = DomainSeed(
                        value=domain, label=self.format_label(asset)
                    )
                    self.add_seed(domain_seed)

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
                if domain_name := asset_dict.get("fqdn"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(
                            value=domain_name, label=self.format_label(zone)
                        )
                        self.add_seed(domain_seed)
                if cname := asset_dict.get("cname_record", {}).get("cname"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(
                            value=cname, label=self.format_label(zone)
                        )
                        self.add_seed(domain_seed)
                for a_record in asset_dict.get("a_records", []):
                    ip_address = a_record.get("ipv4_address")
                    if not ip_address:
                        continue

                    with SuppressValidationError():
                        ip_seed = IpSeed(
                            value=ip_address, label=self.format_label(zone)
                        )
                        self.add_seed(ip_seed)

    def _list_containers(
        self, bucket_client: BlobServiceClient, account: StorageAccount
    ) -> Generator[ContainerProperties, None, None]:
        """List Azure containers.

        Args:
            bucket_client (BlobServiceClient): Blob service client.
            account (StorageAccount): Storage account.

        Yields:
            ContainerProperties: Azure container properties.
        """
        try:
            yield from bucket_client.list_containers()
        except HttpResponseError as error:
            self.logger.error(
                f"Failed to get Azure containers for {account.name}: {error.message}"
            )
            return

    def get_storage_containers(self):
        """Get Azure containers."""
        storage_client = StorageManagementClient(self.credentials, self.subscription_id)

        for account in storage_client.storage_accounts.list():
            bucket_client = BlobServiceClient(
                f"https://{account.name}.blob.core.windows.net/", self.credentials
            )
            account_dict = account.as_dict()
            if (custom_domain := account_dict.get("custom_domain")) and (
                domain := custom_domain.get("name")
            ):
                with SuppressValidationError():
                    domain_seed = DomainSeed(
                        value=domain, label=self.format_label(account)
                    )
                    self.add_seed(domain_seed)
            uid = f"{self.subscription_id}/{self.credentials._tenant_id}/{account.name}"

            for container in self._list_containers(bucket_client, account):
                try:
                    container_client = bucket_client.get_container_client(container)
                    container_url = container_client.url
                    with SuppressValidationError():
                        container_asset = AzureContainerAsset(
                            value=container_url,
                            uid=uid,
                            scan_data={
                                "accountNumber": self.subscription_id,
                                "publicAccess": container.public_access,
                                "location": account.location,
                            },
                        )
                        self.add_cloud_asset(container_asset)
                except ServiceRequestError as error:  # pragma: no cover
                    self.logger.error(
                        f"Failed to get Azure container {container} for {account.name}: {error.message}"
                    )
