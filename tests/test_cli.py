from unittest import TestCase

import pytest
from parameterized import parameterized

from censys.cloud_connectors.common.cli import main
from censys.cloud_connectors.common.cli.commands import config, scan
from censys.cloud_connectors.common.enums import ProviderEnum
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
        # Mock
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.common.cli.commands.config.prompt",
            return_value={"provider": ProviderEnum.AZURE},
        )

        mock_args = self.mocker.MagicMock()
        mock_args.provider = None

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
        config.cli_config(mock_args)

        # Assertions
        assert mock_prompt.call_count == 1
        mock_importlib.assert_called_once_with(
            "censys.cloud_connectors.azure_connector"
        )
        mock_settings.return_value.read_providers_config_file.assert_called_once_with()
        mock_setup_cls.assert_called_once()
        mock_setup_cls.return_value.setup.assert_called_once()

    def test_cli_config_provider_option(self):
        # Mock
        mock_args = self.mocker.MagicMock()
        mock_args.provider = ProviderEnum.GCP

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
        config.cli_config(mock_args)

        # Assertions
        mock_importlib.assert_called_once_with("censys.cloud_connectors.gcp_connector")
        mock_settings.return_value.read_providers_config_file.assert_called_once_with()
        mock_setup_cls.assert_called_once()
        mock_setup_cls.return_value.setup.assert_called_once()


class TestScanCli(BaseCase, TestCase):
    def test_cli_scan(self):
        # Mock
        mock_args = self.mocker.MagicMock()
        mock_args.provider = None
        mock_args.scan_interval = None

        mock_settings = self.mocker.patch(
            "censys.cloud_connectors.common.cli.commands.scan.Settings"
        )
        mock_settings.return_value.read_providers_config_file = self.mocker.Mock()
        mock_settings.return_value.scan_all = self.mocker.Mock()

        # Actual call
        scan.cli_scan(mock_args)

        # Assertions
        mock_settings.return_value.read_providers_config_file.assert_called_once_with(
            mock_args.provider
        )
        mock_settings.return_value.scan_all.assert_called_once()

    def test_cli_scan_provider_option(self):
        # Mock
        mock_args = self.mocker.MagicMock()
        mock_args.provider = [ProviderEnum.AZURE]
        mock_args.scan_interval = None

        mock_settings = self.mocker.patch(
            "censys.cloud_connectors.common.cli.commands.scan.Settings"
        )
        mock_settings.return_value.read_providers_config_file = self.mocker.Mock()
        mock_settings.return_value.scan_all = self.mocker.Mock()

        # Actual call
        scan.cli_scan(mock_args)

        # Assertions
        mock_settings.return_value.read_providers_config_file.assert_called_once_with(
            mock_args.provider
        )
        mock_settings.return_value.scan_all.assert_called_once_with()
