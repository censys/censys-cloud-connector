import json
from unittest import TestCase
from unittest.mock import MagicMock

import pytest
from parameterized import parameterized

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import Settings
from censys.cloud_connectors.gcp_connector.connector import GcpCloudConnector
from censys.cloud_connectors.gcp_connector.enums import GcpCloudAssetInventoryTypes
from censys.cloud_connectors.gcp_connector.settings import GcpSpecificSettings
from tests.base_connector_case import BaseConnectorCase

failed_import = False
try:
    from google.cloud.asset_v1.services.asset_service.pagers import (
        SearchAllResourcesPager,
    )
    from google.cloud.asset_v1.types import (
        ResourceSearchResult,
        SearchAllResourcesResponse,
    )
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
        self.connector.all_projects = {}
        self.connector.found_projects = set()

    # def tearDown(self) -> None:
    #     # Reset the deaultdicts as they are immutable
    #     for seed_key in list(self.connector.seeds.keys()):
    #         del self.connector.seeds[seed_key]
    #     for cloud_asset_key in list(self.connector.cloud_assets.keys()):
    #         del self.connector.cloud_assets[cloud_asset_key]

    def mock_asset(self, data: dict) -> ResourceSearchResult:
        """Populate the ResourceSearchResult object.

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

    @parameterized.expand([("test-filter")])
    def test_search_all_resources(self, filter: str):
        # Mock
        mock_cloud_asset_client = self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.AssetServiceClient"
        )
        self.connector.cloud_asset_client = mock_cloud_asset_client.return_value

        # Actual call
        self.connector.search_all_resources(filter)

        # Assertions
        mock_cloud_asset_client.return_value.search_all_resources.assert_called_once_with(
            request={
                "scope": f"organizations/{self.connector.organization_id}",
                "asset_types": [filter],
                "read_mask": "*",
            }
        )

    def test_scan(self):
        # Mock
        mock_credentials = self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.service_account.Credentials.from_service_account_file",
        )
        mock_cai_client = self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.AssetServiceClient"
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
        second_test_creds["organization_id"] = 987654321012
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
            ("my-cc-test-project"),
        ]
    )
    def test_format_label(self, test_project_id: str):
        # Actual call
        label = self.connector.format_label(test_project_id)

        # Assertions
        assert label == f"GCP: {self.connector.organization_id}/{test_project_id}"

    def test_list_projects(self):
        # Test data
        test_projects = []
        test_project_map: dict[str, dict] = {}
        for i in range(3):
            test_project = self.data["TEST_PROJECT"]
            project_id = "test_project" + str(i)
            project_number = "111111111111" + str(i)
            name = "Test Project" + str(i)
            test_project["versioned_resources"][0]["resource"]["projectId"] = project_id
            test_project["versioned_resources"][0]["resource"][
                "projectNumber"
            ] = project_number
            test_project["versioned_resources"][0]["resource"]["name"] = name
            test_projects.append(self.mock_asset(test_project))
            test_project_map[project_number] = {"project_id": project_id, "name": name}

        # Mock
        mock_pager = SearchAllResourcesPager(
            response=SearchAllResourcesResponse(results=test_projects),
            request={},
            method=None,
        )
        mock_search_all_resources = self.mocker.patch.object(
            self.connector, "search_all_resources", return_value=mock_pager
        )

        # Actual call
        all_projects = self.connector.list_projects()

        # Assertions
        mock_search_all_resources.assert_called_once_with(
            filter=GcpCloudAssetInventoryTypes.PROJECT
        )

        assert len(all_projects) == len(test_project_map)
        for project_number, project in all_projects.items():
            assert (
                project["project_id"] == test_project_map[project_number]["project_id"]
            )
            assert project["name"] == test_project_map[project_number]["name"]

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
        test_all_projects = {
            "123456789123": {
                "project_id": "censys-cc-test-project",
                "name": "Censys CC Test Project",
            }
        }
        for i in range(3):
            test_asset = self.data["TEST_COMPUTE_ADDRESS"]
            ip_address = test_asset["versioned_resources"][0]["resource"]["address"]
            ip_address = ip_address[:-1] + str(i)
            test_asset["versioned_resources"][0]["resource"]["address"] = ip_address
            test_seed_values.append(ip_address)
            test_assets.append(self.mock_asset(test_asset))
        test_label = self.connector.format_label("censys-cc-test-project")

        # Mock
        mock_pager = SearchAllResourcesPager(
            response=SearchAllResourcesResponse(results=test_assets),
            request={},
            method=None,
        )
        mock_search_all_resources = self.mocker.patch.object(
            self.connector, "search_all_resources", return_value=mock_pager
        )
        self.mocker.patch.object(self.connector, "all_projects", test_all_projects)

        # Actual call
        self.connector.get_compute_addresses()

        # Assertions
        mock_search_all_resources.assert_called_once_with(
            filter=GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_container_clusters(self):
        # Test data
        test_assets = []
        test_seed_values = []
        test_all_projects = {
            "123456789123": {
                "project_id": "censys-cc-test-project",
                "name": "Censys CC Test Project",
            }
        }
        for i in range(3):
            test_asset = self.data["TEST_CONTAINER_CLUSTER"]
            private_cluster_config = test_asset["versioned_resources"][0]["resource"][
                "privateClusterConfig"
            ]
            ip_address = private_cluster_config["publicEndpoint"]
            ip_address = ip_address[:-1] + str(i)
            private_cluster_config["publicEndpoint"] = ip_address
            test_asset["versioned_resources"][0]["resource"][
                "privateClusterConfig"
            ] = private_cluster_config
            test_seed_values.append(ip_address)
            test_assets.append(self.mock_asset(test_asset))
        test_label = self.connector.format_label("censys-cc-test-project")

        # Mock
        mock_pager = SearchAllResourcesPager(
            response=SearchAllResourcesResponse(results=test_assets),
            request={},
            method=None,
        )
        mock_search_all_resources = self.mocker.patch.object(
            self.connector, "search_all_resources", return_value=mock_pager
        )
        self.mocker.patch.object(self.connector, "all_projects", test_all_projects)

        # Actual call
        self.connector.get_container_clusters()

        # Assertions
        mock_search_all_resources.assert_called_once_with(
            filter=GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_cloud_sql_instances(self):
        # Test data
        test_assets = []
        test_seed_values = []
        test_all_projects = {
            "123456789123": {
                "project_id": "censys-cc-test-project",
                "name": "Censys CC Test Project",
            }
        }
        for i in range(1, 4):
            test_asset = self.data["TEST_CLOUD_SQL_INSTANCE"]
            ip_addresses: list[dict] = []
            # populate ip_addresses.ipAddress with i number of ips
            for j in range(i):
                ip_address = f"195.111.{i}.{j}"
                ip_addresses.append({"ipAddress": ip_address})
                test_seed_values.append(ip_address)
            test_asset["versioned_resources"][0]["resource"][
                "ipAddresses"
            ] = ip_addresses
            test_assets.append(self.mock_asset(test_asset))
        test_label = self.connector.format_label("censys-cc-test-project")

        # Mock
        mock_pager = SearchAllResourcesPager(
            response=SearchAllResourcesResponse(results=test_assets),
            request={},
            method=None,
        )
        mock_search_all_resources = self.mocker.patch.object(
            self.connector, "search_all_resources", return_value=mock_pager
        )
        self.mocker.patch.object(self.connector, "all_projects", test_all_projects)

        # Actual call
        self.connector.get_cloud_sql_instances()

        # Assertions
        mock_search_all_resources.assert_called_once_with(
            filter=GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_dns_records(self):
        # Test data
        test_assets = []
        test_seed_values = []
        test_all_projects = {
            "123456789123": {
                "project_id": "censys-cc-test-project",
                "name": "Censys CC Test Project",
            }
        }
        for i in range(3):
            test_asset = self.data["TEST_DNS_ZONE"]
            domain = str(i) + "." + "censys.io"
            test_asset["versioned_resources"][0]["resource"]["dnsName"] = domain + "."
            test_seed_values.append(domain)
            test_assets.append(self.mock_asset(test_asset))
        test_label = self.connector.format_label("censys-cc-test-project")

        # Mock
        mock_pager = SearchAllResourcesPager(
            response=SearchAllResourcesResponse(results=test_assets),
            request={},
            method=None,
        )
        mock_search_all_resources = self.mocker.patch.object(
            self.connector, "search_all_resources", return_value=mock_pager
        )
        self.mocker.patch.object(self.connector, "all_projects", test_all_projects)

        # Actual call
        self.connector.get_dns_records()

        # Assertions
        mock_search_all_resources.assert_called_once_with(
            filter=GcpCloudAssetInventoryTypes.DNS_ZONE
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_seeds(self):
        # Test data
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )

        seed_scanners = {
            GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE: self.mocker.Mock(),
            GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS: self.mocker.Mock(),
            GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER: self.mocker.Mock(),
            GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE: self.mocker.Mock(),
            GcpCloudAssetInventoryTypes.DNS_ZONE: self.mocker.Mock(),
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
            GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE: self.mocker.Mock(),
            GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS: self.mocker.Mock(),
            GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER: self.mocker.Mock(),
            GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE: self.mocker.Mock(),
            GcpCloudAssetInventoryTypes.DNS_ZONE: self.mocker.Mock(),
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
        test_all_projects = {
            "123456789123": {
                "project_id": "censys-cc-test-project",
                "name": "Censys CC Test Project",
            }
        }
        for i in range(3):
            test_asset = self.data["TEST_STORAGE_BUCKET"]
            bucket_name = "bucket" + str(i)
            test_asset["versioned_resources"][0]["resource"]["id"] = bucket_name
            test_buckets.append(bucket_name)
            test_assets.append(self.mock_asset(test_asset))
        test_uid = self.connector.format_uid("censys-cc-test-project")

        # Mock
        mock_pager = SearchAllResourcesPager(
            response=SearchAllResourcesResponse(results=test_assets),
            request={},
            method=None,
        )
        mock_search_all_resources = self.mocker.patch.object(
            self.connector, "search_all_resources", return_value=mock_pager
        )

        self.mocker.patch.object(self.connector, "all_projects", test_all_projects)

        # Actual call
        self.connector.get_storage_buckets()

        # Assertions
        mock_search_all_resources.assert_called_once_with(
            filter=GcpCloudAssetInventoryTypes.STORAGE_BUCKET
        )
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
            GcpCloudAssetInventoryTypes.STORAGE_BUCKET: self.mocker.Mock(),
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
