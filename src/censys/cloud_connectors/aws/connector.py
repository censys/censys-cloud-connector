"""AWS Cloud Connector."""
from censys.cloud_connectors.common.connector import CloudConnector


class AwsCloudConnector(CloudConnector):
    """AWS Cloud Connector."""

    platform = "aws"

    # TODO: Add scanning for AWS
