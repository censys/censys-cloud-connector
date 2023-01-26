"""AWS Cloud Connector."""
import contextlib
from collections.abc import Generator, Sequence
from typing import Any, Optional, TypeVar

import boto3
import botocore
from botocore.exceptions import ClientError
from mypy_boto3_apigateway import APIGatewayClient
from mypy_boto3_apigatewayv2 import ApiGatewayV2Client
from mypy_boto3_ec2 import EC2Client
from mypy_boto3_ec2.type_defs import (
    FilterTypeDef,
    NetworkInterfaceTypeDef,
    TagDescriptionTypeDef,
    TagTypeDef,
)
from mypy_boto3_ecs import ECSClient
from mypy_boto3_elb import ElasticLoadBalancingClient
from mypy_boto3_elbv2 import ElasticLoadBalancingv2Client
from mypy_boto3_rds import RDSClient
from mypy_boto3_route53 import Route53Client
from mypy_boto3_route53domains import Route53DomainsClient
from mypy_boto3_s3 import S3Client
from mypy_boto3_sts import STSClient
from mypy_boto3_sts.type_defs import CredentialsTypeDef

from censys.cloud_connectors.aws_connector.enums import (
    AwsDefaults,
    AwsResourceTypes,
    AwsServices,
    SeedLabel,
)
from censys.cloud_connectors.aws_connector.settings import AwsSpecificSettings
from censys.cloud_connectors.common.cloud_asset import AwsStorageBucketAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.context import SuppressValidationError
from censys.cloud_connectors.common.enums import EventTypeEnum, ProviderEnum
from censys.cloud_connectors.common.healthcheck import Healthcheck
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

T = TypeVar("T", bound="botocore.client.BaseClient")

VALID_RECORD_TYPES = ["A", "CNAME"]
IGNORED_TAGS = ["censys-cloud-connector-ignore"]


