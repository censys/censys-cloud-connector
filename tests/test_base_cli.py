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

    def test_print(self):
        # Test data
        test_args = ["test", "args"]
        test_kwargs = {"test": "kwargs"}

        # Mock
        mock_print = self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.rich.print"
        )

        # Actual call
        self.base_cli.print(*test_args, **test_kwargs)

        # Assertions
        mock_print.assert_called_once_with(*test_args, **test_kwargs)

    @parameterized.expand(
        [
            ("[blue]i[/blue] ", "print_info"),
            ("[yellow]![/yellow] ", "print_warning"),
            ("[red]x[/red] ", "print_error"),
        ]
    )
    def test_print_types(self, prefix: str, method: str):
        # Mock
        mock_print = self.mocker.patch.object(self.base_cli, "print")

        # Actual call
        print_func = getattr(self.base_cli, method)
        print_func(TEST_MESSAGE)

        # Assertions
        mock_print.assert_called_once_with(prefix + TEST_MESSAGE)

    def test_print_command(self):
        # Mock
        mock_print = self.mocker.patch.object(self.base_cli, "print")
        mock_syntax = self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.Syntax"
        )

        # Actual call
        self.base_cli.print_command("test command")

        # Assertions
        mock_syntax.assert_called_once_with("test command", "bash", word_wrap=True)
        mock_print.assert_called_once_with(mock_syntax.return_value)

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
            "censys.cloud_connectors.common.cli.base.prompt", return_value=test_answers
        )

        # Actual call
        actual_answers = self.base_cli.prompt([{"type": "input", "name": "test"}])

        # Assertions
        assert actual_answers == test_answers

    def test_prompt_no_answers(self):
        # Mock
        self.mocker.patch(
            "censys.cloud_connectors.common.cli.base.prompt", return_value={}
        )

        # Actual call
        with pytest.raises(KeyboardInterrupt):
            self.base_cli.prompt([{"type": "input", "name": "test"}])

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
