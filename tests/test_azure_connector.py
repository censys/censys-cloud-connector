import json
from unittest import TestCase
from unittest.mock import MagicMock

import pytest
from parameterized import parameterized

from censys.cloud_connectors.azure_connector.enums import AzureResourceTypes
from censys.cloud_connectors.common.enums import ProviderEnum
from tests.base_connector_case import BaseConnectorCase

failed_import = False
try:
    from azure.core.exceptions import ClientAuthenticationError, HttpResponseError

    from censys.cloud_connectors.azure_connector import AzureCloudConnector
    from censys.cloud_connectors.azure_connector.settings import AzureSpecificSettings
except ImportError:
    failed_import = True


@pytest.mark.skipif(failed_import, reason="Azure SDK not installed")
class TestAzureCloudConnector(BaseConnectorCase, TestCase):
    connector: AzureCloudConnector
    connector_cls = AzureCloudConnector

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
        self.connector.subscription_id = self.data["TEST_CREDS"]["subscription_id"]
        self.connector.credentials = self.mocker.MagicMock()

    def mock_asset(self, data: dict) -> MagicMock:
        asset = self.mocker.MagicMock()
        for key, value in data.items():
            asset.__setattr__(key, value)
        asset.as_dict.return_value = data
        return asset

    def mock_client(self, client_name: str) -> MagicMock:
        return self.mocker.patch(
            f"censys.cloud_connectors.azure_connector.connector.{client_name}"
        )

    @parameterized.expand([(ClientAuthenticationError,)])
    def test_scan_fail(self, exception):
        # Mock super().scan()
        mock_scan = self.mocker.patch.object(
            self.connector.__class__.__bases__[0],
            "scan",
            side_effect=exception,
        )

        # Actual call
        self.connector.scan()

        # Assertions
        mock_scan.assert_called_once()

    def test_scan_all(self):
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
        self.connector.settings.providers[self.connector.provider] = provider_settings

        # Mock scan
        mock_scan = self.mocker.patch.object(self.connector, "scan")

        # Actual call
        self.connector.scan_all()

        # Assertions
        assert mock_scan.call_count == 3

    def test_format_label(self):
        # Test data
        test_location = "test-location"
        test_asset = self.mock_asset({"location": test_location})

        # Actual call
        label = self.connector.format_label(test_asset)

        # Assertions
        assert label == f"AZURE: {self.connector.subscription_id}/{test_location}"

    def test_format_label_no_location(self):
        # Test data
        test_asset = self.mock_asset({})
        del test_asset.location

        # Actual call
        with pytest.raises(ValueError, match="Asset has no location"):
            self.connector.format_label(test_asset)

    def test_get_seeds(self):
        # Test data
        self.connector.provider_settings = AzureSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )
        seed_scanners = {
            AzureResourceTypes.PUBLIC_IP_ADDRESSES: self.mocker.Mock(),
            AzureResourceTypes.CONTAINER_GROUPS: self.mocker.Mock(),
            AzureResourceTypes.SQL_SERVERS: self.mocker.Mock(),
            AzureResourceTypes.DNS_ZONES: self.mocker.Mock(),
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
        self.connector.provider_settings = AzureSpecificSettings.from_dict(
            self.data["TEST_CREDS_IGNORE"]
        )
        seed_scanners = {
            resource_type: self.mocker.Mock()
            for resource_type in [
                AzureResourceTypes.PUBLIC_IP_ADDRESSES,
                AzureResourceTypes.CONTAINER_GROUPS,
                AzureResourceTypes.SQL_SERVERS,
                AzureResourceTypes.DNS_ZONES,
            ]
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

    def test_get_ip_addresses(self):
        # Test data
        test_list_all_response = []
        test_seed_values = []
        for i in range(3):
            test_ip_response = self.data["TEST_IP_ADDRESS"].copy()
            ip_address = test_ip_response["ip_address"][:-1] + str(i)
            test_ip_response["ip_address"] = ip_address
            test_seed_values.append(ip_address)
            test_list_all_response.append(self.mock_asset(test_ip_response))
        test_label = self.connector.format_label(test_list_all_response[0])

        # Mock list_all
        mock_network_client = self.mock_client("NetworkManagementClient")
        mock_public_ips = self.mocker.patch.object(
            mock_network_client.return_value, "public_ip_addresses"
        )
        mock_public_ips.list_all.return_value = test_list_all_response

        # Actual call
        self.connector.get_ip_addresses()

        # Assertions
        mock_network_client.assert_called_with(
            self.connector.credentials, self.connector.subscription_id
        )
        mock_public_ips.list_all.assert_called_once()
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_clusters(self):
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
        test_label = self.connector.format_label(test_list_response[0])

        # Mock list
        mock_container_client = self.mock_client("ContainerInstanceManagementClient")
        mock_container_groups = self.mocker.patch.object(
            mock_container_client.return_value, "container_groups"
        )
        mock_container_groups.list.return_value = test_list_response

        # Actual call
        self.connector.get_clusters()

        # Assertions
        mock_container_client.assert_called_with(
            self.connector.credentials, self.connector.subscription_id
        )
        mock_container_groups.list.assert_called_once()
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_sql_servers(self):
        # Test data
        test_list_response = []
        test_seed_values = []
        for i in range(3):
            test_server_response = self.data["TEST_SQL_SERVER"].copy()
            domain = f"test-{i}" + test_server_response["fully_qualified_domain_name"]
            test_server_response["fully_qualified_domain_name"] = domain
            test_seed_values.append(domain)
            test_list_response.append(self.mock_asset(test_server_response))
        test_label = self.connector.format_label(test_list_response[0])

        # Mock list
        mock_sql_client = self.mock_client("SqlManagementClient")
        mock_servers = self.mocker.patch.object(mock_sql_client.return_value, "servers")
        mock_servers.list.return_value = test_list_response

        # Actual call
        self.connector.get_sql_servers()

        # Assertions
        mock_sql_client.assert_called_with(
            self.connector.credentials, self.connector.subscription_id
        )
        mock_servers.list.assert_called_once()
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_dns_records(self):
        # Test data
        test_zones = [self.mock_asset(self.data["TEST_DNS_ZONE"])]
        test_label = self.connector.format_label(test_zones[0])
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
        mock_zones = self.mocker.patch.object(mock_dns_client.return_value, "zones")
        mock_zones.list.return_value = test_zones
        mock_records = self.mocker.patch.object(
            mock_dns_client.return_value, "record_sets"
        )
        mock_records.list_all_by_dns_zone.return_value = test_list_records

        # Actual call
        self.connector.get_dns_records()

        # Assertions
        mock_dns_client.assert_called_with(
            self.connector.credentials, self.connector.subscription_id
        )
        mock_records.list_all_by_dns_zone.assert_called_once()
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_dns_records_fail(self):
        # Mock list
        mock_dns_client = self.mock_client("DnsManagementClient")
        mock_zones = self.mocker.patch.object(mock_dns_client.return_value, "zones")
        mock_zones.list.side_effect = HttpResponseError
        mock_error_logger = self.mocker.patch.object(self.connector.logger, "error")

        # Actual call
        self.connector.get_dns_records()

        # Assertions
        mock_dns_client.assert_called_with(
            self.connector.credentials, self.connector.subscription_id
        )
        mock_zones.list.assert_called_once()
        mock_error_logger.assert_called_once()
        assert mock_error_logger.call_args[0][0].startswith(
            "Failed to get Azure DNS records"
        )

    def test_get_cloud_assets(self):
        # Test data
        self.connector.provider_settings = AzureSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )
        cloud_asset_scanners = {
            AzureResourceTypes.STORAGE_ACCOUNTS: self.mocker.Mock(),
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
        self.connector.provider_settings = AzureSpecificSettings.from_dict(
            self.data["TEST_CREDS_IGNORE"]
        )

        # Mock
        mock_storage_container = self.mocker.patch.object(
            self.connector, "get_storage_containers"
        )

        # Actual call
        self.connector.get_cloud_assets()

        # Assertions
        mock_storage_container.assert_not_called()

    def test_get_storage_containers(self):
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
        test_label = self.connector.format_label(test_storage_accounts[0])

        # Mock list
        mock_storage_client = self.mock_client("StorageManagementClient")
        mock_storage_accounts = self.mocker.patch.object(
            mock_storage_client.return_value, "storage_accounts"
        )
        mock_storage_accounts.list.return_value = test_storage_accounts

        # Mock list containers
        mock_blob_client = self.mock_client("BlobServiceClient")
        mock_blob_client.return_value.list_containers.return_value = test_containers

        def get_container_with_url(container):
            container.url = f"https://{container.name}.blob.core.windows.net"
            return container

        mock_blob_client.return_value.get_container_client.side_effect = (
            get_container_with_url
        )

        # Actual call
        self.connector.get_storage_containers()

        # Assertions
        mock_storage_client.assert_called_with(
            self.connector.credentials, self.connector.subscription_id
        )
        assert mock_blob_client.call_count == len(test_storage_accounts)
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )
        test_uid = list(self.connector.cloud_assets.keys())[0]
        assert len(self.connector.cloud_assets[test_uid]) == len(test_containers)
