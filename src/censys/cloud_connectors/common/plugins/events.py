"""Cloud Connector Event Types."""
from enum import Enum
from typing import TYPE_CHECKING, Optional, TypedDict, Union

from censys.cloud_connectors.common.enums import EventTypeEnum, ProviderEnum

if TYPE_CHECKING:
    from censys.cloud_connectors.common.connector import CloudConnector


class EventContext(TypedDict):
    """EventContext data."""

    event_type: EventTypeEnum
    provider: Optional[ProviderEnum]
    service: Optional[Union[str, Enum]]
    connector: "CloudConnector"
