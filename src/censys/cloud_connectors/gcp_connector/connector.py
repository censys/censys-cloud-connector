"""Gcp Cloud Connector."""
import json
from pathlib import Path
from typing import Any, Optional

from google.api_core import exceptions
from google.cloud.asset_v1 import AssetServiceClient
from google.cloud.asset_v1.services.asset_service.pagers import SearchAllResourcesPager
from google.cloud.asset_v1.types import ResourceSearchResult
from google.oauth2 import service_account

from censys.cloud_connectors.common.cloud_asset import GcpStorageBucketAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.context import SuppressValidationError
from censys.cloud_connectors.common.enums import EventTypeEnum, ProviderEnum
from censys.cloud_connectors.common.healthcheck import Healthcheck
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .enums import GcpApiVersions, GcpCloudAssetInventoryTypes
from .settings import GcpSpecificSettings


class GcpCloudConnector(CloudConnector):
    """Gcp Cloud Connector."""

    provider = ProviderEnum.GCP
    organization_id: int
    credentials: service_account.Credentials
    provider_settings: GcpSpecificSettings
    cloud_asset_client: AssetServiceClient
    all_projects: dict[str, dict[str, str]]
    found_projects: set[str]

    def __init__(self, settings: Settings):
        """Initialize Gcp Cloud Connector.

        Args:
            settings (Settings): Settings.
        """
        super().__init__(settings)
        self.seed_scanners = {
            GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE: self.get_compute_instances,
            GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS: self.get_compute_addresses,
            GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER: self.get_container_clusters,
            GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE: self.get_cloud_sql_instances,
            GcpCloudAssetInventoryTypes.DNS_ZONE: self.get_dns_records,
        }
        self.cloud_asset_scanners = {
            GcpCloudAssetInventoryTypes.STORAGE_BUCKET: self.get_storage_buckets,
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
                self.clean_up()
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
        results = self.search_all_resources(filter=GcpCloudAssetInventoryTypes.PROJECT)
        projects: dict[str, dict[str, str]] = {}
        for result in results:
            try:
                project = ResourceSearchResult.to_dict(result)
                self.logger.debug(f"FINDME EXAMPLE project: {project}")
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse project: {project}")
                continue
            try:
                if versioned_resource := self.check_asset_version(
                    GcpCloudAssetInventoryTypes.PROJECT, project
                ):
                    resource = versioned_resource["resource"]
                    version = versioned_resource["version"]
                    if version == "v3":
                        project_id = resource["projectId"]
                        project_number = self.parse_project_number(resource["name"])
                        name = resource.get("displayName", "")  # Optional
                    else:
                        project_id = resource["projectId"]
                        project_number = resource["projectNumber"]
                        name = resource.get("name", "")  # Optional
                    if (not project_id) or (not project_number):
                        self.logger.debug(f"Failed to parse project: {project}")
                    projects[project_number] = {"project_id": project_id, "name": name}
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                self.logger.debug(f"Failed to parse project: {project}: {e}")
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

    def return_if_str(self, val: Any) -> str:
        """Return the value if it is a string.

        Args:
            val (Any): The value to check.

        Returns:
            str: The value if it is a string.
        """
        if isinstance(val, str):
            return val
        return ""

    def check_asset_version(
        self, asset_type: GcpCloudAssetInventoryTypes, asset: dict
    ) -> Optional[dict]:
        """Check if the asset version is supported and returns the resource if it is.

        Args:
            asset_type (GcpCloudAssetInventoryTypes): Asset type.
            asset (dict): Asset.

        Returns:
            Optional[dict]: Resource with supported version, if it exists.
        """
        versioned_resources = asset.get("versioned_resources", [])
        # Found resource with version `v1`
        if len(versioned_resources) == 1:
            if versioned_resources[0][
                "version"
            ] in GcpApiVersions.SUPPORTED_VERSIONS.get_versions(asset_type):
                return versioned_resources[0]
            elif versioned_resources[0][
                "version"
            ] in GcpApiVersions.UNSUPPORTED_VERSIONS.get_versions(asset_type):
                self.logger.debug(
                    f"Version {versioned_resources[0]['version']} is unsupported and will be ignored."
                )
            else:
                self.logger.warning(
                    f"Version {versioned_resources[0]['version']} of the API for resource type {asset_type} is unknown."
                )
        # Found multiple versioned resources
        elif len(versioned_resources) > 1:
            for versioned_resource in versioned_resources:
                if versioned_resources[0][
                    "version"
                ] in GcpApiVersions.SUPPORTED_VERSIONS.get_versions(asset_type):
                    self.logger.debug(
                        f"Found multiple versioned resources. Version {versioned_resource['version']} is supported and will be used."
                    )
                    return versioned_resource
                elif versioned_resources[0][
                    "version"
                ] in GcpApiVersions.UNSUPPORTED_VERSIONS.get_versions(asset_type):
                    self.logger.debug(
                        f"Found multiple versioned resources. Version {versioned_resource['version']} is unsupported and will be ignored."
                    )
                else:
                    self.logger.warning(
                        f"Version {versioned_resource['version']} of the API for resource type {asset_type} is unknown."
                    )

        return None

    def clean_up(self):
        """Remove seeds and cloud assets for GCP projects where no assets were found."""
        possible_projects = set(self.all_projects.keys())
        empty_projects = possible_projects - self.found_projects
        for project in empty_projects:
            label = self.format_label(self.all_projects[project]["project_id"])
            self.delete_seeds_by_label(label)

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
        results = self.search_all_resources(
            filter=GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE
        )
        for result in results:
            try:
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    if (
                        network_interfaces := resource.get("networkInterfaces", [])
                    ) and (
                        project_id := self.all_projects.get(project_number, {}).get(
                            "project_id"
                        )
                    ):
                        for network_interface in network_interfaces:
                            access_configs = network_interface.get("accessConfigs", [])
                            external_ip_addresses = [
                                ip_address
                                for access_config in access_configs
                                if (ip_address := access_config.get("natIP"))
                                and (access_config.get("name") == "External NAT")
                            ]
                            for ip_address in external_ip_addresses:
                                label = self.format_label(project_id)
                                self.logger.debug(
                                    f"FINDME EXAMPLE compute instance: {asset}"
                                )
                                with SuppressValidationError():
                                    ip_seed = IpSeed(
                                        value=ip_address,
                                        label=label,
                                    )
                                    self.add_seed(ip_seed)
                                    self.found_projects.add(project_number)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

    def get_compute_addresses(self):
        """Get Gcp ip address assets."""
        results = self.search_all_resources(
            filter=GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS
        )
        for result in results:
            try:
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    ip_address: str = resource["address"]
                    if project_id := self.all_projects.get(project_number, {}).get(
                        "project_id"
                    ):
                        with SuppressValidationError():
                            label = self.format_label(project_id)
                            self.logger.debug(
                                f"FINDME EXAMPLE compute address: {asset}"
                            )
                            ip_seed = IpSeed(
                                value=ip_address,
                                label=label,
                            )
                            self.add_seed(ip_seed)
                            self.found_projects.add(project_number)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

    def get_container_clusters(self):
        """Get Gcp container clusters."""
        results = self.search_all_resources(
            filter=GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER
        )
        for result in results:
            try:
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
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
                        self.logger.debug(f"FINDME EXAMPLE cluster: {asset}")
                        with SuppressValidationError():
                            ip_seed = IpSeed(
                                value=ip_address,
                                label=label,
                            )
                            self.add_seed(ip_seed)
                            self.found_projects.add(project_number)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

    def get_cloud_sql_instances(self):
        """Get Gcp cloud sql instances."""
        results = self.search_all_resources(
            filter=GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE
        )
        for result in results:
            try:
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    ip_addresses: list = resource["ipAddresses"]
                    if project_id := self.all_projects.get(project_number, {}).get(
                        "project_id"
                    ):
                        for ip_address in [
                            address
                            for ip in ip_addresses
                            if (address := ip["ipAddress"])
                        ]:
                            label = self.format_label(project_id)
                            self.logger.debug(f"FINDME EXAMPLE cloud sql: {asset}")
                            with SuppressValidationError():
                                ip_seed = IpSeed(
                                    value=ip_address,
                                    label=label,
                                )
                                self.add_seed(ip_seed)
                                self.found_projects.add(project_number)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

    def get_dns_records(self):
        """Get Gcp dns records."""
        results = self.search_all_resources(filter=GcpCloudAssetInventoryTypes.DNS_ZONE)
        for result in results:
            try:
                asset = ResourceSearchResult.to_dict(result)

                if versioned_resource := self.check_asset_version(
                    GcpCloudAssetInventoryTypes.DNS_ZONE, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    domain: str = resource["dnsName"]
                    if (resource.get("visibility", "") == "PUBLIC") and (  # Optional
                        project_id := self.all_projects.get(project_number, {}).get(
                            "project_id"
                        )
                    ):
                        label = self.format_label(project_id)
                        self.logger.debug(f"FINDME EXAMPLE dns zone: {asset}")
                        with SuppressValidationError():
                            domain_seed = DomainSeed(value=domain, label=label)
                            self.add_seed(domain_seed)
                            self.found_projects.add(project_number)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

    def get_storage_buckets(self):
        """Get Gcp storage buckets."""
        results = self.search_all_resources(
            filter=GcpCloudAssetInventoryTypes.STORAGE_BUCKET
        )
        for result in results:
            try:
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    GcpCloudAssetInventoryTypes.STORAGE_BUCKET, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    bucket_name: str = resource["id"]
                    scan_data = {"accountNumber": int(project_number)}
                    if project_id := self.all_projects.get(project_number, {}).get(
                        "project_id"
                    ):
                        scan_data["projectName"] = project_id
                    scan_data["location"]: str = resource["location"]
                    scan_data["selfLink"]: str = resource["selfLink"]
                    uid = self.format_uid(project_id)
                    self.logger.debug(f"FINDME EXAMPLE storage bucket: {asset}")
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
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue
