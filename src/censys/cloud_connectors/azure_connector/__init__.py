"""Azure specific cloud connector."""
from .connector import AzureCloudConnector
from .provider_setup import AzureSetupCli
from .settings import AzureSpecificSettings

__connector__ = AzureCloudConnector
__provider_setup__ = AzureSetupCli
__settings__ = AzureSpecificSettings

__all__ = ["__connector__", "__provider_setup__", "__settings__"]
