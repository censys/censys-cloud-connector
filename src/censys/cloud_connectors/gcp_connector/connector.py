"""Gcp Cloud Connector."""
import json
from pathlib import Path
from typing import Callable, Optional

from google.api_core import exceptions
from google.cloud import securitycenter_v1
from google.cloud.securitycenter_v1.services.security_center.pagers import (
    ListAssetsPager,
)
from google.cloud.securitycenter_v1.types import ListAssetsResponse
from google.oauth2 import service_account

from censys.cloud_connectors.common.cloud_asset import GcpStorageBucketAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .enums import GcpSecurityCenterResourceTypes
from .settings import GcpSpecificSettings

# TODO: Implement this type of cloud function and terraform: https://github.com/GoogleCloudPlatform/security-response-automation


class GcpCloudConnector(CloudConnector):
    """Gcp Cloud Connector."""

    provider = ProviderEnum.GCP
    organization_id: int
    credentials: service_account.Credentials
    provider_settings: GcpSpecificSettings
    security_center_client: securitycenter_v1.SecurityCenterClient

    seed_scanners: dict[GcpSecurityCenterResourceTypes, Callable[[], None]]
    cloud_asset_scanners: dict[GcpSecurityCenterResourceTypes, Callable[[], None]]

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

    def scan(self):
        """Scan Gcp."""
        key_file_path = (
            Path(self.settings.secrets_dir)
            / self.provider_settings.service_account_json_file
        )
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                str(key_file_path)
            )
        except ValueError as e:
            self.logger.error(
                "Failed to load service account credentials from"
                f" {key_file_path}: {e}"
            )
        self.security_center_client = securitycenter_v1.SecurityCenterClient(
            credentials=self.credentials
        )
        try:
            super().scan()
        except exceptions.PermissionDenied as e:  # pragma: no cover
            # Thrown when the service account does not have permission to
            # access the securitycenter service or the service is disabled.
            self.logger.error(e.message)
        # TODO: Uncomment this when connector is fully tested
        # except Exception as e:
        #     self.logger.error(f"Failed to scan {self.organization_id}: {e}")

    def scan_all(self):
        """Scan all Gcp Organizations."""
        provider_settings: dict[
            tuple, GcpSpecificSettings
        ] = self.settings.providers.get(self.provider, {})
        for provider_setting in provider_settings.values():
            self.provider_settings = provider_setting
            self.organization_id = provider_setting.organization_id
            self.scan()

    def format_label(self, result: ListAssetsResponse.ListAssetsResult) -> str:
        """Format Gcp label.

        Args:
            result (ListAssetsResponse.ListAssetsResult): Gcp asset result.

        Returns:
            str: Formatted asset label.
        """
        # print(result.__class__.to_json(result))
        # TODO: Include location in label
        asset_project_display_name = (
            result.asset.security_center_properties.resource_project_display_name
        )
        return f"{self.label_prefix}{self.organization_id}/{asset_project_display_name}"

    def list_assets(self, filter: Optional[str] = None) -> ListAssetsPager:
        """List Gcp assets.

        Args:
            filter (Optional[str]): Filter string.

        Returns:
            ListAssetsPager: Gcp assets.
        """
        request = {
            "parent": self.provider_settings.parent(),
        }
        if filter:
            request["filter"] = filter
        return self.security_center_client.list_assets(request=request)

    def get_asset_dict(
        self, list_assets_result: ListAssetsResponse.ListAssetsResult
    ) -> dict:
        """Get Gcp asset dict.

        Args:
            list_assets_result (ListAssetsResponse.ListAssetsResult): Gcp asset result.

        Returns:
            dict: Gcp asset dict.
        """
        return {
            "asset": list_assets_result.asset,
            "label": self.format_label(list_assets_result),
        }

    def get_compute_instances(self):
        """Get Gcp compute instances assets."""
        list_assets_results = self.list_assets(
            filter=GcpSecurityCenterResourceTypes.COMPUTE_INSTANCE.filter()
        )
        for list_assets_result in list_assets_results:
            self.logger.debug(list_assets_result.__dict__)
            if network_interfaces := list_assets_result.asset.resource_properties.get(
                "networkInterfaces"
            ):
                # network_interfaces is a json string that needs to be parsed
                try:
                    network_interfaces = json.loads(network_interfaces)
                except json.JSONDecodeError:
                    self.logger.error(
                        f"Failed to parse network_interfaces for {list_assets_result.asset.name}"
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
                    self.add_seed(
                        IpSeed(
                            value=ip_address,
                            label=self.format_label(list_assets_result),
                        )
                    )

    def get_compute_addresses(self):
        """Get Gcp ip address assets."""
        list_assets_results = self.list_assets(
            filter=GcpSecurityCenterResourceTypes.COMPUTE_ADDRESS.filter()
        )
        for list_assets_result in list_assets_results:
            if ip_address := list_assets_result.asset.resource_properties.get(
                "address"
            ):
                self.add_seed(
                    IpSeed(
                        value=ip_address, label=self.format_label(list_assets_result)
                    )
                )

    def get_container_clusters(self):
        """Get Gcp container clusters."""
        list_assets_results = self.list_assets(
            filter=GcpSecurityCenterResourceTypes.CONTAINER_CLUSTER.filter()
        )
        for list_assets_result in list_assets_results:
            if private_cluster_config := list_assets_result.asset.resource_properties.get(
                "privateClusterConfig"
            ):
                # private_cluster_config is a json string that needs to be parsed
                try:
                    private_cluster_config = json.loads(private_cluster_config)
                except json.decoder.JSONDecodeError:  # pragma: no cover
                    self.logger.debug(
                        f"Failed to parse privateClusterConfig: {private_cluster_config}"
                    )
                    continue
                if ip_address := private_cluster_config.get("publicEndpoint"):
                    self.add_seed(
                        IpSeed(
                            value=ip_address,
                            label=self.format_label(list_assets_result),
                        )
                    )

    def get_cloud_sql_instances(self):
        """Get Gcp cloud sql instances."""
        list_assets_results = self.list_assets(
            filter=GcpSecurityCenterResourceTypes.CLOUD_SQL_INSTANCE.filter()
        )
        for list_assets_result in list_assets_results:
            if ip_addresses := list_assets_result.asset.resource_properties.get(
                "ipAddresses"
            ):
                # ip_addresses is a json string that needs to be parsed
                ip_addresses = json.loads(ip_addresses)
                for ip_address in [
                    address for ip in ip_addresses if (address := ip.get("ipAddress"))
                ]:
                    self.add_seed(
                        IpSeed(
                            value=ip_address,
                            label=self.format_label(list_assets_result),
                        )
                    )

    def get_dns_records(self):
        """Get Gcp dns records."""
        list_assets_results = self.list_assets(
            filter=GcpSecurityCenterResourceTypes.DNS_ZONE.filter()
        )
        for list_assets_result in list_assets_results:
            resource_properties = list_assets_result.asset.resource_properties
            if resource_properties.get("visibility") == "PUBLIC" and (
                domain := resource_properties.get("dnsName")
            ):
                self.add_seed(
                    DomainSeed(
                        value=domain, label=self.format_label(list_assets_result)
                    )
                )

    def get_seeds(self):
        """Get Gcp seeds."""
        for seed_type, seed_scanner in self.seed_scanners.items():
            if (
                self.provider_settings.ignore
                and seed_type in self.provider_settings.ignore
            ):
                self.logger.debug(f"Skipping {seed_type}")
                continue
            self.logger.debug(f"Scanning {seed_type}")
            seed_scanner()

    def get_storage_buckets(self):
        """Get Gcp storage buckets."""
        list_assets_results = self.list_assets(
            filter=GcpSecurityCenterResourceTypes.STORAGE_BUCKET.filter()
        )
        for list_assets_result in list_assets_results:
            resource_properties = list_assets_result.asset.resource_properties
            if (bucket_name := resource_properties.get("id")) and (
                project_number := resource_properties.get("projectNumber")
            ):
                scan_data = {"accountNumber": int(project_number)}
                if (
                    project_name := list_assets_result.asset.security_center_properties.resource_project_display_name
                ):
                    scan_data["projectName"] = project_name
                if location := resource_properties.get("location"):
                    scan_data["location"] = location
                if self_link := resource_properties.get("selfLink"):
                    scan_data["selfLink"] = self_link
                self.add_cloud_asset(
                    GcpStorageBucketAsset(
                        # TODO: Update when API can accept other urls
                        value=f"https://storage.googleapis.com/{bucket_name}",
                        uid=self.format_label(list_assets_result),
                        # Cast project_number to int from float
                        scan_data=scan_data,
                    )
                )

    def get_cloud_assets(self):
        """Get Gcp cloud assets."""
        for cloud_asset_type, cloud_asset_scanner in self.cloud_asset_scanners.items():
            if (
                self.provider_settings.ignore
                and cloud_asset_type in self.provider_settings.ignore
            ):
                self.logger.debug(f"Skipping {cloud_asset_type}")
                continue
            self.logger.debug(f"Scanning {cloud_asset_type}")
            cloud_asset_scanner()
