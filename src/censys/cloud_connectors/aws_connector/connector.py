"""AWS Cloud Connector."""
import contextlib
from collections.abc import AsyncGenerator, Sequence
from typing import Optional, Union

from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from types_aiobotocore_apigateway.client import APIGatewayClient
from types_aiobotocore_apigatewayv2.client import ApiGatewayV2Client
from types_aiobotocore_ec2.client import EC2Client
from types_aiobotocore_ec2.type_defs import (
    FilterTypeDef,
    NetworkInterfaceTypeDef,
    TagDescriptionTypeDef,
    TagTypeDef,
)
from types_aiobotocore_ecs.client import ECSClient
from types_aiobotocore_elb.client import ElasticLoadBalancingClient
from types_aiobotocore_elbv2.client import ElasticLoadBalancingv2Client
from types_aiobotocore_rds.client import RDSClient
from types_aiobotocore_route53.client import Route53Client
from types_aiobotocore_s3.client import S3Client

from censys.cloud_connectors.common.cloud_asset import AwsStorageBucketAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.context import SuppressValidationError
from censys.cloud_connectors.common.enums import EventTypeEnum, ProviderEnum
from censys.cloud_connectors.common.healthcheck import Healthcheck
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

from .credentials import AwsCredentials, get_aws_credentials
from .enums import AwsResourceTypes, SeedLabel
from .settings import AwsAccount, AwsSpecificSettings

VALID_RECORD_TYPES = ["A", "CNAME"]
IGNORED_TAGS = ["censys-cloud-connector-ignore"]


