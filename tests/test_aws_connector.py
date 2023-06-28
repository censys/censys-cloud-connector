import json
from typing import Any, Optional, TypedDict
from unittest.mock import MagicMock, call

import asynctest
from asynctest import TestCase
from botocore.exceptions import ClientError
from parameterized import parameterized

from censys.cloud_connectors.aws_connector.connector import (
    IGNORED_TAGS,
    AwsCloudConnector,
)
from censys.cloud_connectors.aws_connector.credentials import (
    AwsCredentials,
    get_aws_credentials,
)
from censys.cloud_connectors.aws_connector.enums import AwsResourceTypes, SeedLabel
from censys.cloud_connectors.aws_connector.settings import AwsSpecificSettings
from censys.cloud_connectors.common.cloud_asset import AwsStorageBucketAsset
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import IpSeed
from tests.base_connector_case import BaseConnectorCase


class ExpectedScan(TypedDict, total=False):
    """Expected scan details."""

    account_number: str
    access_key: Optional[str]
    secret_key: Optional[str]
    sts_client_access_key: Optional[str]
    sts_client_secret_key: Optional[str]
    role_name: Optional[str]
    role_session_name: Optional[str]
    ignored_tags: Optional[list[str]]
    regions: list[str]


class TestAwsConnector(BaseConnectorCase, TestCase):
    connector: AwsCloudConnector
    connector_cls = AwsCloudConnector
    test_credentials: AwsCredentials
    data: dict[str, dict]

    async def setUp(self) -> None:
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
        self.region = self.data["TEST_CREDS"]["regions"][0]
        self.test_credentials = await get_aws_credentials(
            test_aws_settings, None, self.region
        )

    def mock_session(self) -> asynctest.MagicMock:
        """Mock the session creator.

        Returns:
            MagicMock: mocked session
        """
        mock_get_session = self.mocker.patch(
            "censys.cloud_connectors.aws_connector.connector.get_session",
            new_callable=asynctest.MagicMock(),
        )
        mock_session = mock_get_session.return_value
        return mock_session

    def mock_create_client(
        self, mock_session: asynctest.MagicMock
    ) -> asynctest.MagicMock:
        """Mock the client creator.

        Args:
            mock_session (asynctest.MagicMock): mocked session

        Returns:
            MagicMock: mocked client
        """
        mock_create_client = mock_session.create_client
        return mock_create_client

    def mock_client(
        self, mock_create_client: asynctest.MagicMock
    ) -> asynctest.MagicMock:
        """Mock the client.

        Args:
            mock_create_client (asynctest.MagicMock): mocked client creator

        Returns:
            MagicMock: mocked client
        """
        mock_client = mock_create_client.return_value.__aenter__.return_value
        return mock_client

    def mock_client_api_response(
        self, mock_client: asynctest.MagicMock, method_name: str, data: Any
    ) -> asynctest.MagicMock:
        """Mock the boto3 client API response.

        Args:
            mock_client (asynctest.MagicMock): mocked client
            method_name (str): method name
            data (Any): data to return

        Returns:
            MagicMock: mocked client
        """
        setattr(mock_client, method_name, asynctest.CoroutineMock(return_value=data))
        return mock_client

    def mock_healthcheck(self) -> MagicMock:
        """Mock the healthcheck.

        Returns:
            MagicMock: mocked healthcheck
        """
        return self.mocker.patch(
            "censys.cloud_connectors.aws_connector.connector.Healthcheck"
        )

    async def test_scan_all(self):
        # Test data
        test_single_account = self.data["TEST_ACCOUNTS"]
        test_aws_settings = [
            AwsSpecificSettings.from_dict(test_single_account),
        ]
        provider_settings: dict[tuple, AwsSpecificSettings] = {
            p.get_provider_key(): p for p in test_aws_settings
        }
        self.connector.settings.providers[self.connector.provider] = provider_settings  # type: ignore[arg-type]

        # Mock scan
        mock_healthcheck = self.mock_healthcheck()
        with asynctest.patch.object(self.connector, "scan") as mock_scan:
            # Actual call
            await self.connector.scan_all()

        # Assertions
        expected_calls = 3
        assert mock_scan.call_count == expected_calls
        self.assert_healthcheck_called(mock_healthcheck, expected_calls)

    def get_settings_file(self, file_name) -> list[AwsSpecificSettings]:
        """Read a test providers.yml file.

        Args:
            file_name (str): Filename.

        Returns:
            list[AwsSpecificSettings]: List of AWS provider settings.
        """
        # Clear existing settings
        self.settings.providers.clear()

        # Read test settings
        self.settings.providers_config_file = self.shared_datadir / "aws" / file_name
        self.settings.read_providers_config_file([ProviderEnum.AWS])

        # Get settings
        provider_settings = self.settings.providers[ProviderEnum.AWS]
        settings: list[AwsSpecificSettings] = list(provider_settings.values())  # type: ignore
        return settings

    def build_credentials(
        self, scan: ExpectedScan, region: Optional[str] = None
    ) -> AwsCredentials:
        """Build credentials from scan data.

        Args:
            scan (ExpectedScan): Scan data.
            region (Optional[str], optional): Region. Defaults to None.

        Returns:
            AwsCredentials: AWS credentials.
        """
        credentials: AwsCredentials = {}
        if access_key := scan.get("access_key"):
            credentials["aws_access_key_id"] = access_key
        if secret_key := scan.get("secret_key"):
            credentials["aws_secret_access_key"] = secret_key
        if scan.get("role_name"):
            credentials["aws_access_key_id"] = "example-access-key-assumed-1"
            credentials["aws_secret_access_key"] = "example-secret-key-assumed-1"
            credentials["aws_session_token"] = "example-session-token-assumed-1"
        if region:
            credentials["region_name"] = region
        return credentials

    @parameterized.expand(
        [
            (
                "accounts_inherit_role_and_creds.yml",
                [
                    {
                        "account_number": "111111111111",
                        "sts_client_access_key": "example-access-key-1",
                        "sts_client_secret_key": "example-secret-key-1",
                        "role_name": "test-primary-role-name",
                        "ignored_tags": ["test-primary-ignore-tag-1"],
                        "regions": ["test-region"],
                    },
                    {
                        "account_number": "111111111112",
                        "sts_client_access_key": "example-access-key-1",
                        "sts_client_secret_key": "example-secret-key-1",
                        "role_name": "example-role-2",
                        "ignored_tags": ["test-primary-ignore-tag-1"],
                        "regions": ["test-region"],
                    },
                    {
                        "account_number": "111111111113",
                        "sts_client_access_key": "example-access-key-1",
                        "sts_client_secret_key": "example-secret-key-1",
                        "role_name": "example-role-3",
                        "ignored_tags": ["test-primary-ignore-tag-1"],
                        "regions": ["test-region"],
                    },
                ],
            ),
            (
                "accounts_inherit_role.yml",
                [
                    {
                        "account_number": "111111111111",
                        "role_name": "test-primary-role-name",
                        "ignored_tags": ["test-primary-ignore-tag-1"],
                        "regions": ["test-region"],
                    },
                    {
                        "account_number": "111111111112",
                        "role_name": "test-primary-role-name",
                        "ignored_tags": ["test-primary-ignore-tag-1"],
                        "regions": ["test-region"],
                    },
                    {
                        "account_number": "111111111113",
                        "role_name": "test-primary-role-name",
                        "ignored_tags": ["test-primary-ignore-tag-1"],
                        "regions": ["test-region"],
                    },
                ],
            ),
            (
                "accounts_key.yml",
                [
                    {
                        "account_number": "111111111111",
                        "access_key": "example-access-key-1",
                        "secret_key": "example-secret-key-1",
                        "regions": ["test-region"],
                    },
                    {
                        "account_number": "111111111112",
                        "access_key": "example-access-key-2",
                        "secret_key": "example-secret-key-2",
                        "regions": ["test-region"],
                    },
                ],
            ),
            (
                "accounts_override_role.yml",
                [
                    {
                        "account_number": "111111111111",
                        "role_name": "test-primary-role-name",
                        "regions": ["test-region"],
                    },
                    {
                        "account_number": "111111111112",
                        "role_name": "test-override-role",
                        "regions": ["test-region"],
                    },
                ],
            ),
            (
                "accounts_override.yml",
                [
                    {
                        "account_number": "111111111111",
                        "sts_client_access_key": "test-primary-access-key",
                        "sts_client_secret_key": "test-primary-secret-key",
                        "role_name": "test-primary-role-name",
                        "ignored_tags": [
                            "test-primary-ignore-tag-1",
                        ],
                        "regions": ["test-region"],
                    },
                    {
                        "account_number": "111111111112",
                        "sts_client_access_key": "test-primary-access-key",
                        "sts_client_secret_key": "test-primary-secret-key",
                        "role_name": "test-override-role",
                        "ignored_tags": [
                            "test-override-ignore-tag-1",
                            "test-primary-ignore-tag-1",
                        ],
                        "regions": ["test-region"],
                    },
                ],
            ),
        ]
    )
    async def test_scan_all_with_providers_yaml(
        self, providers_file: str, scans: list[ExpectedScan]
    ):
        # Test data
        self.get_settings_file(providers_file)

        def assume_role_static(
            account_number: str,
            role_name: str,
            role_session_name: str,
            access_key: Optional[str] = None,
            secret_key: Optional[str] = None,
            region: Optional[str] = None,
        ) -> AwsCredentials:
            return {
                "aws_access_key_id": "example-access-key-assumed-1",
                "aws_secret_access_key": "example-secret-key-assumed-1",
                "aws_session_token": "example-session-token-assumed-1",
                "region_name": region,
            }

        # Mock
        mock_assume_role = self.mocker.patch(
            "censys.cloud_connectors.aws_connector.credentials.assume_role",
            new_callable=asynctest.CoroutineMock,
        )
        mock_assume_role.side_effect = assume_role_static
        mock_healthcheck = self.mock_healthcheck()
        with asynctest.patch.object(
            self.connector, "scan", new_callable=asynctest.CoroutineMock
        ) as mock_scan:
            mock_scan: asynctest.CoroutineMock  # type: ignore[no-redef]
            # Actual call
            await self.connector.scan_all()

        print(mock_scan.call_args_list)

        # Assertions
        expected_calls = 0
        for scan in scans:
            for region in scan["regions"]:
                credentials: AwsCredentials = self.build_credentials(scan, region)
                scan_ignored_tags = scan.get("ignored_tags") or []
                ignored_tags = [*IGNORED_TAGS, *scan_ignored_tags]
                ignored_tags.sort()
                mock_scan.assert_any_await(
                    scan["account_number"],
                    self.connector.provider_settings,
                    credentials,
                    region,
                    ignored_tags=ignored_tags,
                )
                expected_calls += 1
        self.assert_healthcheck_called(mock_healthcheck, expected_calls)

    # TODO test multiple account_numbers with multiple regions
    # TODO test single account_number with multiple regions

    # def test_scan(self):
    #     self.skipTest("TODO")  # TODO

    # # TODO test_scan_clears_account_and_region

    # @parameterized.expand([(ClientError,)])
    # def test_scan_fail(self, exception: Exception):
    #     self.skipTest("TODO")  # TODO

    async def test_get_seeds(self):
        # Test data
        self.connector.provider_settings = AwsSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )
        # Mock
        seed_scanners = {
            AwsResourceTypes.API_GATEWAY: asynctest.CoroutineMock(),
        }
        self.mocker.patch.object(
            self.connector,
            "seed_scanners",
            new_callable=self.mocker.PropertyMock(return_value=seed_scanners),
        )

        # Actual call
        await self.connector.get_seeds(self.connector.provider_settings)

        # Assertions
        for scanner in self.connector.seed_scanners.values():
            scanner.assert_called_once()

    async def test_get_api_gateway_domains(self):
        # Mock
        mocked_scanners = self.mocker.patch.multiple(
            self.connector,
            get_api_gateway_domains_v1=asynctest.CoroutineMock(),
            get_api_gateway_domains_v2=asynctest.CoroutineMock(),
        )

        # Actual call
        await self.connector.get_api_gateway_domains(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.API_GATEWAY,
        )

        # Assertions
        for mocked_scanner in mocked_scanners.values():
            mocked_scanner.assert_called_once_with()

    async def test_get_api_gateway_domains_v1_creates_seeds(self):
        # Test data
        domains = self.data["TEST_API_GATEWAY_DOMAINS_V1"].copy()
        test_label = f"AWS: API Gateway - 999999999999/{self.region}"
        test_seed_values = [f"first-id.execute-api.{self.region}.amazonaws.com"]

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "get_rest_apis", domains)

        # Actual call
        await self.connector.get_api_gateway_domains_v1(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.API_GATEWAY,
        )

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_api_gateway_domains_v2_creates_seeds(self):
        # Test data
        domains = self.data["TEST_API_GATEWAY_DOMAINS_V2"].copy()
        test_label = f"AWS: API Gateway - 999999999999/{self.region}"
        test_seed_values = [
            "a1b2c3d5.execute-api.us-west-2.amazonaws.com",
            "a1b2c3d4.execute-api.us-west-2.amazonaws.com",
        ]

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "get_apis", domains)

        # Actual call
        await self.connector.get_api_gateway_domains_v2(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.API_GATEWAY,
        )

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_load_balancers(self):
        # Mock
        mocked_scanners = self.mocker.patch.multiple(
            self.connector,
            get_load_balancers_v1=asynctest.CoroutineMock(),
            get_load_balancers_v2=asynctest.CoroutineMock(),
        )

        # Actual call
        await self.connector.get_load_balancers(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.LOAD_BALANCER,
        )

        # Assertions
        for mocked_scanner in mocked_scanners.values():
            mocked_scanner.assert_called_once_with()

    async def test_get_elbv1_instances_creates_seeds(self):
        # Test data
        data = self.data["TEST_LOAD_BALANCER_V1"].copy()
        test_label = f"AWS: ELB - 999999999999/{self.region}"
        test_seed_values = ["my-load-balancer-1234567890.us-west-2.elb.amazonaws.com"]

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "describe_load_balancers", data)

        # Actual call
        await self.connector.get_load_balancers_v1(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.LOAD_BALANCER,
        )

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_elbv2_instances_creates_seeds(self):
        # Test data
        data = self.data["TEST_LOAD_BALANCER_V2"].copy()
        test_label = f"AWS: ELB - 999999999999/{self.region}"
        test_seed_values = ["my-load-balancer-424835706.us-west-2.elb.amazonaws.com"]

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "describe_load_balancers", data)

        # Actual call
        await self.connector.get_load_balancers_v2(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.LOAD_BALANCER,
        )

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_network_interfaces_creates_seeds(self):
        # Test data
        data = self.data["TEST_NETWORK_INTERFACES"].copy()
        test_label = f"AWS: ENI - 999999999999/{self.region}"
        test_seed_values = ["108.156.117.66"]

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "describe_network_interfaces", data)

        # Actual call
        await self.connector.get_network_interfaces(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.NETWORK_INTERFACE,
        )

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_get_network_interfaces_ignores_tags(self):
        # Test data
        data = self.data["TEST_NETWORK_INTERFACES_IGNORES_TAGS"].copy()
        self.connector.ignored_tags = ["test-ignore-tag-name"]

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "describe_network_interfaces", data)
        add_seed = self.mocker.patch.object(self.connector, "add_seed")

        # Actual call
        await self.connector.get_network_interfaces(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.NETWORK_INTERFACE,
        )

        # Assertions
        add_seed.assert_not_called()

    async def test_ignore_tags_on_ec2_and_eni(self):
        pass

    async def test_describe_network_interfaces_ignores_tags(self):
        # Test data
        expected = {
            "3.87.58.15": {
                "NetworkInterfaceId": "eni-0754a4d9b25b09f20",
                "InstanceId": "i-0a9a18cd985cf3dcf",
            },
        }
        data = self.data["TEST_DESCRIBE_NETWORK_INTERFACES_IGNORES_TAGS"].copy()

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "describe_network_interfaces", data)

        self.connector.ignored_tags = ["eni-ignore-tag-test"]

        # Actual call
        network_interfaces = await self.connector.describe_network_interfaces(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
        )

        # Assertions
        assert network_interfaces == expected

    async def test_get_network_interfaces_ignores_instance_tags(self):
        # Test data
        data = self.data["TEST_DESCRIBE_NETWORK_INTERFACES_RESULT"].copy()
        resource_tags = self.data["TEST_INSTANCE_RESOURCE_TAGS"].copy()
        self.connector.ignored_tags = ["test-ignore-instance-tag-name"]

        # Mock
        mock_describe_network_interfaces = asynctest.MagicMock()
        mock_describe_network_interfaces.__aiter__.return_value = data
        self.mocker.patch.object(
            self.connector,
            "describe_network_interfaces",
            return_value=mock_describe_network_interfaces,
        )

        mock_get_resource_tags_paginated = asynctest.MagicMock()
        mock_get_resource_tags_paginated.__aiter__.return_value = resource_tags
        self.mocker.patch.object(
            self.connector,
            "get_resource_tags_paginated",
            return_value=mock_get_resource_tags_paginated,
        )
        add_seed = self.mocker.patch.object(self.connector, "add_seed")

        # Actual call
        await self.connector.get_network_interfaces(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.NETWORK_INTERFACE,
        )

        # Assertions
        add_seed.assert_not_called()

    async def test_get_resource_tags_handles_multiple_formats(self):
        # Test data
        expected = {
            "test-resource-id-1": ["resource-tag-in-key", "resource-tag-in-value"]
        }
        data = self.data["TEST_RESOURCE_TAGS_MULTIPLE_FORMATS"].copy()

        # Mock
        mock_get_resource_tags_paginated = asynctest.MagicMock()
        mock_get_resource_tags_paginated.__aiter__.return_value = data
        self.mocker.patch.object(
            self.connector,
            "get_resource_tags_paginated",
            return_value=mock_get_resource_tags_paginated,
        )

        # Actual call
        resource_tags = await self.connector.get_resource_tags(
            self.test_credentials, ["instance"]
        )

        # Assertions
        assert resource_tags == expected

    async def test_rds_instances_creates_seeds(self):
        # Test data
        data = self.data["TEST_RDS_INSTANCES"].copy()
        test_label = f"AWS: RDS - 999999999999/{self.region}"
        test_seed_values = [f"my-db-instance.ccc.{self.region}.rds.amazonaws.com"]

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "describe_db_instances", data)

        # Actual call
        await self.connector.get_rds_instances(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.RDS,
        )

        # Assertions
        self.assert_seeds_with_values(
            self.connector.seeds[test_label], test_seed_values
        )

    async def test_rds_skips_private_instances(self):
        # Test data
        data = self.data["TEST_RDS_SKIPS_PRIVATE"].copy()

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "describe_db_instances", data)

        # Actual call
        await self.connector.get_rds_instances(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.RDS,
        )

        # Assertions
        assert self.connector.seeds == {}

    # async def test_route53_zones_creates_seeds(self):
    #     # Test data
    #     hosts = self.data["TEST_ROUTE53_ZONES_LIST_HOSTED_ZONES"].copy()
    #     resources = self.data["TEST_ROUTE53_ZONES_LIST_RESOURCE_RECORD_SETS"].copy()
    #     test_label = f"AWS: Route53/Zones - 999999999999/{self.region}"
    #     expected_calls = [
    #         call(
    #             DomainSeed(value="example.com", label=test_label),
    #             route53_zone_res=self.mocker.ANY,
    #             aws_client=self.mocker.ANY,
    #         ),
    #         call(
    #             DomainSeed(value="example.com", label=test_label),
    #             route53_zone_res=self.mocker.ANY,
    #             aws_client=self.mocker.ANY,
    #         ),
    #         call(
    #             DomainSeed(value="sub.example.com", label=test_label),
    #             route53_zone_res=self.mocker.ANY,
    #             aws_client=self.mocker.ANY,
    #         ),
    #     ]

    #     # Mock
    #     self.mocker.patch.multiple(
    #         self.connector,
    #         _get_route53_zone_hosts=Mock(return_value=hosts),
    #         _get_route53_zone_resources=Mock(return_value=resources),
    #     )

    #     mock_add_seed = self.mocker.patch.object(self.connector, "add_seed")

    #     # Actual Call
    #     await self.connector.get_route53_zones(self.connector.provider_settings)

    #     # Assertions
    #     mock_add_seed.assert_has_calls(expected_calls)
    #     assert mock_add_seed.call_count == 3

    # async def test_route53_zones_pagination(self):
    #     self.skipTest("TODO client.get_paginator")

    # TODO test_route53_invalid_domain_raises

    async def test_get_s3_instances_creates_seeds(self):
        # Test data
        data = self.data["TEST_S3_BUCKETS"].copy()
        test_label = f"AWS: S3 - 999999999999/{self.region}"
        expected_calls = [
            call(
                AwsStorageBucketAsset(  # type: ignore[call-arg]
                    value="https://test-bucket-1.s3.test-region-1.amazonaws.com",
                    uid=test_label,
                    scan_data={"accountNumber": "999999999999"},
                ),
                bucket_name=self.mocker.ANY,
                aws_client=self.mocker.ANY,
            ),
            call(
                AwsStorageBucketAsset(  # type: ignore[call-arg]
                    value="https://test-bucket-2.s3.test-region-1.amazonaws.com",
                    uid=test_label,
                    scan_data={"accountNumber": "999999999999"},
                ),
                bucket_name=self.mocker.ANY,
                aws_client=self.mocker.ANY,
            ),
        ]

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "list_buckets", data)
        mock_add = self.mocker.patch.object(self.connector, "add_cloud_asset")

        self.mocker.patch.object(
            self.connector, "get_s3_region"
        ).return_value = self.region

        # Actual Call
        await self.connector.get_s3_instances(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.STORAGE_BUCKET,
        )

        # Assertions
        mock_add.assert_has_calls(expected_calls)
        assert mock_add.call_count == 2

    async def test_get_s3_region_has_no_region(self):
        data = {"LocationConstraint": None}
        bucket_name = "test-bucket-1"

        mock_client = self.mocker.patch(
            "types_aiobotocore_s3.client.S3Client", autospec=True
        )
        mock_bucket_location = self.mocker.patch.object(
            mock_client, "get_bucket_location", return_value=data
        )
        region = await self.connector.get_s3_region(mock_client, bucket_name)

        mock_bucket_location.assert_called_once_with(Bucket=bucket_name)
        # TODO: use AwsDefaults.REGION.value when available
        assert region == "us-east-1"

    async def test_get_s3_handles_bucket_region_exception(self):
        # Test data
        buckets = self.data["TEST_S3_BUCKETS"].copy()

        # Mock
        mock_session = self.mock_session()
        mock_create_client = self.mock_create_client(mock_session)
        mock_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(mock_client, "list_buckets", buckets)
        self.mocker.patch.object(
            self.connector, "get_s3_region", side_effect=ClientError({}, "test")
        )
        mock_add_asset = self.mocker.patch.object(self.connector, "add_cloud_asset")
        mock_log = self.mocker.patch.object(self.connector.logger, "error")

        # Actual Call
        await self.connector.get_s3_instances(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.STORAGE_BUCKET,
        )

        # Assertions
        mock_add_asset.assert_not_called()
        mock_log.assert_called_once()

    async def test_ecs_instances_creates_seeds(self):
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
        session = self.mock_session()
        mock_create_client = self.mock_create_client(session)

        ecs_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(ecs_client, "list_clusters", clusters)
        self.mock_client_api_response(
            ecs_client, "list_container_instances", containers
        )
        self.mock_client_api_response(
            ecs_client, "describe_container_instances", instances
        )

        ec2_client = self.mock_client(mock_create_client)
        self.mock_client_api_response(ec2_client, "describe_instances", descriptions)

        mock_add_seed = self.mocker.patch.object(self.connector, "add_seed")

        # Actual call
        await self.connector.get_ecs_instances(
            self.connector.provider_settings,
            self.test_credentials,
            self.region,
            [],
            AwsResourceTypes.ECS,
        )

        # Assertions
        mock_add_seed.assert_has_calls(expected_calls)
        assert mock_add_seed.call_count == 2

    def test_format_label_without_region(self):
        # Test data
        expected = "AWS: S3 - 999999999999"

        # Actual call
        label = self.connector.format_label(SeedLabel.STORAGE_BUCKET, region=None)

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
        label = self.connector.format_label(SeedLabel.STORAGE_BUCKET, self.region)

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

    # TODO: Add ignore tag tests for updated credential logic

    def test_extract_tags_from_tagset(self):
        tag_set = [{"Key": "tag-1"}, {"Key": "tag-2"}]
        tags = self.connector.extract_tags_from_tagset(tag_set)  # type: ignore[arg-type]
        assert tags == ["tag-1", "tag-2"]
