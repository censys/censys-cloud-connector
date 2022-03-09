import json
from pathlib import Path
from unittest import TestCase

import pytest
from pytest_mock import MockerFixture


class BaseTestCase(TestCase):
    mocker: MockerFixture
    shared_datadir: Path
    consts: dict

    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture, shared_datadir: Path):
        self.mocker = mocker
        self.shared_datadir = shared_datadir

    def setUp(self):
        with open(self.shared_datadir / "test_consts.json") as f:
            self.consts = json.load(f)
