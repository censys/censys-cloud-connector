"""Cloud Connector Plugin Registry."""
from enum import Enum
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Protocol, Union

from censys.cloud_connectors.common.enums import EventTypeEnum, ProviderEnum
from censys.cloud_connectors.common.settings import Settings

from .events import EventContext

if TYPE_CHECKING:
    from .plugin import CloudConnectorPlugin


class EventHandlerCallable(Protocol):
    """Event handler callable."""

    def __call__(self, context: EventContext, **kwargs) -> None:
        """Handle the event.

        Args:
            context: Event context.
            kwargs: Additional event data.
        """
        ...


class CloudConnectorPluginRegistry:
    """Registry for Cloud Connector plugins.

    Uses the Singleton pattern.
    """

    _instance = None
    # A handlers hashmap including the handler function, the plugin name and version, with an optional provider and service
    _handlers: dict[
        EventTypeEnum,
        list[
            tuple[
                EventHandlerCallable,
                str,
                str,
                Optional[ProviderEnum],
                Optional[Union[str, Enum]],
            ]
        ],
    ] = {}

    logger: Logger
    settings: Settings

    def __init__(self):
        """Initialize the registry.

        Raises:
            Exception: If the registry is already initialized.
        """
        if CloudConnectorPluginRegistry._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            CloudConnectorPluginRegistry._instance = self

    @classmethod
    def get_instance(cls):
        """Get the singleton instance.

        Returns:
            Instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def load_plugins(cls, settings: Settings, logger: Logger) -> None:
        """Load plugins from the plugins directory.

        Args:
            settings: Settings.
            logger: Logger.
        """
        plugins_dir = Path(__file__).parent.parent.parent / "plugins"

        # Find all instances of CloudConnectorPlugin in the external plugins directory
        # and register them
        registry = cls.get_instance()
        registry.logger = logger
        registry.settings = settings
        # List all python files in the plugins directory, ignore __init__.py
        for plugin_file in [
            f for f in plugins_dir.glob("*.py") if f.name != "__init__.py"
        ]:
            try:
                # Import the plugin module
                plugin_module = __import__(
                    f"censys.cloud_connectors.plugins.{plugin_file.stem}",
                    fromlist=["__plugin__"],
                )
                # Get the CloudConnectorPlugin class from the module
                plugin_class: type["CloudConnectorPlugin"] = plugin_module.__plugin__
                # Instantiate the plugin class
                plugin = plugin_class(settings)

                # Skip disabled plugins
                if not plugin.enabled():
                    continue

                # Register the plugin
                plugin.register(registry)
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_file.stem}: {e}")
                continue

    def register_event_handler(
        self,
        event_type: EventTypeEnum,
        handler: EventHandlerCallable,
        plugin: "CloudConnectorPlugin",
        provider: Optional[ProviderEnum] = None,
        service: Optional[Union[str, Enum]] = None,
    ):
        """Register an event handler.

        Args:
            event_type: Event type.
            handler: Event handler.
            plugin: Plugin.
            provider: Cloud service provider.
            service: Cloud service.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(
            (handler, plugin.name, plugin.version, provider, service)
        )

    def get_event_handlers(
        self,
        event_type: EventTypeEnum,
        provider: Optional[ProviderEnum] = None,
        service: Optional[Union[str, Enum]] = None,
    ) -> list[EventHandlerCallable]:
        """Get event handlers for an event.

        Args:
            event_type (EventTypeEnum): Event type.
            provider (ProviderEnum, optional): Cloud service provider.
            service (str, optional): Cloud service.

        Returns:
            Event handlers.
        """
        handlers = []
        for handler, _, _, handler_provider, handler_service in self._handlers.get(
            event_type, []
        ):
            if (
                provider is None
                or provider == handler_provider
                or handler_provider is None
            ) and (
                service is None or service == handler_service or handler_service is None
            ):
                handlers.append(handler)
        return handlers

    @classmethod
    def dispatch_event(
        cls,
        context: EventContext,
        **kwargs,
    ) -> None:
        """Dispatch an event.

        Args:
            context: Event context.
            kwargs: Additional event data.
        """
        registry = cls.get_instance()
        for handler in registry.get_event_handlers(
            context["event_type"],
            provider=context.get("provider"),
            service=context.get("service"),
        ):
            handler(context, **kwargs)
