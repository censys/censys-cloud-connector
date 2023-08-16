"""AWS Cloud Connector."""
import contextlib
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from logging import Logger
from multiprocessing import Pool
from typing import Any, Optional, TypeVar, Union

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
from censys.cloud_connectors.common.logger import get_logger
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from censys.cloud_connectors.common.settings import Settings

T = TypeVar("T", bound="botocore.client.BaseClient")

VALID_RECORD_TYPES = ["A", "CNAME"]
IGNORED_TAGS = ["censys-cloud-connector-ignore"]

# TODO: fix self.{property} references:
# This has to happen because if the worker pool spawns multiple account + regions, each worker will change the self.{property} value, thus making each process scan the SAME account.
#
# instead of changing everything everywhere, perhaps a data structure can handle this?
# make a dictionary of provider-setting-key (which is account + region)
# then inside scan use self.scan_contexts[provider-setting-key] = {...}

# TODO: logging changes:
# add account + region, current resource-type


@dataclass
class AwsScanContext:
    """Required configuration context for scan()."""

    provider_settings: AwsSpecificSettings
    # temp_sts_cred: Optional[dict]
    credential: dict
    account_number: str
    region: str

    # ignored tags on for the current credential (aws account)
    ignored_tags: list[str]
    logger: Logger


class AwsCloudConnector(CloudConnector):
    """AWS Cloud Connector.

    Integration uses the AWS SDK called boto3 [1].

    [1]: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
    """

    provider = ProviderEnum.AWS

    # workaround for storing multiple configurations during a scan() call
    # multiprocessing dictates that each worker runs scan in a different process
    # each process will share the same AwsCloudConnector instance
    # if a worker sets a self property, that is updated for _all_ workers
    # therefore, make a dict that each worker can reference it's unique account+region configuration
    #
    # each scan_contexts entry will have a unique key so that multiple accounts and regions can be scanned in parallel
    # scan_config_entry = {
    #   "temp_sts_cred": {}, "account_number": "", "region": "", "ignored_tags":[], credential: {}
    # }
    scan_contexts: dict[str, AwsScanContext] = {}

    # Temporary STS credentials created with Assume Role will be stored here during
    # a connector scan.
    # temp_sts_cred: Optional[dict] = None
    # During a run this will be set to the current account being scanned
    # It is common to have multiple top level accounts in providers.yml
    # provider_settings: AwsSpecificSettings
    # credential: dict = {}
    # account_number: str
    # ignored_tags: list[str]
    # pool: Pool

    global_ignored_tags: set[
        str
    ]  # this can remain self. as it is global across all accounts

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
        self.global_ignored_tags: set[str] = set(IGNORED_TAGS)
        # self.ignored_tags = []
        # self.pool = Pool(processes=settings.scan_concurrency)

    def scan_seeds(self, **kwargs):
        """Scan AWS."""
        # when scan() is called, it has been forked into a separate process (from scan_all)

        scan_context_key = kwargs["scan_context_key"]
        scan_context: AwsScanContext = kwargs["scan_context"]
        # scan_context must be set within scan(), otherwise race conditions happen where it doesn't exist when accessed
        self.scan_contexts[scan_context_key] = scan_context

        # multiprocessing requires separate logger instances per process
        # TODO: there is still something odd going on here, notice logger isnt being set to self.logger, but by even calling get_logger it "fixes" the sub-process log level from being WARNING to .env's DEBUG
        logger = get_logger(
            log_name=f"{self.provider.lower()}_cloud_connector",
            level=self.settings.logging_level,
            # TODO: extra - add account + region to log lines
        )
        scan_context.logger = logger

        self.logger.info(
            f"Scanning AWS - account:{scan_context.account_number} region:{scan_context.region}"
        )

        self.scan_contexts[scan_context_key] = scan_context
        # TODO: self.dispatch_event(EventTypeEnum.SCAN_STARTED)
        super().scan_seeds(**kwargs)
        # TODO: self.dispatch_event(EventTypeEnum.SCAN_FINISHED)

    def scan_cloud_assets(self, **kwargs):
        """Scan AWS for cloud assets."""
        # TODO: pull scan_seeds changes in after rebase
        scan_context_key = kwargs["scan_context_key"]
        scan_context = kwargs["scan_context"]
        self.scan_contexts[scan_context_key] = scan_context
        self.logger.info(f"Scanning AWS account {scan_context.account_number}")
        super().scan_cloud_assets(**kwargs)

    def scan_all(self):
        """Scan all configured AWS provider accounts."""
        provider_settings: dict[
            tuple, AwsSpecificSettings
        ] = self.settings.providers.get(self.provider, {})

        self.logger.debug(
            f"scanning AWS using {self.settings.scan_concurrency} processes"
        )

        pool = Pool(processes=self.settings.scan_concurrency)

        for provider_setting in provider_settings.values():
            # `provider_setting` represents a specific top-level AwsAccount entry in providers.yml
            #
            # DO NOT use provider_settings anywhere in this class!
            # provider_settings exists for the parent CloudConnector
            self.provider_settings = provider_setting
            self.scan_contexts = {}

            # for credential in self.provider_settings.get_credentials():
            for credential in provider_settings.get_credentials():
                # self.credential = credential
                # self.account_number = credential["account_number"]
                account_number = credential["account_number"]
                ignored_tags = self.get_ignored_tags(credential["ignore_tags"])
                # self.ignored_tags = ignored_tags

                # for each account + region combination, run each seed scanner
                for region in provider_settings.regions:
                    # self.temp_sts_cred = None
                    # self.region = region
                    try:
                        with Healthcheck(
                            self.settings,
                            provider_settings,
                            provider={
                                "region": region,
                                "account_number": account_number,
                                # self.account_number,
                            },
                        ):
                            self.logger.debug(
                                "starting pool account:%s region:%s",
                                account_number,
                                region,
                            )

                            # Credentials aren't exactly obvious how they work
                            # Assume role flow:
                            # - use the "primary account" access + secret key to "connect"
                            # - call STS assume role to get "temporary credentials"
                            # - temporary credentials can be used for all resource types in an account + region
                            # - note: creds expire after N time (hours?)
                            scan_context_key = f"{account_number}_{region}"
                            scan_context = AwsScanContext(
                                provider_settings=provider_settings,
                                credential=credential,
                                account_number=account_number,
                                region=region,
                                ignored_tags=ignored_tags,
                                logger=None,
                                # temp_sts_cred=None,
                            )

                            # scan workflow:
                            # - get seeds + cloud-assets + tags-plugin
                            # - submit seeds + cloud-assets
                            print(f"scan_all logging level {self.logger.level}")
                            pool.apply_async(
                                self.scan_seeds,
                                kwds={
                                    # TODO remove all of this except `scan_context_key`
                                    # "provider_setting": provider_setting,
                                    # "credential": credential,
                                    # "region": region,
                                    "scan_context_key": scan_context_key,
                                    "scan_context": scan_context,
                                },
                            )
                            # self.scan(**kwargs)
                    except Exception as e:
                        self.logger.error(
                            f"Unable to scan account {credential['account_number']} in region {region}. Error: {e}"
                        )
                        self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)
                    # self.region = None

                # for each account, run each cloud asset scanner
                try:
                    # self.temp_sts_cred = None
                    # self.region = None
                    with Healthcheck(
                        self.settings,
                        provider_setting,
                        provider={"account_number": self.account_number},
                    ):
                        pool.apply_async(
                            self.scan_cloud_assets,
                            kwds={
                                "credential": credential,
                                "region": region,
                            },
                        )
                except Exception as e:
                    self.logger.error(
                        f"Unable to scan account {self.account_number}. Error: {e}"
                    )
                    self.dispatch_event(EventTypeEnum.SCAN_FAILED, exception=e)

        pool.close()
        pool.join()

    def format_label(
        self,
        service: AwsServices,
        account_number: str,
        region: Optional[str] = None,
    ) -> str:
        """Format AWS label.

        Args:
            service (AwsServices): AWS Service Type
            region (str): AWS Region override
            account_number (str): AWS Account number

        Returns:
            str: Formatted label.
        """
        region_label = f"/{region}" if region != "" else ""
        return f"AWS: {service} - {account_number}{region_label}"

    def credentials(self, ctx: AwsScanContext) -> dict:
        """Generate required credentials for AWS.

        This method will attempt to use any active STS sessions before falling
        back on the regular provider settings.

        Returns:
            dict: Boto Credential format.
        """
        # Note: original design of credentials() was to lazily-load a connection if one
        # didn't exist using a previous STS temporary credential.

        # Role name is the credential field which causes STS to activate.
        # Once activated the temporary STS creds will be used by all
        # subsequent AWS service client calls.

        # TODO: fix self.credential
        if role_name := ctx.credential.get("role_name"):
            self.logger.debug(f"Using STS for role {role_name}")
            return self.get_assume_role_credentials(ctx)  # (account_number, role_name)

        self.logger.debug("Using provider settings credentials")
        return self.boto_cred(
            ctx.region,
            ctx.provider_settings.access_key,
            ctx.provider_settings.secret_key,
            ctx.provider_settings.session_token,
        )

    def get_aws_client(
        self,
        service: AwsServices,
        ctx: AwsScanContext,
        credentials: Optional[dict] = None,
    ) -> T:
        """Creates an AWS client for the provided service.

        Args:
            service (AwsServices): The AWS service name.
            ctx (AwsScanContext): The scan context.
            credentials (dict): Override credentials instead of using the default. Typically used with STS

        Raises:
            Exception: If the client could not be created.

        Returns:
            T: An AWS boto3 client.
        """
        try:
            credentials = credentials or self.credentials(ctx)

            if self.settings.aws_endpoint_url:
                credentials["endpoint_url"] = self.settings.aws_endpoint_url

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

    def get_assume_role_credentials(
        self,
        ctx: AwsScanContext,
        # account_number: Optional[str] = None,  # TODO: pass this in
        # role_name: Optional[str] = None,
        # role_session_name: Optional[str] = None,
    ) -> dict:
        """Acquire temporary STS credentials and cache them for the duration of the scan.

        Args:
            role_name (str): Role name.

        Returns:
            dict: STS credentials.

        Raises:
            Exception: If the credentials could not be created.
        """
        role_name = ctx.credential["role_name"]
        role_session_name = ctx.credential["role_session_name"]

        # TODO: temp_sts_cred is removed, make sure this works (and doesnt "assume role" per seed - should only be on the resource type level)
        # TODO: fix self.temp_sts_cred
        # if self.temp_sts_cred:
        #     self.logger.debug("Using cached temporary STS credentials")
        # else:
        try:
            temp_creds = self.assume_role(
                # account_number, region, role_name, role_session_name
                ctx,
                role_name=role_name,
                role_session_name=role_session_name,
            )
            # TODO: fix self.temp_sts_cred
            # self.temp_sts_cred = self.boto_cred(
            self.logger.debug(f"Created temporary STS credentials for role {role_name}")
            return self.boto_cred(
                ctx.region,
                temp_creds["AccessKeyId"],
                temp_creds["SecretAccessKey"],
                temp_creds["SessionToken"],
            )
        except Exception as e:
            self.logger.error(f"Failed to assume role: {e}")
            raise
        # TODO: fix self.temp_sts_cred
        # return self.temp_sts_cred

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

        Raises:
            Exception: If no credentials could be created.
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

        if cred == {}:
            raise Exception("Could not create STS request credentials")

        return cred

    def assume_role(
        self,
        ctx: AwsScanContext,
        # account_number: str,
        # region: str,
        role_name: Optional[str] = None,
        role_session_name: Optional[str] = None,
    ) -> CredentialsTypeDef:
        """Acquire temporary credentials generated by Secure Token Service (STS).

        This will always use the primary AWS account credentials when querying
        the STS service.

        Args:
            account_number(str): AWS account number.
            role_name (str, optional): Role name to assume. Defaults to "CensysCloudConnectorRole".
            role_session_name (str, optional): Role session name. Defaults to "CensysCloudConnectorSession".

        Returns:
            CredentialsTypeDef: Temporary credentials.
        """
        role_name = role_name or AwsDefaults.ROLE_NAME.value
        role_session_name = role_session_name or AwsDefaults.ROLE_SESSION_NAME.value

        # TODO: verify this works with worker pool change- Always use the primary account credentials to query STS
        # use primary account's credentials to query STS for temp creds
        credentials = self.boto_cred(
            ctx.region,
            ctx.provider_settings.access_key,
            ctx.provider_settings.secret_key,
            ctx.provider_settings.session_token,
        )
        client: STSClient = self.get_aws_client(
            AwsServices.SECURE_TOKEN_SERVICE,
            credentials=credentials,
            ctx=ctx,
        )

        role: dict[str, Any] = {
            "RoleArn": f"arn:aws:iam::{ctx.account_number}:role/{role_name}",
            "RoleSessionName": role_session_name,
        }

        temp_creds = client.assume_role(**role)

        self.logger.debug(
            f"Assume role acquired temporary credentials for role {role_name}"
        )
        return temp_creds["Credentials"]

    def get_api_gateway_domains_v1(self, **kwargs):
        """Retrieve all API Gateway V1 domains and emit seeds."""
        key = kwargs["scan_context_key"]
        ctx: AwsScanContext = self.scan_contexts[key]

        client: APIGatewayClient = self.get_aws_client(service=AwsServices.API_GATEWAY, ctx)
        label = self.format_label(SeedLabel.API_GATEWAY, ctx.account_number, ctx.region)

        try:
            apis = client.get_rest_apis()
            for domain in apis.get("items", []):
                domain_name = f"{domain['id']}.execute-api.{ctx.region}.amazonaws.com"
                with SuppressValidationError():
                    domain_seed = DomainSeed(value=domain_name, label=label)
                    # self.add_seed(domain_seed, api_gateway_res=domain)
                    self.emit_seed(ctx, domain_seed, api_gateway_res=domain)
        except ClientError as e:
            self.logger.error(f"Could not connect to API Gateway V1. Error: {e}")

    def get_api_gateway_domains_v2(self, **kwargs):
        """Retrieve API Gateway V2 domains and emit seeds."""
        key = kwargs["scan_context_key"]
        ctx: AwsScanContext = self.scan_contexts[key]

        client: ApiGatewayV2Client = self.get_aws_client(
            AwsServices.API_GATEWAY_V2, ctx
        )
        label = self.format_label(SeedLabel.API_GATEWAY, ctx.account_number, ctx.region)

        try:
            apis = client.get_apis()
            for domain in apis.get("Items", []):
                domain_name = domain["ApiEndpoint"].split("//")[1]
                with SuppressValidationError():
                    domain_seed = DomainSeed(value=domain_name, label=label)
                    # self.add_seed(domain_seed, api_gateway_res=domain)
                    self.emit_seed(ctx, domain_seed, api_gateway_res=domain)
        except ClientError as e:
            self.logger.error(f"Could not connect to API Gateway V2. Error: {e}")

    def get_api_gateway_domains(self, **kwargs):
        """Retrieve all versions of Api Gateway data and emit seeds."""
        self.get_api_gateway_domains_v1(**kwargs)
        self.get_api_gateway_domains_v2(**kwargs)
        label = self.format_label(SeedLabel.API_GATEWAY)
        if not self.seeds.get(label):
            self.delete_seeds_by_label(label)

    def get_load_balancers_v1(self, **kwargs):
        """Retrieve Elastic Load Balancers (ELB) V1 data and emit seeds."""
        key = kwargs["scan_context_key"]
        ctx: AwsScanContext = self.scan_contexts[key]

        client: ElasticLoadBalancingClient = self.get_aws_client(
            service=AwsServices.LOAD_BALANCER, ctx
        )
        label = self.format_label(SeedLabel.LOAD_BALANCER, ctx.account_number, ctx.region)

        try:
            data = client.describe_load_balancers()
            for elb in data.get("LoadBalancerDescriptions", []):
                if value := elb.get("DNSName"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=value, label=label)
                        # self.add_seed(domain_seed, elb_res=elb, aws_client=client)
                        self.emit_seed(ctx, domain_seed, elb_res=elb, aws_client=client)
        except ClientError as e:
            self.logger.error(f"Could not connect to ELB V1. Error: {e}")

    def get_load_balancers_v2(self, **kwargs):
        """Retrieve Elastic Load Balancers (ELB) V2 data and emit seeds."""
        key = kwargs["scan_context_key"]
        ctx: AwsScanContext = self.scan_contexts[key]

        client: ElasticLoadBalancingv2Client = self.get_aws_client(
            AwsServices.LOAD_BALANCER_V2, ctx
        )
        label = self.format_label(SeedLabel.LOAD_BALANCER, ctx.account_number, ctx.region)

        try:
            data = client.describe_load_balancers()
            for elb in data.get("LoadBalancers", []):
                if value := elb.get("DNSName"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=value, label=label)
                        # self.add_seed(domain_seed, elb_res=elb, aws_client=client)
                        self.emit_seed(ctx, domain_seed, elb_res=elb, aws_client=client)
        except ClientError as e:
            self.logger.error(f"Could not connect to ELB V2. Error: {e}")

    def get_load_balancers(self, **kwargs):
        """Retrieve Elastic Load Balancers (ELB) data and emit seeds."""
        self.get_load_balancers_v1(**kwargs)
        self.get_load_balancers_v2(**kwargs)
        label = self.format_label(SeedLabel.LOAD_BALANCER)
        if not self.seeds.get(label):
            self.delete_seeds_by_label(label)

    def get_network_interfaces(self, **kwargs):
        """Retrieve EC2 Elastic Network Interfaces (ENI) data and emit seeds."""
        key = kwargs["scan_context_key"]
        ctx: AwsScanContext = self.scan_contexts[key]

        label = self.format_label(SeedLabel.NETWORK_INTERFACE, ctx.account_number, ctx.region)
        interfaces = self.describe_network_interfaces(ctx)
        instance_tags, instance_tag_sets = self.get_resource_tags(ctx)

        for ip_address, record in interfaces.items():
            instance_id = record["InstanceId"]
            tags = instance_tags.get(instance_id)
            if tags and self.has_ignored_tag(ctx.ignored_tags, tags):
                self.logger.debug(
                    f"Skipping ignored tag for network instance {ip_address}"
                )
                continue

            with SuppressValidationError():
                ip_seed = IpSeed(value=ip_address, label=label)
                # self.add_seed(ip_seed, tags=instance_tag_sets.get(instance_id))
                self.emit_seed(ctx, ip_seed, tags=instance_tag_sets.get(instance_id))

    def describe_network_interfaces(self, ctx: AwsScanContext) -> dict:
        """Retrieve EC2 Elastic Network Interfaces (ENI) data.

        Raises:
            ClientError: If the client could not be created.

        Returns:
            dict: Network Interfaces.
        """
        ec2: EC2Client = self.get_aws_client(AwsServices.EC2, ctx)
        interfaces: dict[str, dict[str, Union[None, str, list]]] = {}

        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_network_interfaces
        filters: Sequence[FilterTypeDef] = [
            {"Name": "association.public-ip", "Values": ["*"]}
        ]

        try:
            data = ec2.describe_network_interfaces(Filters=filters)
            for network in data.get("NetworkInterfaces", {}):
                network_interface_id = network.get("NetworkInterfaceId")
                instance_id = network.get("Attachment", {}).get("InstanceId")

                if self.network_interfaces_ignored_tags(ctx.ignored_tags, network):
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
            raise

        return interfaces

    def get_resource_tags_paginated(
        self,
        ctx: AwsScanContext,
        resource_types: Optional[list[str]] = None,
    ) -> Generator[TagDescriptionTypeDef, None, None]:
        """Retrieve EC2 resource tags paginated.

        Args:
            resource_types (Optional[list[str]]): Resource types. Defaults to None.

        Yields:
            Generator[TagDescriptionTypeDef]: Tags.
        """
        ec2: EC2Client = self.get_aws_client(AwsServices.EC2, ctx)
        paginator = ec2.get_paginator("describe_tags")

        for page in paginator.paginate(
            Filters=[
                {"Name": "resource-type", "Values": resource_types or ["instance"]}
            ]
        ):
            tags = page.get("Tags", [])
            yield from tags

    def get_resource_tags(
        self,
        ctx: AwsScanContext,
        resource_types: Optional[list[str]] = None,
    ) -> tuple[dict, dict]:
        """Get EC2 resource tags based on resource types.

        Args:
            resource_types (Optional[list[str]]): Resource type filter.

        Returns:
            tuple[dict, dict]: Instance tags and tag sets.
        """
        resource_tags: dict = {}
        resource_tag_sets: dict = {}

        for tag in self.get_resource_tags_paginated(resource_types, ctx):
            # Tags come in two formats:
            # 1. Tag = { Key = "Name", Value = "actual-tag-name" }
            # 2. Tag = { Key = "actual-key-name", Value = "tag-value-that-is-unused-here"}
            tag_name = tag.get("Key")
            if tag_name == "Name":
                tag_name = tag.get("Value")

            # Note: resource id is instance id
            resource_id = tag.get("ResourceId")
            if _resource_tags := resource_tags.get(resource_id):
                _resource_tags.append(tag_name)
                resource_tag_sets[resource_id].append(tag)
            else:
                resource_tags[resource_id] = [tag_name]
                resource_tag_sets[resource_id] = [tag]

        return resource_tags, resource_tag_sets

    def network_interfaces_ignored_tags(
        self, ignored_tags: list[str], data: NetworkInterfaceTypeDef
    ) -> bool:
        """Check if network interface has ignored tags.

        Args:
            data (NetworkInterfaceTypeDef): Raw AWS tag data in key value pairs.

        Returns:
            bool: True if ignore tags detected.
        """
        tag_set = data.get("TagSet", [])
        tags = self.extract_tags_from_tagset(tag_set)
        return self.has_ignored_tag(ignored_tags, tags)

    def get_rds_instances(self, **kwargs):
        """Retrieve Relational Database Services (RDS) data and emit seeds."""
        key = kwargs["scan_context_key"]
        ctx: AwsScanContext = self.scan_contexts[key]

        client: RDSClient = self.get_aws_client(service=AwsServices.RDS, ctx)
        label = self.format_label(SeedLabel.RDS, ctx.account_number, ctx.region)
        has_added_seeds = False

        try:
            data = client.describe_db_instances()
            for instance in data.get("DBInstances", []):
                if not instance.get("PubliclyAccessible"):
                    continue

                if domain_name := instance.get("Endpoint", {}).get("Address"):
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=domain_name, label=label)
                        # self.add_seed(domain_seed, rds_res=instance)
                        has_added_seeds = True
                        self.emit_seed(ctx, domain_seed, rds_res=instance)
            if not has_added_seeds:
                self.delete_seeds_by_label(label)
        except ClientError as e:
            self.logger.error(f"Could not connect to RDS Service. Error: {e}")

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

    def get_route53_zones(self, **kwargs):
        """Retrieve Route 53 Zones and emit seeds."""
        key = kwargs["scan_context_key"]
        ctx: AwsScanContext = self.scan_contexts[key]

        client: Route53Client = self.get_aws_client(AwsServices.ROUTE53_ZONES, ctx)
        label = self.format_label(
            SeedLabel.ROUTE53_ZONES, ctx.account_number, ctx.region
        )

        has_added_seeds = False
        try:
            zones = self._get_route53_zone_hosts(client)
            for zone in zones.get("HostedZones", []):
                if zone.get("Config", {}).get("PrivateZone"):
                    continue

                # Add the zone itself as a seed
                domain_name = zone.get("Name").rstrip(".")
                with SuppressValidationError():
                    domain_seed = DomainSeed(value=domain_name, label=label)
                    has_added_seeds = True
                    # self.add_seed(domain_seed, route53_zone_res=zone, aws_client=client)
                    self.emit_seed(ctx, domain_seed, route53_zone_res=zone)

                id = zone.get("Id")
                resource_sets = self._get_route53_zone_resources(client, id)
                for resource_set in resource_sets.get("ResourceRecordSets", []):
                    # Note: localstack creates 2 entries per hosted zone. (remember this if stats are "off")
                    # if resource_set.get("Type") not in VALID_RECORD_TYPES:
                    # continue  # turned off so localstack things show up

                    domain_name = resource_set.get("Name").rstrip(".")
                    with SuppressValidationError():
                        domain_seed = DomainSeed(value=domain_name, label=label)
                        self.add_seed(
                            domain_seed, route53_zone_res=zone, aws_client=client
                        )
                        has_added_seeds = True
            if not has_added_seeds:
                self.delete_seeds_by_label(label)
        except ClientError as e:
            self.logger.error(f"Could not connect to Route 53 Zones. Error: {e}")

    def get_ecs_instances(self, **kwargs):
        """Retrieve Elastic Container Service data and emit seeds."""
        key = kwargs["scan_context_key"]
        ctx: AwsScanContext = self.scan_contexts[key]

        ecs: ECSClient = self.get_aws_client(AwsServices.ECS, ctx)
        ec2: EC2Client = self.get_aws_client(AwsServices.EC2, ctx)
        label = self.format_label(SeedLabel.ECS, ctx.account_number, ctx.region)

        has_added_seeds = False
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
                            # self.add_seed(ip_seed, ecs_res=instance)
                            has_added_seeds = True
                            self.emit_seed(ctx, ip_seed, ecs_res=instance)
            if not has_added_seeds:
                self.delete_seeds_by_label(label)
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

    def get_s3_instances(self, **kwargs):
        """Retrieve Simple Storage Service data and emit seeds."""
        # TODO: how to pass in cred,region?
        key = kwargs["scan_context_key"]
        ctx: AwsScanContext = self.scan_contexts[key]

        client: S3Client = self.get_aws_client(AwsServices.STORAGE_BUCKET, ctx)

        try:
            data = client.list_buckets().get("Buckets", [])

            for bucket in data:
                bucket_name = bucket.get("Name")
                if not bucket_name:
                    continue

                lookup_region = self.get_s3_region(client, bucket_name)
                label = self.format_label(
                    SeedLabel.STORAGE_BUCKET,
                    ctx.account_number,
                    ctx.region,
                )

                with SuppressValidationError():
                    bucket_asset = AwsStorageBucketAsset(
                        value=AwsStorageBucketAsset.url(bucket_name, lookup_region),
                        uid=label,
                        scan_data={
                            "accountNumber": ctx.account_number,
                        },
                    )
                    # self.add_cloud_asset(bucket_asset, bucket_name=bucket_name, aws_client=client)
                    self.emit_cloud_asset(
                        ctx, bucket_asset, bucket_name=bucket_name, aws_client=client
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

    def has_ignored_tag(self, ignored_tags: list[str], tags: list[str]) -> bool:
        """Check if a list of tags contains an ignored tag.

        Args:
            ignored_tags (list[str]): Ignored tags for the current AwsScanContext
            tags (list[str]): Tags on the current AWS resource.

        Returns:
            bool: If the list contains an ignored tag.
        """
        return any(tag in ignored_tags for tag in tags)

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
