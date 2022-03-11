from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import Seed
from censys.cloud_connectors.common.settings import Settings

from .base_case import BaseCase


class BaseConnectorCase(BaseCase):
    settings: Settings
    connector_cls: type[CloudConnector]
    connector: CloudConnector

    def setUpConnector(self, connector_cls: type[CloudConnector]):
        self.connector_cls = connector_cls
        self.connector = connector_cls(self.settings)

    def setUp(self) -> None:
        super().setUp()
        self.settings = Settings(
            censys_api_key=self.consts["censys_api_key"],
            providers_config_file=str(self.shared_datadir / "test_empty_providers.yml"),
        )

    def tearDown(self) -> None:
        super().tearDown()
        # Reset the deaultdicts (seeds and cloud_assets) as they are immutable
        for seed_key in list(self.connector.seeds.keys()):
            del self.connector.seeds[seed_key]
        for cloud_asset_key in list(self.connector.cloud_assets.keys()):
            del self.connector.cloud_assets[cloud_asset_key]

    def assert_seeds_with_values(self, seeds: list[Seed], values: list[str]):
        """Assert that the seeds have the expected values.

        Args:
            seeds (list[Seed]): The seeds.
            values (list[str]): The expected values.

        Raises:
            AssertionError: If the seeds do not have the expected values.
        """
        assert len(seeds) == len(
            values
        ), "The number of seeds and values must be the same."
        for seed in seeds:
            assert (
                seed.value in values
            ), f"The seed {seed.value} is not in the expected values."

    def test_init(self) -> None:
        # Assert that the connector is initialized correctly
        assert issubclass(self.connector_cls, CloudConnector)
        assert isinstance(self.connector, self.connector_cls)

        # Assert that the connector has the correct attributes
        assert isinstance(self.connector.provider, ProviderEnum)
        assert self.connector.provider == self.connector_cls.provider
        assert self.connector.label_prefix == self.connector_cls.provider.label() + ": "
        assert self.connector.settings == self.settings
        assert self.connector.logger is not None

        # Assert that the Seeds API client is initialized correctly
        assert self.connector.seeds_api is not None
        assert self.connector.seeds_api._api_key == self.consts["censys_api_key"]
        assert (
            self.connector._add_cloud_asset_path
            == f"{self.settings.censys_beta_url}/cloudConnector/addCloudAssets"
        )

        # Assert that the connector has no seeds and cloud_assets
        assert list(self.connector.seeds.keys()) == []
        assert list(self.connector.cloud_assets.keys()) == []