class AwsCloudConnector(CloudConnector):
    """AWS Cloud Connector.

    Integration uses the AWS SDK called boto3 [1].

    [1]: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
    """

    provider = ProviderEnum.AWS
    provider_settings: AwsSpecificSettings

    account_number: str
    ignore_tags: list[str]

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
            AwsResourceTypes.ROUTE53: self.get_route53_zones,
            AwsResourceTypes.ECS: self.get_ecs_instances,
        }
        self.cloud_asset_scanners = {
            AwsResourceTypes.STORAGE_BUCKET: self.get_s3_instances,
        }

        self.ignored_tags: list[str] = []
        self.global_ignored_tags: set[str] = set(IGNORED_TAGS)

    async def scan(  # type: ignore
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
    ):  # type: ignore
        """Scan AWS.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
        """
        self.logger.info(
            f"Scanning AWS account {self.account_number} in region {region}"
        )
        await super().scan(
            provider_setting,
            credentials=credentials,
            region=region,
            ignored_tags=ignored_tags,
        )

    async def scan_all(self):
        """Scan all configured AWS provider accounts."""
        provider_settings: dict[
            tuple, AwsSpecificSettings
        ] = self.settings.providers.get(
            self.provider, {}  # type: ignore
        )

        for provider_setting in provider_settings.values():
            self.provider_settings = provider_setting
            accounts: list[Union[None, AwsAccount]]
            if provider_setting.accounts:
                # Scan the default account first, then scan the rest
                accounts = [None, *provider_setting.accounts]
            else:
                # If no accounts are configured, scan the default account
                accounts = [None]

            # Scan each account in the provider
            for account in accounts:
                # Use the account number from the account if it is configured
                if account is not None:
                    self.account_number = account.account_number
                    self.ignored_tags = (
                        self.get_ignored_tags(account.ignore_tags)
                        if account.ignore_tags
                        else self.get_ignored_tags(provider_setting.ignore_tags)
                    )

                # Use the account number from the provider if it is not configured
                else:
                    self.account_number = provider_setting.account_number
                    self.ignored_tags = self.get_ignored_tags(
                        provider_setting.ignore_tags
                    )

                # TODO: Add support for global services

                # Scan each region in the account
                for region in provider_setting.regions:
                    try:
                        with Healthcheck(
                            self.settings,
                            provider_setting,
                            provider={
                                "region": region,
                                "account_number": self.account_number,
                            },
                        ):
                            # Get credentials for the account
                            credentials = await get_aws_credentials(
                                provider_setting, account, region
                            )

                            # Scan the account
                            await self.scan(
                                provider_setting,
                                credentials,
                                region,
                                ignored_tags=self.ignored_tags,
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Unable to scan account {self.account_number} in region"
                            f" {region}. Error: {e}"
                        )
                        self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)

    def format_label(self, service: SeedLabel, region: Optional[str] = None) -> str:
        """Format AWS label.

        Args:
            service (SeedLabel): AWS Service Type
            region (str): AWS Region override

        Returns:
            str: Formatted label.
        """
        region_label = f"/{region}" if region else ""
        return f"AWS: {service} - {self.account_number}{region_label}"

    async def get_api_gateway_domains_v1(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve all API Gateway V1 domains and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        label = self.format_label(SeedLabel.API_GATEWAY, region)

        async with get_session().create_client(
            "apigateway", **credentials
        ) as client:  # type: ignore
            client: APIGatewayClient  # type: ignore[no-redef]

            try:
                apis = await client.get_rest_apis()
                for domain in apis.get("items", []):
                    domain_id = domain["id"]
                    domain_name = f"{domain_id}.execute-api.{region}.amazonaws.com"
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=domain_name, label=label)
                        self.add_seed(domain_seed, api_gateway_res=domain)
            except ClientError as e:
                self.logger.error(f"Could not connect to API Gateway V1. Error: {e}")

    async def get_api_gateway_domains_v2(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve API Gateway V2 domains and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        label = self.format_label(SeedLabel.API_GATEWAY, region)

        async with get_session().create_client(
            "apigatewayv2", **credentials
        ) as client:  # type: ignore
            client: ApiGatewayV2Client  # type: ignore[no-redef]

            try:
                apis = await client.get_apis()
                for domain in apis.get("Items", []):
                    domain_name = domain["ApiEndpoint"].split("//")[1]
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=domain_name, label=label)
                        self.add_seed(domain_seed, api_gateway_res=domain)
            except ClientError as e:
                self.logger.error(f"Could not connect to API Gateway V2. Error: {e}")

    async def get_api_gateway_domains(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve all versions of Api Gateway data and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        await self.get_api_gateway_domains_v1(
            provider_setting, credentials, region, ignored_tags, current_service
        )
        await self.get_api_gateway_domains_v2(
            provider_setting, credentials, region, ignored_tags, current_service
        )

    async def get_load_balancers_v1(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve Elastic Load Balancers (ELB) V1 data and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        label = self.format_label(SeedLabel.LOAD_BALANCER, region)

        async with get_session().create_client(
            "elb",
            **credentials,
        ) as client:  # type: ignore
            client: ElasticLoadBalancingClient  # type: ignore[no-redef]

            try:
                data = await client.describe_load_balancers()
                for elb in data.get("LoadBalancerDescriptions", []):
                    if value := elb.get("DNSName"):
                        with SuppressValidationError():
                            domain_seed = DomainSeed(value=value, label=label)
                            self.add_seed(domain_seed, elb_res=elb, aws_client=client)
            except ClientError as e:
                self.logger.error(f"Could not connect to ELB V1. Error: {e}")

    async def get_load_balancers_v2(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve Elastic Load Balancers (ELB) V2 data and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        label = self.format_label(SeedLabel.LOAD_BALANCER, region)

        async with get_session().create_client(
            "elbv2",
            **credentials,
        ) as client:  # type: ignore
            client: ElasticLoadBalancingv2Client  # type: ignore[no-redef]

            try:
                data = await client.describe_load_balancers()
                for elb in data.get("LoadBalancers", []):
                    if value := elb.get("DNSName"):
                        with SuppressValidationError():
                            domain_seed = DomainSeed(value=value, label=label)
                            self.add_seed(domain_seed, elb_res=elb, aws_client=client)
            except ClientError as e:
                self.logger.error(f"Could not connect to ELB V2. Error: {e}")

    async def get_load_balancers(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve Elastic Load Balancers (ELB) data and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        await self.get_load_balancers_v1(
            provider_setting, credentials, region, ignored_tags, current_service
        )
        await self.get_load_balancers_v2(
            provider_setting, credentials, region, ignored_tags, current_service
        )

    async def get_network_interfaces(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve EC2 Elastic Network Interfaces (ENI) data and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        label = self.format_label(SeedLabel.NETWORK_INTERFACE, region)

        interfaces = await self.describe_network_interfaces(
            provider_setting, credentials, region, ignored_tags
        )
        instance_tags = await self.get_resource_tags(credentials)

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

    async def describe_network_interfaces(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
    ) -> dict:
        """Retrieve EC2 Elastic Network Interfaces (ENI) data.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.

        Returns:
            dict: Network Interfaces.
        """
        interfaces = {}

        async with get_session().create_client(
            "ec2",
            **credentials,
        ) as ec2:  # type: ignore
            ec2: EC2Client  # type: ignore[no-redef]

            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_network_interfaces
            filters: Sequence[FilterTypeDef] = [
                {"Name": "association.public-ip", "Values": ["*"]}
            ]

            try:
                data = await ec2.describe_network_interfaces(Filters=filters)
                for network in data.get("NetworkInterfaces", {}):
                    network_interface_id = network.get("NetworkInterfaceId")
                    instance_id = network.get("Attachment", {}).get("InstanceId")

                    if self.network_interfaces_ignored_tags(network):
                        self.logger.debug(
                            "Skipping ignored tag for network interface"
                            f" {network_interface_id}"
                        )
                        continue

                    for addresses in network.get("PrivateIpAddresses", []):
                        if ip_address := addresses.get("Association", {}).get(
                            "PublicIp"
                        ):
                            interfaces[ip_address] = {
                                "NetworkInterfaceId": network_interface_id,
                                "InstanceId": instance_id,
                            }
            except ClientError as e:
                self.logger.error(f"Could not connect to ENI Service. Error: {e}")

        return interfaces

    async def get_resource_tags_paginated(
        self, credentials: AwsCredentials, resource_types: Optional[list[str]] = None
    ) -> AsyncGenerator[TagDescriptionTypeDef, None]:
        """Retrieve EC2 resource tags paginated.

        Args:
            credentials (AwsCredentials): AWS credentials.
            resource_types (Optional[list[str]]): Resource types. Defaults to None.

        Yields:
            AsyncGenerator[TagDescriptionTypeDef]: Tags.
        """
        async with get_session().create_client(
            "ec2",
            **credentials,
        ) as ec2:  # type: ignore
            ec2: EC2Client  # type: ignore[no-redef]

            try:
                async for page in ec2.get_paginator("describe_tags").paginate(
                    Filters=[
                        {
                            "Name": "resource-type",
                            "Values": resource_types or ["instance"],
                        }
                    ]  # type: ignore
                ):
                    for tag in page.get("Tags", []):  # noqa: SIM104
                        yield tag
            except ClientError as e:
                self.logger.error(f"Could not connect to EC2 Service. Error: {e}")

    async def get_resource_tags(
        self, credentials: AwsCredentials, resource_types: Optional[list[str]] = None
    ) -> dict:
        """Get EC2 resource tags based on resource types.

        Args:
            credentials (AwsCredentials): AWS credentials.
            resource_types (list[str]): Resource type filter.

        Returns:
            dict: Tags grouped by resource keys.
        """
        resource_tags: dict = {}

        async for tag in self.get_resource_tags_paginated(credentials, resource_types):
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

    async def get_rds_instances(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve Relational Database Services (RDS) data and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        label = self.format_label(SeedLabel.RDS, region)

        async with get_session().create_client(
            "rds",
            **credentials,
        ) as client:  # type: ignore
            client: RDSClient  # type: ignore[no-redef]

            try:
                data = await client.describe_db_instances()
                for instance in data.get("DBInstances", []):
                    if not instance.get("PubliclyAccessible"):
                        continue

                    if domain_name := instance.get("Endpoint", {}).get("Address"):
                        with SuppressValidationError():
                            domain_seed = DomainSeed(value=domain_name, label=label)
                            self.add_seed(domain_seed, rds_res=instance)
            except ClientError as e:
                self.logger.error(f"Could not connect to RDS Service. Error: {e}")

    async def get_route53_zones(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve Route 53 Zones and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        label = self.format_label(SeedLabel.ROUTE53_ZONES, region)

        async with get_session().create_client(
            "route53",
            **credentials,
        ) as client:  # type: ignore
            client: Route53Client  # type: ignore[no-redef]

            try:
                async for zones in client.get_paginator("list_hosted_zones").paginate():
                    for zone in zones.get("HostedZones", []):
                        if not zone or zone.get("Config", {}).get("PrivateZone"):
                            continue

                        # Add the zone itself as a seed
                        domain_name = zone["Name"].rstrip(".")
                        with SuppressValidationError():
                            domain_seed = DomainSeed(value=domain_name, label=label)
                            self.add_seed(
                                domain_seed, route53_zone_res=zone, aws_client=client
                            )

                        hosted_zone_id = zone["Id"]
                        async for resource_sets in client.get_paginator(
                            "list_resource_record_sets"
                        ).paginate(
                            HostedZoneId=hosted_zone_id,
                            # StartRecordName="*",
                        ):
                            for resource_set in resource_sets.get(
                                "ResourceRecordSets", []
                            ):
                                if resource_set.get("Type") not in VALID_RECORD_TYPES:
                                    continue

                                domain_name = resource_set["Name"].rstrip(".")
                                with SuppressValidationError():
                                    domain_seed = DomainSeed(
                                        value=domain_name, label=label
                                    )
                                    self.add_seed(
                                        domain_seed,
                                        route53_zone_res=zone,
                                        aws_client=client,
                                    )
            except ClientError as e:
                self.logger.error(f"Could not connect to Route 53 Zones. Error: {e}")

    async def get_ecs_instances(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve Elastic Container Service data and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        label = self.format_label(SeedLabel.ECS, region)

        session = get_session()

        async with session.create_client(
            "ecs",
            **credentials,
        ) as ecs, session.create_client(
            "ec2",
            **credentials,
        ) as ec2:  # type: ignore
            ecs: ECSClient  # type: ignore[no-redef]
            ec2: EC2Client  # type: ignore[no-redef]

            try:
                clusters = await ecs.list_clusters()
                for cluster in clusters.get("clusterArns", []):
                    cluster_instances = await ecs.list_container_instances(
                        cluster=cluster
                    )
                    containers = cluster_instances.get("containerInstanceArns", [])
                    if len(containers) == 0:
                        continue

                    instances = await ecs.describe_container_instances(
                        cluster=cluster, containerInstances=containers
                    )

                    instance_ids = [
                        i["ec2InstanceId"]
                        for i in instances.get("containerInstances", [])
                    ]
                    if not instance_ids:
                        continue

                    descriptions = await ec2.describe_instances(
                        InstanceIds=instance_ids
                    )
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

    async def get_s3_region(self, client: S3Client, bucket: str) -> str:
        """Lookup S3 bucket location.

        Args:
            client (S3Client): botocore S3 client
            bucket (str): S3 bucket name

        Returns:
            str: Bucket location (or us-east-1 for legacy buckets)
        """
        location = await client.get_bucket_location(Bucket=bucket)
        return location.get("LocationConstraint") or "us-east-1"

    async def get_s3_instances(
        self,
        provider_setting: AwsSpecificSettings,
        credentials: AwsCredentials,
        region: str,
        ignored_tags: list[str],
        current_service: str,
    ) -> None:
        """Retrieve Simple Storage Service data and emit seeds.

        Args:
            provider_setting (AwsSpecificSettings): AWS provider settings.
            credentials (AwsCredentials): AWS credentials.
            region (str): AWS region.
            ignored_tags (list[str], optional): List of tags to ignore. Defaults to IGNORED_TAGS.
            current_service (str): Current service.
        """
        async with get_session().create_client(
            "s3",
            **credentials,
        ) as client:  # type: ignore
            client: S3Client  # type: ignore[no-redef]

            try:
                data = await client.list_buckets()
                for bucket in data.get("Buckets", []):
                    bucket_name = bucket.get("Name")
                    if not bucket_name:
                        continue

                    s3_region = await self.get_s3_region(client, bucket_name)
                    label = self.format_label(SeedLabel.STORAGE_BUCKET, s3_region)

                    with SuppressValidationError():
                        bucket_asset = AwsStorageBucketAsset(  # type: ignore
                            value=AwsStorageBucketAsset.url(bucket_name, s3_region),
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

    def get_ignored_tags(self, tags: Optional[list[str]] = None) -> list[str]:
        """Generate ignored tags based off provider settings and global ignore list.

        Args:
            tags (Optional[list[str]]): List of tags to ignore. Defaults to None.

        Returns:
            list[str]: Ignored tags.
        """
        if not tags:
            return list(self.global_ignored_tags)

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
