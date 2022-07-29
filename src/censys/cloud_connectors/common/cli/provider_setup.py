"""Base for all provider-specific setup cli commands."""
import logging
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Union, get_origin

import backoff
from InquirerPy import prompt
from InquirerPy.validator import PathValidator
from prompt_toolkit.validation import Document, ValidationError, Validator
from pydantic.fields import ModelField
from pydantic.utils import lenient_issubclass
from rich.progress import BarColumn, Progress, TaskID, TextColumn, TimeElapsedColumn

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.logger import get_logger
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
    """
    values: list[str] = []
    while True:
        field_name = snake_case_to_english(field.name)
        questions: list[dict[str, Union[str, Validator]]] = [
            {
                "type": "input",
                "name": field.name,
                "message": f"Enter a {field_name}:",
                "validate": generate_validation(field),
            },
            {
                "type": "confirm",
                "name": "add_another",
                "message": f"Add another {field_name}?",
            },
        ]
        try:
            answers = prompt(questions)
            if not answers:
                raise KeyboardInterrupt
        except KeyboardInterrupt:
            break
        answer = str(answers[field.name])
        values.append(answer.strip())
        if not answers.get("add_another", False):
            break
    return values


def backoff_wrapper(
    exception: Union[type[Exception], Iterable[type[Exception]]],
    task_description: Optional[str] = None,
    **bo_kwargs: Any,
) -> Callable:
    """Wrap a method with a backoff decorator.

    Args:
        exception (Type[Exception] | Iterable[Type[Exception]]): The exception(s) to backoff on.
        task_description (Optional[str]): The task description to use.
        **bo_kwargs: The backoff decorator arguments.

    Returns:
        Callable: The wrapped method.
    """

    def decorator(method: Callable) -> Callable:
        @wraps(method)
        def wrapper(*args, **kwargs):
            _progress: Optional[Progress] = None
            _task: Optional[TaskID] = None

            def on_success(_: Any) -> None:
                if _progress and _task:
                    _progress.stop_task(_task)

            self: "ProviderSetupCli" = args[0]

            default_kwargs = {
                "wait_gen": backoff.expo,
                "exception": exception,
                "max_time": self.settings.validation_timeout,
                "raise_on_giveup": False,
                "on_success": on_success,
                "logger": self.logger,
                "backoff_log_level": logging.DEBUG,
            }
            default_kwargs.update(bo_kwargs)

            # columns = Progress.get_default_columns()
            columns = (
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
            )
            with Progress(*columns) as progress:
                _progress = progress
                task = progress.add_task(
                    task_description or "[red]Loading...", transient=True, total=None
                )
                progress.start_task(task)
                _task = task

                @backoff.on_exception(**default_kwargs)
                def _method():
                    res = method(*args, **kwargs)
                    progress.advance(task)
                    return res

                return _method()

        return wrapper

    return decorator


class ProviderSetupCli(BaseCli):
    """Base for all provider-specific setup cli commands."""

    provider: ProviderEnum
    provider_specific_settings_class: type[ProviderSpecificSettings]
    settings: Settings
    extra_instructions: dict[str, str] = {}

    def __init__(self, settings: Settings):
        """Initialize the provider setup cli command.

        Args:
            settings (Settings): The settings to use.
        """
        self.settings = settings
        self.logger = get_logger("cloud_connector_setup", self.settings.logging_level)

    def setup(self) -> None:
        """Setup the provider.

        This function is called by the CLI when the user selects the manual
        input configuration option.

        Raises:
            KeyboardInterrupt: If the user cancels the setup.
        """
        provider_settings = self.prompt_for_settings()
        answers = prompt(
            {
                "type": "confirm",
                "name": "save",
                "message": f"Save to {self.settings.providers_config_file}?",
                "default": True,
            }
        )
        if not answers.get("save"):  # pragma: no cover
            raise KeyboardInterrupt
        self.add_provider_specific_settings(provider_settings)

    def add_provider_specific_settings(
        self, provider_settings: ProviderSpecificSettings
    ) -> None:
        """Add provider-specific settings to the settings.

        Args:
            provider_settings (ProviderSpecificSettings): The provider-specific settings to add.
        """
        # TODO: Confirm overwrite if it exists
        self.settings.providers[self.provider][
            provider_settings.get_provider_key()
        ] = provider_settings

    def prompt_for_settings(self) -> ProviderSpecificSettings:
        """Prompt for settings.

        Returns:
            ProviderSpecificSettings: The settings.

        Raises:
            ValueError: If the settings are invalid.
        """
        excluded_fields: list[str] = ["provider", "ignore"]
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
                "instruction": self.extra_instructions.get(field.name),
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
                question["message"] = "Enter a " + question["message"]  # type: ignore
                question["default"] = None
                question["min_allowed"] = getattr(field_type, "gt", 0)
                question["max_allowed"] = getattr(field_type, "lt", None)
            elif lenient_issubclass(field_type, str):
                question["type"] = "input"
                question["message"] = "Enter a " + question["message"]  # type: ignore

                # TODO: Is this something we want?
                if "secret" in field.name.lower():
                    question["type"] = "password"
            elif lenient_issubclass(field_type, Path):
                question["type"] = "filepath"
                question["message"] = "Select a " + question["message"]  # type: ignore
                question["default"] = self.settings.secrets_dir + "/"
                question["filter"] = lambda path_str: Path(path_str).name
                question["validate"] = PathValidator(is_file=True)
            else:  # pragma: no cover
                raise ValueError(f"Unsupported type for field {field.name}.")

            answers.update(self.prompt(question))
        if not answers:  # pragma: no cover
            raise ValueError("No answers provided.")
        return self.provider_specific_settings_class(**answers)
