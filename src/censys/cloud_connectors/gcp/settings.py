"""GCP platform-specific settings."""
from typing import Union

from pydantic import ConstrainedStr, Field, FilePath, validator

from censys.cloud_connectors.common.enums import PlatformEnum
from censys.cloud_connectors.common.settings import PlatformSpecificSettings


class ProjectId(ConstrainedStr):
    """GCP Project ID."""

    min_length = 6
    max_length = 30


class GcpSpecificSettings(PlatformSpecificSettings):
    """GCP specific settings."""

    platform: str = PlatformEnum.GCP

    service_account_json_file: FilePath = Field(env="GOOGLE_APPLICATION_CREDENTIALS")
    organization_id: str = Field(min_length=36, max_length=36, default=None)
    project_id: str = Field(min_length=6, max_length=30, to_lower=True, default=None)

    @validator("project_id", pre=True, allow_reuse=True)
    def validate_project_id(cls, v: Union[str, list[str]]) -> list[str]:
        """Validate the project id.

        Args:
            v (Union[str, List[str]]): The value to validate.

        Returns:
            List[str]: The validated value.
        """
        if not isinstance(v, list):
            return [v]
        return v
