"""Base for all cli commands."""

import subprocess
from typing import Union

import rich
from InquirerPy import prompt
from InquirerPy.utils import InquirerPyQuestions
from rich.syntax import Syntax


class BaseCli:
    """Base for all cli commands.

    For the CLI, we use rich to print colored messages and syntax highlighting.
    And we use InquirerPy to prompt the user for answers.
    """

    def print(self, *args, **kwargs) -> None:
        """Print a object.

        This is a wrapper around rich's print function.

        Args:
            *args: The arguments to print.
            **kwargs: The keyword arguments to print.
        """
        rich.print(*args, **kwargs)

    def print_info(self, message: str) -> None:
        """Print an info message.

        Args:
            message (str): The message to print.
        """
        self.print("[blue]i[/blue] " + message)

    def print_warning(self, message: str) -> None:
        """Print a warning message.

        Args:
            message (str): The message to print.
        """
        self.print("[yellow]![/yellow] " + message)

    def print_error(self, message: str) -> None:
        """Print an error message.

        Args:
            message (str): The message to print.
        """
        self.print("[red]x[/red] " + message)

    def print_command(self, command: Union[str, list[str]]) -> None:
        """Print a command.

        Args:
            command (Union[str, list[str]]): The command to print.
        """
        if isinstance(command, list):
            command = " ".join(command)
        self.print(Syntax(command, "bash", word_wrap=True))

    def print_json(self, json_object: dict) -> None:
        """Print a json object.

        This is a wrapper around print_json's print function.

        Args:
            json_object (dict): The json object to print.
        """
        rich.print_json(data=json_object)

    def prompt(self, questions: InquirerPyQuestions, **kwargs) -> dict:
        """Prompt the user for answers.

        This is a wrapper around InquirerPy's prompt function.

        Args:
            questions (InquirerPyQuestions): The question(s) to ask.
            **kwargs: The keyword arguments to pass to prompt.

        Returns:
            dict: The answers.

        Raises:
            KeyboardInterrupt: If the user cancels the prompt.
        """
        # Add better instructions
        if isinstance(questions, dict):
            questions = [questions]
        for question in questions:
            if question.get("type") == "list":
                question["instruction"] = "(Use arrow keys)"
                if question.get("multiselect"):
                    question["instruction"] = "(Use ctrl+r to select all)"
            # TODO: Add additional instructions for other types

        answers = prompt(questions, **kwargs)
        if not answers:
            # If the user cancels the prompt (returns no answers), we raise a KeyboardInterrupt.
            raise KeyboardInterrupt
        return answers

    def run_command(self, command: str, **kwargs) -> subprocess.CompletedProcess:
        """Run a command.

        Args:
            command (str): The command to run.
            **kwargs: The keyword arguments to pass to run_command.

        Returns:
            subprocess.CompletedProcess: The completed process.
        """
        if not kwargs:
            kwargs = {"shell": True, "capture_output": True, "text": True}
        return subprocess.run(command, **kwargs)
