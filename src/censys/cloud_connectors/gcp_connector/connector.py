"""Gcp Cloud Connector."""
import json
from pathlib import Path
from typing import Optional

from google.api_core import exceptions
from google.cloud.asset_v1.services.asset_service.client import AssetServiceClient
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
    cloud_asset_client: AssetServiceClient
    all_projects: dict[str, dict]
    found_projects: set[str]

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
                self.cloud_asset_client = AssetServiceClient(
                    credentials=self.credentials
                )
                self.logger.info(f"Scanning GCP organization {self.organization_id}")
                self.all_projects = self.list_projects()
                self.found_projects = set()
                super().scan()
                # self.clean_up()
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

    def parse_project_number(self, path: str) -> str:
        """Parses an asset name to extract the project number.

        Args:
            path (str): Project path in the format "projects/{PROJECT NUMBER}".

        Returns:
            str: Asset parts.
        """
        project = AssetServiceClient.parse_common_project_path(path)
        if project_number := project.get("project"):
            return project_number
        return ""

    def check_asset_version(self, asset: dict) -> Optional[dict]:
        """Check if the asset version is supported.

        Args:
            asset (dict): Asset.

        Returns:
            Optional[dict]: Resource with version `v1`, if it exists.
        """
        versioned_resources = asset.get("versioned_resources", [])
        # Found resource with version `v1`
        if (
            len(versioned_resources) == 1
            and versioned_resources[0].get("version") == "v1"
        ):
            return versioned_resources[0].get("resource")
        # Found multiple versioned resources
        elif len(versioned_resources) > 1:
            for versioned_resource in versioned_resources:
                if versioned_resource.get("version") == "v1":
                    self.logger.debug(
                        "Found multiple versioned resources. Version `v1` is supported and will be used."
                    )
                    return versioned_resource.get("resource")

        self.logger.debug("Found no resources of version `v1`.")
        return None

    # def clean_up(self):
    #     """Remove seeds and cloud assets for GCP projects where no assets were found."""
    #     possible_projects = set(self.all_projects.keys())
    #     empty_projects = possible_projects - self.found_projects

    def format_label(self, project_id: str) -> str:
        """Format Gcp label.

        Args:
            project_id (str): Gcp asset project ID

        Returns:
            str: Formatted asset label.
        """
        return f"{self.label_prefix}{self.organization_id}/{project_id}"

    def format_uid(self, project_id: Optional[str]) -> str:
        """Format Gcp uid.

        Args:
            project_id (Optional[str]): Gcp asset project id.

        Returns:
            str: Formatted asset uid.
        """
        return f"{self.label_prefix}{self.organization_id}/{project_id}"

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
        assets = self.search_all_resources(filter=GcpCloudAssetTypes.COMPUTE_INSTANCE)
        for asset in assets:
            try:
                asset = ResourceSearchResult.to_dict(asset)
                self.logger.debug(f"compute instance: {asset}")
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse asset: {asset}")
                continue

            if resource := self.check_asset_version(asset):
                project_path = asset.get("project")
                project_number = self.parse_project_number(project_path)
            if (network_interfaces := resource.get("networkInterfaces")) and (
                project_id := self.all_projects.get(project_number, {}).get(
                    "project_id"
                )
            ):
                if (
                    not isinstance(network_interfaces, list)
                    or len(network_interfaces) == 0
                ):
                    continue
                for network_interface in network_interfaces:
                    access_configs = network_interface.get("accessConfigs", [])
                    external_ip_addresses = [
                        ip_address
                        for access_config in access_configs
                        if (ip_address := access_config.get("natIP"))
                        and access_config.get("name") == "External NAT"
                    ]
                    for ip_address in external_ip_addresses:
                        label = self.format_label(project_id)
                        with SuppressValidationError():
                            ip_seed = IpSeed(
                                value=ip_address,
                                label=label,
                            )
                            self.add_seed(ip_seed)
                            self.found_projects.add(project_number)

    def get_compute_addresses(self):
        """Get Gcp ip address assets."""
        assets = self.search_all_resources(filter=GcpCloudAssetTypes.COMPUTE_ADDRESS)
        for asset in assets:
            try:
                asset = ResourceSearchResult.to_dict(asset)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse asset: {asset}")
                continue
            if resource := self.check_asset_version(asset):
                project_path = asset.get("project")
                project_number = self.parse_project_number(project_path)
                if ip_address := resource.get("address") and (
                    project_id := self.all_projects.get(project_number, {}).get(
                        "project_id"
                    )
                ):
                    with SuppressValidationError():
                        label = self.format_label(project_id)
                        ip_seed = IpSeed(
                            value=ip_address,
                            label=label,
                        )
                        self.add_seed(ip_seed)
                        self.found_projects.add(project_number)

    def get_container_clusters(self):
        """Get Gcp container clusters."""
        assets = self.search_all_resources(filter=GcpCloudAssetTypes.CONTAINER_CLUSTER)
        for asset in assets:
            try:
                asset = ResourceSearchResult.to_dict(asset)
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}")
                continue
            if resource := self.check_asset_version(asset):
                project_path = asset.get("project")
                project_number = self.parse_project_number(project_path)
                if (
                    ip_address := resource.get("privateClusterConfig", {}).get(
                        "publicEndpoint"
                    )
                ) and (
                    project_id := self.all_projects.get(project_number, {}).get(
                        "project_id"
                    )
                ):
                    label = self.format_label(project_id)
                    with SuppressValidationError():
                        ip_seed = IpSeed(
                            value=ip_address,
                            label=label,
                        )
                        self.add_seed(ip_seed)
                        self.found_projects.add(project_number)

    def get_cloud_sql_instances(self):
        """Get Gcp cloud sql instances."""
        assets = self.search_all_resources(filter=GcpCloudAssetTypes.CLOUD_SQL_INSTANCE)
        for asset in assets:
            try:
                asset = ResourceSearchResult.to_dict(asset)
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}")
                continue
            if resource := self.check_asset_version(asset):
                project_path = asset.get("project")
                project_number = self.parse_project_number(project_path)
                if ip_addresses := resource.get("ipAddresses") and (
                    project_id := self.all_projects.get(project_number, {}).get(
                        "project_id"
                    )
                ):
                    for ip_address in [
                        address
                        for ip in ip_addresses
                        if (address := ip.get("ipAddress"))
                    ]:
                        label = self.format_label(project_id)
                        with SuppressValidationError():
                            ip_seed = IpSeed(
                                value=ip_address,
                                label=label,
                            )
                            self.add_seed(ip_seed)
                            self.found_projects.add(project_number)

    def get_dns_records(self):
        """Get Gcp dns records."""
        assets = self.search_all_resources(filter=GcpCloudAssetTypes.DNS_ZONE)
        for asset in assets:
            try:
                asset = ResourceSearchResult.to_dict(asset)
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}")
                continue
            if resource := self.check_asset_version(asset):
                project_path = asset.get("project")
                project_number = self.parse_project_number(project_path)
                if (
                    resource.get("visibility") == "PUBLIC"
                    and (domain := resource.get("dnsName"))
                    and (
                        project_id := self.all_projects.get(project_number, {}).get(
                            "project_id"
                        )
                    )
                ):
                    label = self.format_label(project_id)
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=domain, label=label)
                        self.add_seed(domain_seed)
                        self.found_projects.add(project_number)

    def get_storage_buckets(self):
        """Get Gcp storage buckets."""
        assets = self.search_all_resources(filter=GcpCloudAssetTypes.STORAGE_BUCKET)
        for asset in assets:
            try:
                asset = ResourceSearchResult.to_dict(asset)
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}")
                continue
            if resource := self.check_asset_version(asset):
                project_path = asset.get("project")
                project_number = self.parse_project_number(project_path)
                if bucket_name := resource.get("id") and project_number:
                    scan_data = {"accountNumber": int(project_number)}
                    if project_id := self.all_projects.get(project_number, {}).get(
                        "project_id"
                    ):
                        scan_data["projectName"] = project_id
                    if location := resource.get("location"):
                        scan_data["location"] = location
                    if self_link := resource.get("selfLink"):
                        scan_data["selfLink"] = self_link
                    uid = self.format_uid(project_id)
                    with SuppressValidationError():
                        bucket_asset = GcpStorageBucketAsset(
                            # TODO: Update when API can accept other urls
                            value=f"https://storage.googleapis.com/{bucket_name}",
                            uid=uid,
                            # Cast project_number to int from float
                            scan_data=scan_data,
                        )
                        self.add_cloud_asset(bucket_asset)
                        self.found_projects.add(project_number)
