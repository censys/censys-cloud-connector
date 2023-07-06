from unittest import TestCase

import pytest

from censys.cloud_connectors.aws_connector.settings import (
    AwsAccount,
    AwsSpecificSettings,
)
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
