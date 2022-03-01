"""Settings for the Censys Cloud Connector."""
import collections
import importlib
from typing import DefaultDict, OrderedDict, Union

import yaml
from pydantic import BaseSettings, Field, HttpUrl

from .enums import ProviderEnum


def ordered_dict_representer(
    dumper: yaml.Dumper, data: OrderedDict
) -> yaml.nodes.MappingNode:  # pragma: no cover
    """Represent a ordereddict as a mapping.

    Args:
        dumper (yaml.Dumper): The dumper.
        data (OrderedDict): The data to represent.

    Returns:
        yaml.nodes.MappingNode: The mapping node.
    """
    return yaml.representer.SafeRepresenter.represent_dict(dumper, data.items())


"""This allows ordereddict to be represented as a mapping."""
yaml.representer.SafeRepresenter.add_representer(
    collections.OrderedDict, ordered_dict_representer  # type: ignore
)


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
        if provider_name := settings_as_dict.get("provider"):
            settings_as_dict["provider"] = provider_name.lower()
        for key in ["provider"]:
            res[key] = settings_as_dict.pop(key)
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


class Settings(BaseSettings):
    """Settings for the Cloud Connector."""

    # Providers settings
    providers: DefaultDict[str, list] = collections.defaultdict(list)

    # Required
    censys_api_key: str = Field(env="CENSYS_API_KEY", min_length=36, max_length=36)

    # Optional
    providers_config_file: str = Field(
        default="providers.yml", env="PROVIDERS_CONFIG_FILE"
    )
    scan_frequency: int = Field(default=-1)
    logging_level: str = Field(default="INFO", env="LOGGING_LEVEL")
    search_ips: bool = Field(default=True, env="SEARCH_IPS")
    search_containers: bool = Field(default=True, env="SEARCH_CONTAINERS")
    search_databases: bool = Field(default=True, env="SEARCH_DATABASES")
    search_dns: bool = Field(default=True, env="SEARCH_DNS")
    search_storage: bool = Field(default=True, env="SEARCH_STORAGE")

    # Censys
    censys_beta_url: HttpUrl = Field(
        default="https://app.censys.io/api/beta", env="CENSYS_BETA_URL"
    )

    class Config:
        """Config for pydantic."""

        env_file = ".env"

    def read_providers_config_file(self):
        """Read provider config file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: Provider name is not valid.
        """
        try:
            with open(self.providers_config_file) as f:
                provider_config = yaml.safe_load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Provider config file not found: {self.providers_config_file}"
            ) from e

        if not provider_config:
            return

        for provider_config in provider_config:
            provider_name = provider_config.get("provider")
            if not provider_name:
                raise ValueError("Provider name is required")
            try:
                provider = ProviderEnum[provider_name.upper()]
            except KeyError as e:
                raise ValueError(f"Provider name is not valid: {provider_name}") from e
            provider_settings_cls = importlib.import_module(
                provider.module_path()
            ).__settings__
            provider_settings = provider_settings_cls.from_dict(provider_config)
            self.providers[provider].append(provider_settings)

    def write_providers_config_file(self):
        """Write providers config file."""
        all_providers = []
        for provider_settings in self.providers.values():
            all_providers.extend([pss.as_dict() for pss in provider_settings])
        with open(self.providers_config_file, "w") as f:
            yaml.safe_dump(all_providers, f, default_flow_style=False, sort_keys=False)

    def scan_all(self):
        """Scan all providers."""
        for provider in self.providers.keys():
            connector_cls = importlib.import_module(
                provider.module_path()
            ).__connector__
            connector = connector_cls(self)
            connector.scan_all()
