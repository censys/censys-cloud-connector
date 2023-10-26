"""Azure Cloud Connector."""
from collections.abc import Generator
from dataclasses import dataclass
from multiprocessing import Pool
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
from censys.cloud_connectors.common.healthcheck import Healthcheck
from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .enums import AzureResourceTypes
from .settings import AzureSpecificSettings


# TODO: make a ctor that has required params but also optional params
# the scan() method is currently building all of this out which could lead to misconfiguration and runtime errors
@dataclass
class AzureScanContext:
    """Required configuration context for Azure scans."""

    label_prefix: str
    provider_settings: AzureSpecificSettings
    subscription_id: str
    credentials: ClientSecretCredential
    possible_labels: set[str]  # = set()  # TODO: verify this works
    scan_all_regions: bool


class AzureCloudConnector(CloudConnector):
    """Azure Cloud Connector."""

    provider = ProviderEnum.AZURE
    # subscription_id: str
    # credentials: ClientSecretCredential
    #
    # TODO: provider_settings is used in the parent class... figure out how to break out those methods (would fix the parent self.logger calls using root logger instead of ctx.logger)
    provider_settings: AzureSpecificSettings
    #
    # possible_labels: set[str]
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
        # self.possible_labels = set()
        self.scan_all_regions = settings.azure_refresh_all_regions

    def get_all_labels(
        self,
        credentials: ClientSecretCredential,
        subscription_id: str,
        label_prefix: str,
    ) -> set[str]:
        """Get Azure labels.

        Args:
            subscription_id (str): Azure subscription ID.
            label_prefix (str): Label prefix.

        Returns:
            set[str]: Azure labels.
        """
        subscription_client = SubscriptionClient(credentials)

        locations = subscription_client.subscriptions.list_locations(subscription_id)

        # self.possible_labels.clear()
        possible_labels = set()

        for location in locations:
            # self.possible_labels.add(
            possible_labels.add(
                # f"{self.label_prefix}{self.subscription_id}/{location.name}"
                f"{label_prefix}{subscription_id}/{location.name}"
            )

        return possible_labels

    def scan(self, **kwargs):
        """Scan Azure Subscription.

        Args:
            **kwargs: Keyword arguments.
                scan_context (AzureScanContext): Azure scan context.
        """
        ctx: AzureScanContext = kwargs["scan_context"]

        ctx.credentials = ClientSecretCredential(
            tenant_id=ctx.provider_settings.tenant_id,
            client_id=ctx.provider_settings.client_id,
            client_secret=ctx.provider_settings.client_secret,
        )

        # TODO: remove possible_labels
        ctx.label_prefix = self.get_provider_label_prefix()  # TODO: move to ctor
        if self.scan_all_regions:
            ctx.possible_labels = self.get_all_labels(
                ctx.subscription_id, ctx.label_prefix
            )
        else:
            ctx.possible_labels = set()

        logger = get_logger(
            log_name=f"{self.provider.lower()}_cloud_connector",
            level=self.settings.logging_level,
            provider=f"{self.provider}_{ctx.subscription_id}",
        )
        ctx.logger = logger
        ctx.logger.info(f"Scanning {self.provider} - sub:{ctx.subscription_id}")

        with Healthcheck(
            self.settings,
            ctx.provider_settings,  # self.provider_settings,
            # provider={"subscription_id": self.subscription_id},
            provider={"subscription_id": ctx.subscription_id},
            exception_map={
                ClientAuthenticationError: "PERMISSIONS",
            },
        ):
            super().scan(**kwargs)

            # TODO: remove possible_labels
            if self.scan_all_regions:
                # for label_not_found in self.possible_labels:
                for label_not_found in ctx.possible_labels:
                    self.delete_seeds_by_label(label_not_found)

    def scan_all(self):
        """Scan all Azure Subscriptions."""
        provider_settings: dict[
            tuple, AzureSpecificSettings
        ] = self.settings.providers.get(self.provider, {})

        self.logger.debug(
            f"scanning {self.provider} using {self.settings.scan_concurrency} processes"
        )

        pool = Pool(processes=self.settings.scan_concurrency)

        for provider_setting in provider_settings.values():
            # this is so confusing - plural settings to setting?
            self.provider_settings = provider_setting

            # self.credentials = ClientSecretCredential(
            # credentials = ClientSecretCredential(
            #     tenant_id=provider_setting.tenant_id,
            #     client_id=provider_setting.client_id,
            #     client_secret=provider_setting.client_secret,
            # )

            for subscription_id in self.provider_settings.subscription_id:
                self.logger.info(f"Scanning Azure Subscription {subscription_id}")
                # self.subscription_id = subscription_id

                try:
                    scan_context = AzureScanContext(
                        provider_settings=provider_setting,
                        subscription_id=subscription_id,
                        credentials=None,
                        # credentials=credentials,
                        # possible_labels=possible_labels,  # self.possible_labels,
                        possible_labels=None,
                        scan_all_regions=self.scan_all_regions,
                        label_prefix=None,  # label_prefix=label_prefix,
                    )

                    # self.scan(**{"scan_context": scan_context})
                    # pool.apply_async(
                    pool.apply_async(
                        # self.scan_seeds,
                        self.scan,
                        kwds={
                            "scan_context": scan_context,
                        },
                        error_callback=lambda e: self.logger.error(f"Async Error: {e}"),
                    )
                except Exception as e:
                    self.logger.error(
                        f"Unable to scan Azure Subscription {subscription_id}. Error: {e}"
                    )
                    self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)
                # self.subscription_id = None

        pool.close()
        pool.join()

    # TODO: reorder params (sub_id, asset, label_prefix)
    def format_label(
        self,
        asset: AzureModel,
        subscription_id: str,
        label_prefix: str,
    ) -> str:
        """Format Azure asset label.

        Args:
            asset (AzureModel): Azure asset.
            subscription_id (str): Azure subscription ID.
            label_prefix (str): Label prefix.

        Returns:
            str: Formatted label.

        Raises:
            ValueError: If asset has no location.
        """
        asset_location: Optional[str] = getattr(asset, "location", None)
        if not asset_location:
            raise ValueError("Asset has no location.")
        # return f"{self.label_prefix}{self.subscription_id}/{asset_location}"
        return f"{label_prefix}{subscription_id}/{asset_location}"

    def get_ip_addresses(self, **kwargs):
        """Get Azure IP addresses.

        Args:
            **kwargs: Keyword arguments.
                scan_context (AzureScanContext): Azure scan context.
        """
        ctx: AzureScanContext = kwargs["scan_context"]
        # network_client = NetworkManagementClient(self.credentials, self.subscription_id)
        network_client = NetworkManagementClient(ctx.credentials, ctx.subscription_id)

        try:
            assets = network_client.public_ip_addresses.list_all()
        except HttpResponseError as error:
            ctx.logger.error(f"Failed to get Azure IP addresses: {error.message}")
            return

        for asset in assets:
            try:
                seeds = []
                label = self.format_label(asset, ctx.subscription_id, ctx.label_prefix)
                asset_dict = asset.as_dict()

                if ip_address := asset_dict.get("ip_address"):
                    with SuppressValidationError():
                        # ip_seed = IpSeed(value=ip_address, label=label)
                        # self.add_seed(ip_seed)
                        # self.possible_labels.discard(label)
                        seed = self.process_seed(IpSeed(value=ip_address, label=label))
                        seeds.append(seed)
                        ctx.possible_labels.discard(label)

                self.submit_seed_payload(label, seeds)
            except Exception as e:
                ctx.logger.error(f"Failed to process Azure IP addresses: {e}")

    def get_clusters(self, **kwargs):
        """Get Azure clusters.

        Args:
            **kwargs: Keyword arguments.
                scan_context (AzureScanContext): Azure scan context.
        """
        ctx: AzureScanContext = kwargs["scan_context"]
        # container_client = ContainerInstanceManagementClient(self.credentials, self.subscription_id)
        container_client = ContainerInstanceManagementClient(
            ctx.credentials, ctx.subscription_id
        )
        try:
            assets = container_client.container_groups.list()
        except HttpResponseError as error:
            ctx.logger.error(
                f"Failed to get Azure Container Instances: {error.message}"
            )
            return

        for asset in assets:
            try:
                asset_dict = asset.as_dict()
                if (
                    (ip_address_dict := asset_dict.get("ip_address"))
                    and (ip_address_dict.get("type") == "Public")
                    and (ip_address := ip_address_dict.get("ip"))
                ):
                    seeds = []
                    label = self.format_label(
                        asset, ctx.subscription_id, ctx.label_prefix
                    )

                    with SuppressValidationError():
                        # ip_seed = IpSeed(value=ip_address, label=label)
                        # self.add_seed(ip_seed)
                        # self.possible_labels.discard(label)
                        seed = self.process_seed(IpSeed(value=ip_address, label=label))
                        seeds.append(seed)
                        ctx.possible_labels.discard(label)

                    if domain := ip_address_dict.get("fqdn"):
                        with SuppressValidationError():
                            # domain_seed = DomainSeed(value=domain, label=label)
                            # self.add_seed(domain_seed)
                            # self.possible_labels.discard(label)
                            seed = self.process_seed(
                                DomainSeed(value=domain, label=label)
                            )
                            seeds.append(seed)
                            ctx.possible_labels.discard(label)

                    self.submit_seed_payload(label, seeds)
            except Exception as e:
                ctx.logger.error(f"Failed to process Azure clusters: {e}")

    def get_sql_servers(self, **kwargs):
        """Get Azure SQL servers.

        Args:
            **kwargs: Keyword arguments.
                scan_context (AzureScanContext): Azure scan context.
        """
        ctx: AzureScanContext = kwargs["scan_context"]
        # sql_client = SqlManagementClient(self.credentials, self.subscription_id)
        sql_client = SqlManagementClient(ctx.credentials, ctx.subscription_id)

        try:
            assets = sql_client.servers.list()
        except HttpResponseError as error:
            ctx.logger.error(f"Failed to get Azure SQL servers: {error.message}")
            return

        for asset in assets:
            asset_dict = asset.as_dict()
            try:
                if (
                    domain := asset_dict.get("fully_qualified_domain_name")
                ) and asset_dict.get("public_network_access") == "Enabled":
                    with SuppressValidationError():
                        label = self.format_label(
                            asset, ctx.subscription_id, ctx.label_prefix
                        )
                        # domain_seed = DomainSeed(value=domain, label=label)
                        # self.add_seed(domain_seed)
                        # self.possible_labels.discard(label)

                        # TODO: verify that asset+label->payload is correct; other methods have a seeds array that is appended to and 1 payload is sent
                        seed = self.process_seed(DomainSeed(value=domain, label=label))
                        ctx.possible_labels.discard(label)
                        self.submit_seed_payload(label, [seed])
            except Exception as e:
                ctx.logger.error(f"Failed to process Azure SQL servers: {e}")

    def get_dns_records(self, **kwargs):
        """Get Azure DNS records.

        Args:
            **kwargs: Keyword arguments.
                scan_context (AzureScanContext): Azure scan context.
        """
        ctx: AzureScanContext = kwargs["scan_context"]
        # dns_client = DnsManagementClient(self.credentials, self.subscription_id)
        dns_client = DnsManagementClient(ctx.credentials, ctx.subscription_id)

        try:
            zones = dns_client.zones.list()
        except HttpResponseError as error:
            ctx.logger.error(f"Failed to get Azure DNS records: {error.message}")
            return

        try:
            for zone in zones:
                zone_dict = zone.as_dict()
                # TODO: Do we need to check if zone is public? (ie. do we care?)
                if zone_dict.get("zone_type") != "Public":  # pragma: no cover
                    continue

                try:
                    label = self.format_label(
                        zone, ctx.subscription_id, ctx.label_prefix
                    )
                    seeds = []

                    zone_resource_group = zone_dict.get("id").split("/")[4]
                    for asset in dns_client.record_sets.list_all_by_dns_zone(
                        zone_resource_group, zone_dict.get("name")
                    ):
                        asset_dict = asset.as_dict()

                        if domain_name := asset_dict.get("fqdn"):
                            with SuppressValidationError():
                                # domain_seed = DomainSeed(value=domain_name, label=label)
                                # self.add_seed(domain_seed)
                                # self.possible_labels.discard(label)
                                seed = self.process_seed(
                                    DomainSeed(value=domain_name, label=label)
                                )
                                seeds.append(seed)
                                ctx.possible_labels.discard(label)

                        if cname := asset_dict.get("cname_record", {}).get("cname"):
                            with SuppressValidationError():
                                # domain_seed = DomainSeed(value=cname, label=label)
                                # self.add_seed(domain_seed)
                                # self.possible_labels.discard(label)
                                seed = self.process_seed(
                                    DomainSeed(value=cname, label=label)
                                )
                                seeds.append(seed)
                                ctx.possible_labels.discard(label)

                        for a_record in asset_dict.get("a_records", []):
                            ip_address = a_record.get("ipv4_address")
                            if not ip_address:
                                continue

                            with SuppressValidationError():
                                # ip_seed = IpSeed(value=ip_address, label=label)
                                # self.add_seed(ip_seed)
                                # self.possible_labels.discard(label)
                                seed = self.process_seed(
                                    IpSeed(value=ip_address, label=label)
                                )
                                seeds.append(seed)
                                ctx.possible_labels.discard(label)

                    self.submit_seed_payload(label, seeds)
                except Exception as e:
                    ctx.logger.error(f"Failed to process Azure DNS records: {e}")

        except Exception as e:
            # TODO: health check should have a way to emit errors yet still proceed to next resource type
            ctx.logger.error(f"Failed to list Azure DNS records: {e}")

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

    def get_storage_containers(self, **kwargs):
        """Get Azure containers.

        Args:
            **kwargs: Keyword arguments.
                scan_context (AzureScanContext): Azure scan context.
        """
        ctx: AzureScanContext = kwargs["scan_context"]
        # storage_client = StorageManagementClient(self.credentials, self.subscription_id)
        storage_client = StorageManagementClient(ctx.credentials, ctx.subscription_id)

        try:
            accounts = storage_client.storage_accounts.list()
        except HttpResponseError as error:
            ctx.logger.error(f"Failed to get Azure storage accounts: {error.message}")
            return

        for account in accounts:
            try:
                # bucket_client = BlobServiceClient(f"https://{account.name}.blob.core.windows.net/", self.credentials)
                bucket_client = BlobServiceClient(
                    f"https://{account.name}.blob.core.windows.net/", ctx.credentials
                )

                label = self.format_label(
                    account, ctx.subscription_id, ctx.label_prefix
                )
                account_dict = account.as_dict()

                # create seed from storage container
                if (custom_domain := account_dict.get("custom_domain")) and (
                    domain := custom_domain.get("name")
                ):
                    with SuppressValidationError():
                        # domain_seed = DomainSeed(value=domain, label=label)
                        # self.add_seed(domain_seed)
                        # self.possible_labels.discard(label)
                        seed = self.process_seed(DomainSeed(value=domain, label=label))
                        ctx.possible_labels.discard(label)
                        self.submit_seed_payload(label, seed)

                # create cloud asset from storage container
                # uid = f"{self.subscription_id}/{self.credentials._tenant_id}/{account.name}"
                uid = (
                    f"{ctx.subscription_id}/{ctx.credentials._tenant_id}/{account.name}"
                )

                for container in self._list_containers(bucket_client, account):
                    try:
                        container_client = bucket_client.get_container_client(container)
                        container_url = container_client.url
                        with SuppressValidationError():
                            container_asset = self.process_cloud_asset(
                                AzureContainerAsset(
                                    value=container_url,
                                    uid=uid,
                                    scan_data={
                                        "accountNumber": ctx.subscription_id,  # "accountNumber": self.subscription_id,
                                        "publicAccess": container.public_access,
                                        "location": account.location,
                                    },
                                ),
                                label_prefix=ctx.label_prefix,
                            )
                            # self.add_cloud_asset(container_asset)
                            self.submit_cloud_asset_payload(label, [container_asset])
                    except ServiceRequestError as error:  # pragma: no cover
                        ctx.logger.error(
                            f"Failed to get Azure container {container} for {account.name}: {error.message}"
                        )

            except Exception as e:
                ctx.logger.error(f"Failed to process Azure storage accounts: {e}")
