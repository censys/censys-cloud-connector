"""Settings for the Censys Cloud Connector."""
import collections
import importlib
import pathlib
from abc import abstractmethod
from typing import TYPE_CHECKING, DefaultDict, Optional, OrderedDict, Union

import yaml
from pydantic import BaseSettings, Field, HttpUrl, validate_arguments, validator

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


class ProviderSpecificSettings(BaseSettings):
    """Base class for all provider-specific settings."""

    provider: str

    def as_dict(self) -> OrderedDict[str, Union[str, list[str]]]:
        """Return the settings as a dictionary.

        Returns:
            OrderedDict[str, Union[str, List[str]]]: The settings as a dictionary.
        """
        res = OrderedDict()
        settings_as_dict = self.dict()
        if provider_name := settings_as_dict.pop("provider", None):
            res["provider"] = provider_name.lower()
        if ignore := settings_as_dict.pop("ignore", None):
            res["ignore"] = ignore
        res.update(settings_as_dict)
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
            data["provider"] = provider_name.title()
        return cls(**data)

    @abstractmethod
    def get_provider_key(self) -> tuple:
        """Get the provider key.

        Returns:
            tuple: The provider key.
        """
        raise NotImplementedError


class Settings(BaseSettings):
    """Settings for the Cloud Connector."""

    # Providers settings
    providers: DefaultDict[
        ProviderEnum, dict[tuple, ProviderSpecificSettings]
    ] = DefaultDict(dict)

    # Required
    censys_api_key: str = Field(env="CENSYS_API_KEY", min_length=36, max_length=36)

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
    logging_level: str = Field(default="INFO", env="LOGGING_LEVEL")
    dry_run: bool = Field(default=False, env="DRY_RUN")

    # Verification timeout
    validation_timeout: int = Field(default=120, env="VALIDATION_TIMEOUT")

    # Censys
    censys_beta_url: HttpUrl = Field(
        default="https://app.censys.io/api/beta", env="CENSYS_BETA_URL"
    )

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

    class Config:
        """Config for pydantic."""

        env_file = ".env"
        case_sensitive = False

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
