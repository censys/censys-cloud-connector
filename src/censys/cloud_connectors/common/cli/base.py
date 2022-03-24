"""Base for all cli commands."""

import subprocess
from typing import Optional, Union

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

    @staticmethod
    def prompt(questions: InquirerPyQuestions, **kwargs) -> dict:
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
        if isinstance(questions, dict):
            questions = [questions]
        for question in questions:
            # Add better instructions
            if question.get("type") == "list":
                question["instruction"] = "(Use arrow keys)"
                if question.get("multiselect"):
                    question["instruction"] = "(Use ctrl+r to select all)"
            elif question.get("type") == "filepath":
                question["instruction"] = "(Tab completion is enabled)"

        answers = prompt(questions, **kwargs)
        if not answers:
            # If the user cancels the prompt (returns no answers), we raise a KeyboardInterrupt.
            raise KeyboardInterrupt
        return answers

    def prompt_select_one(
        self,
        message: str,
        choices: list[dict],
        name_key: str = "name",
        default: Optional[str] = None,
        **question_kwargs,
    ) -> Optional[dict]:
        """Prompt the user for a list of choices.

        This method will ask the users to confirm if there is only one choice
        otherwise it will ask the user to pick one of the choices.

        Args:
            message (str): The message to print.
            choices (list[dict]): The choices to pick from.
            name_key (str): The key to use for the name of the choice.
            default (Optional[str]): The default choice.
            **question_kwargs: The keyword arguments to pass to prompt.

        Returns:
            dict: The choice.
        """
        if len(choices) == 1:
            first_choice = choices[0]
            if first_choice_value := first_choice.get(name_key):
                answers = self.prompt(
                    {
                        "type": "confirm",
                        "name": "use_only_choice",
                        "message": f"Use {first_choice_value}?",
                        "default": True,
                    }
                )
                if not answers.get("use_only_choice"):
                    return None
                return first_choice

        if name_key != "name":
            # Ensure that we have proper names for the choices
            new_choices = []
            for choice in choices:
                new_choices.append({"name": choice[name_key], "value": choice})
            choices = new_choices

        question = {
            "type": "list",
            "name": "choice",
            "message": message,
            "choices": choices,
            **question_kwargs,
        }
        if default:
            question["default"] = default
        answers = self.prompt(question)
        return answers.get("choice")

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
