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
            "account_number": "123123123123",
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

    def test_missing_role_and_access_key(self):
        with pytest.raises(ValueError, match="Specify either access_key"):
            AwsSpecificSettings(  # type: ignore[call-arg]
                account_number="123123123123",
                regions=["us-east-1"],
            )

    def test_provider_key(self):
        account = "123123123123"
        expected = (account,)
        settings = self.aws_settings({"account_number": account})
        assert settings.get_provider_key() == expected

    # def test_ignore_tags_provider(self):
    #     expected = ["test-provider-ignore-tag"]
    #     settings = self.aws_settings(
    #         {
    #             "ignore_tags": expected,
    #         }
    #     )
    #     creds = next(settings.get_credentials())
    #     assert creds["ignore_tags"] == expected

    # def test_ignore_tags_account_overrides_provider(self):
    #     child = {
    #         "account_number": "123123123123",
    #         "ignore_tags": ["test-account-ignore-tag"],
    #     }
    #     primary = {
    #         "ignore_tags": ["test-primary-ignore-tag"],
    #         "accounts": [child],
    #     }
    #     settings = self.aws_settings(primary)
    #     creds = list(settings.get_credentials())
    #     assert creds[0]["ignore_tags"] == primary["ignore_tags"]
    #     assert creds[1]["ignore_tags"] == child["ignore_tags"]
