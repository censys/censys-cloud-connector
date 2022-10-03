from unittest.mock import MagicMock

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
            **self.default_settings,
            providers_config_file=str(self.shared_datadir / "test_empty_providers.yml"),
        )

    def tearDown(self) -> None:
        super().tearDown()
        # Reset the deaultdicts (seeds and cloud_assets) as they are immutable
        for seed_key in list(self.connector.seeds.keys()):
            del self.connector.seeds[seed_key]
        for cloud_asset_key in list(self.connector.cloud_assets.keys()):
            del self.connector.cloud_assets[cloud_asset_key]

    def assert_seeds_with_values(self, seeds: set[Seed], values: list[str]):
        """Assert that the seeds have the expected values.

        Each Seed type has a value property which is compared against the values array in order.

        Args:
            seeds (set[Seed]): The seeds.
            values (list[str]): The expected values.

        Raises:
            AssertionError: If the seeds do not have the expected values.
        """
        # seeds_len = len(seeds)
        # values_len = len(values)
        # assert seeds_len == values_len, f"Expected {values_len} seeds, got {seeds_len}"
        seed_values = [seed.value for seed in seeds]
        seed_values.sort()
        values.sort()
        assert values == seed_values, f"Expected {values}, got {seed_values}"
        # for seed in seeds:
        #     assert (
        #         seed.value in values
        #     ), f"The seed {seed.value} is not in the expected values {values}"

    def mock_healthcheck(self) -> MagicMock:
        """Mock the healthcheck.

        Returns:
            MagicMock: mocked healthcheck
        """
        return self.mocker.patch(
            "censys.cloud_connectors.common.healthcheck.Healthcheck"
        )

    def assert_healthcheck_called(self, healthcheck: MagicMock, count: int = 1):
        """Assert that the healthcheck was called.

        Args:
            healthcheck (MagicMock): The mocked healthcheck.
            count (int): The number of times the healthcheck was called. Defaults to 1.
        """
        assert (
            healthcheck.call_count == count
        ), f"Expected {count} calls, got {healthcheck.call_count}"
        assert (
            healthcheck.return_value.__enter__.call_count == count
        ), f"Expected {count} calls, got {healthcheck.return_value.__enter__.call_count}"
        assert (
            healthcheck.return_value.__exit__.call_count == count
        ), f"Expected {count} calls, got {healthcheck.return_value.__exit__.call_count}"

    def test_init(self) -> None:
        # Test data
        add_cloud_asset_path = (
            "https://app.censys.io/api/beta/cloudConnector/addCloudAssets"
        )

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
        assert (
            self.connector.seeds_api._api_key == self.default_settings["censys_api_key"]
        )
        assert (
            self.connector._add_cloud_asset_path == add_cloud_asset_path
        ), f"Expected {add_cloud_asset_path}, got {self.connector._add_cloud_asset_path}"

        # Assert that the connector has no seeds and cloud_assets
        assert list(self.connector.seeds.keys()) == []
        assert list(self.connector.cloud_assets.keys()) == []
