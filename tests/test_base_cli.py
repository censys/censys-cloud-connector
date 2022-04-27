from typing import Optional
from unittest import TestCase

import pytest
from parameterized import parameterized

from censys.cloud_connectors.common.cli.base import BaseCli

from .base_case import BaseCase

TEST_MESSAGE = "test message"


class TestBaseCli(BaseCase, TestCase):
    def setUp(self):
        super().setUp()
        self.base_cli = BaseCli()

    @parameterized.expand(
        [
            ("[info]i[/info] ", "print_info"),
            ("[yellow]![/yellow] ", "print_warning"),
            ("[red]✘[/red] ", "print_error"),
            ("[green]✔[/green] ", "print_success"),
            ("[questionmark]?[/questionmark] ", "print_question"),
        ]
    )
    def test_print_types(self, prefix: str, method: str):
        # Mock
        mock_print = self.mocker.patch("censys.cloud_connectors.common.cli.base.print")

        # Actual call
        print_func = getattr(self.base_cli, method)
        print_func(TEST_MESSAGE)

        # Assertions
        mock_print.assert_called_once_with(prefix + TEST_MESSAGE)

    def test_print_command(self):
        # Mock
        mock_print = self.mocker.patch("censys.cloud_connectors.common.cli.base.print")
        mock_syntax = self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.Syntax"
        )

        # Actual call
        self.base_cli.print_command("test command")

        # Assertions
        mock_syntax.assert_called_once_with("test command", "bash", word_wrap=True)
        # mock_print.assert_called_once_with(mock_syntax.return_value)
        calls = [
            self.mocker.call(),
            self.mocker.call(mock_syntax.return_value),
            self.mocker.call(),
        ]
        mock_print.assert_has_calls(calls)

    def test_print_json(self):
        # Test data
        test_json_object = {"test": "json"}

        # Mock
        mock_print = self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.rich.print_json"
        )

        # Actual call
        self.base_cli.print_json(test_json_object)

        # Assertions
        mock_print.assert_called_once_with(data=test_json_object)

    def test_prompt(self):
        # Test data
        test_answers = {"test": "answers"}

        # Mock
        self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.inquirer_prompt",
            return_value=test_answers,
        )

        # Actual call
        actual_answers = self.base_cli.prompt([{"type": "input", "name": "test"}])

        # Assertions
        assert actual_answers == test_answers

    @parameterized.expand(
        [
            ("input"),
            ("input", "draw", "draw"),
            ("list", "(Use arrow keys)"),
            ("list", "(Use ctrl+r to select all)", None, True),
            ("filepath", "(Tab completion is enabled)"),
        ]
    )
    def test_prompt_instructions(
        self,
        type: str,
        expected_instruction: Optional[str] = None,
        given_instructions: Optional[str] = None,
        multiselect: Optional[bool] = None,
    ):
        # Test data
        given_question = {
            "type": type,
            "name": "test",
            "instruction": given_instructions,
            "multiselect": multiselect,
        }

        expected_question = {
            "type": type,
            "name": "test",
            "instruction": expected_instruction,
            "multiselect": multiselect,
        }

        # Mock
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.inquirer_prompt"
        )
        # Actual call
        self.base_cli.prompt(given_question)

        # Assertions
        mock_prompt.assert_called_once_with([expected_question])

    def test_prompt_multiple(self):
        # Test data
        given_questions = [
            {"type": "input", "name": "test_input", "instruction": "draw"},
            {"type": "list", "name": "test_list"},
        ]
        expected_questions = [
            {"type": "input", "name": "test_input", "instruction": "draw"},
            {"type": "list", "name": "test_list", "instruction": "(Use arrow keys)"},
        ]

        # Mock
        mock_prompt = self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.inquirer_prompt"
        )
        # Actual call
        self.base_cli.prompt(given_questions)

        # Assertions
        mock_prompt.assert_called_once_with(expected_questions)

    def test_prompt_no_answers(self):
        # Mock
        self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.inquirer_prompt", return_value={}
        )

        # Actual call
        with pytest.raises(KeyboardInterrupt):
            self.base_cli.prompt([{"type": "input", "name": "test"}])

    @parameterized.expand(
        [
            (True, {"name": "test_name", "value": "test_value"}),
            (False, None),
        ]
    )
    def test_prompt_select_one_from_one(
        self, choose: bool, expected_answer: Optional[dict]
    ):
        # Test data
        test_choices = [{"name": "test_name", "value": "test_value"}]

        # Mock
        self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.prompt",
            return_value={"use_only_choice": choose},
        )

        # Actual call
        actual_answers = self.base_cli.prompt_select_one("Choose:", test_choices)

        # Assertions
        assert actual_answers == expected_answer

    def test_prompt_select_one_from_many(self):
        # Test data
        test_answers = {"choice": "name_b", "value": "value_b"}
        test_choices = [
            {"choice": "name_a", "value": "value_a"},
            {"choice": "name_b", "value": "value_b"},
            {"choice": "name_c", "value": "value_c"},
        ]

        # Mock
        self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.prompt",
            return_value={"choice": test_answers},
        )

        # Actual call
        actual_answers = self.base_cli.prompt_select_one(
            "Choose:", test_choices, "choice", "value_b"
        )

        # Assertions
        assert actual_answers == test_answers

    @parameterized.expand(
        [
            ({}, {"shell": True, "capture_output": True, "text": True}),
            ({"shell": False}, {"shell": False}),
        ]
    )
    def test_run_command(self, test_kwargs, expected_kwargs):
        # Test data
        test_command = "test command"

        # Mock
        mock_run = self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.subprocess.run", return_value=0
        )

        # Actual call
        self.base_cli.run_command(test_command, **test_kwargs)

        # Assertions
        mock_run.assert_called_once_with(test_command, **expected_kwargs)
