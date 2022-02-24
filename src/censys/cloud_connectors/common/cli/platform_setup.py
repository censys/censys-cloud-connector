"""Base for all platform-specific setup cli commands."""
from typing import List, Union, get_args, get_origin

from pydantic import ValidationError
from pydantic.fields import ModelField
from pydantic.utils import lenient_issubclass
from PyInquirer import prompt

from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.settings import PlatformSpecificSettings, Settings


def snake_case_to_english(snake_case: str) -> str:
    """Convert a snake case string to an English sentence.

    Args:
        snake_case (str): The snake case string.

    Returns:
        str: The English sentence.
    """
    return " ".join(word.capitalize() for word in snake_case.split("_"))


def prompt_for_list(field: ModelField) -> List[str]:
    """Prompt for a list of values.

    Args:
        field (ModelField): The field to prompt for.

    Returns:
        List[str]: The list of values.

    Raises:
        KeyboardInterrupt: If the user cancels the prompt.
    """
    questions = [
        {
            "type": "input",
            "name": field.name,
            "message": f"Enter a {snake_case_to_english(field.name)}",
            "validate": lambda x: x.strip() != "",
        },
        {
            "type": "confirm",
            "name": "add_another",
            "message": "Add another",
        },
    ]
    answers = prompt(questions)
    if answers == {}:
        raise KeyboardInterrupt
    values = [answers[field.name]]
    while answers["add_another"]:
        answers = prompt(questions)
        if answers == {}:
            raise KeyboardInterrupt
        values.append(answers[field.name])
    return values


class PlatformSetupCli:
    """Base for all platform-specific setup cli commands."""

    platform: str
    platform_specific_settings_class: PlatformSpecificSettings

    def __init__(self, settings: Settings):
        """Initialize the platform setup cli command.

        Args:
            settings (Settings): The settings to use.
        """
        self.settings = settings
        self.logger = get_logger(
            log_name=f"{self.platform}_setup", level=settings.logging_level
        )

    def setup(self) -> None:
        """Setup the platform."""
        platform_settings = self.prompt_for_settings()
        self.settings.platforms[self.platform].append(platform_settings)

    def prompt_for_settings(
        self, exclude_fields: List[str] = ["platform"]
    ) -> PlatformSpecificSettings:
        """Prompt for settings.

        Args:
            exclude_fields (List[str]): The fields to exclude.

        Returns:
            PlatformSpecificSettings: The settings.

        Raises:
            ValueError: If the settings are invalid.
        """
        settings_fields = self.platform_specific_settings_class.__fields__
        questions = []
        answers = {}
        for field in settings_fields.values():
            if field.name in exclude_fields:
                continue
            question = {
                "name": field.name,
                "message": snake_case_to_english(field.name) + ":",
            }
            if lenient_issubclass(field.type_, str):
                question["type"] = "input"
                question["message"] = "Enter a " + question["message"]
            elif lenient_issubclass(field.type_, bool):
                question["type"] = "confirm"
            elif get_origin(field.type_) is Union:
                args = get_args(field.type_)
                if List[str] in args:
                    answers[field.name] = prompt_for_list(field)
                    continue
                else:
                    raise ValueError(f"Unsupported union type for field {field.name}.")
            else:
                raise ValueError(f"Unsupported type for field {field.name}.")

            questions.append(question)
        answers.update(prompt(questions))
        if answers == {}:
            raise ValueError("No answers provided.")
        return self.platform_specific_settings_class(**answers)