class AwsCloudConnector(CloudConnector):
    """AWS Cloud Connector.

    Integration uses the AWS SDK called boto3 [1].

    [1]: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
    """

    provider = ProviderEnum.AWS
    provider_settings: AwsSpecificSettings

    # Temporary STS credentials created with Assume Role will be stored here during
    # a connector scan.
    temp_sts_cred: Optional[dict] = None

    # When scanning, the current loaded credential will be set here.
    credential: dict = {}

    account_number: str
    region: Optional[str]

    # Current set of ignored tags (combined set of user settings + overall settings)
    ignored_tags: list[str]
    global_ignored_tags: set[str]

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

        self.ignored_tags = []
        self.global_ignored_tags: set[str] = set(IGNORED_TAGS)

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
                self.account_number = credential["account_number"]
                self.ignored_tags = self.get_ignored_tags(credential["ignore_tags"])

                for region in self.provider_settings.regions:
                    self.temp_sts_cred = None
                    self.region = region
                    try:
                        with Healthcheck(
                            self.settings,
                            provider_setting,
                            provider={
                                "region": region,
                                "account_number": self.account_number,
                            },
                        ):
                            self.scan()
                    except Exception as e:
                        self.logger.error(
                            f"Unable to scan account {self.account_number} in region {self.region}. Error: {e}"
                        )
                        self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)
                    self.region = None

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

    def credentials(self) -> dict:
        """Generate required credentials for AWS.

        This method will attempt to use any active STS sessions before falling
        back on the regular provider settings.

        Returns:
            dict: Boto Credential format.
        """
        # Role name is the credential field which causes STS to activate.
        # Once activated the temporary STS creds will be used by all
        # subsequent AWS service client calls.
        if role_name := self.credential.get("role_name"):
            self.logger.debug(f"Using STS for role {role_name}")
            return self.get_assume_role_credentials(role_name)

        self.logger.debug("Using provider settings credentials")
        return self.boto_cred(
            self.region,
            self.provider_settings.access_key,
            self.provider_settings.secret_key,
            self.provider_settings.session_token,
        )

    def get_aws_client(
        self, service: AwsServices, credentials: Optional[dict] = None
    ) -> T:
        """Creates an AWS client for the provided service.

        Args:
            service (AwsServices): The AWS service name.
            credentials (dict): Override credentials instead of using the default.

        Raises:
            Exception: If the client could not be created.

        Returns:
            T: An AWS boto3 client.
        """
        try:
            credentials = credentials or self.credentials()
            if credentials.get("aws_access_key_id"):
                self.logger.debug(f"AWS Service {service} using access key credentials")
                return boto3.client(service, **credentials)  # type: ignore

            # calling client without credentials follows the standard
            # credential import path to source creds from the environment
            self.logger.debug(
                f"AWS Service {service} using external boto configuration"
            )
            return boto3.client(service)  # type: ignore
        except Exception as e:
            self.logger.error(
                f"Could not connect with client type '{service}'. Error: {e}"
            )
            raise

    def get_assume_role_credentials(self, role_name: Optional[str] = None) -> dict:
        """Acquire temporary STS credentials and cache them for the duration of the scan.

        Args:
            role_name (str): Role name.

        Returns:
            dict: STS credentials.

        Raises:
            Exception: If the credentials could not be created.
        """
        if self.temp_sts_cred:
            self.logger.debug("Using cached temporary STS credentials")
        else:
            try:
                temp_creds = self.assume_role(role_name)
                self.temp_sts_cred = self.boto_cred(
                    self.region,
                    temp_creds["AccessKeyId"],
                    temp_creds["SecretAccessKey"],
                    temp_creds["SessionToken"],
                )
                self.logger.debug(
                    f"Created temporary STS credentials for role {role_name}"
                )
            except Exception as e:
                self.logger.error(f"Failed to assume role: {e}")
                raise

        return self.temp_sts_cred

    def boto_cred(
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

    def assume_role(
        self, role_name: Optional[str] = AwsDefaults.ROLE_NAME.value
    ) -> CredentialsTypeDef:
        """Acquire temporary credentials generated by Secure Token Service (STS).

        This will always use the primary AWS account credentials when querying
        the STS service.

        Args:
            role_name (str, optional): Role name to assume. Defaults to "CensysCloudConnectorRole".

        Returns:
            CredentialsTypeDef: Temporary credentials.
        """
        credentials = self.boto_cred(
            self.region,
            self.provider_settings.access_key,
            self.provider_settings.secret_key,
            self.provider_settings.session_token,
        )

        # pass in explicit boto creds to force a new STS session
        client: STSClient = self.get_aws_client(
            service=AwsServices.SECURE_TOKEN_SERVICE,  # type: ignore
            credentials=credentials,
        )

        role_session = (
            self.credential["role_session_name"] or AwsDefaults.ROLE_SESSION_NAME.value
        )
        role: dict[str, Any] = {
            "RoleArn": f"arn:aws:iam::{self.account_number}:role/{role_name}",
            "RoleSessionName": role_session,
        }

        temp_creds = client.assume_role(**role)

        self.logger.debug(
            f"Assume role acquired temporary credentials for role {role_name}"
        )
        return temp_creds["Credentials"]

    def get_api_gateway_domains_v1(self):
        """Retrieve all API Gateway V1 domains and emit seeds."""
        client: APIGatewayClient = self.get_aws_client(service=AwsServices.API_GATEWAY)
        label = self.format_label(SeedLabel.API_GATEWAY)

        try:
            apis = client.get_rest_apis()
            for domain in apis.get("items", []):
                domain_name = f"{domain['id']}.execute-api.{self.region}.amazonaws.com"
                with SuppressValidationError():
                    domain_seed = DomainSeed(value=domain_name, label=label)
                    self.add_seed(domain_seed, api_gateway_res=domain)
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
                with SuppressValidationError():
                    domain_seed = DomainSeed(value=domain_name, label=label)
                    self.add_seed(domain_seed, api_gateway_res=domain)
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
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=value, label=label)
                        self.add_seed(domain_seed, elb_res=elb, aws_client=client)
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
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=value, label=label)
                        self.add_seed(domain_seed, elb_res=elb, aws_client=client)
        except ClientError as e:
            self.logger.error(f"Could not connect to ELB V2. Error: {e}")

    def get_load_balancers(self):
        """Retrieve Elastic Load Balancers (ELB) data and emit seeds."""
        self.get_load_balancers_v1()
        self.get_load_balancers_v2()

    def get_network_interfaces(self):
        """Retrieve EC2 Elastic Network Interfaces (ENI) data and emit seeds."""
        label = self.format_label(SeedLabel.NETWORK_INTERFACE)

        interfaces = self.describe_network_interfaces()
        instance_tags = self.get_resource_tags()

        for ip_address, record in interfaces.items():
            instance_id = record["InstanceId"]
            tags = instance_tags.get(instance_id)
            if tags and self.has_ignored_tag(tags):
                self.logger.debug(
                    f"Skipping ignored tag for network instance {ip_address}"
                )
                continue

            with SuppressValidationError():
                ip_seed = IpSeed(value=ip_address, label=label)
                self.add_seed(ip_seed, tags=tags)

    def describe_network_interfaces(self) -> dict:
        """Retrieve EC2 Elastic Network Interfaces (ENI) data.

        Returns:
            dict: Network Interfaces.
        """
        ec2: EC2Client = self.get_aws_client(AwsServices.EC2)
        interfaces = {}

        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_network_interfaces
        filters: Sequence[FilterTypeDef] = [
            {"Name": "association.public-ip", "Values": ["*"]}
        ]

        try:
            data = ec2.describe_network_interfaces(Filters=filters)
            for network in data.get("NetworkInterfaces", {}):
                network_interface_id = network.get("NetworkInterfaceId")
                instance_id = network.get("Attachment", {}).get("InstanceId")

                if self.network_interfaces_ignored_tags(network):
                    self.logger.debug(
                        f"Skipping ignored tag for network interface {network_interface_id}"
                    )
                    continue

                for addresses in network.get("PrivateIpAddresses", []):
                    if ip_address := addresses.get("Association", {}).get("PublicIp"):
                        interfaces[ip_address] = {
                            "NetworkInterfaceId": network_interface_id,
                            "InstanceId": instance_id,
                        }
        except ClientError as e:
            self.logger.error(f"Could not connect to ENI Service. Error: {e}")

        return interfaces

    def get_resource_tags_paginated(
        self, resource_types: list[str] = None
    ) -> Generator[TagDescriptionTypeDef, None, None]:
        """Retrieve EC2 resource tags paginated.

        Args:
            resource_types (Optional[list[str]]): Resource types. Defaults to None.

        Yields:
            Generator[TagDescriptionTypeDef]: Tags.
        """
        ec2: EC2Client = self.get_aws_client(AwsServices.EC2)
        paginator = ec2.get_paginator(
            "describe_tags",
        )

        for page in paginator.paginate(
            Filters=[
                {"Name": "resource-type", "Values": resource_types or ["instance"]}
            ]
        ):
            tags = page.get("Tags", [])
            yield from tags

    def get_resource_tags(self, resource_types: list[str] = None) -> dict:
        """Get EC2 resource tags based on resource types.

        Args:
            resource_types (list[str]): Resource type filter.

        Returns:
            dict: Tags grouped by resource keys.
        """
        resource_tags: dict = {}

        for tag in self.get_resource_tags_paginated(resource_types):
            # Tags come in two formats:
            # 1. Tag = { Key = "Name", Value= "actual-tag-name" }
            # 2. Tag = { Key = "actual-key-name", Value = "tag-value-that-is-unused-here"}
            tag_name = tag.get("Key")
            if tag_name == "Name":
                tag_name = tag.get("Value")

            # Note: resource id is instance id
            resource_id = tag.get("ResourceId")
            if _resource_tags := resource_tags.get(resource_id):
                _resource_tags.append(tag_name)
            else:
                resource_tags[resource_id] = [tag_name]

        return resource_tags

    def network_interfaces_ignored_tags(self, data: NetworkInterfaceTypeDef) -> bool:
        """Check if network interface has ignored tags.

        Args:
            data (NetworkInterfaceTypeDef): Raw AWS tag data in key value pairs.

        Returns:
            bool: True if ignore tags detected.
        """
        tag_set = data.get("TagSet", [])
        tags = self.extract_tags_from_tagset(tag_set)
        return self.has_ignored_tag(tags)

    def get_rds_instances(self):
        """Retrieve Relational Database Services (RDS) data and emit seeds."""
        client: RDSClient = self.get_aws_client(service=AwsServices.RDS)
        label = self.format_label(SeedLabel.RDS)

        try:
            data = client.describe_db_instances()
            for instance in data.get("DBInstances", []):
                if not instance.get("PubliclyAccessible"):
                    continue

                if domain_name := instance.get("Endpoint", {}).get("Address"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=domain_name, label=label)
                        self.add_seed(domain_seed, rds_res=instance)
        except ClientError as e:
            self.logger.error(f"Could not connect to RDS Service. Error: {e}")

    def _get_route53_domains(self, client: Route53DomainsClient):
        """Retrieve Paginated Route 53 Domains.

        Args:
            client (Route53DomainsClient): Route 53 Client.

        Yields:
            Generator[dict]: A Page of Route 53 Domains
        """
        next_page_marker = None
        while True:
            try:
                if next_page_marker:
                    data = client.list_domains(Marker=next_page_marker)
                else:
                    data = client.list_domains()

                yield data

                if not (next_page_marker := data.get("NextPageMarker")):
                    break
            except ClientError as e:
                self.logger.error(f"Could not connect to Route 53 Domains. Error: {e}")
                break

    def get_route53_domains(self):
        """Retrieve Route 53 Domains and emit seeds."""
        client: Route53DomainsClient = self.get_aws_client(
            service=AwsServices.ROUTE53_DOMAINS
        )
        label = self.format_label(SeedLabel.ROUTE53_DOMAINS)

        for data in self._get_route53_domains(client):
            for domain in data.get("Domains", []):
                if domain_name := domain.get("DomainName"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=domain_name, label=label)
                        self.add_seed(
                            domain_seed, route53_domain_res=domain, aws_client=client
                        )

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
            dict: Resource Record Sets.
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

                    domain_name = resource_set.get("Name").rstrip(".")
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=domain_name, label=label)
                        self.add_seed(
                            domain_seed, route53_zone_res=zone, aws_client=client
                        )
        except ClientError as e:
            self.logger.error(f"Could not connect to Route 53 Zones. Error: {e}")

    def get_route53_instances(self):
        """Retrieve Route 53 data and emit seeds."""
        # Route53 domains have been removed until a client need is identified.
        # self.get_route53_domains()
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
                        ip_address = instance.get("PublicIpAddress")
                        if not ip_address:
                            continue

                        with SuppressValidationError():
                            ip_seed = IpSeed(value=ip_address, label=label)
                            self.add_seed(ip_seed, ecs_res=instance)
        except ClientError as e:
            self.logger.error(f"Could not connect to ECS. Error: {e}")

    def get_s3_region(self, client: S3Client, bucket: str) -> str:
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

                region = self.get_s3_region(client, bucket_name)
                label = self.format_label(SeedLabel.STORAGE_BUCKET, region)

                with SuppressValidationError():
                    bucket_asset = AwsStorageBucketAsset(
                        value=AwsStorageBucketAsset.url(bucket_name, region),
                        uid=label,
                        scan_data={
                            "accountNumber": self.account_number,
                        },
                    )
                    self.add_cloud_asset(
                        bucket_asset, bucket_name=bucket_name, aws_client=client
                    )
        except ClientError as e:
            self.logger.error(f"Could not connect to S3. Error: {e}")

    def get_ignored_tags(self, tags: Optional[list[str]] = None):
        """Generate ignored tags based off provider settings and global ignore list.

        Args:
            tags (Optional[list[str]]): List of tags to ignore. Defaults to None.

        Returns:
            list[str]: Ignored tags.
        """
        if not tags:
            return self.global_ignored_tags

        ignored = self.global_ignored_tags.copy()
        ignored.update(tags)

        return list(ignored)

    def has_ignored_tag(self, tags: list[str]) -> bool:
        """Check if a list of tags contains an ignored tag.

        Args:
            tags (list[str]): Tags on the current resource.

        Returns:
            bool: If the list contains an ignored tag.
        """
        return any(tag in self.ignored_tags for tag in tags)

    def extract_tags_from_tagset(self, tag_set: list[TagTypeDef]) -> list[str]:
        """Extract tags from tagset.

        Args:
            tag_set (dict): AWS TagSet data.

        Returns:
            list[str]: List of tag names.
        """
        tags = []

        with contextlib.suppress(KeyError):
            for tag in tag_set:
                name = tag["Key"]
                if name == "Name":
                    tags.append(tag["Value"])
                else:
                    tags.append(name)

        return tags
