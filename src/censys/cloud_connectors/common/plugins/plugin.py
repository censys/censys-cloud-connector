"""Cloud Connector Plugin Class."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from censys.cloud_connectors.common.settings import Settings

if TYPE_CHECKING:
    from censys.cloud_connectors.common.plugins.registry import (
        CloudConnectorPluginRegistry,
    )


class CloudConnectorPlugin(ABC):
    """Base class for plugins."""

    name: str
    version: str
    settings: Settings

    def __init__(self, settings: Settings):
        """Initialize the plugin.

        This method is called when the plugin is loaded.

        Args:
            settings (Settings): The settings to use.

        Raises:
            NotImplementedError: If not implemented.
        """
        if not hasattr(self, "name"):
            raise NotImplementedError("Plugin must define a name.")
        if not hasattr(self, "version"):
            raise NotImplementedError("Plugin must define a version.")
        self.settings = settings

    @abstractmethod
    def enabled(self) -> bool:
        """Check if the plugin is enabled.

        Returns:
            bool: True if the plugin is enabled.
        """
        raise NotImplementedError("Plugin must implement enabled.")

    @abstractmethod
    def register(self, registry: "CloudConnectorPluginRegistry"):
        """Register the plugin.

        Args:
            registry: Plugin registry.
        """
        raise NotImplementedError("Plugin must implement register.")
