from unittest import TestCase

import pytest
from parameterized import parameterized
from pytest_mock import MockerFixture

from censys.cloud_connectors.common.cli.platform_setup import (
    PlatformSetupCli,
    prompt_for_list,
    snake_case_to_english,
)
from censys.cloud_connectors.common.settings import Settings


class TestPlatformSetup(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture):
        self.mocker = mocker

    @parameterized.expand(
        [
            ("test_variable", "Test Variable"),
            ("test_variable_with_underscore", "Test Variable With Underscore"),
        ]
    )
    def test_snake_case_to_english(self, snake_case: str, expected_output: str):
        assert snake_case_to_english(snake_case) == expected_output

    @parameterized.expand(
        [
            ([{"test_variable": "test_value", "add_another": False}], 1),
            (
                [
                    {"test_variable": "test_value_1", "add_another": True},
                    {"test_variable": "test_value_2", "add_another": False},
                ],
                2,
            ),
            (
                [{"test_variable": "test_value_1", "add_another": True}, {}],
                2,
            ),
        ]
    )
    def test_prompt_for_list(self, prompt_side_effect, prompt_call_count: int):
        # Mock prompt
        test_field = self.mocker.MagicMock()
        test_field_name = "test_variable"
        test_field.name = test_field_name
        test_field.type_ = str
        test_field.validate.return_value = (None, None)
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.common.cli.platform_setup.prompt"
        )
        mock_prompt.side_effect = prompt_side_effect

        # Actual call
        values = prompt_for_list(test_field)

        # Assertions
        assert values == [
            value for q in prompt_side_effect if (value := q.get(test_field_name))
        ]
        assert mock_prompt.call_count == prompt_call_count


class ExamplePlatformSetupCli(PlatformSetupCli):
    platform: str = "test_platform"


class TestPlatformSetupCli(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture):
        self.mocker = mocker

    def setUp(self) -> None:
        self.settings = Settings()
        self.setup_cli = ExamplePlatformSetupCli(self.settings)

    def test_init(self):
        assert self.setup_cli.settings == self.settings
        assert self.setup_cli.logger is not None

    def test_setup(self):
        # Mock prompt
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt_for_settings")
        mock_prompt.return_value = self.mocker.MagicMock()
        test_platform = ExamplePlatformSetupCli.platform
        assert self.setup_cli.settings.platforms[test_platform] == []

        # Actual call
        self.setup_cli.setup()

        # Assertions
        mock_prompt.assert_called_once()
        assert self.setup_cli.settings.platforms[test_platform] == [
            mock_prompt.return_value
        ]

    def test_prompt_for_settings(self):
        pass
