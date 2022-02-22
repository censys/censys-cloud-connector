from pathlib import Path
from unittest import TestCase

import pytest
from pytest_mock import MockerFixture

from censys.cloud_connectors.azure import AzureCloudConnector
from censys.cloud_connectors.common.settings import AzureSpecificSettings, Settings

TEST_CENSYS_API_KEY = "test-censys-api-key-xxxxxxxxxxxxxxxx"
TEST_AZURE_KEY = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
TEST_AZURE_PLATFORM_CONFIG = {
    "subscription_id": TEST_AZURE_KEY,
    "tenant_id": TEST_AZURE_KEY,
    "client_id": TEST_AZURE_KEY,
    "client_secret": TEST_AZURE_KEY,
}


class TestAzureCloudConnector(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture, shared_datadir: Path):
        self.mocker = mocker
        self.shared_datadir = shared_datadir

    def setUp(self) -> None:
        self.settings = Settings(
            censys_api_key=TEST_CENSYS_API_KEY, platforms_config_file=None
        )
        self.settings.platforms["azure"] = [
            AzureSpecificSettings(**TEST_AZURE_PLATFORM_CONFIG)
        ]
        self.connector = AzureCloudConnector(self.settings)

    def test_init(self):
        assert self.connector.platform == "azure"
        assert self.connector.label_prefix == "AZURE: "
        assert self.connector.settings == self.settings

    def test_scan_all(self):
        pass

    def test_format_label(self):
        test_asset = self.mocker.MagicMock()
        test_asset.location = "test-location"
        self.connector.subscription_id = TEST_AZURE_KEY
        assert (
            self.connector._format_label(test_asset)
            == f"AZURE: {TEST_AZURE_KEY}/test-location"
        )

    def test_get_seeds(self):
        mocks = self.mocker.patch.multiple(
            AzureCloudConnector,
            _get_ip_addresses=self.mocker.Mock(),
            _get_clusters=self.mocker.Mock(),
            _get_sql_servers=self.mocker.Mock(),
            _get_dns_records=self.mocker.Mock(),
        )
        self.connector.get_seeds()
        for mock in mocks.values():
            mock.assert_called_once()

    def test_get_ip_addresses(self):
        pass

    def test_get_clusters(self):
        pass

    def test_get_sql_servers(self):
        pass

    def test_get_dns_records(self):
        pass

    def test_get_cloud_assets(self):
        mocks = self.mocker.patch.multiple(
            AzureCloudConnector,
            _get_storage_containers=self.mocker.Mock(),
            # Include more when needed
        )
        self.connector.get_cloud_assets()
        for mock in mocks.values():
            mock.assert_called_once()
