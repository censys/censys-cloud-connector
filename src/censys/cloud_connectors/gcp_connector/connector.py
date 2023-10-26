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

    label_prefix: str
    provider_settings: GcpSpecificSettings
    organization_id: int
    credentials: service_account.Credentials

    cloud_asset_client: AssetServiceClient
    all_projects: dict[str, dict[str, str]]
    logger: Logger

# TODO: question: seed labels and cloud asset uids are the same for GCP. Is that confusing for keeping stale seeds out? Or does the fact that we submit seeds and cloud assets separately make it ok?

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
        ctx: GcpScanContext = kwargs["scan_context"]

        logger = get_logger(
            log_name=f"{self.provider.lower()}_connector",
            level=self.settings.logging_level,
            provider=f"{self.provider}_{ctx.organization_id}",
        )
        ctx.logger = logger

        key_file_path = (
            Path(self.settings.secrets_dir)
            / ctx.provider_settings.service_account_json_file
        )
        try:
            ctx.credentials = (
                service_account.Credentials.from_service_account_file(
                    str(key_file_path)
                )
            )
        except ValueError as e:
            ctx.logger.error(
                "Failed to load service account credentials from"
                f" {key_file_path}: {e}"
            )
            raise

        ctx.cloud_asset_client = AssetServiceClient(
            credentials=ctx.credentials
        )

        # TODO: potentially add this to provider_settings. once populated it doesn't change, just accessed
        all_projects = self.list_projects(ctx)
        ctx.all_projects = all_projects

        ctx.logger.info(
            f"Scanning GCP organization {ctx.organization_id} for seeds."
        )

        # TODO: make sure events are working (not broken by worker pool change)
        # TODO: specify that this is a scan of seeds
        self.dispatch_event(EventTypeEnum.SCAN_STARTED)
        super().scan_seeds(**kwargs)
        self.dispatch_event(EventTypeEnum.SCAN_FINISHED)
        # TODO: maybe we can add some additional info here (like project id) for the healthcheck ui?

    def scan_cloud_assets(self, **kwargs):
        """Scan AWS for cloud assets."""
        ctx: GcpScanContext = kwargs["scan_context"]

        logger = get_logger(
            log_name=f"{self.provider.lower()}_connector",
            level=self.settings.logging_level,
            provider=f"{self.provider}_{ctx.organization_id}",
        )
        ctx.logger = logger

        key_file_path = (
            Path(self.settings.secrets_dir)
            / ctx.provider_settings.service_account_json_file
        )
        try:
            ctx.credentials = (
                service_account.Credentials.from_service_account_file(
                    str(key_file_path)
                )
            )
        except ValueError as e:
            ctx.logger.error(
                "Failed to load service account credentials from"
                f" {key_file_path}: {e}"
            )
            raise

        ctx.cloud_asset_client = AssetServiceClient(
            credentials=ctx.credentials
        )

        all_projects = self.list_projects(ctx)
        ctx.all_projects = all_projects

        ctx.logger.info(
            f"Scanning GCP organization {ctx.organization_id} for cloud assets."
        )

        # TODO: make sure events are working (not broken by worker pool change)
        # TODO: specify that this is a scan of cloud assets
        self.dispatch_event(EventTypeEnum.SCAN_STARTED)
        super().scan_cloud_assets(**kwargs)
        self.dispatch_event(EventTypeEnum.SCAN_FINISHED)

    def scan_all(self):
        """Scan all Gcp Organizations."""
        provider_settings: dict[
            tuple, GcpSpecificSettings
        ] = self.settings.providers.get(self.provider, {})

        self.logger.debug(
            f"Scanning GCP using {self.settings.scan_concurrency} processes."
        )

        label_prefix = self.get_provider_label_prefix()

        pool = Pool(processes=self.settings.scan_concurrency)

        self.logger.debug("after pool, before for loop")

        for provider_setting in provider_settings.values():
            # `provider_setting` represents a specific top-level GcpOrganization entry in providers.yml
            #
            # DO NOT use provider_settings anywhere in this class!
            # provider_settings exists for the parent CloudConnector
            self.provider_settings = provider_setting
            organization_id = provider_setting.organization_id

            try:
                # scan seeds
                with Healthcheck(
                    self.settings,
                    provider_setting,
                    provider={"organization_id": organization_id},
                    exception_map={
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
                        credentials=None,
                        cloud_asset_client=None,
                        all_projects=None,
                        logger=None,
                        label_prefix=label_prefix,
                    )
                    
                    pool.apply_async(
                        self.scan_seeds,
                        kwds={"scan_context": scan_context},
                        error_callback=lambda e: self.logger.error(f"Async Error: {e}")
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
                    provider={"organization_id": organization_id},
                    exception_map={
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
                        credentials=None,
                        cloud_asset_client=None,
                        all_projects=None,
                        logger=None,
                        label_prefix=label_prefix,
                    )

                    
                    pool.apply_async(
                        self.scan_cloud_assets,
                        kwds={"scan_context": scan_context},
                        error_callback=lambda e: self.logger.error(f"Async Error: {e}")
                    )

            except Exception as e:
                self.logger.error(
                    f"Unable to scan GCP organization {organization_id}. Error: {e}",
                )
                self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)

        pool.close()
        pool.join()

    def list_projects(self, ctx: GcpScanContext) -> dict[str, dict]:
        """List Gcp projects.

        Returns:
            dict[str, dict]: Gcp projects.
        """
        results = self.search_all_resources(ctx, filter=GcpCloudAssetInventoryTypes.PROJECT)
        projects: dict[str, dict[str, str]] = {}
        for result in results:
            try:
                project = ResourceSearchResult.to_dict(result)
            except json.decoder.JSONDecodeError:  # pragma: no cover
                self.logger.debug(f"Failed to parse project: {project}")
                continue

            try:
                if versioned_resource := self.check_asset_version(
                    ctx, GcpCloudAssetInventoryTypes.PROJECT, project
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

    # TODO: do we need this still?
    # def clean_up(self):
    #     """Remove seeds and cloud assets for GCP projects where no assets were found."""
    #     possible_projects = set(self.all_projects.keys())
    #     empty_projects = possible_projects - self.found_projects
    #     for project in empty_projects:
    #         label = self.format_label(self.all_projects[project]["project_id"])
    #         self.delete_seeds_by_label(label)

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
            "scope": ctx.provider_settings.parent(), # TODO: can I use this?
            "asset_types": [filter],
            "read_mask": "*",
        }
        return ctx.cloud_asset_client.search_all_resources(request=request)

    def get_compute_instances(self, **kwargs):
        """Get Gcp compute instances assets."""
        ctx: GcpScanContext = kwargs["scan_context"]
        try:
            results = self.search_all_resources(
                ctx, filter=GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE
            )
        except ValueError as e:
            ctx.logger.error(f"Failed to get compute instances: {e}")
            return

        for result in results:
            try:
                seeds = []
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    ctx, GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    if (
                        network_interfaces := resource.get("networkInterfaces", [])
                    ) and (
                        project_id := ctx.all_projects.get(project_number, {}).get(
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
                                label = self.format_label(ctx, project_id)
                                with SuppressValidationError():
                                    # ip_seed = IpSeed(
                                    #     value=ip_address,
                                    #     label=label,
                                    # )
                                    # self.add_seed(ip_seed)
                                    seed = self.process_seed(
                                        IpSeed(
                                            value=ip_address,
                                            label=label,
                                        )
                                    )
                                    seeds.append(seed)

            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                ctx.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

        self.submit_seed_payload(label, seeds)

    def get_compute_addresses(self, **kwargs):
        """Get Gcp ip address assets."""
        ctx: GcpScanContext = kwargs["scan_context"]

        try:
            results = self.search_all_resources(
                ctx, filter=GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS
            )
        except ValueError as e:
            ctx.logger.error(f"Failed to get compute addresses: {e}")
            return

        for result in results:
            try:
                seeds = []
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    ctx, GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    ip_address: str = resource["address"]
                    if project_id := ctx.all_projects.get(project_number, {}).get(
                        "project_id"
                    ):
                        with SuppressValidationError():
                            label = self.format_label(ctx, project_id)
                            # ip_seed = IpSeed(
                            #     value=ip_address,
                            #     label=label,
                            # )
                            # self.add_seed(ip_seed)
                            seed = self.process_seed(
                                IpSeed(
                                    value=ip_address,
                                    label=label,
                                )
                            )
                            seeds.append(seed)
            
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                ctx.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

        self.submit_seed_payload(label, seeds)

    def get_container_clusters(self, **kwargs):
        """Get Gcp container clusters."""
        ctx: GcpScanContext = kwargs["scan_context"]

        try:
            results = self.search_all_resources(
                ctx, filter=GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER
            )
        except ValueError as e:
            ctx.logger.error(f"Failed to get container clusters: {e}")
            return

        for result in results:
            try:
                seeds = []
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    ctx, GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    if (
                        ip_address := resource.get("privateClusterConfig", {}).get(
                            "publicEndpoint"
                        )
                    ) and (
                        project_id := ctx.all_projects.get(project_number, {}).get(
                            "project_id"
                        )
                    ):
                        label = self.format_label(ctx, project_id)
                        with SuppressValidationError():
                            # ip_seed = IpSeed(
                            #     value=ip_address,
                            #     label=label,
                            # )
                            # self.add_seed(ip_seed)
                            seed = self.process_seed(
                                IpSeed(
                                    value=ip_address,
                                    label=label,
                                )
                            )
                            seeds.append(seed)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                ctx.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

        self.submit_seed_payload(label, seeds)

    def get_cloud_sql_instances(self, **kwargs):
        """Get Gcp cloud sql instances."""
        ctx: GcpScanContext = kwargs["scan_context"]

        try:
            results = self.search_all_resources(
                ctx, filter=GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE
            )
        except ValueError as e:
            ctx.logger.error(f"Failed to get cloud sql instances: {e}")
            return

        for result in results:
            try:
                seeds = []
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    ctx, GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    ip_addresses: list = resource["ipAddresses"]
                    if project_id := ctx.all_projects.get(project_number, {}).get(
                        "project_id"
                    ):
                        for ip_address in [
                            address
                            for ip in ip_addresses
                            if (address := ip["ipAddress"])
                        ]:
                            label = self.format_label(ctx, project_id)
                            with SuppressValidationError():
                                # ip_seed = IpSeed(
                                #     value=ip_address,
                                #     label=label,
                                # )
                                # self.add_seed(ip_seed)
                                seed = self.process_seed(
                                    IpSeed(
                                        value=ip_address,
                                        label=label,
                                    )
                                )
                                seeds.append(seed)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                ctx.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

        self.submit_seed_payload(label, seeds)

    def get_dns_records(self, **kwargs):
        """Get Gcp dns records."""
        ctx: GcpScanContext = kwargs["scan_context"]
        
        try:
            results = self.search_all_resources(ctx, filter=GcpCloudAssetInventoryTypes.DNS_ZONE)
        except ValueError as e:
            ctx.logger.error(f"Failed to get dns records: {e}")
            return

        for result in results:
            try:
                seeds = []
                asset = ResourceSearchResult.to_dict(result)
                if versioned_resource := self.check_asset_version(
                    ctx, GcpCloudAssetInventoryTypes.DNS_ZONE, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    domain: str = resource["dnsName"]
                    if (resource.get("visibility", "") == "PUBLIC") and (  # Optional
                        project_id := ctx.all_projects.get(project_number, {}).get(
                            "project_id"
                        )
                    ):
                        label = self.format_label(ctx, project_id)
                        with SuppressValidationError():
                            # domain_seed = DomainSeed(value=domain, label=label)
                            # self.add_seed(domain_seed)
                            seed = self.process_seed(
                                DomainSeed(value=domain, label=label)
                            )
                            seeds.append(seed)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                ctx.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

        self.submit_seed_payload(label, seeds)

    def get_storage_buckets(self, **kwargs):
        """Get Gcp storage buckets."""
        ctx: GcpScanContext = kwargs["scan_context"]

        try:
            results = self.search_all_resources(
                ctx, filter=GcpCloudAssetInventoryTypes.STORAGE_BUCKET
            )
        except ValueError as e:
            ctx.logger.error(f"Failed to get storage buckets: {e}")
            return

        
        for result in results:
            try:
                asset = ResourceSearchResult.to_dict(result)
                # We want to submit a payload per uid, so we need to keep track of the uids we've seen
                # TODO: should this be a set instead of a list? Could there be duplicate buckets?
                # findings = { 'GCP: 123456789123/my-project-1': [asset, ...], 'GCP: 123456789123/my-project-2': [asset, ...]}
                findings: dict[str, list[GcpStorageBucketAsset]] = {}
                if versioned_resource := self.check_asset_version(
                    ctx, GcpCloudAssetInventoryTypes.STORAGE_BUCKET, asset
                ):
                    resource = versioned_resource["resource"]
                    project_path: str = asset["project"]
                    project_number = self.parse_project_number(project_path)
                    bucket_name: str = resource["id"]
                    scan_data = {"accountNumber": int(project_number)}
                    if project_id := ctx.all_projects.get(project_number, {}).get(
                        "project_id"
                    ):
                        scan_data["projectName"] = project_id
                    scan_data["location"]: str = resource["location"]
                    scan_data["selfLink"]: str = resource["selfLink"]
                    uid = self.format_uid(ctx, project_id)
                    with SuppressValidationError():
                        bucket_asset = GcpStorageBucketAsset(
                            # TODO: Update when API can accept other urls
                            value=f"https://storage.googleapis.com/{bucket_name}",
                            uid=uid,
                            # Cast project_number to int from float
                            scan_data=scan_data, # TODO: is the scan_data the same?
                        )
                        # self.add_cloud_asset(bucket_asset)

                        # TODO: do we need this? does it need other args like bucket_name?
                        bucket_asset = self.process_cloud_asset(bucket_asset)

                        if uid not in findings:
                            findings[uid] = []
                        findings[uid].append(bucket_asset)
            except (
                json.decoder.JSONDecodeError,
                ValueError,
                KeyError,
            ) as e:  # pragma: no cover
                ctx.logger.debug(f"Failed to parse asset: {asset}: {e}")
                continue

        for uid, assets in findings.items():
            self.submit_cloud_asset_payload(uid, assets)
