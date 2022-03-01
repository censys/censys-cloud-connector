"""GCP specific cloud connector."""
from .connector import GcpCloudConnector
from .settings import GcpSpecificSettings

__connector__ = GcpCloudConnector
__provider_setup__ = None
__settings__ = GcpSpecificSettings

__all__ = ["__connector__", "__provider_setup__", "__settings__"]
