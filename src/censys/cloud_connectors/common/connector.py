"""Base class for all cloud connectors."""
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from logging import Logger
from typing import Callable, Optional, Union

from cloudevents.http import CloudEvent

from censys.asm import Beta, Seeds
from censys.common.exceptions import CensysAsmException

from censys.cloud_connectors.common.aurora import Aurora

from .cloud_asset import CloudAsset
from .enums import EventTypeEnum, PayloadTypes, ProviderEnum
from .logger import get_logger
from .plugins import CloudConnectorPluginRegistry, EventContext
from .seed import Seed
from .settings import ProviderSpecificSettings, Settings


class CloudConnector(ABC):
    """Base class for Cloud Connectors."""

    provider: ProviderEnum
    provider_settings: ProviderSpecificSettings
    label_prefix: str
    settings: Settings
    logger: Logger
    seeds_api: Seeds
    beta_api: Beta
    aurora_api: Aurora
    seeds: dict[str, set[Seed]]
    cloud_assets: dict[str, set[CloudAsset]]
    seed_scanners: dict[str, Callable[[], None]]
    cloud_asset_scanners: dict[str, Callable[[], None]]
    current_service: Optional[Union[str, Enum]]

    def __init__(self, settings: Settings):
        """Initialize the Cloud Connector.

        Args:
            settings (Settings): The settings to use.

        Raises:
            ValueError: If the provider is not set.
        """
        if not self.provider:
            raise ValueError("The provider must be set.")
        self.label_prefix = self.provider.label() + ": "
        self.settings = settings
        self.logger = get_logger(
            log_name=f"{self.provider.lower()}_cloud_connector",
            level=settings.logging_level,
        )

        self.seeds_api = Seeds(
            settings.censys_api_key,
            url=settings.censys_asm_api_base_url,
            user_agent=settings.censys_user_agent,
            cookies=settings.censys_cookies,
        )
        self.beta_api = Beta(
            settings.censys_api_key,
            url=settings.censys_asm_api_base_url,
            user_agent=settings.censys_user_agent,
            cookies=settings.censys_cookies,
        )
        self.aurora_api = Aurora(
            settings.censys_api_key,
            url=settings.censys_asm_api_base_url,
            user_agent=settings.censys_user_agent,
            cookies=settings.censys_cookies,
        )

        self.seeds = defaultdict(set)
        self.cloud_assets = defaultdict(set)
        self.current_service = None

    def delete_seeds_by_label(self, label: str):
        """Replace seeds for [label] with an empty list.

        Args:
            label: Label for seeds to be deleted.
        """
        try:
            self.logger.debug(f"Deleting any seeds matching label {label}.")
            self.seeds_api.replace_seeds_by_label(label, [], True)
        except CensysAsmException as e:
            self.logger.error(f"Error deleting seeds for label {label}: {e}")
        self.logger.info(f"Deleted any seeds for label {label}.")
        self.dispatch_event(EventTypeEnum.SEEDS_DELETED, label=label)

    def get_seeds(self, **kwargs) -> None:
        """Gather seeds."""
        for seed_type, seed_scanner in self.seed_scanners.items():
            self.current_service = seed_type
            if (
                self.provider_settings.ignore
                and seed_type in self.provider_settings.ignore
            ):
                self.logger.debug(f"Skipping {seed_type}")
                continue
            self.logger.debug(f"Scanning {seed_type}")

            start = time.time()
            seed_scanner(**kwargs)
            duration = time.time() - start
            self.logger.debug(
                f"Scan seed-type:{seed_type} count:{len(self.seeds)} duration:{duration:.2f}"
            )
        self.current_service = None

    def get_cloud_assets(self, **kwargs) -> None:
        """Gather cloud assets."""
        for cloud_asset_type, cloud_asset_scanner in self.cloud_asset_scanners.items():
            self.current_service = cloud_asset_type
            if (
                self.provider_settings.ignore
                and cloud_asset_type in self.provider_settings.ignore
            ):
                self.logger.debug(f"Skipping {cloud_asset_type}")
                continue
            self.logger.debug(f"Scanning {cloud_asset_type}")

            start = time.time()
            cloud_asset_scanner(**kwargs)
            duration = time.time() - start
            self.logger.debug(
                f"Scan cloud-asset-type:{cloud_asset_type} count:{len(self.seeds)} duration:{duration:.2f}"
            )
        self.current_service = None

    def get_event_context(
        self,
        event_type: EventTypeEnum,
        service: Optional[Union[str, Enum]] = None,
    ) -> EventContext:
        """Get the event context.

        Args:
            event_type (EventTypeEnum): The event type.
            service (Union[str, Enum], optional): The service. Defaults to None.

        Returns:
            EventContext: The event context.
        """
        return {
            "event_type": event_type,
            "connector": self,
            "provider": self.provider,
            # service=None, this uses the self.current_service for the value
            "service": service or self.current_service,
        }

    def dispatch_event(
        self,
        event_type: EventTypeEnum,
        service: Optional[Union[str, Enum]] = None,
        **kwargs,
    ):
        """Dispatch an event.

        Args:
            event_type (EventTypeEnum): The event type.
            service (Union[str, Enum], optional): The service. Defaults to None.
            **kwargs: The event data.
        """
        context = self.get_event_context(event_type, service)
        CloudConnectorPluginRegistry.dispatch_event(context=context, **kwargs)

    def add_seed(self, seed: Seed, **kwargs):
        """Add a seed.

        Args:
            seed (Seed): The seed to add.
            **kwargs: Additional data for event dispatching.
        """
        # TODO: not compatible with multiprocessing
        if not seed.label.startswith(self.label_prefix):
            seed.label = self.label_prefix + seed.label
        self.seeds[seed.label].add(seed)
        self.logger.debug(f"Found Seed: {seed.to_dict()}")
        self.dispatch_event(EventTypeEnum.SEED_FOUND, seed=seed, **kwargs)

    def add_cloud_asset(self, cloud_asset: CloudAsset, **kwargs):
        """Add a cloud asset.

        Args:
            cloud_asset (CloudAsset): The cloud asset to add.
            **kwargs: Additional data for event dispatching.
        """
        # TODO: not compatible with multiprocessing
        if not cloud_asset.uid.startswith(self.label_prefix):
            cloud_asset.uid = self.label_prefix + cloud_asset.uid
        self.cloud_assets[cloud_asset.uid].add(cloud_asset)
        self.logger.debug(f"Found Cloud Asset: {cloud_asset.to_dict()}")
        self.dispatch_event(
            EventTypeEnum.CLOUD_ASSET_FOUND, cloud_asset=cloud_asset, **kwargs
        )

    def submit_seeds(self):
        """Submit the seeds to Censys ASM."""
        # TODO: not compatible with multiprocessing
        submitted_seeds = 0
        for label, seeds in self.seeds.items():
            try:
                self.seeds_api.replace_seeds_by_label(
                    label, [seed.to_dict() for seed in seeds]
                )
                submitted_seeds += len(seeds)
            except CensysAsmException as e:
                self.logger.error(f"Error submitting seeds for {label}: {e}")
        self.logger.info(f"Submitted {submitted_seeds} seeds.")
        self.dispatch_event(EventTypeEnum.SEEDS_SUBMITTED, count=submitted_seeds)

    def submit_cloud_assets(self):
        """Submit the cloud assets to Censys ASM."""
        # TODO: not compatible with multiprocessing
        submitted_assets = 0
        for uid, cloud_assets in self.cloud_assets.items():
            try:
                self.beta_api.add_cloud_assets(
                    uid, [asset.to_dict() for asset in cloud_assets]
                )
                submitted_assets += len(cloud_assets)
            except CensysAsmException as e:
                self.logger.error(f"Error submitting cloud assets for {uid}: {e}")
        self.logger.info(f"Submitted {submitted_assets} cloud assets.")
        self.dispatch_event(
            EventTypeEnum.CLOUD_ASSETS_SUBMITTED, count=submitted_assets
        )

    def process_seed(self, seed: Seed, **kwargs) -> Seed:
        """Prepare a seed for submission. Also dispatch events.

        Args:
            seed (Seed): Seed.

        Returns:
            Seed: Processed seed.
        """
        if not seed.label.startswith(self.label_prefix):
            seed.label = self.label_prefix + seed.label

        self.logger.debug(f"Found Seed: {seed.to_dict()}")
        self.dispatch_event(EventTypeEnum.SEED_FOUND, seed=seed, **kwargs)
        return seed

    def process_cloud_asset(self, cloud_asset: CloudAsset, **kwargs) -> CloudAsset:
        """Prepare a cloud asset for submission.

        Args:
            cloud_asset (CloudAsset): The cloud asset to add.
            **kwargs: Additional data for event dispatching.
        """
        if not cloud_asset.uid.startswith(self.label_prefix):
            cloud_asset.uid = self.label_prefix + cloud_asset.uid

        self.logger.debug(f"Found Cloud Asset: {cloud_asset.to_dict()}")
        self.dispatch_event(
            EventTypeEnum.CLOUD_ASSET_FOUND, cloud_asset=cloud_asset, **kwargs
        )
        return cloud_asset

    def get_payload_source(self):
        """Generate the CloudEvent source value.

        Returns:
            str: The CloudEvent source value.
        """
        # see: https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md#source-1
        return f"https://github.com/censys/censys-cloud-connector/releases/tag/v{self.settings.cloud_connector_version}"

    def payload(self, payload_type: PayloadTypes, data: dict) -> CloudEvent:
        """Generate a CloudEvent payload.

        Args:
            type (PayloadTypes): The CloudEvent type.
            data (dict): Payload data.

        Returns:
            CloudEvent: The CloudEvent payload.
        """
        attributes = {
            "type": payload_type.value,
            "source": self.get_payload_source(),
        }
        return CloudEvent(attributes, data)

    def enqueue_payload(self, payload: CloudEvent) -> str:
        """Enqueue a CloudEvent payload.

        Args:
            payload (CloudEvent): The CloudEvent payload.

        Returns:
            str: Event ID.
        """
        result = self.aurora_api.enqueue_payload(payload)
        event_id = result.get("eventId", "ERROR")
        return event_id

    def submit_seed_payload(self, label: str, seeds: list[Seeds]) -> str:
        """Submit a seed payload.

        Args:
            label (str): Label for the seeds.
            seeds (list[Seeds]): List of seeds.

        Returns:
            str: Event ID.
        """
        data = {
            "label": label,
            "seeds": [seed.to_dict() for seed in seeds],
        }
        payload = self.payload(PayloadTypes.PAYLOAD_SEED, data)
        event_id = self.enqueue_payload(payload)
        self.logger.debug(f"seed payload {payload} event_id:{event_id}")
        return event_id

    def submit_cloud_asset_payload(self, uid: str, cloud_assets: list[CloudAsset]):
        """Submit a cloud asset payload.

        Args:
            uid (str): Unique identifier for the cloud asset.
            cloud_assets (list[CloudAsset]): List of cloud assets.
        """
        data = {
            "uid": uid,
            "assets": [asset.to_dict() for asset in cloud_assets],
        }
        payload = self.payload(PayloadTypes.PAYLOAD_CLOUD_ASSET, data)
        event_id = self.enqueue_payload(payload)
        self.logger.debug(f"cloud asset payload {payload} event_id:{event_id}")
        return event_id

    def clear(self):
        """Clear the seeds and cloud assets."""
        # TODO: not compatible with multiprocessing
        self.logger.debug(f"Clearing {len(self.seeds)} seeds")
        self.seeds.clear()

        self.logger.debug(f"Clearing {len(self.cloud_assets)} cloud assets")
        self.cloud_assets.clear()

    def submit(self, **kwargs):  # pragma: no cover
        """Submit the seeds and cloud assets to Censys ASM."""
        if self.settings.dry_run:
            self.logger.info("Dry run enabled. Skipping submission.")
        else:
            self.logger.info("Submitting seeds and cloud assets...")
            self.submit_seeds(**kwargs)
            self.submit_cloud_assets(**kwargs)

        self.clear()

    def submit_seeds_wrapper(self):  # pragma: no cover
        """Submit the seeds to Censys ASM."""
        if self.settings.dry_run:
            self.logger.info("Dry run enabled. Skipping submission.")
        else:
            self.logger.info("Submitting seeds...")
            self.submit_seeds()
        self.clear()

    def submit_cloud_assets_wrapper(self):  # pragma: no cover
        """Submit the cloud assets to Censys ASM."""
        if self.settings.dry_run:
            self.logger.info("Dry run enabled. Skipping submission.")
        else:
            self.logger.info("Submitting cloud assets...")
            self.submit_cloud_assets()
        self.clear()

    def scan_seeds(self, **kwargs):
        """Scan the seeds."""
        self.logger.info("Gathering seeds...")
        self.dispatch_event(EventTypeEnum.SCAN_STARTED)
        self.get_seeds(**kwargs)
        self.submit_seeds_wrapper()
        self.dispatch_event(EventTypeEnum.SCAN_FINISHED)

    def scan_cloud_assets(self, **kwargs):
        """Scan the cloud assets."""
        self.logger.info("Gathering cloud assets...")
        self.dispatch_event(EventTypeEnum.SCAN_STARTED)
        self.get_cloud_assets(**kwargs)
        self.submit_cloud_assets_wrapper()
        self.dispatch_event(EventTypeEnum.SCAN_FINISHED)

    # TODO: how to pass in cred,region? (each scanner will have diff things to pass in)
    def scan(self, **kwargs):
        """Scan the seeds and cloud assets."""
        self.logger.info("Gathering seeds and cloud assets...")
        self.dispatch_event(EventTypeEnum.SCAN_STARTED)
        self.get_seeds(**kwargs)
        self.get_cloud_assets(**kwargs)
        self.submit()
        self.dispatch_event(EventTypeEnum.SCAN_FINISHED)

    @abstractmethod
    def scan_all(self):
        """Scan all the seeds and cloud assets."""
        pass
