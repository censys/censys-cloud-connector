"""AWS Tags Cloud Connector Plugin."""
import contextlib
import urllib.parse
from typing import Callable, Optional

from botocore.exceptions import ClientError
from mypy_boto3_elb import ElasticLoadBalancingClient
from mypy_boto3_elbv2 import ElasticLoadBalancingv2Client
from mypy_boto3_route53 import Route53Client
from mypy_boto3_s3 import S3Client

from censys.asm import AsmClient
from censys.common.exceptions import (
    CensysAsmException,
    CensysDomainNotFoundException,
    CensysException,
)

from censys.cloud_connectors.aws_connector.enums import AwsResourceTypes
from censys.cloud_connectors.common.cloud_asset import AwsStorageBucketAsset, CloudAsset
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.plugins import (
    CloudConnectorPlugin,
    CloudConnectorPluginRegistry,
    EventContext,
    EventTypeEnum,
)
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed, Seed


class AwsTagsPlugin(CloudConnectorPlugin):
    """AWS Tags Plugin.

    This plugin adds tags to Censys ASM for AWS resources.
    To use this plugin, set the AWS_TAGS_PLUGIN_ENABLED env var to True.
    """

    name = "AWS Tags"
    version = "0.0.1"
    client: Optional[AsmClient] = None

    def enabled(self) -> bool:
        """Check if plugin is enabled.

        Returns:
            True if plugin is enabled, False otherwise.
        """
        return self.settings.aws_tags_plugin_enabled

    def register(self, registry: CloudConnectorPluginRegistry) -> None:
        """Register the plugin.

        Args:
            registry: Plugin registry.
        """
        registry.register_event_handler(
            EventTypeEnum.SEED_FOUND,
            self.on_add_seed,  # type: ignore
            self,
            provider=ProviderEnum.AWS,
        )
        registry.register_event_handler(
            EventTypeEnum.CLOUD_ASSET_FOUND,
            self.on_add_cloud_asset,  # type: ignore
            self,
            provider=ProviderEnum.AWS,
        )

    def get_client(self, context: EventContext) -> AsmClient:
        """Get ASM client.

        Args:
            context: Event context.

        Returns:
            ASM client.
        """
        connector = context["connector"]
        settings = connector.settings
        if not self.client:
            self.client = AsmClient(
                settings.censys_api_key,
                url=settings.censys_asm_api_base_url,
                user_agent=settings.censys_user_agent,
                cookies=settings.censys_cookies,
            )
        return self.client

    def on_add_seed(
        self, context: EventContext, seed: Optional[Seed] = None, **kwargs
    ) -> None:
        """On add seed.

        Args:
            context: Event context.
            seed: Seed.
            **kwargs: Additional arguments.
        """
        if seed is None:
            return
        tag_retrieval_handlers: dict[AwsResourceTypes, Callable] = {
            AwsResourceTypes.API_GATEWAY: self._get_api_gateway_tags,
            AwsResourceTypes.LOAD_BALANCER: self._get_load_balancer_tags,
            AwsResourceTypes.NETWORK_INTERFACE: self._get_network_interface_tags,
            AwsResourceTypes.RDS: self._get_rds_tags,
            AwsResourceTypes.ROUTE53: self._get_route53_tags,
            AwsResourceTypes.ECS: self._get_ecs_tags,
        }
        service: Optional[AwsResourceTypes] = context.get("service")  # type: ignore
        if service in tag_retrieval_handlers:
            try:
                tag_retrieval_handlers[service](context, seed, **kwargs)
            except CensysAsmException:
                pass
            except Exception as e:
                connector = context["connector"]
                connector.logger.error(
                    f"Error retrieving tags for {service} {seed.value}: {e}"
                )

    def on_add_cloud_asset(
        self, context: EventContext, cloud_asset: Optional[CloudAsset] = None, **kwargs
    ) -> None:
        """On add cloud asset.

        Args:
            context: Event context.
            cloud_asset: Cloud asset.
            **kwargs: Additional arguments.
        """
        if cloud_asset is None:
            return
        tag_retrieval_handlers: dict[AwsResourceTypes, Callable] = {
            AwsResourceTypes.STORAGE_BUCKET: self._get_storage_bucket_tags,
        }
        service: Optional[AwsResourceTypes] = context.get("service")  # type: ignore
        # service = none, context.get('service') value ins't set
        if service in tag_retrieval_handlers:
            try:
                tag_retrieval_handlers[service](context, cloud_asset, **kwargs)
            except CensysAsmException:
                pass
            except Exception as e:
                connector = context["connector"]
                connector.logger.error(
                    f"Error retrieving tags for {service} {cloud_asset.value}: {e}"
                )

    def format_tags_as_tag_set(self, tags: dict) -> list[dict]:
        """Format tags as tag set.

        Args:
            tags: Tags.

        Returns:
            Formatted tags.
        """
        return [{"Key": k, "Value": v} for k, v in tags.items()]

    def format_tag_set_as_string(self, tag_set: dict) -> str:
        """Format tag set as string.

        Args:
            tag_set: Tag set.

        Returns:
            Formatted tag set.
        """
        return f"{tag_set['Key']}: {tag_set['Value']}"

    def add_ip_tags(
        self, context: EventContext, seed: IpSeed, tag_set: list[dict]
    ) -> None:
        """Add IP tags.

        Args:
            context: Event context.
            seed: Seed.
            tag_set: Tag set.
        """
        client = self.get_client(context)
        for tag in tag_set:
            client.hosts.add_tag(str(seed.value), self.format_tag_set_as_string(tag))

    def _add_subdomain_tag(self, base_domain: str, subdomain: str, tag: str) -> None:
        """Add subdomain tag.

        Args:
            base_domain: Domain.
            subdomain: Subdomain. (Including the base domain)
            tag: Tag.

        Raises:
            CensysException: If the ASM client is not initialized.
        """
        if self.client is None:
            raise CensysException("ASM client not initialized")
        self.client.domains.add_tag(f"{base_domain}/subdomains/{subdomain}", tag)

    def add_subdomain_tag(self, domain_name: str, tag: str) -> None:
        """Add subdomain tag.

        In the case of the following domain: www.test.example.com
        1. Try to add tag to www.test.example.com
        2. If it doesn't exist, try to add tag to the subdomain www.test.example.com at the base domain test.example.com
        3. If it doesn't exist, try to add tag to the subdomain www.test.example.com at the base domain example.com
        4. If it is a TLD, do nothing

        Args:
            domain_name: Domain name.
            tag: Tag.

        Raises:
            CensysException: If the ASM client is not initialized.
        """
        if self.client is None:
            raise CensysException("ASM client not initialized")
        base_domain = domain_name
        while True:
            try:
                self.client.domains.get_asset_by_id(base_domain)
                break
            except CensysDomainNotFoundException:
                base_domain = ".".join(base_domain.split(".")[1:])
                if base_domain.count(".") == 0:
                    return
        self._add_subdomain_tag(base_domain, domain_name, tag)

    def add_domain_tags(
        self, context: EventContext, seed: DomainSeed, tag_set: list[dict]
    ):
        """Add domain tags.

        Args:
            context: Event context.
            seed: Seed.
            tag_set: Tags.
        """
        client = self.get_client(context)
        for tag in tag_set:
            tag_string = self.format_tag_set_as_string(tag)
            # We first try to add the tag to the domain itself
            # If that fails, we try to add the tag to the subdomain at the base domain
            try:
                client.domains.add_tag(str(seed.value), tag_string)
            except CensysDomainNotFoundException:
                self.add_subdomain_tag(str(seed.value), tag_string)

    def add_cloud_asset_tags(
        self, context: EventContext, cloud_asset: CloudAsset, tag_set: list[dict]
    ):
        """Add cloud asset tags.

        Args:
            context: Event context.
            cloud_asset: Cloud asset.
            tag_set: Tags.
        """
        client = self.get_client(context)
        url_encoded_object_storage_key = urllib.parse.quote_plus(
            cloud_asset.value + "/"
        )
        for tag in tag_set:
            # We need to suppress the exception here incase the tag is already added
            # or if the tag is invalid
            with contextlib.suppress(CensysAsmException):
                client.object_storages.add_tag(
                    url_encoded_object_storage_key, self.format_tag_set_as_string(tag)
                )

    def _get_api_gateway_tags(
        self, context: EventContext, seed: DomainSeed, **kwargs
    ) -> None:
        """Get API Gateway tags.

        Args:
            context: Event context.
            seed: Seed.
            kwargs: Additional event data.
        """
        api_gateway_res: Optional[dict] = kwargs.get("api_gateway_res")
        if not api_gateway_res:
            return

        # Check if the api_gateway_res dict has a key called "tags"
        # If it doesn't, then check for the key "Tags"
        tags = api_gateway_res.get("tags", api_gateway_res.get("Tags", []))
        if not tags:
            return

        # Format the tags as a tag set
        tag_set = self.format_tags_as_tag_set(tags)

        self.add_domain_tags(context, seed, tag_set)

    def _get_load_balancer_tags(
        self, context: EventContext, seed: DomainSeed, **kwargs
    ) -> None:
        """Get Load Balancer tags.

        Args:
            context: Event context.
            seed: Seed.
            kwargs: Additional event data.
        """
        elb_res: Optional[dict] = kwargs.get("elb_res")
        aws_client = kwargs.get("aws_client")
        if not elb_res or not aws_client:
            return

        tag_set = None
        if load_balancer_arn := elb_res.get("LoadBalancerArn"):
            # V2 Load Balancer
            aws_client: ElasticLoadBalancingv2Client = aws_client  # type: ignore
            tag_set = aws_client.describe_tags(ResourceArns=[load_balancer_arn])[
                "TagDescriptions"
            ][0]["Tags"]
        elif load_balancer_name := elb_res.get("LoadBalancerName"):
            # V1 Load Balancer
            aws_client: ElasticLoadBalancingClient = aws_client  # type: ignore
            tag_set = aws_client.describe_tags(LoadBalancerNames=[load_balancer_name])[
                "TagDescriptions"
            ][0]["Tags"]

        if not tag_set:
            return

        self.add_domain_tags(context, seed, tag_set)

    def _get_network_interface_tags(
        self, context: EventContext, seed: IpSeed, **kwargs
    ) -> None:
        """Get Network Interface tags.

        Args:
            context: Event context.
            seed: Seed.
            kwargs: Additional event data.
        """
        tags = kwargs.get("tags", [])
        if not tags:
            return

        # Filter out AWS internal tags
        filtered_tags = [tag for tag in tags if not tag["Key"].startswith("aws:")]
        if not filtered_tags:
            return

        self.add_ip_tags(context, seed, filtered_tags)

    def _get_rds_tags(
        self,
        context: EventContext,
        seed: DomainSeed,
        **kwargs,
    ) -> None:
        """Get RDS tags.

        Args:
            context: Event context.
            seed: Seed.
            kwargs: Additional event data.
        """
        rds_res = kwargs.get("rds_res")
        if not rds_res:
            return

        tags = rds_res.get("TagList", [])
        if not tags:
            return

        self.add_domain_tags(context, seed, tags)

    def _get_route53_tags(
        self, context: EventContext, seed: DomainSeed, **kwargs
    ) -> None:
        """Get Route53 tags.

        Args:
            context: Event context.
            seed: Seed.
            kwargs: Additional event data.
        """
        route53_zone_res = kwargs.get("route53_zone_res")
        if not route53_zone_res:
            return
        pre_processed_tags = None
        client: Route53Client = kwargs.get("aws_client")  # type: ignore
        if not client:
            return
        resource_id = route53_zone_res["Id"]
        if resource_id.startswith("/hostedzone/"):
            resource_id = resource_id.split("/hostedzone/")[1]
        pre_processed_tags = client.list_tags_for_resource(
            ResourceType="hostedzone", ResourceId=resource_id
        )["ResourceTagSet"]["Tags"]

        if not pre_processed_tags:
            return

        self.add_domain_tags(context, seed, pre_processed_tags)  # type: ignore

    def _get_ecs_tags(self, context: EventContext, seed: DomainSeed, **kwargs) -> None:
        """Get ECS tags.

        Args:
            context: Event context.
            seed: Seed.
            kwargs: Additional event data.
        """
        ecs_res = kwargs.get("ecs_res")
        if not ecs_res:
            return

        # Getting tags from ec2 instance
        tag_set = ecs_res.get("Tags", [])
        if not tag_set:
            return

        self.add_domain_tags(context, seed, tag_set)

    def _get_storage_bucket_tags(
        self, context: EventContext, cloud_asset: AwsStorageBucketAsset, **kwargs
    ) -> None:
        """Get S3 tags.

        Args:
            context: Event context.
            cloud_asset: Cloud asset.
            kwargs: Additional event data.

        Raises:
            ClientError: If the bucket does not exist.
        """
        bucket_name = kwargs.get("bucket_name")
        client: S3Client = kwargs.get("aws_client")  # type: ignore
        if not bucket_name or not client:
            print(f"tags bucket: {bucket_name} len:0")
            return

        try:
            tag_set = client.get_bucket_tagging(Bucket=bucket_name).get("TagSet", [])
            print(f"tags bucket: {bucket_name} len:{len(tag_set)}")
            if not tag_set:
                return

            # Filter out AWS internal tags
            filtered_tags = [
                tag for tag in tag_set if not tag["Key"].startswith("aws:")
            ]
            if not filtered_tags:
                return

            self.add_cloud_asset_tags(context, cloud_asset, filtered_tags)  # type: ignore
        except ClientError as e:
            print(f"tags bucket: {bucket_name} len:0")
            # If there are no tag sets, it will raise a ClientError with the code "NoSuchTagSet"
            if e.response.get("Error", {}).get("Code") == "NoSuchTagSet":
                return
            raise


__plugin__ = AwsTagsPlugin
