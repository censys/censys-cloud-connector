"""Azure platform-specific settings."""
from typing import TYPE_CHECKING, List, Union

from pydantic import Field, conlist, constr, validator

from censys.cloud_connectors.common.settings import PlatformSpecificSettings

# Avoid mypy error about AzureId not being a valid type.
if TYPE_CHECKING:
    AzureId = str
else:
    AzureId = constr(strip_whitespace=True, min_length=36, max_length=36)


class AzureSpecificSettings(PlatformSpecificSettings):
    """Azure specific settings."""

    platform: str = "Azure"

    subscription_id: conlist(AzureId, min_items=1, unique_items=True)  # type: ignore
    tenant_id: AzureId
    client_id: AzureId
    client_secret: str = Field(min_length=1)

    @validator("subscription_id", pre=True)
    def validate_subscription_id(cls, v: Union[str, List[str]]) -> List[str]:
        """Validate the subscription id.

        Args:
            v (Union[str, List[str]]): The value to validate.

        Returns:
            List[str]: The validated value.
        """
        if isinstance(v, str):
            return [v]
        return v
