"""Enums for AWS."""
from enum import Enum


class AwsDefaults(str, Enum):
    """Default values for AWS connector."""

    STACK_SET_NAME = "CensysCloudConnector"
    ROLE_NAME = "CensysCloudConnectorRole"  # Compatible with existing connector
    ROLE_SESSION_NAME = "censys-cloud-connector"

    def __str__(self) -> str:
        """Get the string representation of the message.

        Returns:
            str: The string representation of the message.
        """
        return self.value


class AwsResourceTypes(str, Enum):
    """AWS resource types.

    Partial AWS CloudFormation resource types [1] are used to define resource types. An example would be AWS::ApiGateway::Account becomes AWS::ApiGateway.
    Resources with multiple versions will be encompassed in a single resource type.

    [1]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html
    """

    API_GATEWAY = "AWS::ApiGateway"  # Represents AWS::ApiGateway & AWS::ApiGatewayV2
    ECS = "AWS::ECS"
    LOAD_BALANCER = "AWS::ElasticLoadBalancing"
    NETWORK_INTERFACE = "AWS::NetworkInterface"
    RDS = "AWS::RDS"
    ROUTE53 = "AWS::Route53"
    STORAGE_BUCKET = "AWS::S3"


class AwsServices(str, Enum):
    """Supported AWS Services in AWS Cloud Connector."""

    API_GATEWAY = "apigateway"
    API_GATEWAY_V2 = "apigatewayv2"
    EC2 = "ec2"
    ECS = "ecs"
    LOAD_BALANCER = "elb"
    LOAD_BALANCER_V2 = "elbv2"
    RDS = "rds"
    ROUTE53_DOMAINS = "route53domains"
    ROUTE53_ZONES = "route53"
    STORAGE_BUCKET = "s3"
    SECURE_TOKEN_SERVICE = "sts"


class SeedLabel(str, Enum):
    """Censys seed labels for AWS services."""

    API_GATEWAY = "API Gateway"
    ECS = "ECS"
    LOAD_BALANCER = "ELB"
    NETWORK_INTERFACE = "ENI"
    RDS = "RDS"
    ROUTE53_DOMAINS = "Route53/Domains"
    ROUTE53_ZONES = "Route53/Zones"
    STORAGE_BUCKET = "S3"


class AwsMessages(str, Enum):
    """AWS messages."""

    ORGANIZATIONS_NOT_IN_USE = "AWS Organizations is not enabled in this account."
    PROMPT_SELECT_PROFILE = "Select an AWS profile to use."
    PROMPT_NO_ACCOUNTS_FOUND = "No additional accounts were found. Continue?"
    KEY_OR_ROLE_REQUIRED = (
        "Specify either access_key and secret_key or role_name and role_session_name"
    )
    PROVIDER_SETUP_DOC_LINK = "https://censys-cloud-connector.readthedocs.io/en/stable/aws/provider_setup.html"
    TEMPORARY_CREDENTIAL_ERROR = "A temporary credential has been detected which is not supported. Please read our documentation on how to configure AWS IAM."

    def __str__(self) -> str:
        """Get the string representation of the message.

        Returns:
            str: The string representation of the message.
        """
        return self.value
