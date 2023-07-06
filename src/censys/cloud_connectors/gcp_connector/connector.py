"""Gcp Cloud Connector."""
import json
from pathlib import Path
from typing import Optional, Union

from google.api_core import exceptions
from google.cloud import securitycenter_v1
from google.cloud.securitycenter_v1.services.security_center.pagers import (
    ListAssetsAsyncPager,
)
from google.cloud.securitycenter_v1.types import ListAssetsResponse
from google.oauth2 import service_account

from censys.cloud_connectors.common.cloud_asset import GcpStorageBucketAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.context import SuppressValidationError
from censys.cloud_connectors.common.enums import EventTypeEnum, ProviderEnum
from censys.cloud_connectors.common.healthcheck import Healthcheck
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .enums import GcpSecurityCenterResourceTypes
from .settings import GcpSpecificSettings


class GcpCloudConnector(CloudConnector):
    """Gcp Cloud Connector."""

    provider = ProviderEnum.GCP
    # organization_id: int
    # credentials: service_account.Credentials
    # provider_settings: GcpSpecificSettings
    # security_center_client: securitycenter_v1.SecurityCenterAsyncClient

    def __init__(self, settings: Settings):
        """Initialize Gcp Cloud Connector.

        Args:
            settings (Settings): Settings.
        """
        super().__init__(settings)
        self.seed_scanners = {
            GcpSecurityCenterResourceTypes.COMPUTE_INSTANCE: self.get_compute_instances,
            GcpSecurityCenterResourceTypes.COMPUTE_ADDRESS: self.get_compute_addresses,
            GcpSecurityCenterResourceTypes.CONTAINER_CLUSTER: self.get_container_clusters,
            GcpSecurityCenterResourceTypes.CLOUD_SQL_INSTANCE: self.get_cloud_sql_instances,
            GcpSecurityCenterResourceTypes.DNS_ZONE: self.get_dns_records,
        }
        self.cloud_asset_scanners = {
            GcpSecurityCenterResourceTypes.STORAGE_BUCKET: self.get_storage_buckets,
        }

    async def scan(self, provider_settings: GcpSpecificSettings):  # type: ignore
        """Scan Gcp.

        Scans Gcp for assets and seeds.

        Args:
            provider_settings (GcpSpecificSettings): Gcp settings.

        Raises:
            ValueError: If the service account credentials file is invalid.
        """
        try:
            with Healthcheck(
                self.settings,
                provider_settings,
                exception_map={
                    exceptions.Unauthenticated: "PERMISSIONS",
                    exceptions.PermissionDenied: "PERMISSIONS",
                },
            ):
                key_file_path = (
                    Path(self.settings.secrets_dir)
                    / provider_settings.service_account_json_file
                )
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        str(key_file_path)
                    )
                except ValueError as e:
                    self.logger.error(
                        "Failed to load service account credentials from"
                        f" {key_file_path}: {e}"
                    )
                    raise

                security_center_client = securitycenter_v1.SecurityCenterAsyncClient(
                    credentials=credentials
                )
                self.logger.info(
                    f"Scanning GCP organization {provider_settings.organization_id}"
                )
                await super().scan(
                    provider_settings, security_center_client=security_center_client
                )
        except Exception as e:
            self.logger.error(
                (
                    "Unable to scan GCP organization"
                    f" {provider_settings.organization_id}. Error: {e}"
                ),
            )
            self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)

    async def scan_all(self):
        """Scan all Gcp Organizations."""
        provider_settings: dict[
            tuple, GcpSpecificSettings
        ] = self.settings.providers.get(
            self.provider, {}  # type: ignore
        )
        for provider_setting in provider_settings.values():
            self.provider_settings = provider_setting
            await self.scan(provider_setting)

    def format_label(
        self,
        provider_settings: GcpSpecificSettings,
        result: ListAssetsResponse.ListAssetsResult,
    ) -> str:
        """Format Gcp label.

        Args:
            provider_settings (GcpSpecificSettings): Gcp settings.
            result (ListAssetsResponse.ListAssetsResult): Gcp asset result.

        Returns:
            str: Formatted asset label.
        """
        # TODO: Include location in label
        asset_project_display_name = (
            result.asset.security_center_properties.resource_project_display_name
        )
        return f"{self.label_prefix}{provider_settings.organization_id}/{asset_project_display_name}"

    async def list_assets(
        self,
        provider_settings: GcpSpecificSettings,
        security_center_client: securitycenter_v1.SecurityCenterAsyncClient,
        filter: Optional[str] = None,
    ) -> ListAssetsAsyncPager:
        """List Gcp assets.

        Args:
            provider_settings (GcpSpecificSettings): Gcp settings.
            security_center_client (securitycenter_v1.SecurityCenterAsyncClient): Gcp security center client.
            filter (Optional[str]): Filter string.

        Returns:
            ListAssetsAsyncPager: Gcp assets.
        """
        request = {
            "parent": provider_settings.parent(),
        }
        if filter:
            request["filter"] = filter
        return await security_center_client.list_assets(request=request)

    async def get_compute_instances(
        self,
        provider_settings: GcpSpecificSettings,
        security_center_client: securitycenter_v1.SecurityCenterAsyncClient,
        current_service: GcpSecurityCenterResourceTypes,
    ):
        """Get Gcp compute instances assets.

        Args:
            provider_settings (GcpSpecificSettings): Gcp settings.
            security_center_client (securitycenter_v1.SecurityCenterAsyncClient): Gcp security center client.
            current_service (GcpSecurityCenterResourceTypes): Gcp security center resource type.
        """
        list_assets_results = await self.list_assets(
            provider_settings,
            security_center_client,
            filter=GcpSecurityCenterResourceTypes.COMPUTE_INSTANCE.filter(),
        )
        async for list_assets_result in list_assets_results:
            if network_interfaces := list_assets_result.asset.resource_properties.get(
                "networkInterfaces"
            ):
                try:
                    network_interfaces = json.loads(network_interfaces)
                except json.JSONDecodeError:
                    self.logger.error(
                        "Failed to parse network_interfaces for"
                        f" {list_assets_result.asset.name}"
                    )
                    continue
                if (
                    not isinstance(network_interfaces, list)
                    or len(network_interfaces) == 0
                ):
                    continue
                access_configs = network_interfaces[0].get("accessConfigs", [])
                external_ip_addresses = [
                    ip_address
                    for access_config in access_configs
                    if (ip_address := access_config.get("natIP"))
                    and access_config.get("name") == "External NAT"
                ]
                for ip_address in external_ip_addresses:
                    with SuppressValidationError():
                        ip_seed = IpSeed(
                            value=ip_address,
                            label=self.format_label(
                                provider_settings, list_assets_result
                            ),
                        )
                        self.add_seed(ip_seed, service=current_service)

    async def get_compute_addresses(
        self,
        provider_settings: GcpSpecificSettings,
        security_center_client: securitycenter_v1.SecurityCenterAsyncClient,
        current_service: GcpSecurityCenterResourceTypes,
    ):
        """Get Gcp ip address assets.

        Args:
            provider_settings (GcpSpecificSettings): Gcp settings.
            security_center_client (securitycenter_v1.SecurityCenterAsyncClient): Gcp security center client.
            current_service (GcpSecurityCenterResourceTypes): Gcp security center resource type.
        """
        list_assets_results = await self.list_assets(
            provider_settings,
            security_center_client,
            filter=GcpSecurityCenterResourceTypes.COMPUTE_ADDRESS.filter(),
        )
        async for list_assets_result in list_assets_results:
            if ip_address := list_assets_result.asset.resource_properties.get(
                "address"
            ):
                with SuppressValidationError():
                    ip_seed = IpSeed(
                        value=ip_address,
                        label=self.format_label(provider_settings, list_assets_result),
                    )
                    self.add_seed(ip_seed, service=current_service)

    async def get_container_clusters(
        self,
        provider_settings: GcpSpecificSettings,
        security_center_client: securitycenter_v1.SecurityCenterAsyncClient,
        current_service: GcpSecurityCenterResourceTypes,
    ):
        """Get Gcp container clusters.

        Args:
            provider_settings (GcpSpecificSettings): Gcp settings.
            security_center_client (securitycenter_v1.SecurityCenterAsyncClient): Gcp security center client.
            current_service (GcpSecurityCenterResourceTypes): Gcp security center resource type.
        """
        list_assets_results = await self.list_assets(
            provider_settings,
            security_center_client,
            filter=GcpSecurityCenterResourceTypes.CONTAINER_CLUSTER.filter(),
        )
        async for list_assets_result in list_assets_results:
            if private_cluster_config := list_assets_result.asset.resource_properties.get(
                "privateClusterConfig"
            ):
                try:
                    private_cluster_config = json.loads(private_cluster_config)
                except json.decoder.JSONDecodeError:  # pragma: no cover
                    self.logger.debug(
                        "Failed to parse privateClusterConfig:"
                        f" {private_cluster_config}"
                    )
                    continue
                if ip_address := private_cluster_config.get("publicEndpoint"):
                    with SuppressValidationError():
                        ip_seed = IpSeed(
                            value=ip_address,
                            label=self.format_label(
                                provider_settings, list_assets_result
                            ),
                        )
                        self.add_seed(ip_seed, service=current_service)

    async def get_cloud_sql_instances(
        self,
        provider_settings: GcpSpecificSettings,
        security_center_client: securitycenter_v1.SecurityCenterAsyncClient,
        current_service: GcpSecurityCenterResourceTypes,
    ):
        """Get Gcp cloud sql instances.

        Args:
            provider_settings (GcpSpecificSettings): Gcp settings.
            security_center_client (securitycenter_v1.SecurityCenterAsyncClient): Gcp security center client.
            current_service (GcpSecurityCenterResourceTypes): Gcp security center resource type.
        """
        list_assets_results = await self.list_assets(
            provider_settings,
            security_center_client,
            filter=GcpSecurityCenterResourceTypes.CLOUD_SQL_INSTANCE.filter(),
        )
        async for list_assets_result in list_assets_results:
            if ip_addresses := list_assets_result.asset.resource_properties.get(
                "ipAddresses"
            ):
                ip_addresses = json.loads(ip_addresses)
                for ip_address in [
                    address for ip in ip_addresses if (address := ip.get("ipAddress"))
                ]:
                    with SuppressValidationError():
                        ip_seed = IpSeed(
                            value=ip_address,
                            label=self.format_label(
                                provider_settings, list_assets_result
                            ),
                        )
                        self.add_seed(ip_seed, service=current_service)

    async def get_dns_records(
        self,
        provider_settings: GcpSpecificSettings,
        security_center_client: securitycenter_v1.SecurityCenterAsyncClient,
        current_service: GcpSecurityCenterResourceTypes,
    ):
        """Get Gcp dns records.

        Args:
            provider_settings (GcpSpecificSettings): Gcp settings.
            security_center_client (securitycenter_v1.SecurityCenterAsyncClient): Gcp security center client.
            current_service (GcpSecurityCenterResourceTypes): Gcp security center resource type.
        """
        list_assets_results = await self.list_assets(
            provider_settings,
            security_center_client,
            filter=GcpSecurityCenterResourceTypes.DNS_ZONE.filter(),
        )
        async for list_assets_result in list_assets_results:
            resource_properties = list_assets_result.asset.resource_properties
            if resource_properties.get("visibility") == "PUBLIC" and (
                domain := resource_properties.get("dnsName")
            ):
                with SuppressValidationError():
                    domain_seed = DomainSeed(
                        value=domain,
                        label=self.format_label(provider_settings, list_assets_result),
                    )
                    self.add_seed(domain_seed, service=current_service)

    async def get_storage_buckets(
        self,
        provider_settings: GcpSpecificSettings,
        security_center_client: securitycenter_v1.SecurityCenterAsyncClient,
        current_service: GcpSecurityCenterResourceTypes,
    ):
        """Get Gcp storage buckets.

        Args:
            provider_settings (GcpSpecificSettings): Gcp settings.
            security_center_client (securitycenter_v1.SecurityCenterAsyncClient): Gcp security center client.
            current_service (GcpSecurityCenterResourceTypes): Gcp security center resource type.
        """
        list_assets_results = await self.list_assets(
            provider_settings,
            security_center_client,
            filter=GcpSecurityCenterResourceTypes.STORAGE_BUCKET.filter(),
        )
        async for list_assets_result in list_assets_results:
            resource_properties = list_assets_result.asset.resource_properties
            if (bucket_name := resource_properties.get("id")) and (
                project_number := resource_properties.get("projectNumber")
            ):
                scan_data: dict[str, Union[str, int]] = {
                    "accountNumber": int(project_number)
                }
                if (
                    project_name := list_assets_result.asset.security_center_properties.resource_project_display_name
                ):
                    scan_data["projectName"] = project_name
                if location := resource_properties.get("location"):
                    scan_data["location"] = location
                if self_link := resource_properties.get("selfLink"):
                    scan_data["selfLink"] = self_link
                with SuppressValidationError():
                    bucket_asset = GcpStorageBucketAsset(  # type: ignore[call-arg]
                        # TODO: Update when API can accept other urls
                        value=f"https://storage.googleapis.com/{bucket_name}",
                        uid=self.format_label(provider_settings, list_assets_result),
                        # Cast project_number to int from float
                        scan_data=scan_data,
                    )
                    self.add_cloud_asset(bucket_asset, service=current_service)
