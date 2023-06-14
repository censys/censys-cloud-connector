import json
from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, Mock, call

import pytest
from parameterized import parameterized

from censys.cloud_connectors.aws_connector.connector import AwsCloudConnector
from censys.cloud_connectors.aws_connector.enums import (
    AwsDefaults,
    AwsResourceTypes,
    AwsServices,
    SeedLabel,
)
from censys.cloud_connectors.aws_connector.settings import AwsSpecificSettings
from censys.cloud_connectors.common.cloud_asset import AwsStorageBucketAsset
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import DomainSeed, IpSeed
from tests.base_connector_case import BaseConnectorCase

failed_import = False
try:
    from botocore.exceptions import ClientError
except ImportError:
    failed_import = True


@pytest.mark.skipif(failed_import, reason="AWS SDK not installed")
class TestAwsConnector(BaseConnectorCase, TestCase):
    connector: AwsCloudConnector
    connector_cls = AwsCloudConnector

    def setUp(self) -> None:
        super().setUp()

        # Note: responses contains a block that stores the credentials
        with open(self.shared_datadir / "test_aws_responses.json") as f:
            self.data = json.load(f)

        test_aws_settings = AwsSpecificSettings.from_dict(self.data["TEST_CREDS"])
        self.settings.providers[ProviderEnum.AWS] = {
            test_aws_settings.get_provider_key(): test_aws_settings
        }
        self.connector = AwsCloudConnector(self.settings)
        self.connector.provider_settings = test_aws_settings

        self.connector.account_number = self.data["TEST_CREDS"]["account_number"]
        creds = test_aws_settings.get_credentials()
        cred = next(creds)
        self.connector.credential = cred

        self.region = self.data["TEST_CREDS"]["regions"][0]
        self.connector.region = self.region

    def mock_client(self) -> MagicMock:
        """Mock the client creator.

        Returns:
            MagicMock: mocked client
        """
        return self.mocker.patch.object(self.connector, "get_aws_client")

    def mock_client_api_response(
        self, client: MagicMock, method_name: str, data: Any
    ) -> MagicMock:
        """Mock the boto3 client API response.

        Args:
            client (MagicMock): mocked client
            method_name (str): method name
            data (Any): data to return

        Returns:
            MagicMock: mocked client
        """
        return self.mocker.patch.object(
            client.return_value, method_name, return_value=data
        )

    def mock_api_response(self, method_name: str, data: Any) -> MagicMock:
        """Create a client and mock the API response.

        Args:
            method_name (str): method name
            data (Any): data to return

        Returns:
            MagicMock: mocked client
        """
        return self.mock_client_api_response(self.mock_client(), method_name, data)

    def mock_healthcheck(self) -> MagicMock:
        """Mock the healthcheck.

        Returns:
            MagicMock: mocked healthcheck
        """
        return self.mocker.patch(
            "censys.cloud_connectors.aws_connector.connector.Healthcheck"
        )

    def test_get_aws_client(self):
        # Test data
        self.connector.provider_settings = AwsSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )
        service = AwsServices.API_GATEWAY

        # Mock
        mock_client = self.mocker.patch("boto3.client", autospec=True)

        # Actual call
        self.connector.get_aws_client(service)

        # Assertions
        mock_client.assert_called_with(
            service,
            region_name=self.connector.region,
            aws_access_key_id=self.connector.provider_settings.access_key,
            aws_secret_access_key=self.connector.provider_settings.secret_key,
        )

    def test_get_aws_client_uses_override_credentials(self):
        service = AwsServices.API_GATEWAY
        expected = self.data["TEST_BOTO_CRED_FULL"]
        mock_client = self.mocker.patch("boto3.client", autospec=True)
        mock_credentials = self.mocker.patch.object(self.connector, "credentials")

        self.connector.get_aws_client(service, expected)

        mock_client.assert_called_with(service, **expected)
        mock_credentials.assert_not_called()

    def test_get_aws_client_no_key(self):
        cred = self.data["TEST_BOTO_CRED_SSO"]
        service = AwsServices.API_GATEWAY
        mock_client = self.mocker.patch("boto3.client", autospec=True)
        self.connector.get_aws_client(service, cred)
        mock_client.assert_called_with(service)

    def test_credentials_using_role(self):
        cred = self.data["TEST_GET_CREDENTIALS_WITH_ROLE"]
        self.connector.credential = cred
        mocked = self.mocker.patch.object(self.connector, "get_assume_role_credentials")
        self.connector.credentials()
        mocked.assert_called_once_with(cred["role_name"])

    def test_credentials_using_access_key(self):
        self.connector.credential = self.data["TEST_GET_CREDENTIALS_WITH_KEYS"]
        mocked = self.mocker.patch.object(self.connector, "boto_cred")
        self.connector.credentials()
        mocked.assert_called_once_with(
            self.connector.region,
            self.connector.provider_settings.access_key,
            self.connector.provider_settings.secret_key,
            self.connector.provider_settings.session_token,
        )

    def test_boto_cred(self):
        expected = self.data["TEST_BOTO_CRED_FULL"]
        actual = self.connector.boto_cred(
            expected["region_name"],
            expected["aws_access_key_id"],
            expected["aws_secret_access_key"],
            expected["aws_session_token"],
        )
        assert actual == expected

    def test_scan_all(self):
        # Test data
        test_single_account = self.data["TEST_ACCOUNTS"]
        test_aws_settings = [
            AwsSpecificSettings.from_dict(test_single_account),
        ]
        provider_settings: dict[tuple, AwsSpecificSettings] = {
            p.get_provider_key(): p for p in test_aws_settings
        }
        self.connector.settings.providers[self.connector.provider] = provider_settings

        # Mock scan
        mock_scan = self.mocker.patch.object(self.connector, "scan")
        mock_healthcheck = self.mock_healthcheck()

        # Actual call
        self.connector.scan_all()

        # Assertions
        expected_calls = 3
        assert mock_scan.call_count == expected_calls
        self.assert_healthcheck_called(mock_healthcheck, expected_calls)

    # TODO test multiple account_numbers with multiple regions
    # TODO test single account_number with multiple regions

    def test_scan(self):
        self.skipTest("TODO")  # TODO

    # TODO test_scan_clears_account_and_region

    @parameterized.expand([(ClientError,)])
    def test_scan_fail(self, exception: Exception):
        self.skipTest("TODO")  # TODO

    def test_get_seeds(self):
        # Test data
        self.connector.provider_settings = AwsSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )
        seed_scanners = {
            AwsResourceTypes.API_GATEWAY: self.mocker.Mock(),
        }

        # Mock
        self.mocker.patch.object(
            self.connector,
            "seed_scanners",
            new_callable=self.mocker.PropertyMock(return_value=seed_scanners),
        )

        # Actual call
        self.connector.get_seeds()

        # Assertions
        for scanner in self.connector.seed_scanners.values():
            scanner.assert_called_once()

    def test_get_api_gateway_domains(self):
        # Mock
        mocked_scanners = self.mocker.patch.multiple(
            self.connector,
            get_api_gateway_domains_v1=self.mocker.Mock(),
            get_api_gateway_domains_v2=self.mocker.Mock(),
        )

        # Actual call
        self.connector.get_api_gateway_domains()

        # Assertions
        for mocked_scanner in mocked_scanners.values():
            mocked_scanner.assert_called_once_with()

    def test_get_api_gateway_domains_v1_creates_seeds(self):
        # Test data
        domains = self.data["TEST_API_GATEWAY_DOMAINS_V1"].copy()
        test_label = f"AWS: API Gateway - 999999999999/{self.region}"
        test_seed_values = [f"first-id.execute-api.{self.region}.amazonaws.com"]

        # Mock
        self.mock_api_response("get_rest_apis", domains)

        # Actual call
        self.connector.get_api_gateway_domains_v1()

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_api_gateway_domains_v2_creates_seeds(self):
        # Test data
        domains = self.data["TEST_API_GATEWAY_DOMAINS_V2"].copy()
        test_label = f"AWS: API Gateway - 999999999999/{self.region}"
        test_seed_values = [
            "a1b2c3d5.execute-api.us-west-2.amazonaws.com",
            "a1b2c3d4.execute-api.us-west-2.amazonaws.com",
        ]

        # Mock
        self.mock_api_response("get_apis", domains)

        # Actual call
        self.connector.get_api_gateway_domains_v2()

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_load_balancers(self):
        # Mock
        mocked_scanners = self.mocker.patch.multiple(
            self.connector,
            get_load_balancers_v1=self.mocker.Mock(),
            get_load_balancers_v2=self.mocker.Mock(),
        )

        # Actual call
        self.connector.get_load_balancers()

        # Assertions
        for mocked_scanner in mocked_scanners.values():
            mocked_scanner.assert_called_once_with()

    def test_get_elbv1_instances_creates_seeds(self):
        # Test data
        data = self.data["TEST_LOAD_BALANCER_V1"].copy()
        test_label = f"AWS: ELB - 999999999999/{self.region}"
        test_seed_values = ["my-load-balancer-1234567890.us-west-2.elb.amazonaws.com"]

        # Mock
        self.mock_api_response("describe_load_balancers", data)

        # Actual call
        self.connector.get_load_balancers_v1()

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_elbv2_instances_creates_seeds(self):
        # Test data
        data = self.data["TEST_LOAD_BALANCER_V2"].copy()
        test_label = f"AWS: ELB - 999999999999/{self.region}"
        test_seed_values = ["my-load-balancer-424835706.us-west-2.elb.amazonaws.com"]

        # Mock
        self.mock_api_response("describe_load_balancers", data)

        # Actual call
        self.connector.get_load_balancers_v2()

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_network_interfaces_creates_seeds(self):
        # Test data
        data = self.data["TEST_NETWORK_INTERFACES"].copy()
        test_label = f"AWS: ENI - 999999999999/{self.region}"
        test_seed_values = ["108.156.117.66"]

        # Mock
        self.mock_api_response("describe_network_interfaces", data)

        # Actual call
        self.connector.get_network_interfaces()

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_get_network_interfaces_ignores_tags(self):
        data = self.data["TEST_NETWORK_INTERFACES_IGNORES_TAGS"].copy()
        self.mock_api_response("describe_network_interfaces", data)

        add_seed = self.mocker.patch.object(self.connector, "add_seed")

        self.connector.ignored_tags = ["test-ignore-tag-name"]
        self.connector.get_network_interfaces()
        add_seed.assert_not_called()

    def test_ignore_tags_on_ec2_and_eni(self):
        pass

    def test_describe_network_interfaces_ignores_tags(self):
        expected = {
            "3.87.58.15": {
                "NetworkInterfaceId": "eni-0754a4d9b25b09f20",
                "InstanceId": "i-0a9a18cd985cf3dcf",
            },
        }

        data = self.data["TEST_DESCRIBE_NETWORK_INTERFACES_IGNORES_TAGS"].copy()
        self.mock_api_response("describe_network_interfaces", data)
        self.connector.ignored_tags = ["eni-ignore-tag-test"]

        assert self.connector.describe_network_interfaces() == expected

    def test_get_network_interfaces_ignores_instance_tags(self):
        data = self.data["TEST_DESCRIBE_NETWORK_INTERFACES_RESULT"].copy()
        self.mocker.patch.object(
            self.connector, "describe_network_interfaces", return_value=data
        )

        resource_tags = self.data["TEST_INSTANCE_RESOURCE_TAGS"].copy()
        self.mocker.patch.object(
            self.connector, "get_resource_tags_paginated", return_value=resource_tags
        )

        add_seed = self.mocker.patch.object(self.connector, "add_seed")

        self.connector.ignored_tags = ["test-ignore-instance-tag-name"]
        self.connector.get_network_interfaces()
        add_seed.assert_not_called()

    def test_get_resource_tags_handles_multiple_formats(self):
        expected = {
            "test-resource-id-1": ["resource-tag-in-key", "resource-tag-in-value"]
        }
        data = self.data["TEST_RESOURCE_TAGS_MULTIPLE_FORMATS"].copy()
        self.mocker.patch.object(
            self.connector, "get_resource_tags_paginated", return_value=data
        )
        assert self.connector.get_resource_tags() == expected

    def test_rds_instances_creates_seeds(self):
        # Test data
        data = self.data["TEST_RDS_INSTANCES"].copy()
        test_label = f"AWS: RDS - 999999999999/{self.region}"
        test_seed_values = [f"my-db-instance.ccc.{self.region}.rds.amazonaws.com"]

        # Mock
        self.mock_api_response("describe_db_instances", data)

        # Actual call
        self.connector.get_rds_instances()

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_rds_skips_private_instances(self):
        # Test data
        data = self.data["TEST_RDS_SKIPS_PRIVATE"].copy()

        # Mock
        self.mock_api_response("describe_db_instances", data)

        # Actual call
        self.connector.get_rds_instances()

        # Assertions
        assert self.connector.seeds == {}

    def test_route53_zones_creates_seeds(self):
        # Test data
        hosts = self.data["TEST_ROUTE53_ZONES_LIST_HOSTED_ZONES"].copy()
        resources = self.data["TEST_ROUTE53_ZONES_LIST_RESOURCE_RECORD_SETS"].copy()
        test_label = f"AWS: Route53/Zones - 999999999999/{self.region}"
        expected_calls = [
            call(
                DomainSeed(value="example.com", label=test_label),
                route53_zone_res=self.mocker.ANY,
                aws_client=self.mocker.ANY,
            ),
            call(
                DomainSeed(value="example.com", label=test_label),
                route53_zone_res=self.mocker.ANY,
                aws_client=self.mocker.ANY,
            ),
            call(
                DomainSeed(value="sub.example.com", label=test_label),
                route53_zone_res=self.mocker.ANY,
                aws_client=self.mocker.ANY,
            ),
        ]

        # Mock
        self.mocker.patch.multiple(
            self.connector,
            _get_route53_zone_hosts=Mock(return_value=hosts),
            _get_route53_zone_resources=Mock(return_value=resources),
        )

        mock_add_seed = self.mocker.patch.object(self.connector, "add_seed")

        # Actual Call
        self.connector.get_route53_zones()

        # Assertions
        mock_add_seed.assert_has_calls(expected_calls)
        assert mock_add_seed.call_count == 3

    def test_route53_zones_pagination(self):
        self.skipTest("TODO client.get_paginator")

    # TODO test_route53_invalid_domain_raises

    def test_get_s3_instances_creates_seeds(self):
        # Test data
        data = self.data["TEST_S3_BUCKETS"].copy()
        test_label = f"AWS: S3 - 999999999999/{self.region}"
        expected_calls = [
            call(
                AwsStorageBucketAsset(
                    value="https://test-bucket-1.s3.test-region-1.amazonaws.com",
                    uid=test_label,
                    scan_data={"accountNumber": "999999999999"},
                ),
                bucket_name=self.mocker.ANY,
                aws_client=self.mocker.ANY,
            ),
            call(
                AwsStorageBucketAsset(
                    value="https://test-bucket-2.s3.test-region-1.amazonaws.com",
                    uid=test_label,
                    scan_data={"accountNumber": "999999999999"},
                ),
                bucket_name=self.mocker.ANY,
                aws_client=self.mocker.ANY,
            ),
        ]

        # Mock
        self.mock_api_response("list_buckets", data)
        mock_add = self.mocker.patch.object(self.connector, "add_cloud_asset")

        self.mocker.patch.object(
            self.connector, "get_s3_region"
        ).return_value = self.region

        # Actual Call
        self.connector.get_s3_instances()

        # Assertions
        mock_add.assert_has_calls(expected_calls)
        assert mock_add.call_count == 2

    def test_get_s3_region_has_no_region(self):
        data = {"LocationConstraint": None}
        bucket_name = "test-bucket-1"

        mock_client = self.mocker.patch("mypy_boto3_s3.client.S3Client", autospec=True)
        mock_bucket_location = self.mocker.patch.object(
            mock_client, "get_bucket_location", return_value=data
        )
        region = self.connector.get_s3_region(mock_client, bucket_name)

        mock_bucket_location.assert_called_once_with(Bucket=bucket_name)
        # TODO: use AwsDefaults.REGION.value when available
        assert region == "us-east-1"

    def test_get_s3_handles_bucket_region_exception(self):
        buckets = self.data["TEST_S3_BUCKETS"].copy()

        self.mock_api_response("list_buckets", buckets)
        self.mocker.patch.object(
            self.connector, "get_s3_region", side_effect=ClientError({}, "test")
        )
        mock_add_asset = self.mocker.patch.object(self.connector, "add_cloud_asset")
        mock_log = self.mocker.patch.object(self.connector.logger, "error")

        self.connector.get_s3_instances()

        mock_add_asset.assert_not_called()
        mock_log.assert_called_once()

    def test_ecs_instances_creates_seeds(self):
        # Test data
        clusters = self.data["TEST_ECS_LIST_CLUSTERS"].copy()
        containers = self.data["TEST_ECS_LIST_CONTAINER_INSTANCES"].copy()
        instances = self.data["TEST_ECS_DESCRIBE_CONTAINER_INSTANCES"].copy()
        descriptions = self.data["TEST_ECS_EC2_DESCRIBE_INSTANCES"].copy()
        test_label = f"AWS: ECS - 999999999999/{self.region}"
        expected_calls = [
            call(
                IpSeed(value="108.156.117.66", label=test_label),
                ecs_res=self.mocker.ANY,
            ),
            call(
                IpSeed(value="108.156.117.67", label=test_label),
                ecs_res=self.mocker.ANY,
            ),
        ]

        # Mock
        ecs_client = self.mock_client()
        self.mocker.patch.multiple(
            ecs_client,
            list_clusters=Mock(return_value=clusters),
            list_container_instances=Mock(return_value=containers),
            describe_container_instances=Mock(return_value=instances),
        )

        ec2_client = self.mock_client()
        self.mocker.patch.object(
            ec2_client, "describe_instances", Mock(return_value=descriptions)
        )

        client_factory = self.mocker.MagicMock()
        client_factory.side_effect = {
            AwsServices.ECS: ecs_client,
            AwsServices.EC2: ec2_client,
        }.get
        self.mocker.patch.object(self.connector, "get_aws_client", client_factory)

        mock_add_seed = self.mocker.patch.object(self.connector, "add_seed")

        # Actual call
        self.connector.get_ecs_instances()

        # Assertions
        mock_add_seed.assert_has_calls(expected_calls)
        assert mock_add_seed.call_count == 2

    def test_assume_role(self):
        # Test data
        data = self.data["TEST_STS"].copy()

        # Mock
        mock = self.mock_api_response("assume_role", data)

        # Actual call
        result = self.connector.assume_role()

        # Assertions
        assert result["AccessKeyId"] == "sts-access-key-value"
        mock.assert_called_with(
            RoleArn="arn:aws:iam::999999999999:role/CensysCloudConnectorRole",
            RoleSessionName=AwsDefaults.ROLE_SESSION_NAME.value,
        )

    def test_assume_role_with_custom_names(self):
        expected_role = "test-override-role-name"
        expected_role_session = "test-override-role-name"
        data = self.data["TEST_STS"].copy()
        mock = self.mock_api_response("assume_role", data)
        self.connector.credential["role_session_name"] = expected_role_session

        self.connector.assume_role(expected_role)

        mock.assert_called_with(
            RoleArn=f"arn:aws:iam::999999999999:role/{expected_role}",
            RoleSessionName=expected_role_session,
        )

    def test_get_assume_role_credentials_uses_cache(self):
        expected = self.data["TEST_GET_CREDENTIALS_WITH_ROLE"]
        self.connector.temp_sts_cred = expected
        assert self.connector.get_assume_role_credentials() == expected

    def test_get_assume_role_credentials(self):
        role_name = "test-assume-role-name"
        expected = self.data["TEST_BOTO_CRED_FULL"]

        assume_role = self.mock_api_response("assume_role", self.data["TEST_STS"])
        self.mocker.patch.object(self.connector, "boto_cred", return_value=expected)

        assert self.connector.get_assume_role_credentials(role_name) == expected
        assume_role.assert_called_once()

    def test_format_label_without_region(self):
        # Test data
        expected = f"AWS: S3 - 999999999999/{self.region}"

        # Actual call
        label = self.connector.format_label(SeedLabel.STORAGE_BUCKET)

        # Assertions
        assert label == expected

    def test_format_label_with_override_region(self):
        # Test data
        expected = "AWS: S3 - 999999999999/test-region-override"

        # Actual call
        label = self.connector.format_label(
            SeedLabel.STORAGE_BUCKET, "test-region-override"
        )

        # Assertions
        assert label == expected

    def test_format_label_with_connector_region(self):
        # Test data
        expected = f"AWS: S3 - 999999999999/{self.region}"

        # Actual call
        label = self.connector.format_label(SeedLabel.STORAGE_BUCKET)

        # Assertions
        assert label == expected

    def test_generate_ignore_tags(self):
        tags = ["tag-2", "tag-3"]
        actual = self.connector.get_ignored_tags(tags)
        assert "censys-cloud-connector-ignore" in actual
        assert "tag-2" in actual
        assert "tag-3" in actual

    def test_has_ignored_tag(self):
        self.connector.ignored_tags = ["tag-name"]
        assert self.connector.has_ignored_tag(["tag-name"])

    def test_no_ignored_tag(self):
        self.connector.ignored_tags = ["non-existent-tag"]
        assert not self.connector.has_ignored_tag(["tag-name"])

    def test_extract_tags_from_tagset(self):
        tag_set = [{"Key": "tag-1"}, {"Key": "tag-2"}]
        tags = self.connector.extract_tags_from_tagset(tag_set)
        assert tags == ["tag-1", "tag-2"]
