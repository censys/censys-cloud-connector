import asyncio
import json
from unittest.mock import MagicMock

import asynctest
import pytest
from asynctest import TestCase
from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.storage.blob import ContainerProperties
from azure.storage.blob.aio import BlobServiceClient
from parameterized import parameterized

from censys.cloud_connectors.azure_connector import AzureCloudConnector
from censys.cloud_connectors.azure_connector.enums import AzureResourceTypes
from censys.cloud_connectors.azure_connector.settings import AzureSpecificSettings
from censys.cloud_connectors.common.enums import ProviderEnum
from tests.base_connector_case import BaseConnectorCase


class TestAzureCloudConnector(BaseConnectorCase, TestCase):
    connector: AzureCloudConnector
    connector_cls = AzureCloudConnector
    test_subscription_id: str
    test_credentials: MagicMock

    def setUp(self) -> None:
        super().setUp()
        with open(self.shared_datadir / "test_azure_responses.json") as f:
            self.data = json.load(f)
        test_azure_settings = AzureSpecificSettings.from_dict(self.data["TEST_CREDS"])
        self.settings.providers[ProviderEnum.AZURE] = {
            test_azure_settings.get_provider_key(): test_azure_settings
        }
        self.connector = AzureCloudConnector(self.settings)
        # Set subscription_id as its required for certain calls
        self.test_subscription_id = self.data["TEST_CREDS"]["subscription_id"]
        self.test_credentials = self.mocker.MagicMock()
        self.connector.provider_settings = test_azure_settings

    def mock_asset(self, data: dict) -> MagicMock:
        asset = self.mocker.MagicMock()
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(asset, key, self.mock_asset(value))
            else:
                setattr(asset, key, value)
        asset.as_dict.return_value = data
        return asset

    def mock_client(self, client_name: str) -> MagicMock:
        mock = self.mocker.patch(
            f"censys.cloud_connectors.azure_connector.connector.{client_name}",
            new_callable=asynctest.MagicMock,
        )
        mock.return_value.close = asynctest.CoroutineMock()
        return mock

    def mock_healthcheck(self) -> MagicMock:
        """Mock the healthcheck.

        Returns:
            MagicMock: mocked healthcheck
        """
        return self.mocker.patch(
            "censys.cloud_connectors.azure_connector.connector.Healthcheck"
        )

    @parameterized.expand([(ClientAuthenticationError,)])
    async def test_scan_fail(self, exception):
        # Mock super().scan()
        mock_scan = self.mocker.patch.object(
            self.connector.__class__.__bases__[0],
            "scan",
            side_effect=exception,
        )
        mock_healthcheck = self.mock_healthcheck()

        # Actual call
        with pytest.raises(exception):
            await self.connector.scan(
                self.connector.provider_settings,  # type: ignore[arg-type]
                self.test_credentials,
                self.test_subscription_id,
            )

        # Assertions
        mock_scan.assert_called_once()
        self.assert_healthcheck_called(mock_healthcheck)

    async def test_scan_all(self):
        # Test data
        test_single_subscription = self.data["TEST_CREDS"]
        test_multiple_subscriptions = test_single_subscription.copy()
        test_multiple_subscriptions["client_id"] = test_multiple_subscriptions[
            "client_id"
        ].replace("x", "y")
        test_multiple_subscriptions["subscription_id"] = [
            test_multiple_subscriptions["subscription_id"],
            test_multiple_subscriptions["subscription_id"].replace("x", "y"),
        ]
        test_azure_settings = [
            AzureSpecificSettings.from_dict(test_single_subscription),
            AzureSpecificSettings.from_dict(test_multiple_subscriptions),
        ]
        provider_settings: dict[tuple, AzureSpecificSettings] = {
            p.get_provider_key(): p for p in test_azure_settings
        }
        self.connector.settings.providers[self.connector.provider] = provider_settings  # type: ignore[arg-type]

        # Mock scan
        mock_scan = self.mocker.patch.object(self.connector, "scan")

        # Actual call
        await self.connector.scan_all()

        # Assertions
        assert mock_scan.call_count == 3

    def test_format_label(self):
        # Test data
        test_location = "test-location"
        test_asset = self.mock_asset({"location": test_location})

        # Actual call
        label = self.connector.format_label(test_asset, self.test_subscription_id)

        # Assertions
        assert label == f"AZURE: {self.test_subscription_id}/{test_location}"

    def test_format_label_no_location(self):
        # Test data
        test_asset = self.mock_asset({})
        del test_asset.location

        # Actual call
        with pytest.raises(ValueError, match="Asset has no location"):
            self.connector.format_label(test_asset, self.test_subscription_id)

    async def test_get_seeds(self):
        # Test data
        self.connector.provider_settings = AzureSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )

        # Mock
        seed_scanners = {
            AzureResourceTypes.PUBLIC_IP_ADDRESSES: asynctest.MagicMock(),
            AzureResourceTypes.CONTAINER_GROUPS: asynctest.MagicMock(),
            AzureResourceTypes.SQL_SERVERS: asynctest.MagicMock(),
            AzureResourceTypes.DNS_ZONES: asynctest.MagicMock(),
        }
        for scanner in seed_scanners.values():
            scanner.return_value = asyncio.Future()
            scanner.return_value.set_result(None)
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
        self.connector.provider_settings = AzureSpecificSettings.from_dict(
            self.data["TEST_CREDS_IGNORE"]
        )

        # Mock
        seed_scanners = {
            resource_type: asynctest.MagicMock()
            for resource_type in [
                AzureResourceTypes.PUBLIC_IP_ADDRESSES,
                AzureResourceTypes.CONTAINER_GROUPS,
                AzureResourceTypes.SQL_SERVERS,
                AzureResourceTypes.DNS_ZONES,
            ]
        }
        for scanner in seed_scanners.values():
            scanner.return_value = asyncio.Future()
            scanner.return_value.set_result(None)
        self.mocker.patch.object(
            self.connector,
            "seed_scanners",
            new_callable=self.mocker.PropertyMock(return_value=seed_scanners),
        )

        # Actual call
        await self.connector.get_seeds(self.connector.provider_settings)

        # Assertions
        for resource_type, mock in self.connector.seed_scanners.items():
            if (
                self.connector.provider_settings.ignore
                and resource_type in self.connector.provider_settings.ignore
            ):
                mock.assert_not_called()
            else:
                mock.assert_called_once()

    async def test_get_ip_addresses(self):
        # Test data
        test_list_all_response = []
        test_seed_values = []
        for i in range(3):
            test_ip_response = self.data["TEST_IP_ADDRESS"].copy()
            ip_address = test_ip_response["ip_address"][:-1] + str(i)
            test_ip_response["ip_address"] = ip_address
            test_seed_values.append(ip_address)
            test_list_all_response.append(self.mock_asset(test_ip_response))
        test_label = self.connector.format_label(
            test_list_all_response[0], self.test_subscription_id
        )

        # Mock list_all
        mock_network_client = self.mock_client("NetworkManagementClient")
        mock_public_ips_list_all = asynctest.MagicMock()
        mock_public_ips_list_all.__aiter__.return_value = test_list_all_response
        mock_network_client.return_value.public_ip_addresses.list_all.return_value = (
            mock_public_ips_list_all
        )

        # Actual call
        await self.connector.get_ip_addresses(
            self.connector.provider_settings,  # type: ignore[arg-type]
            self.test_credentials,
            self.test_subscription_id,
            AzureResourceTypes.PUBLIC_IP_ADDRESSES,
        )

        # Assertions
        mock_network_client.assert_called_with(
            self.test_credentials, self.test_subscription_id
        )
        mock_public_ips_list_all.__aiter__.assert_called_once()
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_clusters(self):
        # Test data
        test_list_response = []
        test_seed_values = []
        base_domain = ".eastus.azurecontainer.io"
        for i in range(3):
            test_container_response = self.data["TEST_CONTAINER_ASSET"].copy()
            ip_address_copy = test_container_response["ip_address"].copy()
            ip_address = ip_address_copy["ip"][:-1] + str(i)
            ip_address_copy["ip"] = ip_address
            test_seed_values.append(ip_address)
            domain = f"test-{i}" + base_domain
            ip_address_copy["fqdn"] = domain
            test_seed_values.append(domain)
            test_container_response["ip_address"] = ip_address_copy
            test_list_response.append(self.mock_asset(test_container_response))
        test_label = self.connector.format_label(
            test_list_response[0], self.test_subscription_id
        )

        # Mock list
        mock_container_client = self.mock_client("ContainerInstanceManagementClient")
        mock_container_groups_list = asynctest.MagicMock()
        mock_container_groups_list.__aiter__.return_value = test_list_response
        mock_container_client.return_value.container_groups.list.return_value = (
            mock_container_groups_list
        )

        # Actual call
        await self.connector.get_clusters(
            self.connector.provider_settings,  # type: ignore[arg-type]
            self.test_credentials,
            self.test_subscription_id,
            AzureResourceTypes.CONTAINER_GROUPS,
        )

        # Assertions
        mock_container_client.assert_called_with(
            self.test_credentials, self.test_subscription_id
        )
        mock_container_groups_list.__aiter__.assert_called_once()
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_sql_servers(self):
        # Test data
        test_list_response = []
        test_seed_values = []
        for i in range(3):
            test_server_response = self.data["TEST_SQL_SERVER"].copy()
            domain = f"test-{i}" + test_server_response["fully_qualified_domain_name"]
            test_server_response["fully_qualified_domain_name"] = domain
            test_seed_values.append(domain)
            test_list_response.append(self.mock_asset(test_server_response))
        test_label = self.connector.format_label(
            test_list_response[0], self.test_subscription_id
        )

        # Mock list
        mock_sql_client = self.mock_client("SqlManagementClient")
        mock_servers_list = asynctest.MagicMock()
        mock_servers_list.__aiter__.return_value = test_list_response
        mock_sql_client.return_value.servers.list.return_value = mock_servers_list

        # Actual call
        await self.connector.get_sql_servers(
            self.connector.provider_settings,  # type: ignore[arg-type]
            self.test_credentials,
            self.test_subscription_id,
            AzureResourceTypes.SQL_SERVERS,
        )

        # Assertions
        mock_sql_client.assert_called_with(
            self.test_credentials, self.test_subscription_id
        )
        mock_servers_list.__aiter__.assert_called_once()
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_dns_records(self):
        # Test data
        test_zones = [self.mock_asset(self.data["TEST_DNS_ZONE"])]
        test_label = self.connector.format_label(
            test_zones[0], self.test_subscription_id
        )
        test_list_records = []
        test_seed_values = []
        for data_key in [
            "TEST_DNS_RECORD_A",
            "TEST_DNS_RECORD_SOA",
            "TEST_DNS_RECORD_CNAME",
        ]:
            test_record = self.data[data_key].copy()
            domain = test_record["fqdn"]
            if domain.endswith("."):
                domain = domain[:-1]
            test_seed_values.append(domain)
            if a_records := test_record.get("a_records"):
                test_seed_values.extend([a["ipv4_address"] for a in a_records])
            if cname_record := test_record.get("cname_record"):
                test_seed_values.append(cname_record["cname"])
            test_list_records.append(self.mock_asset(test_record))

        # Mock list
        mock_dns_client = self.mock_client("DnsManagementClient")
        mock_zones_list = asynctest.MagicMock()
        mock_zones_list.__aiter__.return_value = test_zones
        mock_dns_client.return_value.zones.list.return_value = mock_zones_list
        mock_record_sets = asynctest.MagicMock()
        mock_record_sets.__aiter__.return_value = test_list_records
        mock_dns_client.return_value.record_sets.list_all_by_dns_zone.return_value = (
            mock_record_sets
        )

        # Actual call
        await self.connector.get_dns_records(
            self.connector.provider_settings,  # type: ignore[arg-type]
            self.test_credentials,
            self.test_subscription_id,
            AzureResourceTypes.DNS_ZONES,
        )

        # Assertions
        mock_dns_client.assert_called_with(
            self.test_credentials, self.test_subscription_id
        )
        mock_zones_list.__aiter__.assert_called_once()
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_dns_records_fail(self):
        # Mock list
        mock_dns_client = self.mock_client("DnsManagementClient")
        mock_zones = self.mocker.patch.object(mock_dns_client.return_value, "zones")
        mock_zones.list.side_effect = HttpResponseError
        mock_error_logger = self.mocker.patch.object(self.connector.logger, "error")

        # Actual call
        await self.connector.get_dns_records(
            self.connector.provider_settings,  # type: ignore[arg-type]
            self.test_credentials,
            self.test_subscription_id,
            AzureResourceTypes.DNS_ZONES,
        )

        # Assertions
        mock_dns_client.assert_called_with(
            self.test_credentials, self.test_subscription_id
        )
        mock_zones.list.assert_called_once()
        mock_error_logger.assert_called_once()
        assert mock_error_logger.call_args[0][0].startswith(
            "Failed to get Azure DNS records"
        )

    async def test_get_cloud_assets(self):
        # Test data
        self.connector.provider_settings = AzureSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )

        # Mock
        cloud_asset_scanners = {
            AzureResourceTypes.STORAGE_ACCOUNTS: self.mocker.Mock(),
        }
        for scanner in cloud_asset_scanners.values():
            scanner.return_value = asyncio.Future()
            scanner.return_value.set_result(None)
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
        self.connector.provider_settings = AzureSpecificSettings.from_dict(
            self.data["TEST_CREDS_IGNORE"]
        )

        # Mock
        mock_storage_container = self.mocker.patch.object(
            self.connector, "get_storage_containers"
        )

        # Actual call
        await self.connector.get_cloud_assets(self.connector.provider_settings)

        # Assertions
        mock_storage_container.assert_not_called()

    async def test_get_storage_containers(self):
        # Test data
        test_storage_accounts = []
        test_containers = []
        test_seed_values = []
        for i in range(3):
            test_storage_account = self.data["TEST_STORAGE_ACCOUNT"].copy()
            test_storage_account["name"] = f"test-{i}"
            if custom_domain := test_storage_account.get("custom_domain"):
                custom_domain_copy = custom_domain.copy()
                custom_domain_copy["name"] = f"test-{i}.blobs.censys.io"
                test_seed_values.append(custom_domain_copy["name"])
                test_storage_account["custom_domain"] = custom_domain_copy
            test_storage_accounts.append(self.mock_asset(test_storage_account))
            test_container = self.data["TEST_STORAGE_CONTAINER"].copy()
            test_container["name"] = f"test-{i}"
            test_containers.append(self.mock_asset(test_container))
        test_label = self.connector.format_label(
            test_storage_accounts[0], self.test_subscription_id
        )

        # Mock list
        mock_storage_client = self.mock_client("StorageManagementClient")
        mock_storage_client_iter = asynctest.MagicMock()
        mock_storage_client_iter.__aiter__.return_value = test_storage_accounts
        mock_storage_client_iter = (
            mock_storage_client.return_value.storage_accounts.list.return_value
        ) = mock_storage_client_iter

        # Mock list containers
        mock_blob_client = self.mock_client("BlobServiceClient")
        mock_blob_client.return_value.list_containers.return_value.__aiter__.return_value = (
            test_containers
        )
        mock_get_storage_container_url = asynctest.CoroutineMock()

        def get_container_with_url(
            _: BlobServiceClient, container: ContainerProperties
        ) -> str:
            return f"https://{container.name}.blob.core.windows.net"

        mock_get_storage_container_url.side_effect = get_container_with_url
        self.mocker.patch.object(
            self.connector,
            "get_storage_container_url",
            new_callable=self.mocker.PropertyMock(
                return_value=mock_get_storage_container_url
            ),
        )

        # Actual call
        await self.connector.get_storage_containers(
            self.connector.provider_settings,  # type: ignore[arg-type]
            self.test_credentials,
            self.test_subscription_id,
            AzureResourceTypes.STORAGE_ACCOUNTS,
        )

        # Assertions
        mock_storage_client.assert_called_with(
            self.test_credentials, self.test_subscription_id
        )
        assert mock_blob_client.call_count == len(test_storage_accounts)
        assert (
            mock_blob_client.return_value.list_containers.return_value.__aiter__.call_count
            == len(test_storage_accounts)
        )
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )
        test_uid = list(self.connector.cloud_assets.keys())[0]
        assert len(self.connector.cloud_assets[test_uid]) == len(test_containers)
