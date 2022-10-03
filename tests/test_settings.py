from collections import OrderedDict
from tempfile import NamedTemporaryFile
from unittest import TestCase

import pytest
from parameterized import parameterized

from censys.cloud_connectors.aws_connector.settings import (
    AwsAccount,
    AwsSpecificSettings,
)
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings, Settings
from tests.base_case import BaseCase
from tests.utils import assert_same_yaml


class TestSettings(BaseCase, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.settings = Settings(
            **self.default_settings,
            secrets_dir=str(self.shared_datadir),
        )

    def test_read_providers_config_file_empty(self):
        temp_providers = self.settings.providers.copy()
        self.settings.providers_config_file = (
            self.shared_datadir / "test_empty_providers.yml"
        )
        self.settings.read_providers_config_file()
        assert self.settings.providers == temp_providers

    @parameterized.expand(
        [
            (ProviderEnum.AZURE, "test_azure_providers.yml", 2),
        ]
    )
    def test_read_providers_config_file(self, provider, file_name, expected_count):
        self.settings.providers_config_file = self.shared_datadir / file_name
        self.settings.read_providers_config_file([provider])
        assert len(self.settings.providers[provider]) == expected_count

    @parameterized.expand(
        [
            (ProviderEnum.AZURE, "test_all_providers.yml", 2),
            (ProviderEnum.GCP, "test_all_providers.yml", 1),
            (ProviderEnum.AWS, "test_all_providers.yml", 1),
        ]
    )
    def test_read_providers_config_file_provider_option(
        self, provider, file_name, expected_count
    ):
        self.settings.providers_config_file = self.shared_datadir / file_name
        self.settings.read_providers_config_file([provider])
        assert len(self.settings.providers[provider]) == expected_count

    @parameterized.expand(
        [
            (
                "this_file_does_not_exist.yml",
                FileNotFoundError,
                "Provider config file not found",
            ),
            ("test_no_name_providers.yml", ValueError, "Provider name is required"),
            (
                "test_unknown_providers.yml",
                ValueError,
                "Provider name is not valid: Unknown",
            ),
        ]
    )
    def test_read_providers_config_file_fail(self, file_name, exec, error_msg):
        self.settings.providers_config_file = self.shared_datadir / file_name
        with pytest.raises(exec, match=error_msg):
            self.settings.read_providers_config_file()

    @parameterized.expand(["test_azure_providers.yml"])
    def test_write_providers_config_file(self, file_name):
        original_file = self.shared_datadir / file_name
        self.settings.providers_config_file = original_file
        self.settings.read_providers_config_file()

        temp_file = NamedTemporaryFile(mode="w+")
        self.settings.providers_config_file = temp_file.name
        self.settings.write_providers_config_file()
        assert_same_yaml(original_file, temp_file.name)

    @parameterized.expand(list(ProviderEnum))
    def test_scan_all(self, provider: ProviderEnum):
        self.settings.providers[provider] = {}
        mock_connector = self.mocker.MagicMock()
        mock_connector().scan_all.return_value = []
        mock_provider = self.mocker.MagicMock()
        mock_provider.__connector__ = mock_connector
        mock_import_module = self.mocker.patch(
            "importlib.import_module", return_value=mock_provider
        )
        self.settings.scan_all()
        mock_import_module.assert_called_once_with(provider.module_path())
        mock_connector().scan_all.assert_called_once()


class ExampleProviderSettings(ProviderSpecificSettings):
    advanced: bool
    other: str

    def get_provider_key(self):
        pass

    def get_provider_payload(self):
        pass


class TestProviderSpecificSettings(BaseCase):
    def test_as_dict(self):
        provider_settings = ExampleProviderSettings(
            provider=ProviderEnum.GCP, advanced=True, other="other variable"
        )
        settings_dict = provider_settings.as_dict()
        assert isinstance(settings_dict, OrderedDict), "Must return an OrderedDict"
        assert settings_dict == {
            "provider": "GCP",
            "advanced": True,
            "other": "other variable",
        }, "Dict must follow the priority order"

    def test_from_dict(self):
        provider_settings = ExampleProviderSettings.from_dict(
            {
                "provider": ProviderEnum.AWS,
                "advanced": True,
                "other": "other variable",
            }
        )
        assert provider_settings.provider == "AWS", "Provider name must be capitalized"
        assert provider_settings.advanced is True
        assert (
            provider_settings.other == "other variable"
        ), "Must be the same as the input"


class TestAwsSpecificSettings(BaseCase):
    def test_provider_key(self):
        settings = AwsSpecificSettings(
            account_number=123,
            access_key="access-key",
            secret_key="secret-key",
            regions=["us-east-1", "us-west-1"],
        )

        assert settings.get_provider_key() == ("123", "us-east-1_us-west-1")

    def test_provider_key_sorts_accounts(self):
        settings = AwsSpecificSettings(
            accounts=[AwsAccount(account_number=8), AwsAccount(account_number=7)],
            regions=["us-east-1"],
        )

        assert settings.get_provider_key() == ("7_8", "us-east-1")

    def test_parse_provider(self):
        self.settings = Settings(
            censys_api_key="fake-key-xxxxxxxxxxxxxxxxxxxxxxxxxxx",
            secrets_dir=str(self.shared_datadir),
        )
        self.settings.providers_config_file = (
            self.shared_datadir / "test_aws_providers.yml"
        )
        self.settings.read_providers_config_file()
        assert len(self.settings.providers[ProviderEnum.AWS]) == 8

    def test_get_credentials(self):
        cred1 = {
            "account_number": 123,
            "access_key": "first-access-key",
            "secret_key": "first-secret-key",
            "role_name": None,
            "role_session_name": None,
            "ignore_tags": None,
        }

        cred2 = {
            "account_number": 456,
            "access_key": "second-access-key",
            "secret_key": "second-secret-key",
            "role_name": None,
            "role_session_name": None,
            "ignore_tags": None,
        }

        settings = AwsSpecificSettings(
            accounts=[AwsAccount(**cred1), AwsAccount(**cred2)],
            regions=["us-east-1"],
        )

        creds = []
        for cred in settings.get_credentials():
            creds.append(cred)

        assert creds == [cred1, cred2]

    def test_get_credentials_with_minimum_fields(self):
        expected = {
            "account_number": 123,
        }

        settings = AwsSpecificSettings(
            accounts=[AwsAccount(**expected)],
            regions=["us-east-1"],
        )

        cred = next(settings.get_credentials())
        assert type(cred) is dict
        assert cred["account_number"] == expected["account_number"]

    def test_get_credentials_with_provider_fields(self):
        expected = {
            "account_number": 456,
            "access_key": "base-access-key",
            "secret_key": "base-secret-key",
            "role_name": "base-role-name",
            "role_session_name": "base-role-session-name",
            "ignore_tags": ["base-ignore-tag"],
        }

        account2 = AwsAccount(**expected)
        settings = AwsSpecificSettings(
            access_key=expected["access_key"],
            secret_key=expected["secret_key"],
            accounts=[account2],
            regions=["us-east-1"],
        )

        cred = next(settings.get_credentials())
        assert cred == expected

    def test_get_credentials_with_account_overrides(self):
        expected = {
            "account_number": 456,
            "access_key": "override-access-key",
            "secret_key": "override-secret-key",
            "role_name": "override-role-name",
            "role_session_name": "override-role-session-name",
            "ignore_tags": ["override-ignore-tag"],
        }

        account2 = AwsAccount(**expected)
        settings = AwsSpecificSettings(
            access_key=expected["access_key"],
            secret_key=expected["secret_key"],
            accounts=[account2],
            ignore_tags=["base-ignore-tag-that-should-be-overridden"],
            regions=["us-east-1"],
        )

        cred = next(settings.get_credentials())
        assert cred == expected

    def test_ignore_tags_provider_level(self):
        settings = AwsSpecificSettings(
            accounts=[AwsAccount(account_number=123)],
            regions=["us-east-1"],
            ignore_tags=["test-provider-ignore-tag"],
        )
        creds = next(settings.get_credentials())
        assert creds["ignore_tags"] == ["test-provider-ignore-tag"]

    def test_ignore_tags_account_level(self):
        account1 = AwsAccount(
            account_number=123,
            ignore_tags=["test-account-ignore-tag"],
        )
        settings = AwsSpecificSettings(
            accounts=[account1],
            regions=["us-east-1"],
            ignore_tags=["test-provider-ignore-tag"],
        )
        creds = next(settings.get_credentials())
        assert creds["ignore_tags"] == ["test-account-ignore-tag"]
