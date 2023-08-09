import json
from unittest import TestCase
from unittest.mock import MagicMock

import pytest
from google.cloud.asset_v1.services.asset_service.pagers import ListAssetsPager

# from censys.cloud_connectors.common.seed import Seed
from google.cloud.asset_v1.types import Asset, ContentType, ResourceSearchResult
from parameterized import parameterized

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import Settings
from censys.cloud_connectors.gcp_connector.connector import GcpCloudConnector
from censys.cloud_connectors.gcp_connector.enums import GcpCloudAssetTypes
from censys.cloud_connectors.gcp_connector.settings import GcpSpecificSettings
from tests.base_connector_case import BaseConnectorCase

failed_import = False
try:
    from google.cloud.asset_v1.types import ListAssetsResponse
except ImportError:
    failed_import = True


@pytest.mark.skipif(failed_import, reason="Failed to import gcp dependencies")
class TestGcpConnector(BaseConnectorCase, TestCase):
    connector: GcpCloudConnector
    connector_cls = GcpCloudConnector

    def setUp(self) -> None:
        super().setUp()
        with open(self.shared_datadir / "test_gcp_responses.json") as f:
            self.data = json.load(f)
        self.settings = Settings(
            **self.default_settings,
            secrets_dir=str(self.shared_datadir),
        )
        test_creds = self.data["TEST_CREDS"]
        # Ensure the service account json file exists
        test_creds["service_account_json_file"] = test_creds[
            "service_account_json_file"
        ]
        test_gcp_settings = GcpSpecificSettings.from_dict(test_creds)
        self.settings.providers[ProviderEnum.GCP] = {
            test_gcp_settings.get_provider_key(): test_gcp_settings
        }
        self.connector = GcpCloudConnector(self.settings)
        self.connector.organization_id = self.data["TEST_CREDS"]["organization_id"]
        self.connector.credentials = self.mocker.MagicMock()
        self.connector.provider_settings = test_gcp_settings

    # def tearDown(self) -> None:
    #     # Reset the deaultdicts as they are immutable
    #     for seed_key in list(self.connector.seeds.keys()):
    #         del self.connector.seeds[seed_key]
    #     for cloud_asset_key in list(self.connector.cloud_assets.keys()):
    #         del self.connector.cloud_assets[cloud_asset_key]

    def mock_asset(self, data: dict) -> Asset:
        """Populate the Asset object.

        Args:
            data (dict): The data to mock.

        Returns:
            Asset: The test Asset object.
        """
        return Asset.from_json(json.dumps(data))

    def mock_asset_bucket(self, data: dict) -> ResourceSearchResult:
        """Populate the Asset object.

        Args:
            data (dict): The data to mock.

        Returns:
            ResourceSearchResult: The test ResourceSearchResult object.
        """
        return ResourceSearchResult.from_json(json.dumps(data))

    def mock_healthcheck(self) -> MagicMock:
        """Mock the healthcheck.

        Returns:
            MagicMock: mocked healthcheck
        """
        return self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.Healthcheck"
        )

    def test_init(self):
        assert self.connector.provider == ProviderEnum.GCP
        assert self.connector.label_prefix == "GCP: "
        assert self.connector.settings == self.settings

    def test_scan(self):
        # Mock
        mock_credentials = self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.service_account.Credentials.from_service_account_file",
        )
        mock_cai_client = self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.asset_v1.AssetServiceClient"
        )
        mock_scan = self.mocker.patch.object(
            self.connector.__class__.__bases__[0], "scan"
        )
        mock_healthcheck = self.mock_healthcheck()

        # Actual call
        self.connector.scan()

        # Assertions
        mock_credentials.assert_called_once()
        mock_cai_client.assert_called_once()
        mock_scan.assert_called_once()
        self.assert_healthcheck_called(mock_healthcheck)

    def test_credentials_fail(self):
        # Mock
        mock_credentials = self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.service_account.Credentials.from_service_account_file",
            side_effect=ValueError,
        )
        mock_error_logger = self.mocker.patch.object(self.connector.logger, "error")
        mock_scan = self.mocker.patch.object(
            self.connector.__class__.__bases__[0], "scan"
        )
        mock_healthcheck = self.mock_healthcheck()

        # Actual call
        self.connector.scan()

        # Assertions
        mock_credentials.assert_called_once()
        mock_error_logger.assert_called()
        mock_scan.assert_not_called()
        self.assert_healthcheck_called(mock_healthcheck)

    def test_scan_all(self):
        # Test data
        test_creds = self.data["TEST_CREDS"]
        second_test_creds = test_creds
        second_test_creds["organization_id"] = 9876543210
        test_gcp_settings = [
            GcpSpecificSettings.from_dict(test_creds),
            GcpSpecificSettings.from_dict(second_test_creds),
        ]
        provider_settings: dict[tuple, GcpSpecificSettings] = {
            p.get_provider_key(): p for p in test_gcp_settings
        }
        self.connector.settings.providers[self.connector.provider] = provider_settings

        # Mock
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
        ]
    )
    def test_format_label(self, data_key: str):
        # Test data
        test_asset = self.mock_asset(self.data[data_key])
        # Actual call
        label = self.connector.format_label(test_asset.name)

        # Assertions
        assert label == f"GCP: {self.connector.organization_id}/censys-cc-test-project"

    @parameterized.expand(
        [
            ("TEST_STORAGE_BUCKET"),
        ]
    )
    def test_parse_project_name_buckets(self, data_key: str):
        # Test data
        test_asset = self.mock_asset_bucket(self.data[data_key])
        # Actual call
        project_name = self.connector.parse_project_name_buckets(
            test_asset.parent_full_resource_name
        )["project"]

        # Assertions
        assert project_name == "censys-cc-test-project"

    @parameterized.expand(
        [
            ("TEST_COMPUTE_ADDRESS"),
            ("TEST_CONTAINER_CLUSTER"),
            ("TEST_CLOUD_SQL_INSTANCE"),
            ("TEST_DNS_ZONE"),
        ]
    )
    def test_parse_project_name_seeds(self, data_key: str):
        # Test data
        test_asset = self.mock_asset(self.data[data_key])
        # Actual call
        project_name = self.connector.parse_project_name_seeds(test_asset.name)[
            "project"
        ]

        # Assertions
        assert project_name == "censys-cc-test-project"

    @parameterized.expand([("test-filter")])
    def test_list_assets(self, filter: str):
        # Mock
        mock_cai_client = self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.asset_v1.AssetServiceClient"
        )
        self.connector.cloud_asset_client = mock_cai_client.return_value

        # Actual call
        self.connector.list_assets(filter)

        # Assertions
        mock_cai_client.return_value.list_assets.assert_called_once_with(
            request={
                "parent": f"organizations/{self.connector.organization_id}",
                "content_type": ContentType.RESOURCE,
                "asset_types": [filter],
            }
        )

    def test_get_compute_instances(self):
        self.skipTest("Test data is not available yet")
        # # Test data
        # test_assets = []
        # test_seed_values = []
        # for i in range(3):
        #     test_asset = self.data["TEST_COMPUTE_INSTANCE"]
        #     network_interfaces = test_asset["resource"]["data"]["networkInterfaces"]
        #     access_configs = network_interfaces[0]["accessConfigs"]
        #     # TODO: Implement tests
        #     ip_address = test_asset["asset"]["resourceProperties"]["address"]
        #     ip_address = ip_address[:-1] + str(i)
        #     test_asset["resource"]["data"]["address"] = ip_address
        #     test_seed_values.append(ip_address)
        #     test_assets.append(self.mock_asset(test_asset))

        #     private_cluster_config = json.loads(
        #         test_asset["resource"]["data"]["privateClusterConfig"]
        #     )
        #     ip_address = private_cluster_config["publicEndpoint"]
        #     ip_address = ip_address[:-1] + str(i)
        #     private_cluster_config["publicEndpoint"] = ip_address
        #     test_asset["resource"]["data"]["privateClusterConfig"] = json.dumps(
        #         private_cluster_config
        #     )
        # test_label = self.connector.format_label_cai(test_assets[0])

        # # Mock
        # mock_list = self.mocker.patch.object(
        #     self.connector, "list_assets_cai", return_value=test_assets
        # )

        # # Actual call
        # self.connector.get_compute_instances()

        # # Assertions
        # mock_list.assert_called_once_with(
        #     filter=GcpCloudAssetTypes.COMPUTE_INSTANCE.filter()
        # )
        # self.assert_seeds_with_values(
        #     self.connector.seeds[test_label], test_seed_values
        # )

    def test_get_compute_addresses(self):
        # Test data
        test_assets = []
        test_seed_values = []
        for i in range(3):
            test_asset = self.data["TEST_COMPUTE_ADDRESS"]
            ip_address = test_asset["resource"]["data"]["address"]
            ip_address = ip_address[:-1] + str(i)
            test_asset["resource"]["data"]["address"] = ip_address
            test_seed_values.append(ip_address)
            test_assets.append(self.mock_asset(test_asset))
        test_label = self.connector.format_label(test_asset["name"])

        # Mock
        mock_pager = ListAssetsPager(
            response=ListAssetsResponse(assets=test_assets), request={}, method=None
        )
        mock_list = self.mocker.patch.object(
            self.connector, "list_assets", return_value=mock_pager
        )

        # Actual call
        self.connector.get_compute_addresses()

        # Assertions
        mock_list.assert_called_once_with(filter=GcpCloudAssetTypes.COMPUTE_ADDRESS)
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_container_clusters(self):
        # Test data
        test_assets = []
        test_seed_values = []
        for i in range(3):
            test_asset = self.data["TEST_CONTAINER_CLUSTER"]
            private_cluster_config = test_asset["resource"]["data"][
                "privateClusterConfig"
            ]
            ip_address = private_cluster_config["publicEndpoint"]
            ip_address = ip_address[:-1] + str(i)
            private_cluster_config["publicEndpoint"] = ip_address
            test_asset["resource"]["data"][
                "privateClusterConfig"
            ] = private_cluster_config
            test_seed_values.append(ip_address)
            test_assets.append(self.mock_asset(test_asset))
        test_label = self.connector.format_label(test_asset["name"])

        # Mock
        mock_pager = ListAssetsPager(
            response=ListAssetsResponse(assets=test_assets), request={}, method=None
        )
        mock_list = self.mocker.patch.object(
            self.connector, "list_assets", return_value=mock_pager
        )

        # Actual call
        self.connector.get_container_clusters()

        # Assertions
        mock_list.assert_called_once_with(filter=GcpCloudAssetTypes.CONTAINER_CLUSTER)
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_cloud_sql_instances(self):
        # Test data
        test_assets = []
        test_seed_values = []
        for i in range(1, 4):
            test_asset = self.data["TEST_CLOUD_SQL_INSTANCE"]
            ip_addresses = []
            # populate ip_addresses.ipAddress with i number of ips
            for j in range(i):
                ip_address = f"195.111.{i}.{j}"
                ip_addresses.append({"ipAddress": ip_address})
                test_seed_values.append(ip_address)
            test_asset["resource"]["data"]["ipAddresses"] = ip_addresses
            test_assets.append(self.mock_asset(test_asset))
        test_label = self.connector.format_label(test_asset["name"])

        # Mock
        mock_pager = ListAssetsPager(
            response=ListAssetsResponse(assets=test_assets), request={}, method=None
        )
        mock_list = self.mocker.patch.object(
            self.connector, "list_assets", return_value=mock_pager
        )

        # Actual call
        self.connector.get_cloud_sql_instances()

        # Assertions
        mock_list.assert_called_once_with(filter=GcpCloudAssetTypes.CLOUD_SQL_INSTANCE)
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_dns_records(self):
        # Test data
        test_assets = []
        test_seed_values = []
        for i in range(3):
            test_asset = self.data["TEST_DNS_ZONE"]
            domain = str(i) + "." + "censys.io"
            test_asset["resource"]["data"]["dnsName"] = domain + "."
            test_seed_values.append(domain)
            test_assets.append(self.mock_asset(test_asset))
        test_label = self.connector.format_label(test_asset["name"])

        # Mock
        mock_pager = ListAssetsPager(
            response=ListAssetsResponse(assets=test_assets), request={}, method=None
        )
        mock_list = self.mocker.patch.object(
            self.connector, "list_assets", return_value=mock_pager
        )

        # Actual call
        self.connector.get_dns_records()

        # Assertions
        mock_list.assert_called_once_with(filter=GcpCloudAssetTypes.DNS_ZONE)
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_seeds(self):
        # Test data
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )

        seed_scanners = {
            GcpCloudAssetTypes.COMPUTE_INSTANCE: self.mocker.Mock(),
            GcpCloudAssetTypes.COMPUTE_ADDRESS: self.mocker.Mock(),
            GcpCloudAssetTypes.CONTAINER_CLUSTER: self.mocker.Mock(),
            GcpCloudAssetTypes.CLOUD_SQL_INSTANCE: self.mocker.Mock(),
            GcpCloudAssetTypes.DNS_ZONE: self.mocker.Mock(),
        }

        # Mock
        self.mocker.patch.object(
            self.connector,
            "seed_scanners",
            new_callable=self.mocker.PropertyMock(return_value=seed_scanners),
        )

        # Actual call
        self.connector.get_seeds()

        # Assertions
        for mock in self.connector.seed_scanners.values():
            mock.assert_called_once()

    def test_get_seeds_ignore(self):
        # Test data
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS_IGNORE"]
        )

        seed_scanners = {
            GcpCloudAssetTypes.COMPUTE_INSTANCE: self.mocker.Mock(),
            GcpCloudAssetTypes.COMPUTE_ADDRESS: self.mocker.Mock(),
            GcpCloudAssetTypes.CONTAINER_CLUSTER: self.mocker.Mock(),
            GcpCloudAssetTypes.CLOUD_SQL_INSTANCE: self.mocker.Mock(),
            GcpCloudAssetTypes.DNS_ZONE: self.mocker.Mock(),
        }

        # Mock
        self.mocker.patch.object(
            self.connector,
            "seed_scanners",
            new_callable=self.mocker.PropertyMock(return_value=seed_scanners),
        )

        # Actual call
        self.connector.get_seeds()

        # Assertions
        for resource_type, mock in self.connector.seed_scanners.items():
            if resource_type in self.connector.provider_settings.ignore:
                mock.assert_not_called()
            else:
                mock.assert_called_once()

    def test_get_storage_buckets(self):
        # Test data
        test_assets = []
        test_buckets = []
        for i in range(3):
            test_asset = self.data["TEST_STORAGE_BUCKET"]
            bucket_name = "bucket" + str(i)
            test_asset["versionedResources"][0]["resource"]["id"] = bucket_name
            test_buckets.append(bucket_name)
            test_assets.append(self.mock_asset_bucket(test_asset))
            test_uid = self.connector.format_uid(
                self.connector.parse_project_name_buckets(
                    test_asset["parentFullResourceName"]
                )["project"]
            )

        # Mock
        mock_search = self.mocker.patch.object(
            self.connector, "search_all_resources", return_value=test_assets
        )

        # Actual call
        self.connector.get_storage_buckets()

        # Assertions
        mock_search.assert_called_once_with(filter=GcpCloudAssetTypes.STORAGE_BUCKET)
        assert len(self.connector.cloud_assets[test_uid]) == len(test_buckets)
        for bucket in self.connector.cloud_assets[test_uid]:
            assert "https://storage.googleapis.com/" in bucket.value
            assert (
                bucket.value.removeprefix("https://storage.googleapis.com/")
                in test_buckets
            )
            assert "accountNumber" in bucket.scan_data

    def test_get_cloud_assets(self):
        # Test data
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )
        cloud_asset_scanners = {
            GcpCloudAssetTypes.STORAGE_BUCKET: self.mocker.Mock(),
        }

        # Mock
        self.mocker.patch.object(
            self.connector,
            "cloud_asset_scanners",
            new_callable=self.mocker.PropertyMock(return_value=cloud_asset_scanners),
        )

        # Actual call
        self.connector.get_cloud_assets()

        # Assertions
        for mock in cloud_asset_scanners.values():
            mock.assert_called_once()

    def test_get_cloud_assets_ignore(self):
        # Test data
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS_IGNORE"]
        )

        # Mock
        mock_storage_bucket = self.mocker.patch.object(
            self.connector,
            "get_storage_buckets",
        )

        # Actual call
        self.connector.get_cloud_assets()

        # Assertions
        mock_storage_bucket.assert_not_called()
