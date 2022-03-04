"""GCP provider-specific settings."""
from pydantic import Field, FilePath

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings


class GcpSpecificSettings(ProviderSpecificSettings):
    """GCP specific settings."""

    provider: str = ProviderEnum.GCP

    service_account_json_file: FilePath = Field(
        description="Path to service account json file."
    )
    organization_id: str = Field(
        min_length=1, max_length=64, description="GCP organization ID."
    )
