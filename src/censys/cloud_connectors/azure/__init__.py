"""Azure specific cloud connector."""
from .connector import AzureCloudConnector
from .platform_setup import AzureSetupCli
from .settings import AzureSpecificSettings

__connector__ = AzureCloudConnector
__platform_setup__ = AzureSetupCli
__settings__ = AzureSpecificSettings

__all__ = ["__connector__", "__platform_setup__", "__settings__"]
