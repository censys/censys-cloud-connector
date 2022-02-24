import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock

import pytest
from parameterized import parameterized
from pytest_mock import MockerFixture

from censys.cloud_connectors.common.settings import Settings

failed_import = False
try:
    from azure.core.exceptions import ClientAuthenticationError

    from censys.cloud_connectors.azure import AzureCloudConnector
    from censys.cloud_connectors.azure.settings import AzureSpecificSettings
except ImportError:
    failed_import = True

# Azure keys must be 36 characters long
TEST_AZURE_KEY = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"


@pytest.mark.skipif(failed_import, reason="Azure SDK not installed")
class TestAzureCloudConnector(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture, shared_datadir: Path):
        self.mocker = mocker
        self.shared_datadir = shared_datadir

    def setUp(self) -> None:
        with open(self.shared_datadir / "test_consts.json") as f:
            self.consts = json.load(f)
        with open(self.shared_datadir / "test_azure_responses.json") as f:
            self.data = json.load(f)
        self.settings = Settings(censys_api_key=self.consts["censys_api_key"])
        self.settings.platforms["azure"] = [
            AzureSpecificSettings.from_dict(
                {
                    "subscription_id": TEST_AZURE_KEY,
                    "tenant_id": TEST_AZURE_KEY,
                    "client_id": TEST_AZURE_KEY,
                    "client_secret": TEST_AZURE_KEY,
                }
            )
        ]
        self.connector = AzureCloudConnector(self.settings)
        # Set subscription_id as its required for certain calls
        self.connector.subscription_id = TEST_AZURE_KEY
        self.connector.credentials = self.mocker.MagicMock()

    def mock_asset(self, data: dict) -> MagicMock:
        asset = self.mocker.MagicMock()
        for key, value in data.items():
            asset.__setattr__(key, value)
        asset.as_dict.return_value = data
        return asset

    def test_init(self):
        assert self.connector.platform == "azure"
        assert self.connector.label_prefix == "AZURE: "
        assert self.connector.settings == self.settings

    @parameterized.expand(
        [
            (
                ClientAuthenticationError,
                f"Authentication error for azure subscription {TEST_AZURE_KEY}",
            )
        ]
    )
    def test_scan_fail(self, exception, expected_message):
        # Mock super().scan()
        mock_scan = self.mocker.patch.object(
            self.connector.__class__.__bases__[0],
            "scan",
            side_effect=exception,
        )
        mock_error_logger = self.mocker.patch.object(self.connector.logger, "error")
        self.connector.scan()
        mock_scan.assert_called_once()
        mock_error_logger.assert_called_once()
        assert mock_error_logger.call_args[0][0].startswith(expected_message)

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
        test_list_all_response = []
        test_ips = []
        for i in range(3):
            test_ip_response = self.data["TEST_IP_ADDRESS"].copy()
            ip_address = test_ip_response["ip_address"][:-1] + str(i)
            test_ip_response["ip_address"] = ip_address
            test_ips.append(ip_address)
            test_list_all_response.append(self.mock_asset(test_ip_response))
        test_label = self.connector._format_label(test_list_all_response[0])
        mock_network_client = self.mocker.patch(
            "censys.cloud_connectors.azure.connector.NetworkManagementClient",
        )
        mock_public_ips = self.mocker.patch.object(
            mock_network_client.return_value, "public_ip_addresses"
        )
        mock_public_ips.list_all.return_value = test_list_all_response

        self.connector._get_ip_addresses()

        mock_network_client.assert_called_with(
            self.connector.credentials, TEST_AZURE_KEY
        )
        mock_public_ips.list_all.assert_called_once()
        added_seeds = self.connector.seeds[test_label]
        assert len(added_seeds) == len(test_list_all_response)
        added_ips = [seed.value for seed in added_seeds]
        assert added_ips == test_ips

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
