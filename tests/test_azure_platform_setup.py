import json
from pathlib import Path
from unittest import TestCase

import pytest
from parameterized import parameterized
from pytest_mock import MockerFixture

from censys.cloud_connectors.azure import __platform_setup__
from censys.cloud_connectors.common.settings import Settings

failed_import = False
try:
    from azure.identity._exceptions import CredentialUnavailableError

except ImportError:
    failed_import = True


@pytest.mark.skipif(failed_import, reason="Azure SDK not installed")
class TestAzurePlatformSetup(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture, shared_datadir: Path):
        self.mocker = mocker
        self.shared_datadir = shared_datadir

    def setUp(self) -> None:
        with open(self.shared_datadir / "test_azure_responses.json") as f:
            self.data = json.load(f)
        self.settings = Settings()
        self.setup_cli = __platform_setup__(self.settings)

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
        mock_info_logger = self.mocker.patch.object(self.setup_cli.logger, "info")

        # Actual call
        subscriptions = self.setup_cli.get_subscriptions_from_cli()

        # Assertions
        assert len(subscriptions) == 0, "No subscriptions should be returned"
        assert mock_info_logger.call_count == 1
        assert mock_info_logger.call_args[0][0] == expected_message, "Wrong message"

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
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.azure.platform_setup.prompt"
        )
        mock_selected_ids = ["subscription_0", "subscription_1", "subscription_2"]
        mock_prompt.return_value = {"subscription_ids": mock_selected_ids}

        # Actual call
        selected_subscriptions = self.setup_cli.prompt_select_subscriptions(
            test_subscriptions
        )

        # Assertions
        assert mock_prompt.call_count == 1
        assert len(selected_subscriptions) == len(mock_selected_ids)
        for subscription in selected_subscriptions:
            assert subscription["subscription_id"] in mock_selected_ids

    @parameterized.expand(
        [
            ([{"id": "subscriptions/subscription_0"}], "subscriptions/subscription_0"),
            (
                [
                    {"id": "subscriptions/subscription_0"},
                    {"id": "subscriptions/subscription_1"},
                ],
                "subscriptions/subscription_0 subscriptions/subscription_1",
            ),
        ]
    )
    def test_generate_create_command(self, subscriptions: list, partial_command: str):
        # Actual call
        sp_command = self.setup_cli.generate_create_command(subscriptions)

        # Assertions
        assert sp_command.startswith("az ad sp create-for-rbac")
        assert "--scopes " + partial_command in sp_command

    @parameterized.expand(
        [
            (0, True),
            (1, False),
        ]
    )
    def test_create_service_principal(self, return_code: int, expect_results: bool):
        # Test data
        test_subscriptions = [{"id": "subscriptions/subscription_0"}]

        # Mock prompt
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.azure.platform_setup.prompt",
            return_value={"create_service_principal": True},
        )
        mock_run = self.mocker.patch(
            "censys.cloud_connectors.azure.platform_setup.subprocess.run"
        )
        mock_run.return_value.returncode = return_code
        mock_creds = {"test_service_principal": "test_secret"}
        mock_run.return_value.stdout = json.dumps(mock_creds)

        # Actual call
        creds = self.setup_cli.create_service_principal(test_subscriptions)

        # Assertions
        mock_prompt.assert_called_once()
        mock_run.assert_called_once()
        if expect_results:
            assert creds == mock_creds
        else:
            assert creds is None

    def test_setup_input(self):
        # Mock prompt
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.azure.platform_setup.prompt",
            return_value={"get_credentials_from": "Input"},
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
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.azure.platform_setup.prompt",
            return_value={"get_credentials_from": "CLI"},
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
        # Assert exits if no service principal is created
        with pytest.raises(SystemExit):
            self.setup_cli.setup()
        mock_create_service_principal.return_value = self.data["TEST_SERVICE_PRINCIPAL"]
        # Assert no platform settings are created
        assert self.setup_cli.settings.platforms[self.setup_cli.platform] == []

        # Actual call
        self.setup_cli.setup()

        # Assertions
        mock_prompt.assert_called()
        assert len(self.setup_cli.settings.platforms[self.setup_cli.platform]) == 1