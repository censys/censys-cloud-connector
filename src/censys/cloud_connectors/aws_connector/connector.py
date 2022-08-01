"""AWS Cloud Connector."""
from typing import Any, Callable, Optional

import boto3
import botocore
from botocore.exceptions import ClientError
from mypy_boto3_apigateway import APIGatewayClient
from mypy_boto3_apigatewayv2 import ApiGatewayV2Client
from mypy_boto3_ec2 import EC2Client
from mypy_boto3_ecs import ECSClient
from mypy_boto3_elb import ElasticLoadBalancingClient
from mypy_boto3_elbv2 import ElasticLoadBalancingv2Client
from mypy_boto3_rds import RDSClient
from mypy_boto3_route53 import Route53Client
from mypy_boto3_route53domains import Route53DomainsClient
from mypy_boto3_s3 import S3Client
from mypy_boto3_sts import STSClient

from censys.cloud_connectors.common.cloud_asset import AwsStorageBucketAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .enums import AwsResourceTypes, AwsServices, SeedLabel, ServiceName
from .settings import AwsSpecificSettings

VALID_RECORD_TYPES = ["A", "CNAME"]


class AwsCloudConnector(CloudConnector):
    """AWS Cloud Connector.

    Integration uses the AWS SDK called boto3 [1].

    [1]: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
    """

    provider = ProviderEnum.AWS
    provider_settings: AwsSpecificSettings
    seed_scanners: dict[AwsResourceTypes, Callable[[], None]]
    cloud_asset_scanners: dict[AwsResourceTypes, Callable[[], None]]

    _sts_credentials: Optional[dict] = None
    account_number: int
    region: Optional[str]

    def __init__(self, settings: Settings):
        """Initialize AWS Cloud Connectors.

        Args:
            settings (Settings): Settings.
        """
        super().__init__(settings)
        self.seed_scanners = {
            AwsResourceTypes.API_GATEWAY: self.get_api_gateway_domains,
            AwsResourceTypes.LOAD_BALANCER: self.get_load_balancers,
            AwsResourceTypes.NETWORK_INTERFACE: self.get_network_interfaces,
            AwsResourceTypes.RDS: self.get_rds_instances,
            AwsResourceTypes.ROUTE53: self.get_route53_instances,
            AwsResourceTypes.ECS: self.get_ecs_instances,
        }
        self.cloud_asset_scanners = {
            AwsResourceTypes.STORAGE_BUCKET: self.get_s3_instances,
        }

    def scan(self):
        """Scan AWS."""
        self.logger.info(
            f"Scanning AWS account {self.account_number} in region {self.region}"
        )
        super().scan()

    def scan_all(self):
        """Scan all configured AWS provider accounts."""
        provider_settings: dict[
            tuple, AwsSpecificSettings
        ] = self.settings.providers.get(self.provider, {})

        for provider_setting in provider_settings.values():
            self.provider_settings = provider_setting

            for credential in self.provider_settings.get_credentials():
                self.credential = credential
                self.account_number = credential.get("account_number")

                for region in self.provider_settings.regions:
                    self.region = region
                    self.scan()
                    self.region = None

                self.credential = None
                self.account_number = None

    def format_label(self, service: AwsServices, region: Optional[str] = None) -> str:
        """Format AWS label.

        Args:
            service (AwsServices): AWS Service Type
            region (str): AWS Region override

        Returns:
            str: Formatted label.
        """
        region = region or self.region
        region_label = f"/{region}" if region != "" else ""
        return f"AWS: {service} - {self.account_number}{region_label}"

    def get_seeds(self) -> None:
        """Gather seeds."""
        for seed_type, seed_scanner in self.seed_scanners.items():
            if (
                self.provider_settings.ignore
                and seed_type in self.provider_settings.ignore
            ):
                self.logger.debug(f"Skipping {seed_type}")
                continue

            self.logger.debug(f"Scanning {seed_type}")
            seed_scanner()

    def get_cloud_assets(self) -> None:
        """Gather cloud assets."""
        for cloud_asset_type, cloud_asset_scanner in self.cloud_asset_scanners.items():
            if (
                self.provider_settings.ignore
                and cloud_asset_type in self.provider_settings.ignore
            ):
                self.logger.debug(f"Skipping {cloud_asset_type}")
                continue
            self.logger.debug(f"Scanning {cloud_asset_type}")
            cloud_asset_scanner()

    def credentials(self) -> dict:
        """Generate required credentials for AWS.

        Returns:
            dict: Credentials.
        """
        if role_name := self.credential.get("role_name"):
            return self.get_assume_role_credentials(role_name)

        return self._boto_cred(
            self.region,
            self.provider_settings.access_key,
            self.provider_settings.secret_key,
            self.provider_settings.session_token,
        )

    def get_aws_client(
        self, service: ServiceName, credentials: Optional[dict] = None
    ) -> botocore.client.BaseClient:
        """Creates an AWS client for the provided service.

        Args:
            service (ServiceName): The AWS service name.
            credentials (dict): Override credentials instead of using the default.

        Raises:
            Exception: If the client could not be created.

        Returns:
            botocore.client.BaseClient: An AWS boto3 client.
        """
        try:
            credentials = credentials or self.credentials()
            if credentials.get("aws_access_key_id", None):
                return boto3.client(service, **credentials)
            # calling client without credentials follows the standard
            # credential import path to source creds from the environment
            return boto3.client(service)
        except Exception as e:
            self.logger.error(
                f"Could not connect with client type '{service}'. Error: {e}"
            )
            raise

    def get_assume_role_credentials(self, role_name: Optional[str] = None) -> dict:
        """Generate and cache STS credentials.

        Args:
            role_name (str): Role name.

        Returns:
            dict: STS credentials.

        Raises:
            Exception: If the credentials could not be created.
        """
        if self._sts_credentials is not None:  # TODO and time > creds['Expiration']:
            return self._sts_credentials

        try:
            creds = self.assume_role(role_name)
            self._sts_credentials = self._boto_cred(
                self.region,
                creds["AccessKeyId"],
                creds["SecretAccessKey"],
                creds["SessionToken"],
            )
            return self._sts_credentials
        except Exception as e:
            self.logger.error(f"Failed to assume role: {e}")
            raise

    def _boto_cred(
        self,
        region_name: str = None,
        access_key: str = None,
        secret_key: str = None,
        session_token: str = None,
    ) -> dict[str, Any]:
        """Create a boto3 credential dict. Only params with values are included.

        Args:
            region_name (str): AWS region.
            access_key (str): AWS access key.
            secret_key (str): AWS secret key.
            session_token (str): AWS session token.

        Returns:
            dict: boto3 credential dict.
        """
        cred = {}

        if region_name:
            cred["region_name"] = region_name

        if access_key:
            cred["aws_access_key_id"] = access_key

        if secret_key:
            cred["aws_secret_access_key"] = secret_key

        if session_token:
            cred["aws_session_token"] = session_token

        return cred

    def assume_role(self, role_name: Optional[str] = "CensysCloudConnectorRole"):
        """Acquire temporary credentials generated by Secure Token Service (STS).

        Args:
            role_name (str, optional): Role name to assume. Defaults to "CensysCloudConnectorRole".

        Returns:
            dict: Temporary credentials.
        """
        credentials = self._boto_cred(
            self.region,
            self.provider_settings.access_key,
            self.provider_settings.secret_key,
            self.provider_settings.session_token,
        )

        client: STSClient = self.get_aws_client(
            service=AwsServices.SECURE_TOKEN_SERVICE,  # type: ignore
            credentials=credentials,
        )

        role: dict[str, Any] = {
            "RoleArn": f"arn:aws:iam::{self.account_number}:role/{role_name}"
        }
        if role_session_name := self.credential.get("role_session_name"):
            role["RoleSessionName"] = role_session_name

        assumed_role = client.assume_role(**role)
        return assumed_role.get("Credentials", {})

    def get_api_gateway_domains_v1(self):
        """Retrieve all API Gateway V1 domains and emit seeds."""
        client: APIGatewayClient = self.get_aws_client(service=AwsServices.API_GATEWAY)
        label = self.format_label(SeedLabel.API_GATEWAY)

        try:
            apis = client.get_rest_apis()
            for domain in apis.get("items", []):
                domain_name = f"{domain['id']}.execute-api.{self.region}.amazonaws.com"
                self.add_seed(DomainSeed(value=domain_name, label=label))
        except ClientError as e:
            self.logger.error(f"Could not connect to API Gateway V1. Error: {e}")

    def get_api_gateway_domains_v2(self):
        """Retrieve API Gateway V2 domains and emit seeds."""
        client: ApiGatewayV2Client = self.get_aws_client(
            service=AwsServices.API_GATEWAY_V2
        )
        label = self.format_label(SeedLabel.API_GATEWAY)

        try:
            apis = client.get_apis()
            for domain in apis.get("Items", []):
                domain_name = domain["ApiEndpoint"].split("//")[1]
                self.add_seed(DomainSeed(value=domain_name, label=label))
        except ClientError as e:
            self.logger.error(f"Could not connect to API Gateway V2. Error: {e}")

    def get_api_gateway_domains(self):
        """Retrieve all versions of Api Gateway data and emit seeds."""
        self.get_api_gateway_domains_v1()
        self.get_api_gateway_domains_v2()

    def get_load_balancers_v1(self):
        """Retrieve Elastic Load Balancers (ELB) V1 data and emit seeds."""
        client: ElasticLoadBalancingClient = self.get_aws_client(
            service=AwsServices.LOAD_BALANCER
        )
        label = self.format_label(SeedLabel.LOAD_BALANCER)

        try:
            data = client.describe_load_balancers()
            for elb in data.get("LoadBalancerDescriptions", []):
                if value := elb.get("DNSName"):
                    self.add_seed(DomainSeed(value=value, label=label))
        except ClientError as e:
            self.logger.error(f"Could not connect to ELB V1. Error: {e}")

    def get_load_balancers_v2(self):
        """Retrieve Elastic Load Balancers (ELB) V2 data and emit seeds."""
        client: ElasticLoadBalancingv2Client = self.get_aws_client(
            service=AwsServices.LOAD_BALANCER_V2
        )
        label = self.format_label(SeedLabel.LOAD_BALANCER)

        try:
            data = client.describe_load_balancers()
            for elb in data.get("LoadBalancers", []):
                if value := elb.get("DNSName"):
                    self.add_seed(DomainSeed(value=value, label=label))
        except ClientError as e:
            self.logger.error(f"Could not connect to ELB V2. Error: {e}")

    def get_load_balancers(self):
        """Retrieve Elastic Load Balancers (ELB) data and emit seeds."""
        self.get_load_balancers_v1()
        self.get_load_balancers_v2()

    def get_network_interfaces(self):
        """Retrieve EC2 Elastic Network Interfaces (ENI) data and emit seeds."""
        client: EC2Client = self.get_aws_client(service=AwsServices.EC2)
        label = self.format_label(SeedLabel.NETWORK_INTERFACE)

        try:
            data = client.describe_network_interfaces()
            for networks in data.get("NetworkInterfaces", []):
                for addresses in networks.get("PrivateIpAddresses", []):
                    if value := addresses.get("Association", {}).get("PublicIp"):
                        self.add_seed(IpSeed(value=value, label=label))
        except ClientError as e:
            self.logger.error(f"Could not connect to ENI Service. Error: {e}")

    def get_rds_instances(self):
        """Retrieve Relational Database Services (RDS) data and emit seeds."""
        client: RDSClient = self.get_aws_client(service=AwsServices.RDS)
        label = self.format_label(SeedLabel.RDS)

        try:
            data = client.describe_db_instances()
            for instance in data.get("DBInstances", []):
                if value := instance.get("Endpoint", {}).get("Address"):
                    self.add_seed(DomainSeed(value=value, label=label))
        except ClientError as e:
            self.logger.error(f"Could not connect to RDS Service. Error: {e}")

    def _get_route53_domains(self):
        """Retrieve Paginated Route 53 Domains.

        Yields:
            Generator[dict]: A Page of Route 53 Domains
        """
        client: Route53DomainsClient = self.get_aws_client(
            service=AwsServices.ROUTE53_DOMAINS
        )

        next_page_marker = None
        while True:
            try:
                if next_page_marker:
                    data = client.list_domains(Marker=next_page_marker)
                else:
                    data = client.list_domains()

                yield data

                if data.get("NextPageMarker"):
                    next_page_marker = data.get("NextPageMarker")
                else:
                    break
            except ClientError as e:
                self.logger.error(f"Could not connect to Route 53 Domains. Error: {e}")
                break

    def get_route53_domains(self):
        """Retrieve Route 53 Domains and emit seeds."""
        label = self.format_label(SeedLabel.ROUTE53_DOMAINS)

        for data in self._get_route53_domains():
            for domain in data.get("Domains", []):
                if value := domain.get("DomainName"):
                    self.add_seed(DomainSeed(value=value, label=label))

    def _get_route53_zone_hosts(self, client: botocore.client.BaseClient) -> dict:
        """Retrieve Route 53 Zone hosts.

        Args:
            client (botocore.client.BaseClient): Route53 Client

        Returns:
            dict: Hosted Zones
        """
        return client.get_paginator("list_hosted_zones").paginate().build_full_result()

    def _get_route53_zone_resources(
        self, client: botocore.client.BaseClient, hosted_zone_id
    ) -> dict:
        """Retrieve Route 53 Zone resources.

        Args:
            client (botocore.client.BaseClient): Route53 client
            hosted_zone_id (str): Hosted Zone Id

        Returns:
            dict: _description_
        """
        return (
            client.get_paginator("list_resource_record_sets")
            .paginate(
                HostedZoneId=hosted_zone_id,
                StartRecordName="*",
            )
            .build_full_result()
        )

    def get_route53_zones(self):
        """Retrieve Route 53 Zones and emit seeds."""
        client: Route53Client = self.get_aws_client(service=AwsServices.ROUTE53_ZONES)
        label = self.format_label(SeedLabel.ROUTE53_ZONES)

        try:
            zones = self._get_route53_zone_hosts(client)
            for zone in zones.get("HostedZones", []):
                if zone.get("Config", {}).get("PrivateZone"):
                    continue

                id = zone.get("Id")
                resource_sets = self._get_route53_zone_resources(client, id)
                for resource_set in resource_sets.get("ResourceRecordSets", []):
                    if resource_set.get("Type") not in VALID_RECORD_TYPES:
                        continue

                    value = resource_set.get("Name").rstrip(".")
                    self.add_seed(DomainSeed(value=value, label=label))
        except ClientError as e:
            self.logger.error(f"Could not connect to Route 53 Zones. Error: {e}")

    def get_route53_instances(self):
        """Retrieve Route 53 data and emit seeds."""
        self.get_route53_domains()
        self.get_route53_zones()

    def get_ecs_instances(self):
        """Retrieve Elastic Container Service data and emit seeds."""
        ecs: ECSClient = self.get_aws_client(AwsServices.ECS)
        ec2: EC2Client = self.get_aws_client(AwsServices.EC2)
        label = self.format_label(SeedLabel.ECS)

        try:
            clusters = ecs.list_clusters()
            for cluster in clusters.get("clusterArns", []):
                cluster_instances = ecs.list_container_instances(cluster=cluster)
                containers = cluster_instances.get("containerInstanceArns", [])
                if len(containers) == 0:
                    continue

                instances = ecs.describe_container_instances(
                    cluster=cluster, containerInstances=containers
                )

                instance_ids = [
                    i.get("ec2InstanceId")
                    for i in instances.get("containerInstances", [])
                ]
                if not instance_ids:
                    continue

                descriptions = ec2.describe_instances(InstanceIds=instance_ids)
                for reservation in descriptions.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        value = instance.get("PublicIpAddress")
                        if not value:
                            continue

                        self.add_seed(IpSeed(value=value, label=label))
        except ClientError as e:
            self.logger.error(f"Could not connect to ECS. Error: {e}")

    def _get_s3_region(self, client: S3Client, bucket: str) -> str:
        """Lookup S3 bucket location.

        Args:
            client (S3Client): botocore S3 client
            bucket (str): S3 bucket name

        Returns:
            str: Bucket location (or us-east-1 for legacy buckets)
        """
        location = client.get_bucket_location(Bucket=bucket)["LocationConstraint"]
        return location or "us-east-1"

    def get_s3_instances(self):
        """Retrieve Simple Storage Service data and emit seeds."""
        client: S3Client = self.get_aws_client(service=AwsServices.STORAGE_BUCKET)

        try:
            data = client.list_buckets().get("Buckets", [])
            for bucket in data:
                bucket_name = bucket.get("Name")
                if not bucket_name:
                    continue

                region = self._get_s3_region(client, bucket.get("Name"))
                label = self.format_label(SeedLabel.STORAGE_BUCKET, region)

                self.add_cloud_asset(
                    AwsStorageBucketAsset(
                        value=AwsStorageBucketAsset.url(bucket_name, self.region),
                        uid=label,
                        scan_data={
                            "accountNumber": self.account_number,
                        },
                    )
                )
        except ClientError as e:
            self.logger.error(f"Could not connect to S3. Error: {e}")
