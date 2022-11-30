from unittest import TestCase

import pytest

from censys.cloud_connectors.aws_connector.settings import (
    AwsAccount,
    AwsSpecificSettings,
)
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import Settings
from tests.base_case import BaseCase


class TestAwsSettings(BaseCase, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.settings = Settings(
            **self.default_settings,
            secrets_dir=str(self.shared_datadir),
        )

    def aws_settings(self, overrides: dict) -> AwsSpecificSettings:
        """Generate a customizable settings object for ease of testing.

        Args:
            overrides (dict): Values here will override defaults.

        Returns:
            AwsSpecificSettings: AWS Settings.
        """
        defaults = {
            "account_number": 123,
            "access_key": "test-access-key",
            "secret_key": "test-secret-key",
            "regions": ["us-east-1"],
        }

        accounts = []
        if "accounts" in overrides:
            for account in overrides["accounts"]:
                accounts.append(AwsAccount(**account))
            overrides["accounts"] = accounts

        settings = defaults | overrides

        return AwsSpecificSettings(
            **settings,
        )

    def get_settings_file(self, file_name) -> list[AwsSpecificSettings]:
        """Read a test providers.yml file.

        Args:
            file_name (str): Filename.

        Returns:
            list[AwsSpecificSettings]: List of AWS provider settings.
        """
        self.settings.providers_config_file = self.shared_datadir / "aws" / file_name
        self.settings.read_providers_config_file([ProviderEnum.AWS])
        provider_settings = self.settings.providers[ProviderEnum.AWS]
        settings: list[AwsSpecificSettings] = list(provider_settings.values())  # type: ignore
        return settings

    def get_credentials(self, file_name) -> list[dict]:
        """Get the AWS credential data from a test providers.yml file.

        Args:
            file_name (str): Filename.

        Returns:
            list[dict]: Credentials.
        """
        settings = self.get_settings_file(file_name)
        setting = settings[0]  # type: ignore
        return list(setting.get_credentials())

    def test_missing_role_and_access_key(self):
        with pytest.raises(ValueError, match="Specify either access_key"):
            AwsSpecificSettings(
                account_number=123,
                regions=["us-east-1"],
            )

    def test_primary_get_credentials(self):
        settings = self.get_settings_file("primary_access_key.yml")
        setting = settings[0]
        credentials = list(setting.get_credentials())
        credential = credentials[0]
        assert len(settings) == 1
        assert len(credentials) == 1
        assert setting.regions == ["test-region"]
        assert credential["account_number"] == 111111111111

    def test_parent_key_child_role_loads_parent_key(self):
        credential = self.get_credentials("accounts_parent_key_child_role.yml")[0]
        assert credential["access_key"] == "example-access-key-1"
        assert credential["secret_key"] == "example-secret-key-1"

    def test_parent_key_child_role_loads_child_role(self):
        credential = self.get_credentials("accounts_parent_key_child_role.yml")[1]
        assert credential["role_name"] == "example-role-2"
        assert credential["account_number"] == 111111111112

    def test_parent_account_with_access_key(self):
        credential = self.get_credentials("accounts_key.yml")[0]
        assert credential["access_key"] == "example-access-key-1"
        assert credential["secret_key"] == "example-secret-key-1"

    def test_child_account_with_access_key(self):
        credential = self.get_credentials("accounts_key.yml")[1]
        assert credential["access_key"] == "example-access-key-2"
        assert credential["secret_key"] == "example-secret-key-2"

    def test_ecs_parent_account_with_role(self):
        credential = self.get_credentials("ecs.yml")[0]
        assert credential["role_name"] == "example-role-1"
        assert credential["role_session_name"] == "censys-cloud-connector"

    def test_ecs_child_account_with_role(self):
        credential = self.get_credentials("ecs.yml")[1]
        assert credential["role_name"] == "example-role-2"
        assert credential["role_session_name"] == "censys-cloud-connector"

    def test_accounts_minimum_required_fields(self):
        settings = self.get_settings_file("accounts_inherit.yml")
        setting = settings[0]
        credentials = list(setting.get_credentials())
        assert len(settings) == 1
        assert len(credentials) == 3

    def test_accounts_get_credentials_enumerates_all(self):
        setting = self.get_settings_file("accounts_inherit.yml")[0]
        for cred in setting.get_credentials():
            assert cred["account_number"] in [111111111111, 111111111112, 111111111113]

    def test_accounts_inherit_from_primary(self):
        expected = {
            "account_number": 111111111112,
            "access_key": None,
            "secret_key": None,
            "role_name": "test-primary-role-name",
            "role_session_name": "test-primary-role-session-name",
            "ignore_tags": ["test-primary-ignore-tag-1"],
        }
        credential = self.get_credentials("accounts_inherit.yml")[1]
        assert credential == expected

    def test_accounts_override_primary_values(self):
        expected = {
            "account_number": 111111111112,
            "access_key": None,
            "secret_key": None,
            "role_name": "test-override-role",
            "role_session_name": "test-override-session-name",
            "ignore_tags": ["test-override-ignore-tag-1"],
        }
        credential = self.get_credentials("accounts_override.yml")[1]
        assert credential == expected

    def test_accounts_do_not_inherit_keys(self):
        credential = self.get_credentials("accounts_override.yml")[1]
        assert credential["access_key"] is None
        assert credential["secret_key"] is None

    def test_provider_key(self):
        account = "123123123"
        expected = (account,)
        settings = self.aws_settings({"account_number": account})
        assert settings.get_provider_key() == expected

    def test_ignore_tags_provider(self):
        expected = ["test-provider-ignore-tag"]
        settings = self.aws_settings(
            {
                "ignore_tags": expected,
            }
        )
        creds = next(settings.get_credentials())
        assert creds["ignore_tags"] == expected

    def test_ignore_tags_account_overrides_provider(self):
        child = {
            "account_number": 112,
            "ignore_tags": ["test-account-ignore-tag"],
        }
        primary = {
            "ignore_tags": ["test-primary-ignore-tag"],
            "accounts": [child],
        }
        settings = self.aws_settings(primary)
        creds = list(settings.get_credentials())
        assert creds[0]["ignore_tags"] == primary["ignore_tags"]
        assert creds[1]["ignore_tags"] == child["ignore_tags"]
