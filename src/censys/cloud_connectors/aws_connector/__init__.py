"""AWS specific cloud connector."""
from censys.cloud_connectors.aws_connector.connector import AwsCloudConnector
from censys.cloud_connectors.aws_connector.provider_setup import AwsSetupCli
from censys.cloud_connectors.aws_connector.settings import AwsSpecificSettings

__connector__ = AwsCloudConnector
__provider_setup__ = AwsSetupCli
__settings__ = AwsSpecificSettings
__all__ = ["__connector__", "__provider_setup__", "__settings__"]
