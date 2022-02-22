"""Settings for the Censys Cloud Connector."""
from collections import defaultdict
from typing import Dict, List, Optional

import yaml
from pydantic import BaseSettings, Field, FilePath, HttpUrl


class PlatformSpecificSettings(BaseSettings):
    """Base class for all platform-specific settings."""

    platform: str


class Settings(BaseSettings):
    """Settings for the Cloud Connector."""

    # Required
    censys_api_key: str = Field(env="CENSYS_API_KEY", min_length=36, max_length=36)
    platforms: Dict[str, List[PlatformSpecificSettings]] = defaultdict(list)

    # Optional
    platforms_config_file: Optional[FilePath] = Field(
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


class AzureSpecificSettings(PlatformSpecificSettings):
    """Azure specific settings."""

    platform: str = "Azure"

    subscription_id: str = Field(min_length=36, max_length=36)
    tenant_id: str = Field(min_length=36, max_length=36)
    client_id: str = Field(min_length=36, max_length=36)
    client_secret: str = Field(min_length=1)


class GcpSpecificSettings(PlatformSpecificSettings):
    """GCP specific settings."""

    platform: str = "Gcp"

    organization_id: str = Field(min_length=36, max_length=36)
    service_account_json_file: FilePath = Field(
        default="service_account.json", env="SERVICE_ACCOUNT_JSON_FILE"
    )


PLATFORM_TO_SETTINGS = {
    "azure": AzureSpecificSettings,
    "gcp": GcpSpecificSettings,
}


def create_azure_settings(platform_config: dict) -> List[AzureSpecificSettings]:
    """Create Azure settings.

    Args:
        platform_config: Platform config.

    Returns:
        List of Azure settings.
    """
    azure_settings: List[AzureSpecificSettings] = []
    if isinstance((subscription_ids := platform_config.get("subscription_id")), list):
        for subscription_id in subscription_ids:
            platform_config["subscription_id"] = subscription_id
            azure_settings.append(AzureSpecificSettings(**platform_config))
    else:
        azure_settings.append(AzureSpecificSettings(**platform_config))
    return azure_settings


PLATFORM_SETTINGS_CREATION_FUNCTIONS = {"azure": create_azure_settings}


def get_platform_settings_from_file(
    file_path: str,
) -> Dict[str, List[PlatformSpecificSettings]]:
    """Get platform settings from file.

    Args:
        file_path: Path to platform settings yml file.

    Returns:
        Dict of platform settings.

    Raises:
        ValueError: If the platform settings file is invalid.
    """
    with open(file_path) as f:
        platform_config = yaml.safe_load(f)

    platforms: Dict[str, List[PlatformSpecificSettings]] = defaultdict(list)
    for platform_config in platform_config:
        platform_name = platform_config.get("platform")
        if not platform_name:
            raise ValueError("Platform name is required")
        platform_name = platform_name.lower()
        platform_settings_creation_func = PLATFORM_SETTINGS_CREATION_FUNCTIONS.get(
            platform_name
        )
        if not platform_settings_creation_func:
            raise ValueError(f"Unknown platform: {platform_name}")
        platforms[platform_name].extend(
            platform_settings_creation_func(platform_config)
        )
    return platforms
