"""Base for all cli commands."""

import subprocess

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
        self.print("[red]![/red] " + message)

    def print_bash(self, bash: str) -> None:
        """Print a bash command.

        Args:
            bash (str): The bash command to print.
        """
        self.print(Syntax(bash, "bash", word_wrap=True))

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
        answers = prompt(questions, **kwargs)
        if not answers:
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
            kwargs = {"shell": True, "capture_output": True}
        return subprocess.run(command, **kwargs)
