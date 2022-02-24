import json
from collections import OrderedDict
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase

import pytest
import yaml
from parameterized import parameterized
from pytest_mock import MockerFixture

from censys.cloud_connectors import __connectors__
from censys.cloud_connectors.common.settings import PlatformSpecificSettings, Settings

TEST_AZURE_KEY = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
TEST_AZURE_PLATFORM_CONFIG = {
    "platform": "azure",
    "subscription_id": TEST_AZURE_KEY,
    "tenant_id": TEST_AZURE_KEY,
    "client_id": TEST_AZURE_KEY,
    "client_secret": TEST_AZURE_KEY,
}


def same_yaml(file_a: str, file_b: str) -> bool:
    with open(file_a) as f:
        a = yaml.safe_load(f)
    with open(file_b) as f:
        b = yaml.safe_load(f)
    return a == b


class TestSettings(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture, shared_datadir: Path):
        self.mocker = mocker
        self.shared_datadir = shared_datadir

    def setUp(self) -> None:
        with open(self.shared_datadir / "test_consts.json") as f:
            self.data = json.load(f)
        self.settings = Settings(censys_api_key=self.data["censys_api_key"])

    def test_read_platforms_config_file_empty(self):
        temp_platforms = self.settings.platforms.copy()
        self.settings.platforms_config_file = (
            self.shared_datadir / "test_empty_platforms.yml"
        )
        self.settings.read_platforms_config_file()
        assert self.settings.platforms == temp_platforms

    @parameterized.expand(
        [
            ("azure", "test_azure_platforms.yml", 2),
        ]
    )
    def test_read_platforms_config_file(self, platform, file_name, expected_count):
        self.settings.platforms_config_file = self.shared_datadir / file_name
        self.settings.read_platforms_config_file()
        assert len(self.settings.platforms[platform]) == expected_count

    @parameterized.expand(
        [
            (
                "this_file_does_not_exist.yml",
                FileNotFoundError,
                "Platform config file not found",
            ),
            ("test_no_name_platforms.yml", ValueError, "Platform name is required"),
            (
                "test_unknown_platforms.yml",
                ImportError,
                "Could not import the settings for the unknown platform",
            ),
        ]
    )
    def test_read_platforms_config_file_fail(self, file_name, exec, error_msg):
        self.settings.platforms_config_file = self.shared_datadir / file_name
        with pytest.raises(exec, match=error_msg):
            self.settings.read_platforms_config_file()

    @parameterized.expand([("test_azure_platforms.yml")])
    def test_write_platforms_config_file(self, file_name):
        original_file = self.shared_datadir / file_name
        self.settings.platforms_config_file = original_file
        self.settings.read_platforms_config_file()

        temp_file = NamedTemporaryFile(mode="w+", delete=False)
        self.settings.platforms_config_file = temp_file.name
        self.settings.write_platforms_config_file()
        assert same_yaml(original_file, temp_file.name)

    @parameterized.expand([(c) for c in __connectors__])
    def test_scan_all(self, platform_name: str):
        self.settings.platforms[platform_name] = []
        mock_connector = self.mocker.MagicMock()
        mock_connector().scan_all.return_value = []
        mock_platform = self.mocker.MagicMock()
        mock_platform.__connector__ = mock_connector
        mock_import_module = self.mocker.patch(
            "importlib.import_module", return_value=mock_platform
        )
        self.settings.scan_all()
        mock_import_module.assert_called_once_with(
            f"censys.cloud_connectors.{platform_name}.connector"
        )
        mock_connector().scan_all.assert_called_once()

    def test_scan_all_fail(self):
        self.settings.platforms["this_platform_does_not_exist"] = []
        with pytest.raises(ImportError, match="Could not import the connector for the"):
            self.settings.scan_all()


class ExamplePlatformSettings(PlatformSpecificSettings):
    advanced: bool
    other: str


class TestPlatformSpecificSettings(TestCase):
    def test_as_dict(self):
        platform_settings = ExamplePlatformSettings(
            platform="test", advanced=True, other="other variable"
        )
        settings_dict = platform_settings.as_dict(priority_keys=["platform"])
        assert isinstance(settings_dict, OrderedDict), "Must return an OrderedDict"
        assert settings_dict == {
            "platform": "test",
            "advanced": True,
            "other": "other variable",
        }, "Dict must follow the priority order"

    def test_from_dict(self):
        platform_settings = ExamplePlatformSettings.from_dict(
            {
                "platform": "test",
                "advanced": True,
                "other": "other variable",
            }
        )
        assert platform_settings.platform == "Test", "Platform name must be capitalized"
        assert platform_settings.advanced is True
        assert (
            platform_settings.other == "other variable"
        ), "Must be the same as the input"
