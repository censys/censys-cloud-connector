import json
from unittest import TestCase

import pytest
from parameterized import parameterized

from censys.cloud_connectors.common.settings import Settings
from censys.cloud_connectors.gcp import __provider_setup__
from tests.base_case import BaseCase

failed_import = False
try:
    pass
except ImportError:
    failed_import = True


@pytest.mark.skipif(failed_import, reason="Gcloud SDK not installed")
class TestGcpProviderSetup(BaseCase, TestCase):
    data: dict

    def setUp(self):
        super().setUp()
        with open(self.shared_datadir / "test_gcp_cli_responses.json") as f:
            self.data = json.load(f)
        self.settings = Settings(censys_api_key=self.consts["censys_api_key"])
        self.setup_cli = __provider_setup__(self.settings)

    @parameterized.expand(
        [
            (0, True),
            (1, False),
        ]
    )
    def test_is_gcloud_installed(self, returncode: int, expected: bool):
        # Test data
        command = "gcloud version"

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode

        # Actual call
        actual = self.setup_cli.is_gcloud_installed()

        # Assertions
        assert actual == expected
        mock_run.assert_called_once_with(command)

    def test_get_accounts_from_cli(self):
        # Test data
        expected_accounts = self.data["TEST_ACCOUNTS"]
        test_cli_response = json.dumps(expected_accounts)

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = test_cli_response

        # Actual call
        actual = self.setup_cli.get_accounts_from_cli()

        # Assertions
        assert actual == expected_accounts

    def test_prompt_select_account(self):
        pass

    def test_get_project_id_from_cli(self):
        pass

    def test_get_organization_id_from_cli(self):
        pass

    def test_switch_active_cli_account(self):
        pass

    def test_get_service_accounts_from_cli(self):
        pass

    def test_prompt_select_service_account(self):
        pass

    def test_generate_service_account_email(self):
        pass

    def test_generate_role_binding_command(self):
        pass

    def test_generate_create_service_account_command(self):
        pass

    def test_generate_create_key_command(self):
        pass

    def test_create_service_account(self):
        pass

    def test_check_correct_permissions(self):
        pass

    def test_generate_enable_service_account_command(self):
        pass

    def test_enable_service_account(self):
        pass
