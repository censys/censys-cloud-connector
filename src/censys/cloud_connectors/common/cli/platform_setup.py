"""Base for all platform-specific setup cli commands."""
from logging import Logger
from typing import Callable, List, Type, Union, get_args, get_origin

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


def generate_validation(field: ModelField) -> Callable:
    """Generate a validation function for a field.

    Args:
        field (ModelField): The field to generate the validation for.

    Returns:
        Callable: The validation function.
    """

    def validate(value: str) -> Union[bool, str]:
        """Validate the value.

        Args:
            value (str): The value to validate.

        Returns:
            Union[bool, str]: True or the error message.
        """
        _, error = field.validate(value, {}, loc=field.name)
        if not error:
            return True
        if isinstance(error, list):
            error = error[0]
        return str(error.exc)  # type: ignore

    return validate


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
            "validate": generate_validation(field),
        },
        {
            "type": "confirm",
            "name": "add_another",
            "message": "Add another",
        },
    ]
    answers = prompt(questions)
    if not answers:  # pragma: no cover
        raise KeyboardInterrupt
    values = [answers[field.name]]
    while answers.get("add_another", False):
        answers = prompt(questions)
        if not answers:
            # break instead of raise KeyboardInterrupt
            break
        values.append(str(answers[field.name]).strip())
    return values


class PlatformSetupCli:
    """Base for all platform-specific setup cli commands."""

    platform: str
    platform_specific_settings_class: Type[PlatformSpecificSettings]
    settings: Settings
    logger: Logger

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

    def prompt_for_settings(self) -> PlatformSpecificSettings:
        """Prompt for settings.

        Returns:
            PlatformSpecificSettings: The settings.

        Raises:
            ValueError: If the settings are invalid.
        """
        excluded_fields: List[str] = ["platform"]
        settings_fields = self.platform_specific_settings_class.__fields__
        questions = []
        answers = {}
        for field in settings_fields.values():
            if field.name in excluded_fields:
                continue
            question = {
                "name": field.name,
                "message": f"{snake_case_to_english(field.name)}:",
                "validate": generate_validation(field),
            }
            if lenient_issubclass(field.type_, str):
                question["type"] = "input"
                question["message"] = "Enter a " + question["message"]  # type: ignore
            elif lenient_issubclass(field.type_, bool):
                question["type"] = "confirm"
            elif get_origin(field.type_) is Union:
                args = get_args(field.type_)
                if any([lenient_issubclass(arg, list) for arg in args]):
                    answers[field.name] = prompt_for_list(field)
                    continue
                else:
                    self.logger.debug(f"Unsupported union type: {field.type_}")
                    raise ValueError(f"Unsupported union type for field {field.name}.")
            else:
                raise ValueError(f"Unsupported type for field {field.name}.")

            questions.append(question)
        answers.update(prompt(questions))
        if not answers:
            raise ValueError("No answers provided.")
        return self.platform_specific_settings_class(**answers)
