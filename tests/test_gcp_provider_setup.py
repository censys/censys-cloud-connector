import json
from typing import Optional
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

    @parameterized.expand([("TEST_ACCOUNTS"), ("TEST_ACCOUNTS_NONE_ACTIVE")])
    def test_get_accounts_from_cli(self, test_data_key: str):
        # Test data
        command = "gcloud auth list --format=json"
        expected_accounts: list[dict[str, str]] = self.data[test_data_key]
        test_cli_response = json.dumps(expected_accounts)

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = test_cli_response

        # Actual call
        actual = self.setup_cli.get_accounts_from_cli()

        # Assertions
        assert actual == expected_accounts
        mock_run.assert_called_once_with(command)

    @parameterized.expand(
        [
            ("TEST_ACCOUNTS"),
            ("TEST_ACCOUNTS_NONE_ACTIVE"),
        ]
    )
    def test_prompt_select_account_from_multiple(self, test_data_key: str):
        # Test data
        test_accounts: list[dict[str, str]] = self.data[test_data_key]
        test_selected_account = {
            "account": test_accounts[0]["account"],
            "status": test_accounts[0]["status"],
        }

        # Mock
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt")
        mock_prompt.return_value = {"selected_account": test_selected_account}

        # Actual call
        selected_account = self.setup_cli.prompt_select_account(test_accounts)

        # Assertions
        mock_prompt.assert_called_once()
        assert selected_account == test_selected_account

    @parameterized.expand(
        [
            ("TEST_ACCOUNTS_ONE_ACTIVE"),
            ("TEST_ACCOUNTS_ONE_INACTIVE"),
        ]
    )
    def test_prompt_select_account_from_one(self, test_data_key: str):
        # Test data
        test_accounts: list[dict[str, str]] = self.data[test_data_key]
        test_selected_account = {
            "account": test_accounts[0]["account"],
            "status": test_accounts[0]["status"],
        }

        # Mock
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt")
        mock_prompt.return_value = {"use_account": test_selected_account}

        # Actual call
        selected_account = self.setup_cli.prompt_select_account(test_accounts)

        # Assertions
        mock_prompt.assert_called_once()
        assert selected_account == test_selected_account

    @parameterized.expand(
        [
            (0, "censys-example-project", "TEST_PROJECTS"),
            (1, None, "TEST_PROJECTS_EMPTY"),
        ]
    )
    def test_get_project_id_from_cli(
        self, returncode: int, project_name, test_data_key: str
    ):
        # Test data
        command = "gcloud config get-value project"
        expected_proj_id: str = self.data[test_data_key]

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = expected_proj_id

        # Actual call
        actual = self.setup_cli.get_project_id_from_cli()

        # Assertions
        assert actual == project_name
        mock_run.assert_called_once_with(command)

    @parameterized.expand(
        [
            (0, "TEST_PROJECTS", "TEST_ORGANIZATIONS"),
        ]
    )
    def test_get_organization_id_from_cli(
        self, returncode: int, test_proj_data_key: str, test_org_data_key: str
    ):
        # Test data
        test_proj_id: str = self.data[test_proj_data_key]
        command = f"gcloud projects get-ancestors {test_proj_id} --format=json"
        expected_org_info: list[dict[str, str]] = self.data[test_org_data_key]
        expected_org_info_json = json.dumps(expected_org_info)
        expected_org = "502839482099"

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = expected_org_info_json

        # Actual call
        actual = self.setup_cli.get_organization_id_from_cli(test_proj_id)

        # Assertions
        assert actual == expected_org
        mock_run.assert_called_once_with(command)

    @parameterized.expand(
        [
            (1, "TEST_PROJECTS", None),
        ]
    )
    def test_get_organization_id_from_cli_failure(
        self, returncode: int, test_proj_data_key: str, returnval
    ):
        # Test data
        test_proj_id: str = self.data[test_proj_data_key]
        command = f"gcloud projects get-ancestors {test_proj_id} --format=json"
        expected_warning = "Unable to get organization id from CLI."

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = expected_warning

        # Actual call
        actual = self.setup_cli.get_organization_id_from_cli(test_proj_id)

        # Assertions
        assert actual == returnval
        mock_run.assert_called_once_with(command)

    @parameterized.expand([(0, None), (1, "Unable to switch active account")])
    def test_switch_active_cli_account(self, returncode: int, returnmessage):
        # Test data
        account_name = "censys-test@censys.io"
        command = f"gcloud config set account {account_name}"

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = returnmessage

        # Actual call
        self.setup_cli.switch_active_cli_account(account_name)

        # Assertions
        mock_run.assert_called_once_with(command)

    @parameterized.expand(
        [
            ("TEST_PROJECTS", "TEST_SERVICE_ACCOUNTS"),
            ("TEST_PROJECTS_EMPTY", "TEST_SERVICE_ACCOUNTS"),
        ]
    )
    def test_get_service_accounts_from_cli(
        self, test_data_key_proj: str, test_data_key_service: str
    ):
        # Test data
        command = "gcloud iam service-accounts list --format json"
        test_proj_id: Optional[str] = self.data[test_data_key_proj]
        expected_service_accounts = self.data[test_data_key_service]
        expected_output = json.dumps(expected_service_accounts)

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.stdout = expected_service_accounts

        # Actual call
        actual = self.setup_cli.get_service_accounts_from_cli(test_proj_id)

        # Assertions
        assert actual == expected_output
        mock_run.assert_called_once_with(command)

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
