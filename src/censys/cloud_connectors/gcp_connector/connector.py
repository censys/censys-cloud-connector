"""Gcp Cloud Connector."""
import json
import re
from pathlib import Path
from typing import Optional

from google.api_core import exceptions
from google.cloud import asset_v1
from google.cloud.asset_v1.services.asset_service.pagers import (
    ListAssetsPager,
    SearchAllResourcesPager,
)
from google.cloud.asset_v1.types import Asset, ContentType, ResourceSearchResult
from google.oauth2 import service_account

from censys.cloud_connectors.common.cloud_asset import GcpStorageBucketAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.context import SuppressValidationError
from censys.cloud_connectors.common.enums import EventTypeEnum, ProviderEnum
from censys.cloud_connectors.common.healthcheck import Healthcheck
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .enums import GcpCloudAssetTypes
from .settings import GcpSpecificSettings


class GcpCloudConnector(CloudConnector):
    """Gcp Cloud Connector."""

    provider = ProviderEnum.GCP
    organization_id: int
    credentials: service_account.Credentials
    provider_settings: GcpSpecificSettings
    cloud_asset_client: asset_v1.AssetServiceClient
    projects: dict[str, dict]

    def __init__(self, settings: Settings):
        """Initialize Gcp Cloud Connector.

        Args:
            settings (Settings): Settings.
        """
        super().__init__(settings)
        self.seed_scanners = {
            GcpCloudAssetTypes.COMPUTE_INSTANCE: self.get_compute_instances,
            GcpCloudAssetTypes.COMPUTE_ADDRESS: self.get_compute_addresses,
            GcpCloudAssetTypes.CONTAINER_CLUSTER: self.get_container_clusters,
            GcpCloudAssetTypes.CLOUD_SQL_INSTANCE: self.get_cloud_sql_instances,
            GcpCloudAssetTypes.DNS_ZONE: self.get_dns_records,
        }
        self.cloud_asset_scanners = {
            GcpCloudAssetTypes.STORAGE_BUCKET: self.get_storage_buckets,
        }

    def scan(self):
        """Scan Gcp.

        Scans Gcp for assets and seeds.

        Raises:
            ValueError: If the service account credentials file is invalid.
        """
        try:
            with Healthcheck(
                self.settings,
                self.provider_settings,
                exception_map={
                    exceptions.Unauthenticated: "PERMISSIONS",
                    exceptions.PermissionDenied: "PERMISSIONS",
                },
            ):
                key_file_path = (
                    Path(self.settings.secrets_dir)
                    / self.provider_settings.service_account_json_file
                )
                try:
                    self.credentials = (
                        service_account.Credentials.from_service_account_file(
                            str(key_file_path)
                        )
                    )
                except ValueError as e:
                    self.logger.error(
                        "Failed to load service account credentials from"
                        f" {key_file_path}: {e}"
                    )
                    raise
                self.cloud_asset_client = asset_v1.AssetServiceClient(
                    credentials=self.credentials
                )
                self.logger.info(f"Scanning GCP organization {self.organization_id}")
                self.projects = self.list_projects()
                super().scan()
        except Exception as e:
            self.logger.error(
                f"Unable to scan GCP organization {self.organization_id}. Error: {e}",
            )
            self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)

    def scan_all(self):
        """Scan all Gcp Organizations."""
        provider_settings: dict[
            tuple, GcpSpecificSettings
        ] = self.settings.providers.get(self.provider, {})
        for provider_setting in provider_settings.values():
            self.provider_settings = provider_setting
            self.organization_id = provider_setting.organization_id
            self.scan()

    def list_projects(self) -> dict[str, dict]:
        """List Gcp projects.

        Returns:
            dict[str, dict]: Gcp projects.
        """
        results = self.list_assets(filter=GcpCloudAssetTypes.PROJECT)
        projects: dict[str, dict] = {}
        for result in results:
            try:
                project = Asset.to_dict(result)
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse project: {project}")
                continue
            try:
                project_data = project.get("resource", {}).get("data", {})
                project_id = project_data.get("projectId")
                project_number = project_data.get("projectNumber")
                name = project_data.get("name")
                if not project_data or not project_id or not project_number or not name:
                    self.logger.debug(f"Failed to parse project: {project}")
                projects[project_number] = {"project_id": project_id, "name": name}
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse project: {project}")
                continue

        self.logger.debug(f"Found {len(projects)} projects.")
        return projects

    def parse_project_name_seeds(self, path: str) -> dict[str, str]:
        """Parses an asset name to extract the project display name.

        Args:
            path (str): Asset path.

        Returns:
            dict[str, str]: Asset parts.
        """
        m = re.search(
            r"\.googleapis\.com/projects/(?P<project>.+?)/",
            path,
        )
        return m.groupdict() if m else {}

    def parse_project_name_buckets(self, path: str) -> dict[str, str]:
        """Parses an asset name to extract the project display name.

        Args:
            path (str): Asset path.

        Returns:
            dict[str, str]: Asset parts.
        """
        m = re.search(
            r"\.googleapis\.com/projects/(?P<project>.+?)$",
            path,
        )
        return m.groupdict() if m else {}

    def format_label(self, full_name: str) -> str:
        """Format Gcp label.

        Args:
            full_name (str): Gcp asset resource name

        Returns:
            str: Formatted asset label.
        """
        asset_parts = self.parse_project_name_seeds(full_name)
        asset_project_display_name = asset_parts["project"]

        return f"{self.label_prefix}{self.organization_id}/{asset_project_display_name}"

    def format_uid(self, project_name: Optional[str]) -> str:
        """Format Gcp uid.

        Args:
            project_name (Optional[str]): Gcp asset project name.

        Returns:
            str: Formatted asset uid.
        """
        return f"{self.label_prefix}{self.organization_id}/{project_name}"

    def list_assets(self, filter: Optional[str] = None) -> ListAssetsPager:
        """List Gcp assets.

        Args:
            filter (Optional[str]): Filter string.

        Returns:
            ListAssetsPager: Gcp assets.
        """
        request = {
            "parent": self.provider_settings.parent(),
            "content_type": ContentType.RESOURCE,
            "asset_types": [filter],
        }
        return self.cloud_asset_client.list_assets(request=request)

    def search_all_resources(
        self, filter: Optional[str] = None
    ) -> SearchAllResourcesPager:
        """List Gcp assets.

        Args:
            filter (Optional[str]): Filter string.

        Returns:
            SearchAllResourcesPager: Gcp assets.
        """
        request = {
            "scope": self.provider_settings.parent(),
            "asset_types": [filter],
            "read_mask": "*",
        }
        return self.cloud_asset_client.search_all_resources(request=request)

    def get_compute_instances(self):
        """Get Gcp compute instances assets."""
        assets = self.list_assets(filter=GcpCloudAssetTypes.COMPUTE_INSTANCE)
        for asset in assets:
            try:
                asset = json.loads(Asset.to_json(asset))
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse asset: {asset}")
                continue

            if network_interfaces := asset["resource"]["data"].get("networkInterfaces"):
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
                            label=self.format_label(asset["name"]),
                        )
                        self.add_seed(ip_seed)

    def get_compute_addresses(self):
        """Get Gcp ip address assets."""
        assets = self.list_assets(filter=GcpCloudAssetTypes.COMPUTE_ADDRESS)
        for asset in assets:
            try:
                asset = json.loads(Asset.to_json(asset))
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse asset: {asset}")
                continue
            if ip_address := asset["resource"]["data"].get("address"):
                with SuppressValidationError():
                    ip_seed = IpSeed(
                        value=ip_address,
                        label=self.format_label(asset["name"]),
                    )
                    self.add_seed(ip_seed)

    def get_container_clusters(self):
        """Get Gcp container clusters."""
        assets = self.list_assets(filter=GcpCloudAssetTypes.CONTAINER_CLUSTER)
        for asset in assets:
            try:
                asset = json.loads(Asset.to_json(asset))
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}")
                continue

            if (
                ip_address := asset["resource"]["data"]
                .get("privateClusterConfig", {})
                .get("publicEndpoint")
            ):
                with SuppressValidationError():
                    ip_seed = IpSeed(
                        value=ip_address,
                        label=self.format_label(asset["name"]),
                    )
                    self.add_seed(ip_seed)

    def get_cloud_sql_instances(self):
        """Get Gcp cloud sql instances."""
        assets = self.list_assets(filter=GcpCloudAssetTypes.CLOUD_SQL_INSTANCE)
        for asset in assets:
            try:
                asset = json.loads(Asset.to_json(asset))
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}")
                continue
            if ip_addresses := asset["resource"]["data"].get("ipAddresses"):
                for ip_address in [
                    address for ip in ip_addresses if (address := ip.get("ipAddress"))
                ]:
                    with SuppressValidationError():
                        ip_seed = IpSeed(
                            value=ip_address,
                            label=self.format_label(asset["name"]),
                        )
                        self.add_seed(ip_seed)

    def get_dns_records(self):
        """Get Gcp dns records."""
        assets = self.list_assets(filter=GcpCloudAssetTypes.DNS_ZONE)
        for asset in assets:
            try:
                asset = json.loads(Asset.to_json(asset))
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}")
                continue
            data = asset["resource"]["data"]
            if data.get("visibility") == "PUBLIC" and (domain := data.get("dnsName")):
                with SuppressValidationError():
                    domain_seed = DomainSeed(
                        value=domain, label=self.format_label(asset["name"])
                    )
                    self.add_seed(domain_seed)

    def get_storage_buckets(self):
        """Get Gcp storage buckets."""
        assets = self.search_all_resources(filter=GcpCloudAssetTypes.STORAGE_BUCKET)
        for asset in assets:
            try:
                asset = json.loads(ResourceSearchResult.to_json(asset))
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}")
                continue
            resource = asset["versionedResources"][0]["resource"]
            if (bucket_name := resource.get("id")) and (
                project_number := resource.get("projectNumber")
            ):
                scan_data = {"accountNumber": int(project_number)}
                if project_name := self.parse_project_name_buckets(
                    asset["parentFullResourceName"]
                )["project"]:
                    scan_data["projectName"] = project_name
                if location := resource.get("location"):
                    scan_data["location"] = location
                if self_link := resource.get("selfLink"):
                    scan_data["selfLink"] = self_link
                with SuppressValidationError():
                    bucket_asset = GcpStorageBucketAsset(
                        # TODO: Update when API can accept other urls
                        value=f"https://storage.googleapis.com/{bucket_name}",
                        uid=self.format_uid(project_name),
                        # Cast project_number to int from float
                        scan_data=scan_data,
                    )
                    self.add_cloud_asset(bucket_asset)
