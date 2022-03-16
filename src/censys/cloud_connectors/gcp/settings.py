"""GCP provider-specific settings."""
from pathlib import Path
from typing import Optional

from pydantic import Field, FilePath, validator

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings


class GcpSpecificSettings(ProviderSpecificSettings):
    """GCP specific settings."""

    provider: str = ProviderEnum.GCP

    organization_id: str = Field(
        min_length=1, max_length=64, description="GCP organization ID."
    )
    service_account_json_file: FilePath[Optional] = Field(
        description="Path to service account json file."
    )

    @validator("service_account_json_file", pre=True)
    def validate_service_account_json_file(cls, v: str) -> Path:
        """Validate service account json file.

        Args:
            v (str): Path to service account json file.

        Returns:
            Path: Path to service account json file.
        """
        path = Path(v)
        if "~" in v:
            path = path.expanduser().resolve()
        return path

    def parent(self) -> str:
        """Name of the organization assets should belong to.

        Its format is "organizations/[organization_id], folders/[folder_id], or projects/[project_id]".

        Returns:
            str: Parent.
        """
        return f"organizations/{self.organization_id}"
