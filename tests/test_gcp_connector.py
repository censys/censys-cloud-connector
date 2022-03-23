import json
from unittest import TestCase

import pytest
from parameterized import parameterized

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import Seed
from censys.cloud_connectors.common.settings import Settings
from censys.cloud_connectors.gcp.connector import GcpCloudConnector
from censys.cloud_connectors.gcp.enums import GcpSecurityCenterResourceTypes
from censys.cloud_connectors.gcp.settings import GcpSpecificSettings
from tests.base_case import BaseCase

failed_import = False
try:
    from google.cloud.securitycenter_v1.types import ListAssetsResponse
except ImportError:
    failed_import = True


@pytest.mark.skipif(failed_import, reason="Failed to import gcp dependencies")
class TestGcpConnector(BaseCase, TestCase):
    def setUp(self) -> None:
        super().setUp()
        with open(self.shared_datadir / "test_gcp_responses.json") as f:
            self.data = json.load(f)
        self.settings = Settings(censys_api_key=self.consts["censys_api_key"])
        test_creds = self.data["TEST_CREDS"]
        # Ensure the service account json file exists
        test_creds["service_account_json_file"] = str(
            self.shared_datadir / test_creds["service_account_json_file"]
        )
        self.settings.providers["gcp"] = [GcpSpecificSettings.from_dict(test_creds)]
        self.connector = GcpCloudConnector(self.settings)
        self.connector.organization_id = self.data["TEST_CREDS"]["organization_id"]
        self.connector.credentials = self.mocker.MagicMock()
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )

    def tearDown(self) -> None:
        # Reset the deaultdicts as they are immutable
        for seed_key in list(self.connector.seeds.keys()):
            del self.connector.seeds[seed_key]
        for cloud_asset_key in list(self.connector.cloud_assets.keys()):
            del self.connector.cloud_assets[cloud_asset_key]

    def mock_list_assets_result(
        self, data: dict
    ) -> ListAssetsResponse.ListAssetsResult:
        """Populate the ListAssetsResult object.

        Args:
            data (dict): The data to mock.

        Returns:
            ListAssetsResponse.ListAssetsResult: The test ListAssetsResult object.
        """
        return ListAssetsResponse.ListAssetsResult.from_json(json.dumps(data))

    def assert_seeds_with_values(self, seeds: list[Seed], values: list[str]):
        assert len(seeds) == len(values)
        for seed in seeds:
            assert seed.value in values

    def test_init(self):
        assert self.connector.provider == ProviderEnum.GCP
        assert self.connector.label_prefix == "GCP: "
        assert self.connector.settings == self.settings

    def test_scan(self):
        # Mock
        mock_sc_client = self.mocker.patch(
            "censys.cloud_connectors.gcp.connector.securitycenter_v1.SecurityCenterClient"
        )
        mock_scan = self.mocker.patch.object(
            self.connector.__class__.__bases__[0], "scan"
        )

        # Actual call
        self.connector.scan()

        # Assertions
        mock_sc_client.assert_called_once()
        mock_scan.assert_called_once()

    def test_scan_fail(self):
        # Mock
        mock_credentials = self.mocker.patch(
            "censys.cloud_connectors.gcp.connector.service_account.Credentials.from_service_account_file",
            side_effect=ValueError,
        )
        mock_error_logger = self.mocker.patch.object(self.connector.logger, "error")
        # Mock super().scan()
        mock_scan = self.mocker.patch.object(
            self.connector.__class__.__bases__[0], "scan"
        )

        # Actual call
        self.connector.scan()

        # Assertions
        mock_credentials.assert_called_once()
        mock_error_logger.assert_called_once()
        mock_scan.assert_called_once()

    def test_scan_all(self):
        # Test data
        test_creds = self.data["TEST_CREDS"].copy()
        second_test_creds = test_creds.copy()
        second_test_creds["organization_id"] = 9876543210
        provider_settings = [
            GcpSpecificSettings.from_dict(test_creds),
            GcpSpecificSettings.from_dict(second_test_creds),
        ]
        self.connector.settings.providers[self.connector.provider] = provider_settings

        # Mock
        self.mocker.patch(
            "censys.cloud_connectors.gcp.connector.service_account.Credentials.from_service_account_file",
            return_value=None,
        )
        mock_scan = self.mocker.patch.object(self.connector, "scan")

        # Actual call
        self.connector.scan_all()

        # Assertions
        assert mock_scan.call_count == len(provider_settings)

    @parameterized.expand(
        [
            ("TEST_COMPUTE_ADDRESS"),
            ("TEST_CONTAINER_CLUSTER"),
            ("TEST_CLOUD_SQL_INSTANCE"),
            ("TEST_DNS_ZONE"),
            ("TEST_STORAGE_BUCKET"),
        ]
    )
    def test_format_label(self, data_key: str):
        # Test data
        test_result = self.mock_list_assets_result(self.data[data_key])

        # Actual call
        label = self.connector.format_label(test_result)

        # Assertions
        assert label == f"GCP: {self.connector.organization_id}/censys-cc-test-project"

    @parameterized.expand([("test-filter")])
    def test_list_assets(self, filter: str):
        # Mock
        mock_sc_client = self.mocker.patch(
            "censys.cloud_connectors.gcp.connector.securitycenter_v1.SecurityCenterClient"
        )
        self.connector.security_center_client = mock_sc_client.return_value

        # Actual call
        self.connector.list_assets(filter)

        # Assertions
        self.connector.security_center_client.list_assets.assert_called_once_with(
            request={
                "parent": f"organizations/{self.connector.organization_id}",
                "filter": filter,
            }
        )

    def test_get_compute_addresses(self):
        # Test data
        test_list_assets_results = []
        test_seed_values = []
        for i in range(3):
            test_asset_result = self.data["TEST_COMPUTE_ADDRESS"].copy()
            ip_address = test_asset_result["asset"]["resourceProperties"]["address"]
            ip_address = ip_address[:-1] + str(i)
            test_asset_result["asset"]["resourceProperties"]["address"] = ip_address
            test_seed_values.append(ip_address)
            test_list_assets_results.append(
                self.mock_list_assets_result(test_asset_result)
            )
        test_label = self.connector.format_label(test_list_assets_results[0])

        # Mock
        mock_list = self.mocker.patch.object(
            self.connector, "list_assets", return_value=test_list_assets_results
        )

        # Actual call
        self.connector.get_compute_addresses()

        # Assertions
        mock_list.assert_called_once_with(
            filter=GcpSecurityCenterResourceTypes.COMPUTE_ADDRESS.filter()
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_container_clusters(self):
        # Test data
        test_list_assets_results = []
        test_seed_values = []
        for i in range(3):
            test_asset_result = self.data["TEST_CONTAINER_CLUSTER"].copy()
            private_cluster_config = json.loads(
                test_asset_result["asset"]["resourceProperties"]["privateClusterConfig"]
            )
            ip_address = private_cluster_config["publicEndpoint"]
            ip_address = ip_address[:-1] + str(i)
            private_cluster_config["publicEndpoint"] = ip_address
            test_asset_result["asset"]["resourceProperties"][
                "privateClusterConfig"
            ] = json.dumps(private_cluster_config)
            test_seed_values.append(ip_address)
            test_list_assets_results.append(
                self.mock_list_assets_result(test_asset_result)
            )
        test_label = self.connector.format_label(test_list_assets_results[0])

        # Mock
        mock_list = self.mocker.patch.object(
            self.connector, "list_assets", return_value=test_list_assets_results
        )

        # Actual call
        self.connector.get_container_clusters()

        # Assertions
        mock_list.assert_called_once_with(
            filter=GcpSecurityCenterResourceTypes.CONTAINER_CLUSTER.filter()
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_cloud_sql_instances(self):
        # Test data
        test_list_assets_results = []
        test_seed_values = []
        for i in range(1, 4):
            test_asset_result = self.data["TEST_CLOUD_SQL_INSTANCE"].copy()
            ip_addresses = []
            # populate ip_addresses.ipAddress with i number of ips
            for j in range(i):
                ip_address = f"195.111.{i}.{j}"
                ip_addresses.append({"ipAddress": ip_address})
                test_seed_values.append(ip_address)
            test_asset_result["asset"]["resourceProperties"][
                "ipAddresses"
            ] = json.dumps(ip_addresses)
            test_list_assets_results.append(
                self.mock_list_assets_result(test_asset_result)
            )
        test_label = self.connector.format_label(test_list_assets_results[0])

        # Mock
        mock_list = self.mocker.patch.object(
            self.connector, "list_assets", return_value=test_list_assets_results
        )

        # Actual call
        self.connector.get_cloud_sql_instances()

        # Assertions
        mock_list.assert_called_once_with(
            filter=GcpSecurityCenterResourceTypes.CLOUD_SQL_INSTANCE.filter()
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_dns_records(self):
        # Test data
        test_list_assets_results = []
        test_seed_values = []
        for i in range(3):
            test_asset_result = self.data["TEST_DNS_ZONE"].copy()
            domain = str(i) + "." + "censys.io"
            test_asset_result["asset"]["resourceProperties"]["dnsName"] = domain + "."
            test_seed_values.append(domain)
            test_list_assets_results.append(
                self.mock_list_assets_result(test_asset_result)
            )
        test_label = self.connector.format_label(test_list_assets_results[0])

        # Mock
        mock_list = self.mocker.patch.object(
            self.connector, "list_assets", return_value=test_list_assets_results
        )

        # Actual call
        self.connector.get_dns_records()

        # Assertions
        mock_list.assert_called_once_with(
            filter=GcpSecurityCenterResourceTypes.DNS_ZONE.filter()
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_seeds(self):
        # Mock
        mocks = self.mocker.patch.multiple(
            GcpCloudConnector,
            get_compute_addresses=self.mocker.Mock(),
            get_container_clusters=self.mocker.Mock(),
            get_cloud_sql_instances=self.mocker.Mock(),
            get_dns_records=self.mocker.Mock(),
        )

        # Actual call
        self.connector.get_seeds()

        # Assertions
        for mock in mocks.values():
            mock.assert_called_once()

    def test_get_storage_buckets(self):
        # Test data
        test_list_assets_results = []
        test_buckets = []
        for i in range(3):
            test_asset_result = self.data["TEST_STORAGE_BUCKET"].copy()
            bucket_name = "bucket" + str(i)
            test_asset_result["asset"]["resourceProperties"]["id"] = bucket_name
            test_buckets.append(bucket_name)
            test_list_assets_results.append(
                self.mock_list_assets_result(test_asset_result)
            )
        test_label = self.connector.format_label(test_list_assets_results[0])

        # Mock
        mock_list = self.mocker.patch.object(
            self.connector, "list_assets", return_value=test_list_assets_results
        )

        # Actual call
        self.connector.get_storage_buckets()

        # Assertions
        mock_list.assert_called_once_with(
            filter=GcpSecurityCenterResourceTypes.STORAGE_BUCKET.filter()
        )
        assert len(self.connector.cloud_assets[test_label]) == len(test_buckets)
        for bucket in self.connector.cloud_assets[test_label]:
            assert "https://storage.googleapis.com/" in bucket.value
            assert (
                bucket.value.removeprefix("https://storage.googleapis.com/")
                in test_buckets
            )
            assert "accountNumber" in bucket.scan_data

    def test_get_cloud_assets(self):
        # Mock
        mocks = self.mocker.patch.multiple(
            GcpCloudConnector,
            get_storage_buckets=self.mocker.Mock(),
            # Include more when needed
        )

        # Actual call
        self.connector.get_cloud_assets()

        # Assertions
        for mock in mocks.values():
            mock.assert_called_once()
