"""Base for all cli commands."""

import subprocess
from typing import Optional, Union

import rich
from InquirerPy import prompt as inquirer_prompt
from InquirerPy.utils import InquirerPyQuestions
from rich.console import Console
from rich.syntax import Syntax
from rich.theme import Theme

custom_theme = Theme(
    {
        "info": "#61afef",
        "questionmark": "#e5c07b",
    }
)
console = Console(theme=custom_theme)

print = console.print


def print_info(message: str) -> None:
    """Print an info message.

    Args:
        message (str): Message to print.
    """
    print("[info]i[/info] " + message)


def print_success(message: str) -> None:
    """Print a success message.

    Args:
        message (str): Message to print.
    """
    print("[green]✔[/green] " + message)


def print_warning(message: str) -> None:
    """Print a warning message.

    Args:
        message (str): Message to print.
    """
    print("[yellow]![/yellow] " + message)


def print_error(message: str) -> None:
    """Print an error message.

    Args:
        message (str): Message to print.
    """
    print("[red]✘[/red] " + message)


def print_question(message: str) -> None:
    """Print an info message.

    Args:
        message (str): Message to print.
    """
    print("[questionmark]?[/questionmark] " + message)


def print_command(command: Union[str, list[str]]) -> None:
    """Print a command.

    Args:
        command (Union[str, list[str]]): The command(s) to print.
    """
    if isinstance(command, list):
        command = " ".join(command)
    print()
    print(Syntax(command, "bash", word_wrap=True))
    print()


def print_json(json_object: dict) -> None:
    """Print a json.

    Args:
        json_object (dict): The json to print.
    """
    rich.print_json(data=json_object)


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
        if question.get("instruction") is not None:
            continue
        if question.get("type") == "list":
            question["instruction"] = "(Use arrow keys)"
            if question.get("multiselect"):
                question["instruction"] = "(Use ctrl+r to select all)"
        elif question.get("type") == "filepath":
            question["instruction"] = "(Tab completion is enabled)"

    answers = inquirer_prompt(questions, **kwargs)
    if not answers:
        # If the user cancels the prompt (returns no answers), we raise a KeyboardInterrupt.
        raise KeyboardInterrupt
    return answers


def prompt_select_one(
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
            answers = prompt(
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
    answers = prompt(question)
    return answers.get("choice")


def run_command(command: str, **kwargs) -> subprocess.CompletedProcess:
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


class BaseCli:
    """Base for all cli commands.

    For the CLI, we use rich to print colored messages and syntax highlighting.
    And we use InquirerPy to prompt the user for answers.
    """

    # Ensure that we have the same methods
    print = staticmethod(print)
    print_info = staticmethod(print_info)
    print_success = staticmethod(print_success)
    print_warning = staticmethod(print_warning)
    print_error = staticmethod(print_error)
    print_question = staticmethod(print_question)
    print_command = staticmethod(print_command)
    print_json = staticmethod(print_json)
    prompt = staticmethod(prompt)
    prompt_select_one = staticmethod(prompt_select_one)
    run_command = staticmethod(run_command)
