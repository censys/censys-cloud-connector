import json
import time
from unittest import TestCase
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import HttpResponseError
from parameterized import parameterized

from censys.cloud_connectors.azure_connector import __provider_setup__
from censys.cloud_connectors.azure_connector.settings import AzureSpecificSettings
from censys.cloud_connectors.common.settings import Settings
from tests.base_case import BaseCase

failed_import = False
try:
    from azure.identity._exceptions import CredentialUnavailableError

except ImportError:
    failed_import = True


@pytest.mark.skipif(failed_import, reason="Azure SDK not installed")
class TestAzureProviderSetup(BaseCase, TestCase):
    def setUp(self) -> None:
        super().setUp()
        with open(self.shared_datadir / "test_azure_responses.json") as f:
            self.data = json.load(f)
        self.settings = Settings(**self.default_settings)
        self.setup_cli = __provider_setup__(self.settings)

    def mock_asset(self, data: dict) -> MagicMock:
        asset = self.mocker.MagicMock()
        for key, value in data.items():
            asset.__setattr__(key, value)
        asset.as_dict.return_value = data
        return asset

    def mock_client(
        self, client_name: str, module_name: str = "provider_setup"
    ) -> MagicMock:
        return self.mocker.patch(
            f"censys.cloud_connectors.azure_connector.{module_name}.{client_name}"
        )

    def test_get_subscriptions_from_cli(self):
        # Test data
        subscription_side_effects = []
        for i in range(3):
            mock_subscription = self.mocker.MagicMock()
            mock_subscription.as_dict.return_value = {
                "subscription_id": f"subscription_{i}",
                "display_name": f"Subscription {i}",
                "state": "Enabled",
            }
            subscription_side_effects.append(mock_subscription)

        # Mock list
        mock_cli_credentials = self.mocker.patch("azure.identity.AzureCliCredential")
        mock_cli_credentials.return_value = None
        mock_subscription_client = self.mocker.patch(
            "azure.mgmt.resource.SubscriptionClient"
        )
        mock_subscription_client.return_value.subscriptions.list.return_value = (
            subscription_side_effects
        )

        # Actual call
        subscriptions = self.setup_cli.get_subscriptions_from_cli()

        # Assertions
        assert len(subscriptions) == len(subscription_side_effects)

    @parameterized.expand(
        [
            (CredentialUnavailableError, "Unable to get subscriptions from the CLI"),
            (ImportError, "Please install the Azure SDK for Python"),
        ]
    )
    def test_get_subscriptions_from_cli_fail(self, exception, expected_message):
        # Mock list
        mock_cli_credentials = self.mocker.patch("azure.identity.AzureCliCredential")
        mock_cli_credentials.return_value = None
        mock_subscription_client = self.mocker.patch(
            "azure.mgmt.resource.SubscriptionClient"
        )
        mock_subscription_client.return_value.subscriptions.list.side_effect = exception
        mock_print_warning = self.mocker.patch.object(self.setup_cli, "print_warning")

        # Actual call
        subscriptions = self.setup_cli.get_subscriptions_from_cli()

        # Assertions
        assert len(subscriptions) == 0, "No subscriptions should be returned"
        mock_print_warning.assert_called_once_with(expected_message)

    def test_prompt_select_subscriptions(self):
        # Test data
        test_subscriptions = []
        for i in range(3):
            test_subscriptions.append(
                {
                    "subscription_id": f"subscription_{i}",
                    "display_name": f"Subscription {i}",
                    "state": "Enabled",
                }
            )
        # This would not be selectable
        test_subscriptions.append(
            {
                "subscription_id": "subscription_3",
                "display_name": "Subscription 3",
                "state": "Disabled",
            }
        )

        # Mock prompt
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt")
        mock_selected_subscriptions = test_subscriptions[:-1]
        mock_prompt.return_value = {"subscription_ids": mock_selected_subscriptions}

        # Actual call
        selected_subscriptions = self.setup_cli.prompt_select_subscriptions(
            test_subscriptions
        )

        # Assertions
        assert mock_prompt.call_count == 1
        assert len(selected_subscriptions) == len(mock_selected_subscriptions)
        for subscription in selected_subscriptions:
            assert subscription in mock_selected_subscriptions

    @parameterized.expand(
        [
            (
                [{"id": "subscriptions/subscription_0"}],
                ["subscriptions/subscription_0"],
            ),
            (
                [
                    {"id": "subscriptions/subscription_0"},
                    {"id": "subscriptions/subscription_1"},
                ],
                ["subscriptions/subscription_0", "subscriptions/subscription_1"],
            ),
        ]
    )
    def test_generate_create_command(
        self, subscriptions: list, subscription_ids: list[str]
    ):
        # Actual call
        sp_command = self.setup_cli.generate_create_command(
            subscriptions, only_show_errors=False
        )

        # Assertions
        expected_command_prefix = ["az", "ad", "sp", "create-for-rbac"]
        assert sp_command[: len(expected_command_prefix)] == expected_command_prefix
        expected_scope_suffix = ["--scopes"] + subscription_ids
        assert sp_command[-len(expected_scope_suffix) :] == expected_scope_suffix

    @parameterized.expand(
        [
            (True,),
            (False,),
        ]
    )
    def test_create_service_principal(self, expect_results: bool):
        # Test data
        test_subscriptions = [{"id": "subscriptions/subscription_0"}]
        test_creds = {"test_service_principal": "test_secret"}

        # Mock prompt
        mock_prompt = self.mocker.patch.object(
            self.setup_cli,
            "prompt",
            return_value={"create_service_principal": True},
        )

        mock_cli = self.mocker.patch("azure.cli.core.get_default_cli")
        mock_invoke = mock_cli.return_value.invoke
        if expect_results:
            mock_cli.return_value.result.result = test_creds
        else:
            mock_cli.return_value.result = None

        # Actual call
        creds = self.setup_cli.create_service_principal(test_subscriptions)

        # Assertions
        mock_prompt.assert_called_once()
        mock_invoke.assert_called_once()
        if expect_results:
            assert creds == test_creds
        else:
            assert creds is None

    def test_verify_service_principal_pass(
        self, test_data_key_settings="TEST_AZURE_SPECIFIC_SETTINGS"
    ):
        # Test data
        test_creds = self.data[test_data_key_settings]
        test_settings = AzureSpecificSettings.from_dict(test_creds)
        test_list_all_response = []
        test_seed_values = []
        for i in range(3):
            test_ip_response = self.data["TEST_IP_ADDRESS"].copy()
            ip_address = test_ip_response["ip_address"][:-1] + str(i)
            test_ip_response["ip_address"] = ip_address
            test_seed_values.append(ip_address)
            test_list_all_response.append(self.mock_asset(test_ip_response))

        # Mock
        mock_network_client = self.mock_client("NetworkManagementClient")
        mock_public_ips = self.mocker.patch.object(
            mock_network_client.return_value, "public_ip_addresses"
        )
        mock_public_ips.list_all.return_type = "azure.core.paging.ItemPaged[azure.mgmt.network.v2015_06_15.models.PublicIPAddressListResult]"

        # Actual call
        res = self.setup_cli.verify_service_principal(test_settings)

        # Assertions
        mock_network_client.assert_called_once()
        mock_public_ips.list_all.assert_called_once()
        assert res is True

    def test_verify_service_principal_fail(
        self, test_data_key_settings="TEST_AZURE_SPECIFIC_SETTINGS"
    ):
        # Test data
        test_creds = self.data[test_data_key_settings]
        test_settings = AzureSpecificSettings.from_dict(test_creds)
        test_validation_timeout = 4

        # Mock
        self.mocker.patch.object(
            self.setup_cli.settings,
            "validation_timeout",
            return_value=test_validation_timeout,
        )
        mock_network_client = self.mock_client("NetworkManagementClient")
        mock_public_ips = self.mocker.patch.object(
            mock_network_client.return_value, "public_ip_addresses"
        )
        mock_public_ips.list_all.side_effect = HttpResponseError

        # Start timer
        start_time = time.time()

        # Actual call
        res = self.setup_cli.verify_service_principal(test_settings)

        # End timer
        end_time = time.time()

        # Assertions
        mock_public_ips.list_all.assert_called()
        assert (
            end_time - start_time < test_validation_timeout + 1.5
        ), "Timeout exceeded (with 1.5s margin)"
        assert res is not True

    def test_setup_input(self):
        # Mock prompt
        mock_prompt = self.mocker.patch.object(
            self.setup_cli,
            "prompt",
            return_value={"get_credentials_from": "Input existing credentials"},
        )
        mock_setup = self.mocker.patch.object(
            self.setup_cli.__class__.__bases__[0],
            "setup",
        )

        # Actual call
        self.setup_cli.setup()

        # Assertions
        mock_prompt.assert_called_once()
        mock_setup.assert_called_once()

    def test_setup_cli(self):
        # Test data
        test_subscription_id = self.data["TEST_CREDS"]["subscription_id"]
        test_subscriptions = [{"id": test_subscription_id}]
        # Mock prompt
        mock_prompt = self.mocker.patch.object(
            self.setup_cli,
            "prompt",
            return_value={
                "get_credentials_from": "Generate with Azure CLI (Recommended)"
            },
        )
        # Mock get_subscriptions_from_cli
        mock_get_subscriptions = self.mocker.patch.object(
            self.setup_cli, "get_subscriptions_from_cli", return_value=[]
        )
        # Assert exits if no subscriptions are found
        with pytest.raises(SystemExit):
            self.setup_cli.setup()
        mock_get_subscriptions.return_value = test_subscriptions
        # Mock prompt_select_subscriptions
        mock_prompt_select_subscriptions = self.mocker.patch.object(
            self.setup_cli, "prompt_select_subscriptions", return_value=[]
        )
        # Assert exits if no subscriptions are selected
        with pytest.raises(SystemExit):
            self.setup_cli.setup()
        mock_prompt_select_subscriptions.return_value = [
            {"subscription_id": s["id"]} for s in test_subscriptions
        ]
        # Mock create_service_principal
        mock_create_service_principal = self.mocker.patch.object(
            self.setup_cli, "create_service_principal", return_value=None
        )
        # Mock verify_service_principal
        self.mocker.patch.object(
            self.setup_cli, "verify_service_principal", return_value=True
        )
        # Assert exits if no service principal is created
        with pytest.raises(SystemExit):
            self.setup_cli.setup()
        mock_create_service_principal.return_value = self.data["TEST_SERVICE_PRINCIPAL"]
        # Assert no provider settings are created
        assert self.setup_cli.settings.providers[self.setup_cli.provider] == {}

        # Actual call
        self.setup_cli.setup()

        # Assertions
        mock_prompt.assert_called()
        assert len(self.setup_cli.settings.providers[self.setup_cli.provider]) == 1
