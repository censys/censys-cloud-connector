"""Settings for the Censys Cloud Connector."""
import collections
import importlib
import pathlib
from abc import abstractmethod
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, DefaultDict, Optional, Union

import yaml
from pydantic import BaseSettings, Field, validate_arguments, validator

from .. import __version__ as censys_cloud_connectors_version
from .enums import ProviderEnum

if TYPE_CHECKING:
    from censys.cloud_connectors.common.connector import CloudConnector


def ordered_dict_representer(
    dumper: yaml.SafeDumper, data: OrderedDict
) -> yaml.nodes.MappingNode:  # pragma: no cover
    """Represent a ordereddict as a mapping.

    Args:
        dumper (yaml.SafeDumper): The dumper.
        data (OrderedDict): The data to represent.

    Returns:
        yaml.nodes.MappingNode: The mapping node.
    """
    return yaml.representer.SafeRepresenter.represent_dict(dumper, data.items())


def posix_path_representer(
    dumper: yaml.SafeDumper, path: pathlib.PosixPath
) -> yaml.nodes.ScalarNode:  # pragma: no cover
    """Represent a path as a scalar.

    Args:
        dumper (yaml.SafeDumper): The dumper.
        path (pathlib.PosixPath): The path to represent.

    Returns:
        yaml.nodes.ScalarNode: The scalar node.
    """
    return yaml.representer.SafeRepresenter.represent_str(dumper, str(path))


type_to_representer = {
    collections.OrderedDict: ordered_dict_representer,
    pathlib.PosixPath: posix_path_representer,
}

# Add additional yaml representers.
for type_, representer in type_to_representer.items():
    yaml.representer.SafeRepresenter.add_representer(type_, representer)  # type: ignore


def remove_none_values(data: Any) -> Any:
    """Remove all keys with a value of None.

    Args:
        data (Any): The data to remove the keys from.

    Returns:
        Any: The data with the keys removed.
    """
    if not isinstance(data, dict):
        return data
    for key, value in data.items():
        if isinstance(value, dict):
            data[key] = remove_none_values(value)
        if isinstance(value, list):
            data[key] = [remove_none_values(item) for item in value]
    return {key: value for key, value in data.items() if value is not None}


class ProviderSpecificSettings(BaseSettings):
    """Base class for all provider-specific settings."""

    provider: str
    ignore: Optional[list] = None

    def as_dict(self) -> OrderedDict[str, Union[str, list[str]]]:
        """Return the settings as a dictionary.

        Returns:
            OrderedDict[str, Union[str, List[str]]]: The settings as a dictionary.
        """
        res: OrderedDict[str, Union[str, list[str]]] = OrderedDict()
        settings_as_dict = self.dict()
        if provider_name := settings_as_dict.pop("provider", None):
            res["provider"] = str(ProviderEnum[provider_name])
        res.update(remove_none_values(settings_as_dict))
        return res

    @classmethod
    def from_dict(cls, data: dict):
        """Create a ProviderSpecificSettings object from a dictionary.

        Args:
            data (dict): The dictionary to use.

        Returns:
            ProviderSpecificSettings: The settings.
        """
        if provider_name := data.get("provider"):
            data["provider"] = str(ProviderEnum[provider_name])
        return cls(**data)

    @abstractmethod
    def get_provider_key(self) -> tuple:
        """Get the provider key.

        Returns:
            tuple: The provider key.
        """
        raise NotImplementedError

    @abstractmethod
    def get_provider_payload(self) -> dict:
        """Get the provider payload.

        Returns:
            dict: The provider payload.
        """
        raise NotImplementedError


