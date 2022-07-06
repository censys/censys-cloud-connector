"""AWS specific cloud connector."""
from censys.cloud_connectors.aws_connector.connector import AwsCloudConnector

from .settings import AwsSpecificSettings

__connector__ = AwsCloudConnector
__provider_setup__ = None
__settings__ = AwsSpecificSettings
__all__ = ["__connector__", "__provider_setup__", "__settings__"]
