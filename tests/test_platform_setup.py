from typing import Any
from unittest import TestCase

import pytest
from parameterized import parameterized
from pydantic import (
    BaseConfig,
    NegativeFloat,
    NonNegativeFloat,
    NonPositiveInt,
    PositiveInt,
    confloat,
    conint,
    conlist,
    constr,
)
from pydantic.fields import ModelField
from pytest_mock import MockerFixture

from censys.cloud_connectors.common.cli.platform_setup import (
    PlatformSetupCli,
    generate_validation,
    prompt_for_list,
    snake_case_to_english,
)
from censys.cloud_connectors.common.settings import PlatformSpecificSettings, Settings


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
            (constr(min_length=1), "Test Variable", True),
            (constr(min_length=1), "", "ensure this value has at least 1 characters"),
            (conlist(str, min_items=1), ["Test Variable"], True),
            (conlist(str, min_items=1), [], "ensure this value has at least 1 items"),
            (
                conlist(constr(min_length=10), min_items=1),
                ["lessthan"],
                "ensure this value has at least 10 characters",
            ),
            (conint(ge=0), 0, True),
            (conint(ge=0), -1, "ensure this value is greater than or equal to 0"),
            (confloat(ge=0), 0.0, True),
            (confloat(ge=0), -1.0, "ensure this value is greater than or equal to 0"),
        ]
    )
    def test_generate_validation(self, type_: type, value: Any, expected_output: Any):
        # Make ModelField
        field = ModelField.infer(
            name="test_field",
            value=value,
            annotation=type_,
            class_validators={},
            config=BaseConfig,
        )
        # Generate function
        validation_func = generate_validation(field)
        # Validate
        assert validation_func(value) == expected_output

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


class ExamplePlatformSpecificSettings(PlatformSpecificSettings):
    platform = "test_platform"

    string_1: str
    string_2_with_default: str = "default_value_1"
    string_3_with_constr: constr(min_length=1)  # type: ignore
    list_1: list[str]
    list_2_with_default: list[str] = ["default_value_2"]
    list_3_with_conlist: conlist(str, min_items=1)  # type: ignore
    bool_1: bool
    bool_2_with_default: bool = True
    int_1: int
    int_2_with_default: int = 1
    int_3_with_conint: conint(gt=1)  # type: ignore
    int_4_positive: PositiveInt
    int_5_non_positive: NonPositiveInt
    float_1: float
    float_2_with_default: float = 1.0
    float_3_with_confloat: confloat(gt=1)  # type: ignore
    float_4_negative: NegativeFloat
    float_5_non_negative: NonNegativeFloat


class ExamplePlatformSetupCli(PlatformSetupCli):
    platform = "test_platform"
    platform_specific_settings_class = ExamplePlatformSpecificSettings


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
        # Test data
        expected_str_fields = {
            "string_1": "user_value_1",
            "string_2_with_default": "user_value_2",
            "string_3_with_constr": "user_value_3",
        }
        expected_list_fields = {
            "list_1": ["user_input_1", "user_input_2"],
            "list_2_with_default": ["default_value_2", "user_input_3"],
            "list_3_with_conlist": ["user_input_4", "user_input_5"],
        }
        expected_bool_fields = {
            "bool_1": False,
            "bool_2_with_default": True,
        }
        expected_int_fields = {
            "int_1": 2,
            "int_2_with_default": 3,
            "int_3_with_conint": 4,
            "int_4_positive": 5,
            "int_5_non_positive": -1,
        }
        expected_float_fields = {
            "float_1": 5.0,
            "float_2_with_default": 6.0,
            "float_3_with_confloat": 7.0,
            "float_4_negative": -8.0,
            "float_5_non_negative": 9.0,
        }
        expected_field_values = (
            expected_str_fields
            | expected_list_fields
            | expected_bool_fields
            | expected_int_fields
            | expected_float_fields
        )

        # Mock
        mock_prompt_for_list = self.mocker.patch(
            "censys.cloud_connectors.common.cli.platform_setup.prompt_for_list",
            side_effect=list(expected_list_fields.values()),
        )
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.common.cli.platform_setup.prompt",
            return_value=expected_field_values,
        )

        # Actual call
        actual_settings = self.setup_cli.prompt_for_settings()

        # Assertions
        assert actual_settings.platform == ExamplePlatformSetupCli.platform
        assert mock_prompt_for_list.call_count == len(expected_list_fields)
        mock_prompt.assert_called_once()
        for field_name, field_value in expected_field_values.items():
            assert getattr(actual_settings, field_name) == field_value
