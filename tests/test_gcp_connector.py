import asyncio
import json
from unittest.mock import MagicMock

import asynctest
from asynctest import TestCase
from google.cloud.securitycenter_v1.types import ListAssetsResponse
from parameterized import parameterized

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import Settings
from censys.cloud_connectors.gcp_connector.connector import GcpCloudConnector
from censys.cloud_connectors.gcp_connector.enums import GcpSecurityCenterResourceTypes
from censys.cloud_connectors.gcp_connector.settings import GcpSpecificSettings
from tests.base_connector_case import BaseConnectorCase


class TestGcpConnector(BaseConnectorCase, TestCase):
    connector: GcpCloudConnector
    connector_cls = GcpCloudConnector
    test_organization_id: str
    test_credentials: dict

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
        self.connector.provider_settings = test_gcp_settings
        self.test_organization_id = self.data["TEST_CREDS"]["organization_id"]
        self.test_credentials = self.mocker.MagicMock()

    # def tearDown(self) -> None:
    #     # Reset the deaultdicts as they are immutable
    #     for seed_key in list(self.connector.seeds.keys()):
    #         del self.connector.seeds[seed_key]
    #     for cloud_asset_key in list(self.connector.cloud_assets.keys()):
    #         del self.connector.cloud_assets[cloud_asset_key]

    def mock_list_assets_result(
        self, data: dict
    ) -> ListAssetsResponse.ListAssetsResult:
        """Populate the ListAssetsResult object.

        Args:
            data (dict): The data to mock.

        Returns:
            ListAssetsResponse.ListAssetsResult: The test ListAssetsResult object.
        """
        return ListAssetsResponse.ListAssetsResult.from_json(json.dumps(data))  # type: ignore

    def mock_healthcheck(self) -> MagicMock:
        """Mock the healthcheck.

        Returns:
            MagicMock: mocked healthcheck
        """
        return self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.Healthcheck"
        )

    # def assert_seeds_with_values(self, seeds: list[Seed], values: list[str]):
    #     assert len(seeds) == len(values)
    #     for seed in seeds:
    #         assert seed.value in values

    def test_init(self):
        assert self.connector.provider == ProviderEnum.GCP
        assert self.connector.label_prefix == "GCP: "
        assert self.connector.settings == self.settings

    async def test_scan(self):
        # Mock
        mock_credentials = self.mocker.patch(
            "censys.cloud_connectors.gcp_connector.connector.service_account.Credentials.from_service_account_file",
        )
        mock_scan = self.mocker.patch.object(
            self.connector.__class__.__bases__[0], "scan"
        )
        mock_healthcheck = self.mock_healthcheck()

        # Actual call
        await self.connector.scan(self.connector.provider_settings)  # type: ignore[arg-type]

        # Assertions
        mock_credentials.assert_called_once()
        mock_scan.assert_called_once()
        self.assert_healthcheck_called(mock_healthcheck)

    async def test_credentials_fail(self):
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
        await self.connector.scan(self.connector.provider_settings)  # type: ignore[arg-type]

        # Assertions
        mock_credentials.assert_called_once()
        mock_error_logger.assert_called()
        mock_scan.assert_not_called()
        self.assert_healthcheck_called(mock_healthcheck)

    async def test_scan_all(self):
        # Test data
        test_creds = self.data["TEST_CREDS"].copy()
        second_test_creds = test_creds.copy()
        second_test_creds["organization_id"] = 9876543210
        test_gcp_settings = [
            GcpSpecificSettings.from_dict(test_creds),
            GcpSpecificSettings.from_dict(second_test_creds),
        ]
        provider_settings: dict[tuple, GcpSpecificSettings] = {
            p.get_provider_key(): p for p in test_gcp_settings
        }
        self.connector.settings.providers[self.connector.provider] = provider_settings  # type: ignore[arg-type]

        # Mock
        mock_scan = self.mocker.patch.object(self.connector, "scan")

        # Actual call
        await self.connector.scan_all()

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
        label = self.connector.format_label(
            self.connector.provider_settings, test_result  # type: ignore[arg-type]
        )

        # Assertions
        assert label == f"GCP: {self.test_organization_id}/censys-cc-test-project"

    @parameterized.expand([("test-filter")])
    async def test_list_assets(self, filter: str):
        # Mock
        mock_sc_client = asynctest.MagicMock(
            "censys.cloud_connectors.gcp_connector.connector.securitycenter_v1.SecurityCenterClient"
        )
        mock_sc_client.return_value.list_assets.return_value = asyncio.Future()
        mock_sc_client.return_value.list_assets.return_value.set_result(None)

        # Actual call
        await self.connector.list_assets(
            self.connector.provider_settings, mock_sc_client.return_value, filter  # type: ignore[arg-type]
        )

        # Assertions
        mock_sc_client.return_value.list_assets.assert_called_once_with(
            request={
                "parent": f"organizations/{self.test_organization_id}",
                "filter": filter,
            }
        )

    def test_get_compute_instances(self):
        self.skipTest("Test data is not available yet")
        # Test data
        test_list_assets_results = []
        test_seed_values = []
        for i in range(3):
            test_asset_result = self.data["TEST_COMPUTE_INSTANCE"].copy()
            # network_instances = test_asset_result["asset"]["resourceProperties"]["networkInterfaces"]
            # TODO: Implement tests
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
        self.connector.get_compute_instances()

        # Assertions
        mock_list.assert_called_once_with(
            filter=GcpSecurityCenterResourceTypes.COMPUTE_INSTANCE.filter()
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_compute_addresses(self):
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
        test_label = self.connector.format_label(
            self.connector.provider_settings, test_list_assets_results[0]  # type: ignore[arg-type]
        )

        # Mock
        mock_scc = self.mocker.Mock()
        mock_iter = asynctest.MagicMock()
        mock_iter.__aiter__.return_value = test_list_assets_results
        mock_iter = self.mocker.patch.object(
            self.connector, "list_assets", return_value=mock_iter
        )

        # Actual call
        await self.connector.get_compute_addresses(
            self.connector.provider_settings,  # type: ignore[arg-type]
            mock_scc,
            GcpSecurityCenterResourceTypes.COMPUTE_ADDRESS,
        )

        # Assertions
        mock_iter.assert_called_once_with(
            self.connector.provider_settings,
            mock_scc,
            filter=GcpSecurityCenterResourceTypes.COMPUTE_ADDRESS.filter(),
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_container_clusters(self):
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
        test_label = self.connector.format_label(
            self.connector.provider_settings, test_list_assets_results[0]  # type: ignore[arg-type]
        )

        # Mock
        mock_scc = self.mocker.Mock()
        mock_iter = asynctest.MagicMock()
        mock_iter.__aiter__.return_value = test_list_assets_results
        mock_iter = self.mocker.patch.object(
            self.connector, "list_assets", return_value=mock_iter
        )

        # Actual call
        await self.connector.get_container_clusters(
            self.connector.provider_settings,  # type: ignore[arg-type]
            mock_scc,
            GcpSecurityCenterResourceTypes.CONTAINER_CLUSTER,
        )

        # Assertions
        mock_iter.assert_called_once_with(
            self.connector.provider_settings,
            mock_scc,
            filter=GcpSecurityCenterResourceTypes.CONTAINER_CLUSTER.filter(),
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_cloud_sql_instances(self):
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
        test_label = self.connector.format_label(
            self.connector.provider_settings, test_list_assets_results[0]  # type: ignore[arg-type]
        )

        # Mock
        mock_scc = self.mocker.Mock()
        mock_iter = asynctest.MagicMock()
        mock_iter.__aiter__.return_value = test_list_assets_results
        mock_iter = self.mocker.patch.object(
            self.connector, "list_assets", return_value=mock_iter
        )

        # Actual call
        await self.connector.get_cloud_sql_instances(
            self.connector.provider_settings,  # type: ignore[arg-type]
            mock_scc,
            GcpSecurityCenterResourceTypes.CLOUD_SQL_INSTANCE,
        )

        # Assertions
        mock_iter.assert_called_once_with(
            self.connector.provider_settings,
            mock_scc,
            filter=GcpSecurityCenterResourceTypes.CLOUD_SQL_INSTANCE.filter(),
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_dns_records(self):
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
        test_label = self.connector.format_label(
            self.connector.provider_settings, test_list_assets_results[0]  # type: ignore[arg-type]
        )

        # Mock
        mock_scc = self.mocker.Mock()
        mock_iter = asynctest.MagicMock()
        mock_iter.__aiter__.return_value = test_list_assets_results
        mock_iter = self.mocker.patch.object(
            self.connector, "list_assets", return_value=mock_iter
        )

        # Actual call
        await self.connector.get_dns_records(
            self.connector.provider_settings,  # type: ignore[arg-type]
            mock_scc,
            GcpSecurityCenterResourceTypes.DNS_ZONE,
        )

        # Assertions
        mock_iter.assert_called_once_with(
            self.connector.provider_settings,
            mock_scc,
            filter=GcpSecurityCenterResourceTypes.DNS_ZONE.filter(),
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_seeds(self):
        # Test data
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )

        # Mock
        seed_scanners = {
            GcpSecurityCenterResourceTypes.COMPUTE_INSTANCE: asynctest.CoroutineMock(),
            GcpSecurityCenterResourceTypes.COMPUTE_ADDRESS: asynctest.CoroutineMock(),
            GcpSecurityCenterResourceTypes.CONTAINER_CLUSTER: asynctest.CoroutineMock(),
            GcpSecurityCenterResourceTypes.CLOUD_SQL_INSTANCE: asynctest.CoroutineMock(),
            GcpSecurityCenterResourceTypes.DNS_ZONE: asynctest.CoroutineMock(),
        }
        self.mocker.patch.object(
            self.connector,
            "seed_scanners",
            new_callable=self.mocker.PropertyMock(return_value=seed_scanners),
        )

        # Actual call
        await self.connector.get_seeds(self.connector.provider_settings)

        # Assertions
        for mock in self.connector.seed_scanners.values():
            mock.assert_called_once()

    async def test_get_seeds_ignore(self):
        # Test data
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS_IGNORE"]
        )

        # Mock
        seed_scanners = {
            GcpSecurityCenterResourceTypes.COMPUTE_INSTANCE: asynctest.CoroutineMock(),
            GcpSecurityCenterResourceTypes.COMPUTE_ADDRESS: asynctest.CoroutineMock(),
            GcpSecurityCenterResourceTypes.CONTAINER_CLUSTER: asynctest.CoroutineMock(),
            GcpSecurityCenterResourceTypes.CLOUD_SQL_INSTANCE: asynctest.CoroutineMock(),
            GcpSecurityCenterResourceTypes.DNS_ZONE: asynctest.CoroutineMock(),
        }
        self.mocker.patch.object(
            self.connector,
            "seed_scanners",
            new_callable=self.mocker.PropertyMock(return_value=seed_scanners),
        )

        # Actual call
        await self.connector.get_seeds(self.connector.provider_settings)

        # Assertions
        for resource_type, mock in self.connector.seed_scanners.items():
            if resource_type in self.connector.provider_settings.ignore:  # type: ignore
                mock.assert_not_called()
            else:
                mock.assert_called_once()

    async def test_get_storage_buckets(self):
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
        test_label = self.connector.format_label(
            self.connector.provider_settings, test_list_assets_results[0]  # type: ignore[arg-type]
        )

        # Mock
        mock_scc = self.mocker.Mock()
        mock_iter = asynctest.MagicMock()
        mock_iter.__aiter__.return_value = test_list_assets_results
        mock_iter = self.mocker.patch.object(
            self.connector, "list_assets", return_value=mock_iter
        )

        # Actual call
        await self.connector.get_storage_buckets(
            self.connector.provider_settings,  # type: ignore[arg-type]
            mock_scc,
            GcpSecurityCenterResourceTypes.STORAGE_BUCKET,
        )

        # Assertions
        mock_iter.assert_called_once_with(
            self.connector.provider_settings,
            mock_scc,
            filter=GcpSecurityCenterResourceTypes.STORAGE_BUCKET.filter(),
        )
        assert len(self.connector.cloud_assets[test_label]) == len(test_buckets)
        for bucket in self.connector.cloud_assets[test_label]:
            assert "https://storage.googleapis.com/" in bucket.value
            assert (
                bucket.value.removeprefix("https://storage.googleapis.com/")
                in test_buckets
            )
            assert "accountNumber" in bucket.scan_data

    async def test_get_cloud_assets(self):
        # Test data
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )

        # Mock
        cloud_asset_scanners = {
            GcpSecurityCenterResourceTypes.STORAGE_BUCKET: asynctest.CoroutineMock(),
        }
        self.mocker.patch.object(
            self.connector,
            "cloud_asset_scanners",
            new_callable=self.mocker.PropertyMock(return_value=cloud_asset_scanners),
        )

        # Actual call
        await self.connector.get_cloud_assets(self.connector.provider_settings)

        # Assertions
        for mock in cloud_asset_scanners.values():
            mock.assert_called_once()

    async def test_get_cloud_assets_ignore(self):
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
        await self.connector.get_cloud_assets(self.connector.provider_settings)

        # Assertions
        mock_storage_bucket.assert_not_called()
