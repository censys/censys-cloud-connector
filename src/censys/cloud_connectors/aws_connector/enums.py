"""Enums for AWS."""
from enum import Enum
from typing import Literal


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


# ServiceName is necessary for boto types; string literal is required
ServiceName = Literal[
    "apigateway",
    "apigatewayv2",
    "ec2",
    "ecr",
    "elb",
    "elbv2",
    "rds",
    "route53",
    "route53domains",
    "s3",
    "sts",
]


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
