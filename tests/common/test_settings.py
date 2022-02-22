from pathlib import Path
from unittest import TestCase

import pytest
from parameterized import parameterized
from pytest_mock import MockerFixture

from censys.cloud_connectors.common.settings import (
    create_azure_settings,
    get_platform_settings_from_file,
)

TEST_AZURE_KEY = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
TEST_AZURE_PLATFORM_CONFIG = {
    "platform": "azure",
    "subscription_id": TEST_AZURE_KEY,
    "tenant_id": TEST_AZURE_KEY,
    "client_id": TEST_AZURE_KEY,
    "client_secret": TEST_AZURE_KEY,
}


class TestPlatformSpecificSettings(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture, shared_datadir: Path):
        self.mocker = mocker
        self.shared_datadir = shared_datadir

    def test_create_azure_settings(self):
        platform_settings = create_azure_settings(TEST_AZURE_PLATFORM_CONFIG)
        assert len(platform_settings) == 1
        azure_settings = platform_settings[0]
        assert azure_settings.platform == "azure"
        assert azure_settings.subscription_id == TEST_AZURE_KEY
        assert azure_settings.tenant_id == TEST_AZURE_KEY
        assert azure_settings.client_id == TEST_AZURE_KEY
        assert azure_settings.client_secret == TEST_AZURE_KEY

    def test_create_azure_settings_multiple(self):
        test_azure_platform_config = TEST_AZURE_PLATFORM_CONFIG.copy()
        test_azure_platform_config["subscription_id"] = [
            TEST_AZURE_KEY,
            TEST_AZURE_KEY.replace("x", "y"),
        ]
        azure_settings = create_azure_settings(test_azure_platform_config)
        assert len(azure_settings) == 2
        for azure_setting in azure_settings:
            assert azure_setting.platform == "azure"
            assert azure_setting.subscription_id in [
                TEST_AZURE_KEY,
                TEST_AZURE_KEY.replace("x", "y"),
            ]

    def test_get_platform_settings_from_file(self):
        platform_settings = get_platform_settings_from_file(
            self.shared_datadir / "test_azure_platforms.yml"
        )
        test_keys = [
            TEST_AZURE_KEY,
            TEST_AZURE_KEY.replace("x", "y"),
        ]
        assert len(platform_settings.keys()) == 1
        for azure_settings in platform_settings["azure"]:
            assert azure_settings.platform == "azure"
            assert azure_settings.subscription_id in test_keys
            assert azure_settings.tenant_id in test_keys
            assert azure_settings.client_id in test_keys
            assert azure_settings.client_secret in test_keys

    @parameterized.expand(
        [
            ("test_no_name_platforms.yml", "Platform name is required"),
            ("test_unknown_platforms.yml", "Unknown platform: unknown"),
        ]
    )
    def test_get_platform_settings_from_file_fail(self, file_name, error_msg):
        with pytest.raises(ValueError, match=error_msg):
            get_platform_settings_from_file(self.shared_datadir / file_name)
