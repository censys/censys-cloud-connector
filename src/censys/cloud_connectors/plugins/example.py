"""Example Cloud Connector Plugin."""

from censys.cloud_connectors.azure_connector.enums import AzureResourceTypes
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.plugins import (
    CloudConnectorPlugin,
    CloudConnectorPluginRegistry,
    EventContext,
    EventTypeEnum,
)


class ExamplePlugin(CloudConnectorPlugin):
    """Example Plugin."""

    name = "Example"
    version = "0.0.1"

    def enabled(self) -> bool:
        """Check if plugin is enabled.

        Returns:
            True if plugin is enabled, False otherwise.
        """
        return False

    def register(self, registry: CloudConnectorPluginRegistry) -> None:
        """Register the plugin.

        Args:
            registry: Plugin registry.
        """
        registry.register_event_handler(
            EventTypeEnum.SCAN_STARTED,
            self.on_scan_started,
            self,
            provider=ProviderEnum.AZURE,
        )
        registry.register_event_handler(
            EventTypeEnum.SEED_FOUND,
            self.on_add_seed,
            self,
            provider=ProviderEnum.AZURE,
            service=AzureResourceTypes.PUBLIC_IP_ADDRESSES,
        )

    def on_scan_started(self, context: EventContext, **kwargs) -> None:
        """Handle scan start event.

        Args:
            context: Event context.
            kwargs: Additional event data.
        """
        logger = context["connector"].logger
        logger.debug(f"Scan started with context: {context}")

    def on_add_seed(self, context: EventContext, **kwargs) -> None:
        """Handle add seed event.

        Args:
            context: Event context.
            kwargs: Additional event data.
        """
        logger = context["connector"].logger
        logger.debug(f"Adding seed with context: {context}")


__plugin__ = ExamplePlugin
