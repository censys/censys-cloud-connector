"""Base class for all cloud connectors."""
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, List

from censys.asm import Seeds
from censys.common.exceptions import CensysAsmException

from .cloud_asset import CloudAsset
from .logger import get_logger
from .seed import Seed
from .settings import Settings


class CloudConnector(ABC):
    """Base class for Cloud Connectors."""

    platform: str
    label_prefix: str = ""
    seeds: Dict[str, List[Seed]] = defaultdict(list)
    cloud_assets: Dict[str, List[CloudAsset]] = defaultdict(list)

    def __init__(self, platform: str, settings: Settings):
        """Initialize the Cloud Connector.

        Args:
            platform (str): The platform to scan.
            settings (Settings): The settings to use.
        """
        self.platform = platform
        self.label_prefix = platform.upper() + ": "
        self.settings = settings
        self.logger = get_logger(
            log_name=f"{platform}_cloud_connector", level=settings.logging_level
        )

        self.seeds_api = Seeds(settings.censys_api_key)
        self.add_cloud_asset_path = (
            f"{settings.censys_beta_url}/cloudConnector/addCloudAssets"
        )

    @abstractmethod
    def get_seeds(self) -> None:
        """Gather seeds."""
        pass

    @abstractmethod
    def get_cloud_assets(self) -> None:
        """Gather cloud assets."""
        pass

    def add_seed(self, seed: Seed):
        """Add a seed.

        Args:
            seed (Seed): The seed to add.
        """
        if not seed.label.startswith(self.label_prefix):
            seed.label = self.label_prefix + seed.label
        self.seeds[seed.label].append(seed)

    def add_cloud_asset(self, cloud_asset: CloudAsset):
        """Add a cloud asset.

        Args:
            cloud_asset (CloudAsset): The cloud asset to add.
        """
        if not cloud_asset.uid.startswith(self.label_prefix):
            cloud_asset.uid = self.label_prefix + cloud_asset.uid
        self.cloud_assets[cloud_asset.uid].append(cloud_asset)

    def submit_seeds(self):
        """Submit the seeds to the Censys ASM."""
        for label, seeds in self.seeds.items():
            try:
                self.seeds_api.replace_seeds_by_label(
                    label, [seed.to_dict() for seed in seeds]
                )
            except CensysAsmException as e:
                self.logger.error(f"Error submitting seeds for {label}: {e}")

    def submit_cloud_assets(self):
        """Submit the cloud assets to the Censys ASM."""
        for uid, cloud_assets in self.cloud_assets.items():
            try:
                data = {
                    "cloudConnectorUid": uid,
                    "cloudAssets": [asset.to_dict() for asset in cloud_assets],
                }
                self._add_cloud_assets(data)
            except CensysAsmException as e:
                self.logger.error(f"Error submitting cloud assets for {uid}: {e}")

    def _add_cloud_assets(self, data: dict) -> dict:
        """Add cloud assets to the Censys ASM.

        Args:
            data (dict): The data to add.

        Returns:
            dict: The response from the Censys ASM.
        """
        return self.seeds_api._post(self.add_cloud_asset_path, data=data)

    def submit(self):
        """Submit the seeds and cloud assets to the Censys ASM."""
        self.logger.info("Submitting seeds and assets...")
        # TODO: Re-enable
        # self.submit_seeds()
        # self.submit_cloud_assets()
        self.logger.info("Submitted seeds and assets.")

        for seed_subset in self.seeds.values():
            for seed in seed_subset:
                self.logger.debug(f"Seed: {seed}")
        for cloud_asset_subset in self.cloud_assets.values():
            for cloud_asset in cloud_asset_subset:
                self.logger.debug(f"Cloud Asset: {cloud_asset}")

    def scan(self):
        """Scan the seeds and cloud assets."""
        self.logger.info("Gathering seeds and assets...")
        self.get_seeds()
        self.get_cloud_assets()
        self.submit()

    @abstractmethod
    def scan_all(self):
        """Scan all the seeds and cloud assets."""
        pass
