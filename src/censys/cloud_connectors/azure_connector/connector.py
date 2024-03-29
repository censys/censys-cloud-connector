"""Azure Cloud Connector."""
from collections.abc import Generator
from typing import Optional

from azure.core.exceptions import (
    AzureError,
    ClientAuthenticationError,
    ServiceRequestError,
)
from azure.identity import ClientSecretCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.storage.models import StorageAccount
from azure.storage.blob import BlobServiceClient, ContainerProperties
from msrest.serialization import Model as AzureModel

from censys.cloud_connectors.common.cloud_asset import AzureContainerAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.context import SuppressValidationError
from censys.cloud_connectors.common.enums import EventTypeEnum, ProviderEnum
from censys.cloud_connectors.common.exceptions import CensysAzureException
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
    possible_labels: set[str]
    scan_all_regions: bool

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
        self.possible_labels = set()
        self.scan_all_regions = settings.azure_refresh_all_regions

    def get_all_labels(self):
        """Get Azure labels."""
        subscription_client = SubscriptionClient(self.credentials)

        locations = subscription_client.subscriptions.list_locations(
            self.subscription_id
        )

        self.possible_labels.clear()

        for location in locations:
            self.possible_labels.add(
                f"{self.label_prefix}{self.subscription_id}/{location.name}"
            )

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
                    if self.scan_all_regions:
                        self.get_all_labels()

                    self.scan()

                    if self.scan_all_regions:
                        for label_not_found in self.possible_labels:
                            self.delete_seeds_by_label(label_not_found)
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
        """Get Azure IP addresses.

        Raises:
            CensysAzureException: If Azure reports an error.
        """
        network_client = NetworkManagementClient(self.credentials, self.subscription_id)

        try:
            assets = network_client.public_ip_addresses.list_all()

            for asset in assets:
                asset_dict = asset.as_dict()
                if ip_address := asset_dict.get("ip_address"):
                    with SuppressValidationError():
                        label = self.format_label(asset)
                        ip_seed = IpSeed(value=ip_address, label=label)
                        self.add_seed(ip_seed)
                        self.possible_labels.discard(label)

        except AzureError as error:
            raise CensysAzureException(
                message=f"Failed to get Azure IP Addresses: {error.message}"
            )

    def get_clusters(self):
        """Get Azure clusters.

        Raises:
            CensysAzureException: If Azure reports an error.
        """
        container_client = ContainerInstanceManagementClient(
            self.credentials, self.subscription_id
        )

        try:
            assets = container_client.container_groups.list()

            for asset in assets:
                asset_dict = asset.as_dict()
                if (
                    (ip_address_dict := asset_dict.get("ip_address"))
                    and (ip_address_dict.get("type") == "Public")
                    and (ip_address := ip_address_dict.get("ip"))
                ):
                    label = self.format_label(asset)
                    with SuppressValidationError():
                        ip_seed = IpSeed(value=ip_address, label=label)
                        self.add_seed(ip_seed)
                        self.possible_labels.discard(label)
                    if domain := ip_address_dict.get("fqdn"):
                        with SuppressValidationError():
                            domain_seed = DomainSeed(value=domain, label=label)
                            self.add_seed(domain_seed)
                            self.possible_labels.discard(label)

        except AzureError as error:
            raise CensysAzureException(
                message=f"Failed to get Azure Container Instances: {error.message}"
            )

    def get_sql_servers(self):
        """Get Azure SQL servers.

        Raises:
            CensysAzureException: If Azure reports an error.
        """
        sql_client = SqlManagementClient(self.credentials, self.subscription_id)

        try:
            assets = sql_client.servers.list()

            for asset in assets:
                asset_dict = asset.as_dict()
                if (
                    domain := asset_dict.get("fully_qualified_domain_name")
                ) and asset_dict.get("public_network_access") == "Enabled":
                    with SuppressValidationError():
                        label = self.format_label(asset)
                        domain_seed = DomainSeed(value=domain, label=label)
                        self.add_seed(domain_seed)
                        self.possible_labels.discard(label)

        except AzureError as error:
            raise CensysAzureException(
                message=f"Failed to get Azure SQL servers: {error.message}"
            )

    def get_dns_records(self):
        """Get Azure DNS records.

        Raises:
            CensysAzureException: If Azure reports an error.
        """
        dns_client = DnsManagementClient(self.credentials, self.subscription_id)

        try:
            zones = dns_client.zones.list()

            # Note: for loop is included in try/catch block because it's possible
            # for HttpResponseError to be raised while iterating through zones.
            for zone in zones:
                zone_dict = zone.as_dict()
                label = self.format_label(zone)
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
                            domain_seed = DomainSeed(value=domain_name, label=label)
                            self.add_seed(domain_seed)
                            self.possible_labels.discard(label)
                    if cname := asset_dict.get("cname_record", {}).get("cname"):
                        with SuppressValidationError():
                            domain_seed = DomainSeed(value=cname, label=label)
                            self.add_seed(domain_seed)
                            self.possible_labels.discard(label)
                    for a_record in asset_dict.get("a_records", []):
                        ip_address = a_record.get("ipv4_address")
                        if not ip_address:
                            continue

                        with SuppressValidationError():
                            ip_seed = IpSeed(value=ip_address, label=label)
                            self.add_seed(ip_seed)
                            self.possible_labels.discard(label)

        # Note: The generic AzureError is used to ensure the connector does not
        # fail entirely if the exception is not fatal.
        # See ticket AP-3180 for future improvements to error handling.
        except AzureError as error:
            raise CensysAzureException(
                message=f"Failed to get Azure DNS records: {error.message}"
            )

    def _list_containers(
        self, bucket_client: BlobServiceClient, account: StorageAccount
    ) -> Generator[ContainerProperties, None, None]:
        """List Azure containers.

        Args:
            bucket_client (BlobServiceClient): Blob service client.
            account (StorageAccount): Storage account.

        Yields:
            ContainerProperties: Azure container properties.

        Raises:
            CensysAzureException: If Azure reports an error.
        """
        try:
            yield from bucket_client.list_containers()
        except AzureError as error:
            raise CensysAzureException(
                message=f"Failed to get Azure containers for {account.name}: {error.message}"
            )

    def get_storage_containers(self):
        """Get Azure containers.

        Raises:
            CensysAzureException: If Azure reports an error.
        """
        storage_client = StorageManagementClient(self.credentials, self.subscription_id)
        try:
            accounts = storage_client.storage_accounts.list()

            for account in accounts:
                bucket_client = BlobServiceClient(
                    f"https://{account.name}.blob.core.windows.net/", self.credentials
                )
                label = self.format_label(account)
                account_dict = account.as_dict()
                if (custom_domain := account_dict.get("custom_domain")) and (
                    domain := custom_domain.get("name")
                ):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=domain, label=label)
                        self.add_seed(domain_seed)
                        self.possible_labels.discard(label)
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
                        raise CensysAzureException(
                            message=f"Failed to get Azure container {container} for {account.name}: {error.message}"
                        )

        except AzureError as error:
            raise CensysAzureException(
                message=f"Failed to get Azure storage accounts: {error.message}"
            )
