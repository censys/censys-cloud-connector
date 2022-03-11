"""Base for all provider-specific setup cli commands."""
from typing import get_origin

from InquirerPy import prompt
from InquirerPy.validator import PathValidator
from prompt_toolkit.validation import Document, ValidationError, Validator
from pydantic import FilePath
from pydantic.fields import ModelField
from pydantic.utils import lenient_issubclass

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings, Settings

from .base import BaseCli


def snake_case_to_english(snake_case: str) -> str:
    """Convert a snake case string to an English sentence.

    Args:
        snake_case (str): The snake case string.

    Returns:
        str: The English sentence.
    """
    return " ".join(word.capitalize() for word in snake_case.split("_"))


def generate_validation(field: ModelField) -> Validator:
    """Generate a validation function for a field.

    Args:
        field (ModelField): The field to generate the validation for.

    Returns:
        Validator: The validation class.
    """

    class FieldValidator(Validator):
        def validate(self, document: Document) -> None:
            """Validate the value.

            Args:
                document (Document): The document to validate.

            Raises:
                ValidationError: If the value is invalid.
            """
            _, error = field.validate(document.text, {}, loc=field.name)
            if not error:
                return
            while isinstance(error, list):  # pragma: no cover
                # Sometimes the error is embedded in a nested list
                error = error[0]
            raise ValidationError(
                message=str(error.exc), cursor_position=document.cursor_position  # type: ignore
            )

    return FieldValidator()


def prompt_for_list(field: ModelField) -> list[str]:
    """Prompt for a list of values.

    Args:
        field (ModelField): The field to prompt for.

    Returns:
        List[str]: The list of values.

    Raises:
        KeyboardInterrupt: If the user cancels the prompt.
    """
    field_name = snake_case_to_english(field.name)
    questions = [
        {
            "type": "input",
            "name": field.name,
            "message": f"Enter a {field_name}",
            "validate": generate_validation(field),
        },
        {
            "type": "confirm",
            "name": "add_another",
            "message": f"Add another {field_name}?",
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


class ProviderSetupCli(BaseCli):
    """Base for all provider-specific setup cli commands."""

    provider: ProviderEnum
    provider_specific_settings_class: type[ProviderSpecificSettings]
    settings: Settings

    def __init__(self, settings: Settings):
        """Initialize the provider setup cli command.

        Args:
            settings (Settings): The settings to use.
        """
        self.settings = settings

    def setup(self) -> None:
        """Setup the provider."""
        provider_settings = self.prompt_for_settings()
        self.add_provider_specific_settings(provider_settings)

    def add_provider_specific_settings(
        self, provider_settings: ProviderSpecificSettings
    ) -> None:
        """Add provider-specific settings to the settings.

        Args:
            provider_settings (ProviderSpecificSettings): The provider-specific settings to add.
        """
        self.settings.providers[self.provider].append(provider_settings)

    def prompt_for_settings(self) -> ProviderSpecificSettings:
        """Prompt for settings.

        Returns:
            ProviderSpecificSettings: The settings.

        Raises:
            ValueError: If the settings are invalid.
        """
        excluded_fields: list[str] = ["provider"]
        settings_fields: dict[
            str, ModelField
        ] = self.provider_specific_settings_class.__fields__
        answers = {}
        for field in settings_fields.values():
            if field.name in excluded_fields:
                continue
            question = {
                "name": field.name,
                "message": f"{snake_case_to_english(field.name)}:",
                "validate": generate_validation(field),
            }
            field_type = field.type_
            outer_type = field.outer_type_
            if lenient_issubclass(outer_type, list) or lenient_issubclass(
                get_origin(outer_type), list
            ):
                answers[field.name] = prompt_for_list(field)
                continue
            elif lenient_issubclass(field_type, bool):
                question["type"] = "confirm"
            elif lenient_issubclass(field_type, (int, float)):
                question["type"] = "number"
                question["float_allowed"] = lenient_issubclass(field_type, float)
            elif lenient_issubclass(field_type, str):
                question["type"] = "input"
                question["message"] = "Enter a " + question["message"]  # type: ignore

                # TODO: Is this something we want?
                if "secret" in field.name.lower():
                    question["type"] = "password"
            elif lenient_issubclass(field_type, FilePath):
                question["type"] = "filepath"
                question["validate"] = PathValidator(is_file=True)
            else:  # pragma: no cover
                raise ValueError(f"Unsupported type for field {field.name}.")

            answers.update(self.prompt(question))
        if not answers:  # pragma: no cover
            raise ValueError("No answers provided.")
        return self.provider_specific_settings_class(**answers)
