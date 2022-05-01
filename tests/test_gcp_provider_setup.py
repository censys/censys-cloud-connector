import json
from typing import Optional
from unittest import TestCase

import pytest
from parameterized import parameterized

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import Settings
from censys.cloud_connectors.gcp_connector import __provider_setup__
from censys.cloud_connectors.gcp_connector.enums import GcpRoles
from censys.cloud_connectors.gcp_connector.settings import GcpSpecificSettings
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
        self.settings = Settings(
            censys_api_key=self.consts["censys_api_key"],
            secrets_dir=str(self.shared_datadir),
        )
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

    @parameterized.expand([("TEST_ACCOUNTS"), ("TEST_EMPTY_LIST")])
    def test_get_accounts_from_cli(self, test_data_key: str, returncode: int = 0):
        # Test data
        expected_accounts: list[dict[str, str]] = self.data[test_data_key]

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = json.dumps(expected_accounts)

        # Actual call
        actual = self.setup_cli.get_accounts_from_cli()

        # Assertions
        assert actual == expected_accounts
        mock_run.assert_called_once_with("gcloud auth list --format json")

    def test_get_accounts_from_cli_failure(self):
        # Test data
        expected_accounts = None
        returncode = 1

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = json.dumps(expected_accounts)

        # Actual call
        actual = self.setup_cli.get_accounts_from_cli()

        # Assertions
        assert actual == expected_accounts
        mock_run.assert_called_once_with("gcloud auth list --format json")

    @parameterized.expand(
        [
            ("TEST_ACCOUNTS"),
            ("TEST_ACCOUNTS_NONE_ACTIVE"),
        ]
    )
    def test_prompt_select_account_from_multiple(self, test_data_key: str):
        # Test data
        test_accounts: list[dict[str, str]] = self.data[test_data_key]

        # Mock
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt_select_one")
        mock_prompt.return_value = test_accounts[0]

        # Actual call
        selected_account = self.setup_cli.prompt_select_account(test_accounts)

        # Assertions
        mock_prompt.assert_called_once()
        assert selected_account == mock_prompt.return_value

    @parameterized.expand(
        [
            ("TEST_ACCOUNTS_ONE_ACTIVE"),
            ("TEST_ACCOUNTS_ONE_INACTIVE"),
        ]
    )
    def test_prompt_select_account_from_one(self, test_data_key: str):
        # Test data
        test_accounts: list[dict[str, str]] = self.data[test_data_key]

        # Mock
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt_select_one")
        mock_prompt.return_value = test_accounts[0]

        # Actual call
        selected_account = self.setup_cli.prompt_select_account(test_accounts)

        # Assertions
        mock_prompt.assert_called_once()
        assert selected_account == mock_prompt.return_value

    def test_prompt_select_account_none(self):
        # Test data
        test_accounts: list[dict[str, str]] = self.data["TEST_ACCOUNTS"]

        # Mock
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt_select_one")
        mock_prompt.return_value = None

        # Actual call
        selected_account = self.setup_cli.prompt_select_account(test_accounts)

        # Assertions
        mock_prompt.assert_called_once()
        assert selected_account == mock_prompt.return_value

    @parameterized.expand(
        [
            (0, "TEST_PROJECTS"),
        ]
    )
    def test_get_project_ids_from_cli(self, returncode: int, test_data_key: str):
        # Test data
        expected_projects: list[dict[str, str]] = self.data[test_data_key]

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = json.dumps(expected_projects)

        # Actual call
        actual = self.setup_cli.get_project_ids_from_cli()

        # Assertions
        assert actual == expected_projects
        mock_run.assert_called_once_with("gcloud projects list --format json")

    def test_get_project_ids_from_cli_fail(self):
        # Test data
        expected_projects = None

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = json.dumps(expected_projects)

        # Actual call
        actual = self.setup_cli.get_project_ids_from_cli()

        # Assertions
        assert actual == expected_projects
        mock_run.assert_called_once_with("gcloud projects list --format json")

    @parameterized.expand(
        [
            (0, "censys-example-project", "TEST_PROJECT"),
            (1, None, "TEST_EMPTY_STR"),
        ]
    )
    def test_get_default_project_id_from_cli(
        self, returncode: int, project_name, test_data_key: str
    ):
        # Test data
        expected_proj_id: str = self.data[test_data_key]

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = expected_proj_id

        # Actual call
        actual = self.setup_cli.get_default_project_id_from_cli()

        # Assertions
        mock_run.assert_called_once_with("gcloud config get-value project")
        assert actual == project_name

    @parameterized.expand(["TEST_PROJECTS"])
    def test_prompt_select_project(self, test_data_key: str):
        # Test data
        test_projects: list[dict[str, str]] = self.data[test_data_key]
        test_default_id = test_projects[0]["projectId"]

        # Mock
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt_select_one")
        mock_prompt.return_value = test_projects[0]

        # Actual call
        selected_project = self.setup_cli.prompt_select_project(
            test_projects, test_default_id
        )

        # Assertions
        mock_prompt.assert_called_once()
        assert selected_project == mock_prompt.return_value

    @parameterized.expand(
        [
            ("TEST_PROJECT", "TEST_ORGANIZATION"),
        ]
    )
    def test_get_organization_id_from_cli(
        self, test_proj_data_key: str, test_org_data_key: str, returncode: int = 0
    ):
        # Test data
        test_proj_id: str = self.data[test_proj_data_key]
        expected_org_info: list[dict[str, str]] = self.data[test_org_data_key]
        expected_org_info_json = json.dumps(expected_org_info)
        expected_org = 502839482099

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = expected_org_info_json

        # Actual call
        actual = self.setup_cli.get_organization_id_from_cli(test_proj_id)

        # Assertions
        mock_run.assert_called_once_with(
            f"gcloud projects get-ancestors {test_proj_id} --format json"
        )
        assert actual == expected_org

    @parameterized.expand(
        [
            ("TEST_PROJECT", "TEST_EMPTY_STR", 1),
            ("TEST_PROJECT", "TEST_EMPTY_LIST", 0),
            ("TEST_PROJECT", "TEST_ORGANIZATION_EMPTY", 0),
        ]
    )
    def test_get_organization_id_from_cli_failure(
        self, test_proj_data_key: str, test_out_data_key: str, returncode: int = 0
    ):
        # Test data
        test_proj_id: str = self.data[test_proj_data_key]
        test_out_data = self.data[test_out_data_key]
        test_out_data_json = json.dumps(test_out_data)

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = test_out_data_json

        # Actual call
        actual = self.setup_cli.get_organization_id_from_cli(test_proj_id)

        # Assertions
        mock_run.assert_called_once_with(
            f"gcloud projects get-ancestors {test_proj_id} --format json"
        )
        assert actual is None, "Should return None if no organization id found."

    @parameterized.expand([(0, None), (1, "Unable to switch active account")])
    def test_switch_active_cli_account(self, returncode: int, returnmessage):
        # Test data
        account_name = "censys-test@censys.io"

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = returnmessage

        # Actual call
        self.setup_cli.switch_active_cli_account(account_name)

        # Assertions
        mock_run.assert_called_once_with(f"gcloud config set account {account_name}")

    @parameterized.expand(
        [
            ("TEST_PROJECT", "TEST_SERVICE_ACCOUNTS"),
            ("TEST_EMPTY_STR", "TEST_SERVICE_ACCOUNTS"),
            ("TEST_EMPTY_STR", "TEST_EMPTY_LIST"),
        ]
    )
    def test_get_service_accounts_from_cli(
        self, test_data_key_proj: str, test_data_key_service: str, returncode: int = 0
    ):
        # Test data
        test_command = "gcloud iam service-accounts list --format json"
        test_proj_id: Optional[str] = self.data[test_data_key_proj]
        if test_proj_id:
            test_command += f" --project {test_proj_id}"
        expected_service_accounts = self.data[test_data_key_service]

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = json.dumps(expected_service_accounts)

        # Actual call
        actual = self.setup_cli.get_service_accounts_from_cli(test_proj_id)

        # Assertions
        mock_run.assert_called_once_with(test_command)
        assert actual == expected_service_accounts

    def test_get_service_accounts_from_cli_failure(self):
        # Test data
        test_command = "gcloud iam service-accounts list --format json"
        expected_service_accounts = None
        returncode = 1

        # Mock
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode
        mock_run.return_value.stdout = expected_service_accounts

        # Actual call
        actual = self.setup_cli.get_service_accounts_from_cli()

        # Assertions
        mock_run.assert_called_once_with(test_command)
        assert actual == expected_service_accounts

    @parameterized.expand(
        [
            (
                222222222222,
                "test2-service-account@domain.com",
                "TEST_GCP_SPECIFIC_SETTINGS",
                "test_gcp_service_account.json",
            ),
            (
                333333333333,
                "test3-service-account@domain.com",
                "TEST_GCP_SPECIFIC_SETTINGS",
            ),
        ]
    )
    def test_get_current_key_file_path(
        self,
        test_organization_id: int,
        test_service_account_email: str,
        test_data_key_settings: str,
        return_val: Optional[str] = None,
    ):
        # Test data
        if return_val:
            test_creds = self.data[test_data_key_settings]
            if service_account_json_file := test_creds.get("service_account_json_file"):
                test_creds["service_account_json_file"] = service_account_json_file
            test_settings = GcpSpecificSettings.from_dict(test_creds)
        else:
            test_settings = None
        test_provider_config: dict[tuple, GcpSpecificSettings] = {
            (test_organization_id, test_service_account_email): test_settings
        }

        # Mock
        self.mocker.patch.dict(
            self.setup_cli.settings.providers[ProviderEnum.GCP], test_provider_config
        )

        # Actual call
        actual = self.setup_cli.get_current_key_file_path(
            test_organization_id, test_service_account_email
        )

        # Assertions
        assert actual == return_val

    def test_generate_service_account_email(self):
        # Test data
        test_name = "service-account-name"
        test_project = self.data["TEST_PROJECT"]
        expected_email = self.data["TEST_SERVICE_ACCOUNT_EMAIL"]

        # Actual call
        actual = self.setup_cli.generate_service_account_email(test_name, test_project)

        # Assertions
        assert actual == expected_email

    def test_generate_role_binding_command(self):
        # Test data
        test_organization_id = 6543219870
        test_service_account_email = self.data["TEST_SERVICE_ACCOUNT_EMAIL"]
        test_roles = list(GcpRoles)

        # Actual call
        actual_commands = self.setup_cli.generate_role_binding_command(
            test_organization_id, test_service_account_email, test_roles
        )

        # Assertions
        assert actual_commands[0].startswith("# "), "Should be a comment."
        for i, role in enumerate(test_roles):
            current_command = actual_commands[i + 1]
            assert current_command.startswith(
                "gcloud organizations add-iam-policy-binding "
            )
            assert str(test_organization_id) in current_command
            assert f"'serviceAccount:{test_service_account_email}'" in current_command
            assert f"--role '{role}'" in current_command

    def test_generate_create_service_account_command(self):
        # Test data
        test_name = "test-service-account"
        test_display_name = "Test Display Name"

        # Actual call
        actual_command = self.setup_cli.generate_create_service_account_command(
            test_name, test_display_name
        )

        # Assertions
        assert test_name in actual_command
        assert f"--display-name '{test_display_name}'" in actual_command

    def test_generate_create_key_command(self):
        pass

    @parameterized.expand(
        [
            (
                True,
                True,
            ),
            (False,),
            (True, False, 1),
        ]
    )
    def test_create_service_account(
        self,
        confirmation_answer: bool = True,
        expected_return: bool = False,
        return_code: int = 0,
    ):
        # Test data
        test_organization_id = 6549873210
        test_project_id = "test-project-id"
        test_service_account_name = "test-service-account"
        test_key_file_path = "test-project-key.json"

        # Mock
        mock_print_command = self.mocker.patch.object(self.setup_cli, "print_command")
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt")
        mock_prompt.return_value = {"create_service_account": confirmation_answer}
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = return_code

        # Actual call
        actual_return = self.setup_cli.create_service_account(
            test_organization_id,
            test_project_id,
            test_service_account_name,
            test_key_file_path,
        )

        # Assertions
        mock_print_command.assert_called_once()
        mock_prompt.assert_called_once()
        if confirmation_answer:
            mock_run.assert_called()
        if expected_return:
            assert actual_return == test_key_file_path
        else:
            assert actual_return is None

    def test_check_correct_permissions(self):
        pass

    def test_generate_enable_service_account_command(self):
        pass

    @parameterized.expand(
        [
            (True, True),
            (False, False),
            (True, False, 1),
        ]
    )
    def test_enable_service_account(
        self,
        enable_service_account: bool = True,
        expected_return: bool = True,
        returncode: int = 0,
    ):
        # Test data
        test_organization_id = 6543219870
        test_project_id = "test-project-id"
        test_service_account_name = "test-service-account"
        test_key_file_path = "test-project-key.json"

        # Mock
        mock_print_command = self.mocker.patch.object(self.setup_cli, "print_command")
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt")
        mock_prompt.return_value = {"enable_service_account": enable_service_account}
        mock_run = self.mocker.patch.object(self.setup_cli, "run_command")
        mock_run.return_value.returncode = returncode

        # Actual call
        actual_return = self.setup_cli.enable_service_account(
            test_organization_id,
            test_project_id,
            test_service_account_name,
            test_key_file_path,
        )

        # Assertions
        mock_print_command.assert_called_once()
        mock_prompt.assert_called_once()
        if enable_service_account:
            mock_run.assert_called()
        if expected_return:
            assert actual_return == test_key_file_path
        else:
            assert actual_return is None

    @parameterized.expand(
        [
            (
                "test-service-account",
                {"new_account_name": "test-service-account"},
                "test-project-key.json",
            ),
            ("a", {"new_account_name": ""}, None, "Service account name is required."),
            (
                "test-service-account",
                {"new_account_name": "test-service-account"},
                None,
                "Failed to create service account key file. Please try again.",
            ),
        ]
    )
    def test_prompt_to_create_service_account(
        self,
        test_service_account_name: str,
        prompt_return_val: dict,
        create_account_return_val: Optional[str] = None,
        error_message: str = None,
    ):
        # Test data
        test_organization_id = 6549873210
        test_project_id = "test-project-id"
        expected_email = (
            (
                test_service_account_name
                + "@"
                + test_project_id
                + ".iam.gserviceaccount.com"
            )
            if not error_message
            else ""
        )

        # Mock
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt")
        mock_prompt.return_value = prompt_return_val
        mock_create_service_account = self.mocker.patch.object(
            self.setup_cli, "create_service_account"
        )
        mock_create_service_account.return_value = create_account_return_val

        # Actual call
        actual: str = ""
        if error_message is None:
            actual = self.setup_cli.prompt_to_create_service_account(
                test_organization_id, test_project_id, create_account_return_val
            )
        else:
            with pytest.raises(SystemExit):
                actual = self.setup_cli.prompt_to_create_service_account(
                    test_organization_id, test_project_id, create_account_return_val
                )

        # Assertions
        mock_prompt.assert_called_once()
        if error_message == "Service account name is required.":
            assert mock_create_service_account.call_count == 0
            assert actual == ""
        else:
            mock_create_service_account.assert_called_once()
            assert actual == expected_email
