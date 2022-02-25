"""Gcp platform-specific settings."""
from pydantic import Field, FilePath

from censys.cloud_connectors.common.settings import PlatformSpecificSettings


class GcpSpecificSettings(PlatformSpecificSettings):
    """GCP specific settings."""

    platform: str = "Gcp"

    organization_id: str = Field(min_length=36, max_length=36)
    service_account_json_file: FilePath = Field(
        default="service_account.json", env="SERVICE_ACCOUNT_JSON_FILE"
    )


__settings__ = GcpSpecificSettings
