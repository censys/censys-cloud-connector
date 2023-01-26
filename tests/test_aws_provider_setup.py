import json
from unittest import TestCase

import pytest

from censys.cloud_connectors.aws_connector import __provider_setup__
from censys.cloud_connectors.aws_connector.enums import AwsMessages
from censys.cloud_connectors.aws_connector.settings import AwsSpecificSettings
from censys.cloud_connectors.common.settings import Settings
from tests.base_case import BaseCase

failed_import = False
try:
    from botocore.exceptions import ClientError
except ImportError:
    failed_import = True


@pytest.mark.skipif(failed_import, reason="AWS SDK not installed")
class TestAwsProvidersSetup(BaseCase, TestCase):
    def setUp(self) -> None:
        super().setUp()
        with open(self.shared_datadir / "test_aws_cli_responses.json") as f:
            self.data = json.load(f)
        self.settings = Settings(**self.default_settings)

        self.mocked_logger = self.mocker.MagicMock()
        self.aws = self.mocker.MagicMock()
        self.setup_cli = __provider_setup__(self.settings, self.aws)

    def test_setup(self):
        mock_prompt = self.mocker.patch.object(
            self.setup_cli,
            "prompt",
            return_value={"detect_accounts": "Generate with AWS CLI (Recommended)"},
        )
        self.setup_cli.setup()
        mock_prompt.assert_called()

    def test_detect_accounts_creates_provider_settings(self):
        self.mocker.patch.object(self.setup_cli, "prompt", return_value={})
        self.mocker.patch.object(
            self.setup_cli, "select_profile", return_value="test-profile"
        )
        self.mocker.patch.object(
            self.setup_cli, "ask_primary_account", return_value="123456789012"
        )
        self.mocker.patch.object(
            self.setup_cli, "ask_load_credentials", return_value=True
        )
        self.mocker.patch.object(
            self.setup_cli.aws,
            "get_session_credentials",
            return_value=self.data["TEST_SESSION_CREDENTIALS"],
        )
        self.mocker.patch.object(
            self.setup_cli, "ask_role_name", return_value="test-role"
        )
        self.mocker.patch.object(
            self.setup_cli, "ask_role_session_name", return_value="test-session-name"
        )
        self.mocker.patch.object(
            self.setup_cli, "ask_regions", return_value=["test-region"]
        )
        self.mocker.patch.object(self.setup_cli, "prompt_confirm", return_value=True)
        self.mocker.patch.object(
            self.setup_cli, "ask_account_lookup_method", return_value=["111111222222"]
        )
        self.mocker.patch.object(self.setup_cli, "print_role_creation_instructions")

        mocked_add = self.mocker.patch.object(
            self.setup_cli, "add_provider_specific_settings"
        )

        self.setup_cli.detect_accounts()
        test_data = AwsSpecificSettings.from_dict(self.data["TEST_DETECT_ACCOUNTS"])
        # TODO: there's a bug; provider_name.title() changes this to `Aws`
        test_data.provider = "AWS"
        mocked_add.assert_called_once_with(test_data)

    def test_verify_settings(self):
        settings = AwsSpecificSettings.from_dict(self.data["TEST_VERIFY_SETTINGS"])

        validate_account = self.mocker.patch.object(
            self.setup_cli.aws, "validate_account", return_value=True
        )

        assert self.setup_cli.verify_settings(settings)

        validate_account.assert_called_once_with(
            self.data["TEST_VERIFY_SETTINGS_PRIMARY"]
        )

    def test_verify_settings_failure_prompts_confirm_or_exit(self):
        self.mocker.patch.object(
            self.setup_cli.aws, "validate_account", return_value=False
        )
        confirm = self.mocker.patch.object(self.setup_cli, "confirm_or_exit")
        self.setup_cli.verify_settings(
            AwsSpecificSettings.from_dict(self.data["TEST_VERIFY_SETTINGS"])
        )
        confirm.assert_called_once()

    def test_verify_settings_exception(self):
        self.mocker.patch.object(
            self.setup_cli.aws, "validate_account", side_effect=Exception()
        )
        error = self.mocker.patch.object(self.setup_cli, "print_error")
        confirm = self.mocker.patch.object(self.setup_cli, "confirm_or_exit")
        self.setup_cli.verify_settings(
            AwsSpecificSettings.from_dict(self.data["TEST_VERIFY_SETTINGS"])
        )
        error.assert_called_once()
        confirm.assert_called_once()

    def test_select_profile_uses_aws_profile(self):
        choices = ["test", "test2"]
        profile = "test-profile"
        env = self.mocker.patch("os.getenv", return_value=profile)
        self.mocker.patch.object(
            self.setup_cli, "get_profile_choices", return_value=choices
        )
        select = self.mocker.patch.object(self.setup_cli, "prompt_select_one")

        self.setup_cli.select_profile()
        env.assert_called_once_with("AWS_PROFILE")
        select.assert_called_once_with(
            AwsMessages.PROMPT_SELECT_PROFILE, choices, default=profile
        )

    def test_get_profile_choices(self):
        self.mocker.patch.object(
            self.setup_cli.aws,
            "available_profiles",
            return_value=["test-profile-1", "test-profile-2"],
        )
        choices = self.setup_cli.get_profile_choices()
        assert choices == self.data["TEST_PROFILE_CHOICES"]

    def test_provider_accounts(self):
        ids = ["111111111111", "222222222222"]
        role = "test-role"
        role_session_name = "test-role-session-name"
        res = self.setup_cli.provider_accounts(ids, role, role_session_name)
        assert res == self.data["TEST_PROVIDER_ACCOUNTS"]

    def test_ask_regions(self):
        answer = self.data["TEST_REGIONS"]
        self.mocker.patch.object(self.setup_cli, "prompt", return_value=answer)
        regions = self.setup_cli.ask_regions()
        self.setup_cli.aws.get_regions.assert_called_once()
        assert regions == answer["regions"]

    def test_ask_role_name_no(self):
        self.mocker.patch.object(self.setup_cli, "prompt_confirm", return_value=False)
        no = self.setup_cli.ask_role_name()
        assert no == ""

    def test_ask_role_name(self):
        answer = self.data["TEST_ASK_ROLE_PROMPT"]
        self.mocker.patch.object(self.setup_cli, "prompt_confirm", return_value=True)
        self.mocker.patch.object(self.setup_cli, "prompt", return_value=answer)
        role = self.setup_cli.ask_role_name()
        assert role == answer["answer"]

    def test_get_account_choices_org_not_in_use(self):
        err = ClientError(
            error_response=self.data["TEST_LIST_ACCOUNTS_ERROR"],
            operation_name="list_accounts",
        )
        self.mocker.patch.object(
            self.setup_cli.aws,
            "get_organization_list_accounts",
            side_effect=err,
        )
        warning = self.mocker.patch.object(self.setup_cli, "print_warning")
        confirm = self.mocker.patch.object(self.setup_cli, "confirm_or_exit")
        self.setup_cli.get_account_choices(0)
        warning.assert_called_once()
        confirm.assert_called_once()

    def test_ask_list_accounts_handles_no_accounts(self):
        self.mocker.patch.object(
            self.setup_cli, "get_account_choices", return_value=None
        )
        confirm = self.mocker.patch.object(self.setup_cli, "confirm_or_exit")
        self.mocker.patch.object(self.setup_cli, "prompt", return_value=[])

        accounts = self.setup_cli.ask_list_accounts(0)

        confirm.assert_called_once_with(AwsMessages.PROMPT_NO_ACCOUNTS_FOUND.value)
        assert accounts == []

    def test_get_account_choices_error(self):
        self.mocker.patch.object(
            self.setup_cli.aws,
            "get_organization_list_accounts",
            side_effect=Exception(),
        )
        error = self.mocker.patch.object(self.setup_cli, "print_error")
        confirm = self.mocker.patch.object(self.setup_cli, "confirm_or_exit")
        self.setup_cli.get_account_choices(0)
        error.assert_called_once()
        confirm.assert_called_once()

    def test_get_account_choices(self):
        self.mocker.patch.object(
            self.setup_cli.aws,
            "get_organization_list_accounts",
            return_value=self.data["TEST_LIST_ACCOUNTS"],
        )
        expected = self.data["TEST_LIST_ACCOUNTS"]
        choices = self.setup_cli.get_account_choices(0)
        assert choices == expected

    def test_confirm_or_exit(self):
        mock = self.mocker.patch.object(self.setup_cli, "prompt_confirm")
        self.setup_cli.confirm_or_exit("test-message")
        mock.assert_called_once_with("test-message", default=False)

    def test_confirm_or_exit_exits(self):
        self.mocker.patch.object(self.setup_cli, "prompt_confirm", return_value=False)
        with pytest.raises(SystemExit):
            self.setup_cli.confirm_or_exit("test-message")

    def test_ask_account_lookup_method(self):
        primary_id = 111
        ask_list_accounts = self.mocker.patch.object(
            self.setup_cli, "ask_list_accounts"
        )
        self.mocker.patch.object(
            self.setup_cli,
            "prompt",
            return_value={"answer": "Find by Organization List Accounts"},
        )
        self.setup_cli.ask_account_lookup_method(primary_id)
        ask_list_accounts.assert_called_once_with(primary_id)

    def test_ask_stackset(self):
        self.mocker.patch.object(
            self.setup_cli, "ask_stack_set_name", return_value="test-stackset"
        )
        self.mocker.patch.object(self.setup_cli.aws, "get_stackset_accounts")
        self.mocker.patch.object(
            self.setup_cli, "prompt", return_value={"accounts": ["111", "222"]}
        )
        accounts = self.setup_cli.ask_stackset(0)
        assert accounts == ["111", "222"]

    def test_ask_stackset_error(self):
        self.mocker.patch.object(
            self.setup_cli, "ask_stack_set_name", return_value="test-stackset"
        )
        self.mocker.patch.object(
            self.setup_cli.aws, "get_stackset_accounts", side_effect=Exception()
        )
        error = self.mocker.patch.object(self.setup_cli, "print_error")
        confirm = self.mocker.patch.object(self.setup_cli, "confirm_or_exit")
        stacks = self.setup_cli.ask_stackset(0)
        assert stacks == []
        error.assert_called_once()
        confirm.assert_called_once()

    def test_ask_stackset_handles_no_accounts(self):
        self.mocker.patch.object(self.setup_cli, "ask_stack_set_name")
        self.mocker.patch.object(
            self.setup_cli.aws, "get_stackset_accounts", return_value=[]
        )
        confirm = self.mocker.patch.object(self.setup_cli, "confirm_or_exit")
        self.mocker.patch.object(self.setup_cli, "prompt", return_value=[])

        accounts = self.setup_cli.ask_stackset(0)

        confirm.assert_called_once_with(AwsMessages.PROMPT_NO_ACCOUNTS_FOUND.value)
        assert accounts == []

    def test_print_role_creation_instructions(self):
        info = self.mocker.patch.object(self.setup_cli, "print_info")
        confirm = self.mocker.patch.object(self.setup_cli, "confirm_or_exit")
        self.setup_cli.print_role_creation_instructions("test-role")
        info.assert_called()
        confirm.assert_called_once()

    def test_ask_key_credentials_errors_on_token(self):
        test_creds = self.data["TEST_SESSION_CREDENTIALS_WITH_TOKEN"].copy()
        self.mocker.patch.object(
            self.setup_cli, "ask_load_credentials", return_value=True
        )
        self.mocker.patch.object(
            self.setup_cli.aws, "get_session_credentials", return_value=test_creds
        )
        mock_print_error = self.mocker.patch.object(self.setup_cli, "print_error")

        with pytest.raises(SystemExit):
            self.setup_cli.ask_key_credentials("test-temporary-token-profile")

        mock_print_error.assert_called_once_with(
            AwsMessages.TEMPORARY_CREDENTIAL_ERROR.value
        )

    def test_ask_key_credentials(self):
        test_creds = self.data["TEST_SESSION_CREDENTIALS"].copy()
        self.mocker.patch.object(
            self.setup_cli, "ask_load_credentials", return_value=True
        )
        self.mocker.patch.object(
            self.setup_cli.aws, "get_session_credentials", return_value=test_creds
        )
        access_key, secret_key = self.setup_cli.ask_key_credentials("test-profile")
        assert access_key == test_creds["access_key"]
        assert secret_key == test_creds["secret_key"]

    def test_ask_key_credentials_no_load(self):
        test_access = "test-access-key"
        test_secret = "test-secret-key"
        self.mocker.patch.object(
            self.setup_cli, "ask_load_credentials", return_value=False
        )
        self.mocker.patch.object(
            self.setup_cli, "ask_access_key", return_value=test_access
        )
        self.mocker.patch.object(
            self.setup_cli, "ask_secret_key", return_value=test_secret
        )
        access_key, secret_key = self.setup_cli.ask_key_credentials("test-profile")
        assert access_key == test_access
        assert secret_key == test_secret
