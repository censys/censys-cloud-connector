"""Azure Cloud Connector."""
from collections.abc import AsyncGenerator
from typing import Any, Optional

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
)
from azure.identity.aio import ClientSecretCredential
from azure.mgmt.containerinstance.aio import ContainerInstanceManagementClient
from azure.mgmt.dns.aio import DnsManagementClient
from azure.mgmt.dns.models import ZoneListResult
from azure.mgmt.network.aio import NetworkManagementClient
from azure.mgmt.sql.aio import SqlManagementClient
from azure.mgmt.storage.aio import StorageManagementClient
from azure.mgmt.storage.models import StorageAccount
from azure.storage.blob import ContainerProperties
from azure.storage.blob.aio import BlobServiceClient

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

    async def scan(  # type: ignore
        self,
        provider_settings: AzureSpecificSettings,
        credentials: ClientSecretCredential,
        subscription_id: str,
    ):
        """Scan Azure Subscription.

        Args:
            provider_settings (AzureSpecificSettings): Azure provider settings.
            credentials (ClientSecretCredential): Azure credentials.
            subscription_id (str): Azure subscription ID.
        """
        with Healthcheck(
            self.settings,
            provider_settings,
            provider={"subscription_id": subscription_id},
            exception_map={
                ClientAuthenticationError: "PERMISSIONS",
            },
        ):
            await super().scan(
                provider_settings,
                credentials=credentials,
                subscription_id=subscription_id,
            )

    async def scan_all(self):
        """Scan all Azure Subscriptions."""
        provider_settings: dict[
            tuple, AzureSpecificSettings
        ] = self.settings.providers.get(  # type: ignore
            self.provider, {}  # type: ignore
        )
        for provider_setting in provider_settings.values():
            self.provider_settings = provider_setting
            credentials = ClientSecretCredential(
                tenant_id=provider_setting.tenant_id,
                client_id=provider_setting.client_id,
                client_secret=provider_setting.client_secret,
            )
            for subscription_id in provider_setting.subscription_id:
                self.logger.info(f"Scanning Azure Subscription {subscription_id}")
                try:
                    await self.scan(provider_setting, credentials, subscription_id)
                except Exception as e:
                    self.logger.error(
                        f"Unable to scan Azure Subscription {subscription_id}."
                        f" Error: {e}"
                    )
                    self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)

            await credentials.close()

    def format_label(
        self,
        asset: Any,
        subscription_id: str,
    ) -> str:
        """Format Azure asset label.

        Args:
            asset (Any): Azure asset.
            subscription_id (str): Azure subscription ID.

        Returns:
            str: Formatted label.

        Raises:
            ValueError: If asset has no location.
        """
        asset_location: Optional[str] = getattr(asset, "location", None)
        if not asset_location:
            raise ValueError("Asset has no location.")
        return f"{self.label_prefix}{subscription_id}/{asset_location}"

    async def get_ip_addresses(
        self,
        _: AzureSpecificSettings,
        credentials: ClientSecretCredential,
        subscription_id: str,
        current_service: AzureResourceTypes,
    ):
        """Get Azure IP addresses.

        Args:
            credentials (ClientSecretCredential): Azure credentials.
            subscription_id (str): Azure subscription ID.
            current_service (AzureResourceTypes): Azure resource type.
        """
        network_client = NetworkManagementClient(credentials, subscription_id)  # type: ignore
        async for asset in network_client.public_ip_addresses.list_all():
            asset_dict = asset.as_dict()
            if ip_address := asset_dict.get("ip_address"):
                with SuppressValidationError():
                    ip_seed = IpSeed(
                        value=ip_address,
                        label=self.format_label(asset, subscription_id),
                    )
                    self.add_seed(ip_seed, service=current_service)

        await network_client.close()

    async def get_clusters(
        self,
        _: AzureSpecificSettings,
        credentials: ClientSecretCredential,
        subscription_id: str,
        current_service: AzureResourceTypes,
    ):
        """Get Azure clusters.

        Args:
            credentials (ClientSecretCredential): Azure credentials.
            subscription_id (str): Azure subscription ID.
            current_service (AzureResourceTypes): Azure resource type.
        """
        container_client = ContainerInstanceManagementClient(
            credentials, subscription_id  # type: ignore
        )
        async for asset in container_client.container_groups.list():
            asset_dict = asset.as_dict()
            if (
                (ip_address_dict := asset_dict.get("ip_address"))
                and (ip_address_dict.get("type") == "Public")
                and (ip_address := ip_address_dict.get("ip"))
            ):
                with SuppressValidationError():
                    ip_seed = IpSeed(
                        value=ip_address,
                        label=self.format_label(asset, subscription_id),
                    )
                    self.add_seed(ip_seed, service=current_service)
                if domain := ip_address_dict.get("fqdn"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(
                            value=domain,
                            label=self.format_label(asset, subscription_id),
                        )
                        self.add_seed(domain_seed, service=current_service)

        await container_client.close()

    async def get_sql_servers(
        self,
        _: AzureSpecificSettings,
        credentials: ClientSecretCredential,
        subscription_id: str,
        current_service: AzureResourceTypes,
    ):
        """Get Azure SQL servers.

        Args:
            credentials (ClientSecretCredential): Azure credentials.
            subscription_id (str): Azure subscription ID.
            current_service (AzureResourceTypes): Azure resource type.
        """
        sql_client = SqlManagementClient(credentials, subscription_id)  # type: ignore
        async for asset in sql_client.servers.list():
            asset_dict = asset.as_dict()
            if (
                domain := asset_dict.get("fully_qualified_domain_name")
            ) and asset_dict.get("public_network_access") == "Enabled":
                with SuppressValidationError():
                    domain_seed = DomainSeed(
                        value=domain, label=self.format_label(asset, subscription_id)
                    )
                    self.add_seed(domain_seed, service=current_service)

        await sql_client.close()

    async def _list_dns_zones(
        self, dns_client: DnsManagementClient
    ) -> AsyncGenerator[ZoneListResult, None]:
        """List all DNS zones.

        Args:
            dns_client (DnsManagementClient): Azure DNS client.

        Yields:
            AsyncGenerator[ZoneListResult, None]: DNS zones.
        """
        try:
            async for zone in dns_client.zones.list():
                yield zone
        except HttpResponseError as error:
            self.logger.error(
                f"Failed to get Azure DNS records: {error.reason} or the subscription"
                " does not have access to the Microsoft.Network resource provider."
            )
            await dns_client.close()

    async def get_dns_records(
        self,
        _: AzureSpecificSettings,
        credentials: ClientSecretCredential,
        subscription_id: str,
        current_service: AzureResourceTypes,
    ):
        """Get Azure DNS records.

        Args:
            credentials (ClientSecretCredential): Azure credentials.
            subscription_id (str): Azure subscription ID.
            current_service (AzureResourceTypes): Azure resource type.
        """
        dns_client = DnsManagementClient(credentials, subscription_id)  # type: ignore

        async for zone in self._list_dns_zones(dns_client):
            zone_dict = zone.as_dict()
            # TODO: Do we need to check if zone is public? (ie. do we care?)
            if zone_dict.get("zone_type") != "Public":  # pragma: no cover
                continue
            zone_resource_group = zone_dict.get("id").split("/")[4]
            async for asset in dns_client.record_sets.list_all_by_dns_zone(  # type: ignore
                zone_resource_group, zone_dict.get("name")
            ):
                asset_dict = asset.as_dict()
                if domain_name := asset_dict.get("fqdn"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(
                            value=domain_name,
                            label=self.format_label(zone, subscription_id),
                        )
                        self.add_seed(domain_seed, service=current_service)
                if cname := asset_dict.get("cname_record", {}).get("cname"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(
                            value=cname, label=self.format_label(zone, subscription_id)
                        )
                        self.add_seed(domain_seed, service=current_service)
                for a_record in asset_dict.get("a_records", []):
                    ip_address = a_record.get("ipv4_address")
                    if not ip_address:
                        continue

                    with SuppressValidationError():
                        ip_seed = IpSeed(
                            value=ip_address,
                            label=self.format_label(zone, subscription_id),
                        )
                        self.add_seed(ip_seed, service=current_service)

        await dns_client.close()

    async def _list_containers(
        self, blob_service_client: BlobServiceClient, account: StorageAccount
    ) -> AsyncGenerator[ContainerProperties, None]:
        """List Azure containers.

        Args:
            blob_service_client (BlobServiceClient): Blob service client.
            account (StorageAccount): Storage account.

        Yields:
            ContainerProperties: Azure container properties.
        """
        try:
            async for container in blob_service_client.list_containers():
                yield container
        except HttpResponseError as error:
            self.logger.error(
                f"Failed to get Azure containers for {account.name}: {error.message}"
            )
            await blob_service_client.close()

    async def get_storage_container_url(
        self, blob_service_client: BlobServiceClient, container: ContainerProperties
    ) -> str:
        """Get Azure container URL.

        Args:
            blob_service_client (BlobServiceClient): Blob service client.
            container (ContainerProperties): Azure container properties.

        Returns:
            str: Azure container URL.
        """
        container_client = blob_service_client.get_container_client(container)
        container_url = container_client.url
        await container_client.close()
        return container_url

    async def get_storage_containers(
        self,
        _: AzureSpecificSettings,
        credentials: ClientSecretCredential,
        subscription_id: str,
        current_service: AzureResourceTypes,
    ):
        """Get Azure containers.

        Args:
            credentials (ClientSecretCredential): Azure credentials.
            subscription_id (str): Azure subscription ID.
            current_service (AzureResourceTypes): Azure resource type.
        """
        storage_client = StorageManagementClient(credentials, subscription_id)  # type: ignore

        async for account in storage_client.storage_accounts.list():
            account_dict = account.as_dict()
            if (custom_domain := account_dict.get("custom_domain")) and (
                domain := custom_domain.get("name")
            ):
                with SuppressValidationError():
                    domain_seed = DomainSeed(
                        value=domain, label=self.format_label(account, subscription_id)
                    )
                    self.add_seed(domain_seed, service=current_service)
            uid = f"{subscription_id}/{credentials._client._tenant_id}/{account.name}"

            account_url = f"https://{account.name}.blob.core.windows.net/"
            if (
                account.primary_endpoints is not None
                and account.primary_endpoints.blob is not None
            ):
                account_url = account.primary_endpoints.blob
            blob_service_client = BlobServiceClient(account_url, credentials)  # type: ignore
            async for container in self._list_containers(blob_service_client, account):  # type: ignore
                try:
                    container_url = await self.get_storage_container_url(
                        blob_service_client, container
                    )
                    with SuppressValidationError():
                        container_asset = AzureContainerAsset(  # type: ignore
                            value=container_url,
                            uid=uid,
                            scan_data={
                                "accountNumber": subscription_id,
                                "publicAccess": container.public_access,
                                "location": account.location,
                            },
                        )
                        self.add_cloud_asset(container_asset, service=current_service)
                except ServiceRequestError as error:  # pragma: no cover
                    self.logger.error(
                        f"Failed to get Azure container {container} for {account.name}:"
                        f" {error.message}"
                    )

            await blob_service_client.close()

        await storage_client.close()