class Settings(BaseSettings):
    """Settings for the Cloud Connector."""

    # Providers settings
    providers: DefaultDict[
        ProviderEnum, dict[tuple, ProviderSpecificSettings]
    ] = DefaultDict(dict)

    # Required
    censys_api_key: str = Field(
        env="CENSYS_API_KEY",
        min_length=36,
        max_length=36,
        description="Censys ASM API key",
    )
    censys_asm_api_base_url: str = Field(
        default="https://app.censys.io/api",
        env="CENSYS_ASM_API_BASE_URL",
        description="Censys ASM API Base URL",
    )
    censys_user_agent: str = Field(
        default=f"censys-cloud-connector/{censys_cloud_connectors_version}",
        env="CENSYS_USER_AGENT",
        description="Censys User Agent",
    )
    censys_cookies: dict = Field(
        default={}, env="CENSYS_COOKIES", description="Censys Cookies"
    )

    # Optional
    providers_config_file: str = Field(
        default="providers.yml",
        env="PROVIDERS_CONFIG_FILE",
        description="Providers config file",
    )
    secrets_dir: str = Field(
        default="./secrets",
        env="SECRETS_DIR",
        description="Directory containing secrets",
    )
    logging_level: str = Field(
        default="INFO",
        env="LOGGING_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    dry_run: bool = Field(
        default=False,
        env="DRY_RUN",
        description="Dry run (i.e. do not submit any data)",
    )
    healthcheck_enabled: bool = Field(
        default=True,
        env="HEALTHCHECK_ENABLED",
        description="Enable healthcheck",
    )

    # Verification timeout
    validation_timeout: int = Field(
        default=120,
        env="VALIDATION_TIMEOUT",
        description="Provider Setup CLI Validation timeout",
    )

    # Plugins
    aws_tags_plugin_enabled: bool = Field(
        default=False,
        env="AWS_TAGS_PLUGIN_ENABLED",
        description="Enable AWS Tags plugin",
    )

    class Config:
        """Config for pydantic."""

        case_sensitive = False

    @validator("secrets_dir")
    def validate_secrets_dir(cls, v):
        """Validate secrets_dir.

        Ensure value doesn't end with a slash

        Args:
            v (str): The value to validate.

        Returns:
            str: The validated value.
        """
        if v.endswith("/"):
            v = v[:-1]
        return v

    @validate_arguments
    def read_providers_config_file(
        self, selected_providers: Optional[list[ProviderEnum]] = None
    ):
        """Read provider config file.

        Args:
            selected_providers (Optional[list[ProviderEnum]]): The providers to read.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: Provider name is not valid.
        """
        try:
            with open(self.providers_config_file) as f:
                providers_config = yaml.safe_load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Provider config file not found: {self.providers_config_file}"
            ) from e

        if not providers_config:
            return

        for provider_config in providers_config:
            provider_name = provider_config.get("provider")
            if not provider_name:
                raise ValueError("Provider name is required")
            try:
                provider = ProviderEnum[provider_name]
            except KeyError as e:
                raise ValueError(f"Provider name is not valid: {provider_name}") from e
            if selected_providers and provider not in selected_providers:
                continue
            provider_settings_cls: ProviderSpecificSettings = importlib.import_module(
                provider.module_path()
            ).__settings__
            provider_settings = provider_settings_cls.from_dict(provider_config)
            self.providers[provider][
                provider_settings.get_provider_key()
            ] = provider_settings

    def write_providers_config_file(self):
        """Write providers config file."""
        all_providers = []
        for provider_settings in self.providers.values():
            all_providers.extend([pss.as_dict() for pss in provider_settings.values()])
        with open(self.providers_config_file, "w") as f:
            yaml.safe_dump(all_providers, f, default_flow_style=False, sort_keys=False)

    def scan_all(self):
        """Scan all providers.

        Raises:
            ModuleNotFoundError: If the module does not exist.
        """
        for provider in self.providers.keys():
            try:
                connector_cls = importlib.import_module(
                    provider.module_path()
                ).__connector__
            except ModuleNotFoundError as e:
                raise ModuleNotFoundError(
                    f"Connector module not found for provider: {provider}"
                ) from e
            connector: "CloudConnector" = connector_cls(self)
            connector.scan_all()
