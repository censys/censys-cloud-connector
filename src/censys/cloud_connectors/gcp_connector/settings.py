"""GCP provider-specific settings."""
from pathlib import Path
from typing import Optional

from pydantic import EmailStr, Field

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings

from .enums import GcpSecurityCenterResourceTypes


class GcpSpecificSettings(ProviderSpecificSettings):
    """GCP specific settings."""

    provider = ProviderEnum.GCP

    ignore: Optional[list[GcpSecurityCenterResourceTypes]] = None

    organization_id: int = Field(
        gt=1,
        lt=10**12,
        description="GCP organization ID.",
    )
    service_account_json_file: Path = Field(
        description="Path to service account json file."
    )
    service_account_email: EmailStr = Field(description="Service account email.")

    def parent(self) -> str:
        """Name of the organization assets should belong to.

        Its format is "organizations/[organization_id], folders/[folder_id], or projects/[project_id]".

        Returns:
            str: Parent.
        """
        return f"organizations/{self.organization_id}"

    def get_provider_key(self) -> tuple[int, str]:
        """Get provider key.

        Returns:
            tuple[int, str]: Provider key.
        """
        return self.organization_id, self.service_account_email
