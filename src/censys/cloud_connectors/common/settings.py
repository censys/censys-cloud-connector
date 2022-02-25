"""Settings for the Censys Cloud Connector."""
import collections
import importlib
from typing import DefaultDict, Dict, List, OrderedDict, Union

import yaml
from pydantic import BaseSettings, Field, HttpUrl


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


class PlatformSpecificSettings(BaseSettings):
    """Base class for all platform-specific settings."""

    platform: str

    def as_dict(self) -> OrderedDict[str, Union[str, List[str]]]:
        """Return the settings as a dictionary.

        Returns:
            OrderedDict[str, Union[str, List[str]]]: The settings as a dictionary.
        """
        res = OrderedDict()
        settings_as_dict = self.dict()
        if platform_name := settings_as_dict.get("platform"):
            settings_as_dict["platform"] = platform_name.lower()
        for key in ["platform"]:
            res[key] = settings_as_dict.pop(key)
        res.update(settings_as_dict)
        return res

    @classmethod
    def from_dict(cls, data: Dict):
        """Create a PlatformSpecificSettings object from a dictionary.

        Args:
            data (Dict): The dictionary to use.

        Returns:
            PlatformSpecificSettings: The settings.
        """
        if platform_name := data.get("platform"):
            data["platform"] = platform_name.title()
        return cls(**data)


class Settings(BaseSettings):
    """Settings for the Cloud Connector."""

    # Required
    censys_api_key: str = Field(env="CENSYS_API_KEY", min_length=36, max_length=36)
    platforms: DefaultDict[str, list] = collections.defaultdict(list)

    # Optional
    platforms_config_file: str = Field(
        default="platforms.yml", env="PLATFORMS_CONFIG_FILE"
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

    def read_platforms_config_file(self):
        """Read platform config file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: Platform name is not valid.
            ImportError: If the platform module cannot be imported.
        """
        try:
            with open(self.platforms_config_file) as f:
                platform_config = yaml.safe_load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Platform config file not found: {self.platforms_config_file}"
            ) from e

        if not platform_config:
            return

        for platform_config in platform_config:
            platform_name = platform_config.get("platform")
            if not platform_name:
                raise ValueError("Platform name is required")
            platform_name = platform_name.lower()
            try:
                platform_settings_cls = importlib.import_module(
                    f"censys.cloud_connectors.{platform_name}.settings"
                ).__settings__
            except ImportError:
                raise ImportError(
                    f"Could not import the settings for the {platform_name} platform"
                )
            platform_settings = platform_settings_cls.from_dict(platform_config)
            self.platforms[platform_name].append(platform_settings)

    def write_platforms_config_file(self):
        """Write platforms config file."""
        all_platforms = []
        for platform_settings in self.platforms.values():
            all_platforms.extend([pss.as_dict() for pss in platform_settings])
        with open(self.platforms_config_file, "w") as f:
            yaml.safe_dump(all_platforms, f, default_flow_style=False, sort_keys=False)

    def scan_all(self):
        """Scan all platforms.

        Raises:
            ImportError: If the platform module cannot be imported.
        """
        for platform_name in self.platforms.keys():
            try:
                connector_cls = importlib.import_module(
                    f"censys.cloud_connectors.{platform_name}.connector"
                ).__connector__
            except ImportError:
                raise ImportError(
                    f"Could not import the connector for the {platform_name} platform"
                )
            connector = connector_cls(self)
            connector.scan_all()
