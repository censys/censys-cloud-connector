import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture


class BaseCase:
    """Base mixin class for all tests.

    For testing we use pytest in combination with unittest TestCases.
    We also use pytest-mock to mock external dependencies and pytest-datadir to
    provide test data.

    Links:
        https://docs.pytest.org/
        https://docs.pytest.org/en/latest/unittest.html
        https://pypi.org/project/pytest-mock/
        https://pypi.org/project/pytest-datadir/
    """

    mocker: MockerFixture
    shared_datadir: Path
    default_settings: dict

    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture, shared_datadir: Path):
        """Injects fixtures into the test case."""
        # Inject mocker fixture
        self.mocker = mocker
        # Inject shared data directory fixture
        self.shared_datadir = shared_datadir

    def setUp(self):
        """Sets up the test case."""
        with open(self.shared_datadir / "default_settings.json") as f:
            self.default_settings = json.load(f)

    def tearDown(self) -> None:
        """Tears down the test case."""
        pass
