from unittest import TestCase

import pytest
from parameterized import parameterized
from pytest_mock import MockerFixture

from censys.cloud_connectors.common.cli import main


class TestCli(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture, capsys):
        self.mocker = mocker
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
