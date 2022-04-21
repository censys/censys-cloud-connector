"""Base class for all cloud connectors."""
from abc import ABC, abstractmethod
from collections import defaultdict

from requests.exceptions import JSONDecodeError

from censys.asm import Seeds
from censys.common.exceptions import CensysAsmException

from .cloud_asset import CloudAsset
from .enums import ProviderEnum
from .logger import get_logger
from .seed import Seed
from .settings import Settings


class CloudConnector(ABC):
    """Base class for Cloud Connectors."""

    provider: ProviderEnum
    label_prefix: str
    seeds: dict[str, list[Seed]]
    cloud_assets: dict[str, list[CloudAsset]]

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

        self.seeds_api = Seeds(settings.censys_api_key)
        self._add_cloud_asset_path = (
            f"{settings.censys_beta_url}/cloudConnector/addCloudAssets"
        )

        self.seeds = defaultdict(list)
        self.cloud_assets = defaultdict(list)

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
        self.logger.debug(f"Found Seed: {seed.to_dict()}")

    def add_cloud_asset(self, cloud_asset: CloudAsset):
        """Add a cloud asset.

        Args:
            cloud_asset (CloudAsset): The cloud asset to add.
        """
        if not cloud_asset.uid.startswith(self.label_prefix):
            cloud_asset.uid = self.label_prefix + cloud_asset.uid
        self.cloud_assets[cloud_asset.uid].append(cloud_asset)
        self.logger.debug(f"Found Cloud Asset: {cloud_asset.to_dict()}")

    def submit_seeds(self):
        """Submit the seeds to the Censys ASM."""
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

    def submit_cloud_assets(self):
        """Submit the cloud assets to the Censys ASM."""
        submitted_assets = 0
        for uid, cloud_assets in self.cloud_assets.items():
            try:
                data = {
                    "cloudConnectorUid": uid,
                    "cloudAssets": [asset.to_dict() for asset in cloud_assets],
                }
                self._add_cloud_assets(data)
                submitted_assets += len(cloud_assets)
            except (CensysAsmException, JSONDecodeError) as e:
                self.logger.error(f"Error submitting cloud assets for {uid}: {e}")
        self.logger.info(f"Submitted {submitted_assets} cloud assets.")

    def _add_cloud_assets(self, data: dict) -> dict:
        """Add cloud assets to the Censys ASM.

        Args:
            data (dict): The data to add.

        Returns:
            dict: The response from the Censys ASM.

        Raises:
            CensysAsmException: If the response is not valid.
        """
        res = self.seeds_api._session.post(self._add_cloud_asset_path, json=data)
        json_data = res.json()
        if error_message := json_data.get("error"):
            raise CensysAsmException(
                res.status_code,
                error_message,
                res.text,
                error_code=json_data.get("errorCode"),
            )
        return json_data

    def submit(self):  # pragma: no cover
        """Submit the seeds and cloud assets to the Censys ASM."""
        if self.settings.dry_run:
            self.logger.info("Dry run enabled. Skipping submission.")
        else:
            self.logger.info("Submitting seeds and assets...")
            self.submit_seeds()
            self.submit_cloud_assets()

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
