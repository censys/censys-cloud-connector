"""Azure specific settings."""
from typing import Optional, Union

from pydantic import ConstrainedStr, Field, validator

from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings

from .enums import AzureResourceTypes


class AzureId(ConstrainedStr):
    """Azure ID."""

    min_length = 36
    max_length = 36


class AzureSpecificSettings(ProviderSpecificSettings):
    """Azure specific settings."""

    provider = ProviderEnum.AZURE

    ignore: Optional[list[AzureResourceTypes]] = None

    subscription_id: list[AzureId] = Field(min_items=1)
    tenant_id: AzureId
    client_id: AzureId
    client_secret: str = Field(min_length=1)

    @validator("subscription_id", pre=True, allow_reuse=True)
    def validate_subscription_id(cls, v: Union[str, list[str]]) -> list[str]:
        """Validate the subscription id.

        Args:
            v (Union[str, List[str]]): The value to validate.

        Returns:
            List[str]: The validated value.
        """
        if not isinstance(v, list):
            return [v]
        return v

    def get_provider_key(self) -> tuple[str, str]:
        """Get the provider key.

        Returns:
            tuple[str, str]: The provider key.
        """
        return self.tenant_id, self.client_id
