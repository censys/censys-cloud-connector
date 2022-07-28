import json
from unittest import TestCase
from unittest.mock import Mock, call

import pytest
from parameterized import parameterized

from censys.cloud_connectors.aws_connector.connector import AwsCloudConnector
from censys.cloud_connectors.aws_connector.enums import (
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

    def mock_client(self):
        # client service is irrelevant for integration tests
        return self.mocker.patch.object(self.connector, "get_aws_client")

    def mock_client_api_response(self, client, method_name, data):
        mock_method = self.mocker.patch.object(client.return_value, method_name)
        mock_method.return_value = data
        return mock_method

    def mock_api_response(self, method_name, data):
        # Create a client and mock the API call
        return self.mock_client_api_response(self.mock_client(), method_name, data)

    def test_init(self):
        self.skipTest("TODO")  # TODO

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

        # Actual call
        self.connector.scan_all()

        # Assertions
        assert mock_scan.call_count == 2

    # TODO test multiple account_numbers with multiple regions
    # TODO test single account_number with multiple regions

    def test_scan(self):
        self.skipTest("TODO")  # TODO

    # TODO test_scan_clears_account_and_region

    @parameterized.expand([(ClientError,)])
    def test_scan_fail(self, exception):
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

    def test_get_seeds_ignore(self):
        self.skipTest("TODO")  # TODO

    def test_get_api_gateway_domains(self):
        # TODO ensure v1 & v2 are called
        self.skipTest("TODO")

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
        self.skipTest("TODO")  # TODO ensure v1 & v2 called

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

    def test_route53_instances(self):
        self.skipTest(
            "TODO ensure get_route53_domains and get_route53_zones are called"
        )

    def test_route53_domains_create_seeds(self):
        # Test data
        data = self.data["TEST_ROUTE53_DOMAINS"].copy()
        test_label = f"AWS: Route53/Domains - 999999999999/{self.region}"
        test_seed_values = ["example.net", "example.com"]

        # Mock
        self.mock_api_response("list_domains", data)

        # Actual call
        self.connector.get_route53_domains()

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    def test_route53_domains_pagination(self):
        self.skipTest("TODO list_domains('NextPageMarker')")

    def test_route53_zones_creates_seeds(self):
        # Test data
        hosts = self.data["TEST_ROUTE53_ZONES_LIST_HOSTED_ZONES"].copy()
        resources = self.data["TEST_ROUTE53_ZONES_LIST_RESOURCE_RECORD_SETS"].copy()
        test_label = f"AWS: Route53/Zones - 999999999999/{self.region}"
        expected_calls = [
            call(DomainSeed(value="example.com", label=test_label)),
            call(DomainSeed(value="sub.example.com", label=test_label)),
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
        assert mock_add_seed.call_count == 2

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
                    scan_data={"accountNumber": 999999999999},
                )
            ),
            call(
                AwsStorageBucketAsset(
                    value="https://test-bucket-2.s3.test-region-1.amazonaws.com",
                    uid=test_label,
                    scan_data={"accountNumber": 999999999999},
                )
            ),
        ]

        # Mock
        self.mock_api_response("list_buckets", data)
        mock_add = self.mocker.patch.object(self.connector, "add_cloud_asset")

        self.mocker.patch.object(
            self.connector, "_get_s3_region"
        ).return_value = self.region

        # Actual Call
        self.connector.get_s3_instances()

        # Assertions
        mock_add.assert_has_calls(expected_calls)
        assert mock_add.call_count == 2

    # TODO test_get_s3_instances_without_region

    def test_ecs_instances_creates_seeds(self):
        # Test data
        clusters = self.data["TEST_ECS_LIST_CLUSTERS"].copy()
        containers = self.data["TEST_ECS_LIST_CONTAINER_INSTANCES"].copy()
        instances = self.data["TEST_ECS_DESCRIBE_CONTAINER_INSTANCES"].copy()
        descriptions = self.data["TEST_ECS_EC2_DESCRIBE_INSTANCES"].copy()
        test_label = f"AWS: ECS - 999999999999/{self.region}"
        expected_calls = [
            call(IpSeed(value="108.156.117.66", label=test_label)),
            call(IpSeed(value="108.156.117.67", label=test_label)),
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
            RoleArn="arn:aws:iam::999999999999:role/CensysCloudConnectorRole"
        )

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
