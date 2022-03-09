import json
from pathlib import Path
from typing import Any
from unittest import TestCase

import pytest
from parameterized import parameterized
from prompt_toolkit.validation import Document, ValidationError
from pydantic import (
    BaseConfig,
    Field,
    FilePath,
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

from censys.cloud_connectors.common.cli.provider_setup import (
    ProviderSetupCli,
    generate_validation,
    prompt_for_list,
    snake_case_to_english,
)
from censys.cloud_connectors.common.settings import ProviderSpecificSettings, Settings


class TestProviderSetup(TestCase):
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
            ("Valid str", constr(min_length=1), "Test Variable", True),
            (
                "Empty str",
                constr(min_length=1),
                "",
                "ensure this value has at least 1 characters",
            ),
            ("Valid int", conint(ge=0), "0", True),
            (
                "Negative int",
                conint(ge=0),
                "-1",
                "ensure this value is greater than or equal to 0",
            ),
            ("Valid float", confloat(ge=0), "0.0", True),
            (
                "Negative float",
                confloat(ge=0),
                "-1.0",
                "ensure this value is greater than or equal to 0",
            ),
        ]
    )
    def test_generate_validation(
        self, description: str, type_: type, value: Any, expected_output: Any
    ):
        # Test data
        test_document = Document(text=value, cursor_position=0)
        # Make ModelField
        field = ModelField.infer(
            name="test_field",
            value=value,
            annotation=type_,
            class_validators={},
            config=BaseConfig,
        )
        # Generate class
        validation_cls = generate_validation(field)
        # Validate
        if expected_output is True:
            validation_cls.validate(test_document)
        else:
            with pytest.raises(ValidationError, match=expected_output):
                validation_cls.validate(test_document)

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
            "censys.cloud_connectors.common.cli.provider_setup.prompt"
        )
        mock_prompt.side_effect = prompt_side_effect

        # Actual call
        values = prompt_for_list(test_field)

        # Assertions
        assert values == [
            value for q in prompt_side_effect if (value := q.get(test_field_name))
        ]
        assert mock_prompt.call_count == prompt_call_count


class ExampleProviderSpecificSettings(ProviderSpecificSettings):
    provider = "test_provider"

    # Strings
    string_1: str
    string_2_with_default: str = "default_value_1"
    string_3_with_constr: constr(min_length=1)  # type: ignore
    string_4_with_field: str = Field(min_length=2)

    # Lists
    list_1: list[str]
    list_2_with_default: list[str] = ["default_value_2"]
    list_3_with_conlist: conlist(str, min_items=1)  # type: ignore
    list_4_with_field: list[str] = Field(min_items=2)

    # Booleans
    bool_1: bool
    bool_2_with_default: bool = True

    # Integers
    int_1: int
    int_2_with_default: int = 1
    int_3_with_conint: conint(gt=1)  # type: ignore
    int_4_positive: PositiveInt
    int_5_non_positive: NonPositiveInt
    int_6_with_field: int = Field(gt=1)

    # Floats
    float_1: float
    float_2_with_default: float = 1.0
    float_3_with_confloat: confloat(gt=1)  # type: ignore
    float_4_negative: NegativeFloat
    float_5_non_negative: NonNegativeFloat
    float_6_with_field: float = Field(gt=1)

    # Other
    file_path: FilePath


class ExampleProviderSetupCli(ProviderSetupCli):
    provider = "test_provider"  # type: ignore
    provider_specific_settings_class = ExampleProviderSpecificSettings


class TestProviderSetupCli(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture, shared_datadir: Path):
        self.mocker = mocker
        self.shared_datadir = shared_datadir

    def setUp(self) -> None:
        with open(self.shared_datadir / "test_consts.json") as f:
            self.consts = json.load(f)
        self.settings = Settings(censys_api_key=self.consts["censys_api_key"])
        self.setup_cli = ExampleProviderSetupCli(self.settings)

    def test_init(self):
        assert self.setup_cli.settings == self.settings
        assert self.setup_cli.logger is not None

    def test_setup(self):
        # Mock prompt
        mock_prompt = self.mocker.patch.object(self.setup_cli, "prompt_for_settings")
        mock_prompt.return_value = self.mocker.MagicMock()
        test_provider = ExampleProviderSetupCli.provider
        assert self.setup_cli.settings.providers[test_provider] == []

        # Actual call
        self.setup_cli.setup()

        # Assertions
        mock_prompt.assert_called_once()
        assert self.setup_cli.settings.providers[test_provider] == [
            mock_prompt.return_value
        ]

    def test_prompt_for_settings(self):
        # Test data
        expected_str_fields = {
            "string_1": "user_value_1",
            "string_2_with_default": "user_value_2",
            "string_3_with_constr": "user_value_3",
            "string_4_with_field": "user_value_4",
        }
        expected_list_fields = {
            "list_1": ["user_input_1", "user_input_2"],
            "list_2_with_default": ["default_value_2", "user_input_3"],
            "list_3_with_conlist": ["user_input_4", "user_input_5"],
            "list_4_with_field": ["user_input_6", "user_input_7"],
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
            "int_6_with_field": 7,
        }
        expected_float_fields = {
            "float_1": 5.0,
            "float_2_with_default": 6.0,
            "float_3_with_confloat": 7.0,
            "float_4_negative": -8.0,
            "float_5_non_negative": 9.0,
            "float_6_with_field": 10.0,
        }
        expected_other_fields = {
            "file_path": self.shared_datadir / "test_consts.json",
        }
        expected_field_values = (
            expected_str_fields
            | expected_list_fields
            | expected_bool_fields
            | expected_int_fields
            | expected_float_fields
            | expected_other_fields
        )

        # Mock
        mock_prompt_for_list = self.mocker.patch(
            "censys.cloud_connectors.common.cli.provider_setup.prompt_for_list",
            side_effect=list(expected_list_fields.values()),
        )
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.common.cli.provider_setup.prompt",
            return_value=expected_field_values,
        )

        # Actual call
        actual_settings = self.setup_cli.prompt_for_settings()

        # Assertions
        assert actual_settings.provider == ExampleProviderSetupCli.provider
        assert mock_prompt_for_list.call_count == len(expected_list_fields)
        mock_prompt.assert_called()
        for field_name, field_value in expected_field_values.items():
            assert getattr(actual_settings, field_name) == field_value
