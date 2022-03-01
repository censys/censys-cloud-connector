"""AWS Cloud Connector."""
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.enums import PlatformEnum


class AwsCloudConnector(CloudConnector):
    """AWS Cloud Connector."""

    platform = PlatformEnum.AWS

    # TODO: Add scanning for AWS
