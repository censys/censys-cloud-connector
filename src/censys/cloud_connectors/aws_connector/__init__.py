"""AWS specific cloud connector."""
from .settings import AwsSpecificSettings

__connector__ = None
__provider_setup__ = None
__settings__ = AwsSpecificSettings
__all__ = ["__connector__", "__provider_setup__", "__settings__"]
