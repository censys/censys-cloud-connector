from typing import List, Union

from pydantic import Field

from censys.cloud_connectors.common.settings import PlatformSpecificSettings


class AzureSpecificSettings(PlatformSpecificSettings):
    """Azure specific settings."""

    platform: str = "Azure"

    subscription_id: Union[str, List[str]]
    tenant_id: str = Field(min_length=36, max_length=36)
    client_id: str = Field(min_length=36, max_length=36)
    client_secret: str = Field(min_length=1)


__settings__ = AzureSpecificSettings
