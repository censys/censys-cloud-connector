from unittest import TestCase

import pytest
from parameterized import parameterized

from censys.cloud_connectors.common.cli import main
from censys.cloud_connectors.common.cli.commands import config, scan
from tests.base_case import BaseCase


class TestCli(BaseCase, TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, capsys):
        super().setUp()
        self.capsys = capsys

    @parameterized.expand(
        [
            ([], "usage: censys-cc"),
            (["--version"], "Censys Cloud Connectors Version:"),
        ]
    )
    def test_main(self, commands: list, expected_output: str):
        # Mock sys.argv
        self.mocker.patch("sys.argv", ["censys-cc"] + commands)

        # Actual call
        with pytest.raises(SystemExit):
            main()

        # Assertions
        captured = self.capsys.readouterr()
        assert expected_output in captured.out


class TestConfigCli(BaseCase, TestCase):
    def test_cli_config(self):
        # Test data
        mock_connectors = [
            "test_connector_1",
            "test_connector_2",
        ]

        # Mock
        self.mocker.patch("censys.cloud_connectors.__connectors__", mock_connectors)
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.common.cli.commands.config.prompt",
            side_effect=[
                {
                    "provider": "test_connector_1",
                },
                {"save": True},
            ],
        )
        mock_importlib = self.mocker.patch(
            "censys.cloud_connectors.common.cli.commands.config.importlib.import_module"
        )
        mock_setup_cls = (
            mock_importlib.return_value.__provider_setup__
        ) = self.mocker.Mock()
        mock_settings = self.mocker.patch(
            "censys.cloud_connectors.common.cli.commands.config.Settings"
        )
        mock_settings.return_value.read_providers_config_file = self.mocker.Mock()

        # Actual call
        config.cli_config(None)

        # Assertions
        assert mock_prompt.call_count == 2
        mock_importlib.assert_called_once_with(
            "censys.cloud_connectors.test_connector_1"
        )
        mock_settings.return_value.read_providers_config_file.assert_called_once_with()
        mock_setup_cls.assert_called_once()
        mock_setup_cls.return_value.setup.assert_called_once()


class TestScanCli(BaseCase, TestCase):
    def test_cli_scan(self):
        # Mock
        mock_settings = self.mocker.patch(
            "censys.cloud_connectors.common.cli.commands.scan.Settings"
        )
        mock_settings.return_value.read_providers_config_file = self.mocker.Mock()
        mock_settings.return_value.scan_all = self.mocker.Mock()

        # Actual call
        scan.cli_scan(None)

        # Assertions
        mock_settings.return_value.read_providers_config_file.assert_called_once_with()
        mock_settings.return_value.scan_all.assert_called_once_with()
