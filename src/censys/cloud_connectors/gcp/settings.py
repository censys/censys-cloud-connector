"""GCP provider-specific settings."""
from pydantic import Field, FilePath

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings


class GcpSpecificSettings(ProviderSpecificSettings):
    """GCP specific settings."""

    provider: str = ProviderEnum.GCP

    organization_id: int = Field(
        gt=1,
        description="GCP organization ID.",
    )
    service_account_json_file: FilePath = Field(
        description="Path to service account json file."
    )

    def parent(self) -> str:
        """Name of the organization assets should belong to.

        Its format is "organizations/[organization_id], folders/[folder_id], or projects/[project_id]".

        Returns:
            str: Parent.
        """
        return f"organizations/{self.organization_id}"
