"""Gcp Cloud Connector."""
import json
from dataclasses import dataclass
from logging import Logger
from multiprocessing import Pool
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
from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.healthcheck import Healthcheck
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .enums import GcpApiVersions, GcpCloudAssetInventoryTypes
from .settings import GcpSpecificSettings


@dataclass
class GcpScanContext:
    """Required configuration context for scan()."""

    provider_settings: GcpSpecificSettings
    organization_id: int
    credentials: service_account.Credentials

    cloud_asset_client: AssetServiceClient
    logger: Logger


class GcpCloudConnector(CloudConnector):
    """Gcp Cloud Connector."""

    provider = ProviderEnum.GCP

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

    def scan_seeds(self, **kwargs):
        """Scan AWS for seeds."""
        scan_context: GcpScanContext = kwargs["scan_context"]

        logger = get_logger(
            log_name=f"{self.provider.lower()}_connector",
            level=self.settings.logging_level,
            provider=f"{self.provider}_{scan_context.organization_id}",
        )
        scan_context.logger = logger

        self.logger.info(
            f"Scanning GCP organization {scan_context.organization_id} for seeds."
        )

        super().scan_seeds(**kwargs)

    def scan_cloud_assets(self, **kwargs):
        """Scan AWS for cloud assets."""
        scan_context: GcpScanContext = kwargs["scan_context"]

        logger = get_logger(
            log_name=f"{self.provider.lower()}_connector",
            level=self.settings.logging_level,
            provider=f"{self.provider}_{scan_context.organization_id}",
        )
        scan_context.logger = logger

        self.logger.info(
            f"Scanning GCP organization {scan_context.organization_id} for cloud assets."
        )

        super().scan_cloud_assets(**kwargs)

    def scan_all(self):
        """Scan all Gcp Organizations."""
        provider_settings: dict[
            tuple, GcpSpecificSettings
        ] = self.settings.providers.get(self.provider, {})

        self.logger.debug(
            f"Scanning GCP using {self.settings.scan_concurrency} processes."
        )

        pool = Pool(processes=self.settings.scan_concurrency)

        for provider_setting in provider_settings.values():
            # `provider_setting` represents a specific top-level GcpOrganization entry in providers.yml
            #
            # DO NOT use provider_settings anywhere in this class!
            # provider_settings exists for the parent CloudConnector
            self.provider_settings = provider_setting
            organization_id = provider_setting.organization_id

            key_file_path = (
                Path(self.settings.secrets_dir)
                / provider_setting.service_account_json_file
            )
            try:
                credentials = (
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
            cloud_asset_client = AssetServiceClient(
                credentials=credentials
            )

            try:
                # scan seeds
                with Healthcheck(
                    self.settings,
                    provider_setting,
                    provider={
                        exceptions.Unauthenticated: "PERMISSIONS",
                        exceptions.PermissionDenied: "PERMISSIONS",
                    },
                ):
                    self.logger.debug(
                        "Starting pool organization:%s", organization_id
                    )

                    scan_context = GcpScanContext(
                        provider_settings=provider_setting,
                        organization_id=organization_id,
                        credentials=credentials,
                        cloud_asset_client=cloud_asset_client,
                        logger=None,
                    )
                    
                    pool.apply_async(
                        self.scan_seeds,
                        kwds={"scan_context": scan_context},
                    )

            except Exception as e:
                self.logger.error(
                    f"Unable to scan GCP organization {organization_id}. Error: {e}",
                )
                self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)

            try:
                # scan cloud assets
                with Healthcheck(
                    self.settings,
                    provider_setting,
                    provider={
                        exceptions.Unauthenticated: "PERMISSIONS",
                        exceptions.PermissionDenied: "PERMISSIONS",
                    },
                ):
                    self.logger.debug(
                        "Starting pool organization:%s", organization_id
                    )

                    scan_context = GcpScanContext(
                        provider_settings=provider_setting,
                        organization_id=organization_id,
                        credentials=credentials,
                        cloud_asset_client=cloud_asset_client,
                        logger=None,
                    )
                    
                    pool.apply_async(
                        self.scan_cloud_assets,
                        kwds={"scan_context": scan_context},
                    )

            except Exception as e:
                self.logger.error(
                    f"Unable to scan GCP organization {organization_id}. Error: {e}",
                )
                self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)

        pool.close()
        pool.join()

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
        project_number = project["project"]
        return project_number

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
        self, ctx: GcpScanContext, asset_type: GcpCloudAssetInventoryTypes, asset: dict
    ) -> Optional[dict]:
        """Check if the asset version is supported and returns the resource if it is.

        Args:
            ctx (GcpScanContext): Scan context.
            asset_type (GcpCloudAssetInventoryTypes): Asset type.
            asset (dict): Asset.

        Returns:
            Optional[dict]: Resource with supported version, if it exists.
        """
        versioned_resources = asset.get("versioned_resources", [])
        count = len(versioned_resources)
        supported = GcpApiVersions.SUPPORTED_VERSIONS.get_versions(asset_type)
        unsupported = GcpApiVersions.UNSUPPORTED_VERSIONS.get_versions(asset_type)
        # Found one version of the resource
        if count == 1:
            version = versioned_resources[0]["version"]
            if version in supported:
                return versioned_resources[0]
            elif version in unsupported:
                self.logger.debug(
                    f"Version {version} is unsupported and will be ignored."
                )
            else:
                self.logger.warning(
                    f"Version {version} of the API for resource type {asset_type} is unknown."
                )
        # Found multiple versioned resources
        elif count > 1:
            supported_versioned_resource = None
            for versioned_resource in versioned_resources:
                version = versioned_resource["version"]
                if (version in supported) and (supported_versioned_resource is None):
                    self.logger.debug(
                        f"Found multiple versioned resources. Version {version} is supported and will be used."
                    )
                    supported_versioned_resource = versioned_resource
                elif version in unsupported:
                    self.logger.debug(
                        f"Found multiple versioned resources. Version {version} is unsupported and will be ignored."
                    )
                else:
                    self.logger.warning(
                        f"Version {version} of the API for resource type {asset_type} is unknown."
                    )
            return supported_versioned_resource

        return None

    def clean_up(self):
        """Remove seeds and cloud assets for GCP projects where no assets were found."""
        possible_projects = set(self.all_projects.keys())
        empty_projects = possible_projects - self.found_projects
        for project in empty_projects:
            label = self.format_label(self.all_projects[project]["project_id"])
            self.delete_seeds_by_label(label)

    def format_label(self, ctx: GcpScanContext, project_id: str) -> str:
        """Format Gcp label.

        Args:
            ctx (GcpScanContext): Scan context.
            project_id (str): Gcp asset project ID

        Returns:
            str: Formatted asset label.
        """
        return f"{self.label_prefix}{ctx.organization_id}/{project_id}"

    def format_uid(self, ctx: GcpScanContext, project_id: Optional[str]) -> str:
        """Format Gcp uid.

        Args:
            ctx (GcpScanContext): Scan context.
            project_id (Optional[str]): Gcp asset project id.

        Returns:
            str: Formatted asset uid.
        """
        return f"{self.label_prefix}{ctx.organization_id}/{project_id}"

    def search_all_resources(
        self, ctx: GcpScanContext, filter: Optional[str] = None
    ) -> SearchAllResourcesPager:
        """List Gcp assets.

        Args:
            filter (Optional[str]): Filter string.

        Returns:
            SearchAllResourcesPager: Gcp assets.
        """
        request = {
            "scope": ctx.provider_settings.parent(),
            "asset_types": [filter],
            "read_mask": "*",
        }
        return ctx.cloud_asset_client.search_all_resources(request=request)

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
                    with SuppressValidationError():
                        bucket_asset = GcpStorageBucketAsset(
                            # TODO: Update when API can accept other urls
                            value=f"https://storage.googleapis.com/{bucket_name}",
                            uid=uid,
                            # Cast project_number to int from float
                            scan_data=scan_data,
                        )
                        self.add_cloud_asset(bucket_asset)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                self.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue
