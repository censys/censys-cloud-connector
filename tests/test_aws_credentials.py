from typing import Optional

import asynctest
from asynctest import TestCase
from parameterized import parameterized

from censys.cloud_connectors.aws_connector.credentials import (
    assume_role,
    get_aws_credentials,
)
from censys.cloud_connectors.aws_connector.settings import (
    AwsAccount,
    AwsAccountNumber,
    AwsSpecificSettings,
)
from tests.base_case import BaseCase


class TestAwsCredentials(BaseCase, TestCase):
    @parameterized.expand(
        [
            (
                "account-creds-assume-account-role",
                {"region_name": "us-east-1"},
                {
                    "account_number": "123123123123",
                    "access_key": None,
                    "secret_key": None,
                    "role_name": "test-role-name-settings",
                    "role_session_name": "test-role-session-name-settings",
                },
                (
                    "321321321321",
                    "test-role-name-account",
                    "test-role-session-name-account",
                ),
                {
                    "access_key": "xxxxxxxxxxxxxxxxxxxx",
                    "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "region": "us-east-1",
                },
                AwsAccount(
                    account_number=AwsAccountNumber("321321321321"),
                    access_key="xxxxxxxxxxxxxxxxxxxx",
                    secret_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    role_name="test-role-name-account",
                    role_session_name="test-role-session-name-account",
                ),
                "us-east-1",
            ),
            (
                "account-creds-assume-settings-role",
                {"region_name": "us-east-1"},
                {
                    "account_number": "123123123123",
                    "access_key": None,
                    "secret_key": None,
                    "role_name": "test-role-name-settings",
                    "role_session_name": "test-role-session-name-settings",
                },
                (
                    "321321321321",
                    "test-role-name-settings",
                    "test-role-session-name-settings",
                ),
                {
                    "access_key": "xxxxxxxxxxxxxxxxxxxx",
                    "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "region": "us-east-1",
                },
                AwsAccount(
                    account_number=AwsAccountNumber("321321321321"),
                    access_key="xxxxxxxxxxxxxxxxxxxx",
                    secret_key="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    role_name=None,
                    role_session_name=None,
                ),
                "us-east-1",
            ),
            (
                "settings-creds-assume-account-role",
                {"region_name": "us-east-1"},
                {
                    "account_number": "123123123123",
                    "access_key": "xxxxxxxxxxxxxxxxxxxx",
                    "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "role_name": None,
                    "role_session_name": None,
                },
                (
                    "321321321321",
                    "test-role-name-account",
                    "test-role-session-name-account",
                ),
                {
                    "access_key": "xxxxxxxxxxxxxxxxxxxx",
                    "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "region": "us-east-1",
                },
                AwsAccount(
                    account_number=AwsAccountNumber("321321321321"),
                    access_key=None,
                    secret_key=None,
                    role_name="test-role-name-account",
                    role_session_name="test-role-session-name-account",
                ),
                "us-east-1",
            ),
            (
                "settings-creds-assume-settings-role",
                {"region_name": "us-east-1"},
                {
                    "account_number": "123123123123",
                    "access_key": "xxxxxxxxxxxxxxxxxxxx",
                    "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "role_name": "test-role-name-settings",
                    "role_session_name": "test-role-session-name-settings",
                },
                (
                    "321321321321",
                    "test-role-name-settings",
                    "test-role-session-name-settings",
                ),
                {
                    "access_key": "xxxxxxxxxxxxxxxxxxxx",
                    "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "region": "us-east-1",
                },
                AwsAccount(
                    account_number=AwsAccountNumber("321321321321"),
                    access_key=None,
                    secret_key=None,
                    role_name=None,
                    role_session_name=None,
                ),
                "us-east-1",
            ),
            (
                "settings-creds-assume-settings-role",
                {"region_name": "us-east-1"},
                {
                    "account_number": "123123123123",
                    "access_key": "xxxxxxxxxxxxxxxxxxxx",
                    "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "role_name": "test-role-name",
                    "role_session_name": "test-role-session-name",
                },
                ("123123123123", "test-role-name", "test-role-session-name"),
                {
                    "access_key": "xxxxxxxxxxxxxxxxxxxx",
                    "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "region": "us-east-1",
                },
                None,
                "us-east-1",
            ),
            (
                "local-creds-assume-settings-role",
                {"region_name": "us-east-1"},
                {
                    "account_number": "123123123123",
                    "access_key": None,
                    "secret_key": None,
                    "role_name": "test-role-name",
                    "role_session_name": "test-role-session-name",
                },
                ("123123123123", "test-role-name", "test-role-session-name"),
                {
                    "region": "us-east-1",
                },
                None,
                "us-east-1",
            ),
            (
                "local-creds-assume-settings-role-account",
                {"region_name": "us-east-2"},
                {
                    "account_number": "123123123123",
                    "access_key": None,
                    "secret_key": None,
                    "role_name": "test-role-name",
                    "role_session_name": "test-role-session-name",
                },
                ("321321321321", "test-role-name", "test-role-session-name"),
                {
                    "region": "us-east-2",
                },
                AwsAccount(
                    account_number=AwsAccountNumber("321321321321"),
                    access_key=None,
                    secret_key=None,
                    role_name=None,
                    role_session_name=None,
                ),
                "us-east-2",
            ),
            (
                "local-creds-assume-account-role-account",
                {"region_name": "us-east-3"},
                {
                    "account_number": "123123123123",
                    "access_key": None,
                    "secret_key": None,
                    "role_name": "test-role-name-settings",
                    "role_session_name": "test-role-session-name-settings",
                },
                (
                    "321321321321",
                    "test-role-name-account",
                    "test-role-session-name-account",
                ),
                {
                    "region": "us-east-3",
                },
                AwsAccount(
                    account_number=AwsAccountNumber("321321321321"),
                    access_key=None,
                    secret_key=None,
                    role_name="test-role-name-account",
                    role_session_name="test-role-session-name-account",
                ),
                "us-east-3",
            ),
        ]
    )
    async def test_get_aws_credentials(
        self,
        name,
        expected_credentials: dict,
        provider_settings_dict: dict,
        assume_role_call_args: Optional[tuple] = None,
        assume_role_call_kwargs: Optional[dict] = None,
        account: Optional[AwsAccount] = None,
        region: Optional[str] = None,
    ):
        # Test data
        provider_settings = AwsSpecificSettings.from_dict(
            {
                "regions": ["us-east-1"],
                **provider_settings_dict,
            }
        )

        # Mocks
        mock_assume_role = self.mocker.patch(
            "censys.cloud_connectors.aws_connector.credentials.assume_role",
            new_callable=asynctest.CoroutineMock,
        )

        # Actual call
        credentials = await get_aws_credentials(
            provider_settings, account=account, region=region
        )

        # Assertions
        if assume_role_call_args:
            if not assume_role_call_kwargs:
                assume_role_call_kwargs = {}
            mock_assume_role.assert_awaited_once_with(
                *assume_role_call_args, **assume_role_call_kwargs
            )
            assert credentials == mock_assume_role.return_value
        else:
            mock_assume_role.assert_not_awaited()
            assert credentials == expected_credentials

    @parameterized.expand(
        [
            ("no-credentials",),
            (
                "access-key-pair",
                "xxxxxxxxxxxxxxxxxxxx",
                "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            ),
            (
                "access-key-pair-region",
                "xxxxxxxxxxxxxxxxxxxx",
                "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "us-east-1",
            ),
            (
                "region-only",
                None,
                None,
                "us-east-1",
            ),
        ]
    )
    async def test_assume_role(
        self,
        name: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
    ):
        # Test data
        account_number = "123123123123"
        role_name = "test-role-name"
        role_session_name = "test-role-session-name"
        role_arn = f"arn:aws:iam::{account_number}:role/{role_name}"
        expected_credentials = {
            "aws_access_key_id": access_key or "test-access-key-id",
            "aws_secret_access_key": secret_key or "test-secret-access-key",
            "aws_session_token": "test-session-token",
        }
        create_client_kwargs = {}
        if region:
            create_client_kwargs["region_name"] = region
            expected_credentials["region_name"] = region
        if access_key and secret_key:
            create_client_kwargs["aws_access_key_id"] = access_key
            create_client_kwargs["aws_secret_access_key"] = secret_key

        # Mocks
        mock_get_session = self.mocker.patch(
            "censys.cloud_connectors.aws_connector.credentials.get_session",
            new_callable=asynctest.MagicMock(),
        )
        mock_session = mock_get_session.return_value
        mock_create_client = mock_session.create_client
        mock_client = mock_create_client.return_value.__aenter__.return_value
        mock_client.assume_role = asynctest.CoroutineMock(
            return_value={
                "Credentials": {
                    "AccessKeyId": access_key or "test-access-key-id",
                    "SecretAccessKey": secret_key or "test-secret-access-key",
                    "SessionToken": "test-session-token",
                }
            }
        )
        mock_assume_role = mock_client.assume_role

        # Actual call
        assumed_credentials = await assume_role(
            account_number=account_number,
            role_name=role_name,
            role_session_name=role_session_name,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
        )

        # Assertions
        mock_get_session.assert_called_once_with()
        mock_create_client.assert_called_once_with(
            "sts",
            **create_client_kwargs,
        )
        mock_assume_role.assert_awaited_once_with(
            RoleArn=role_arn,
            RoleSessionName=role_session_name,
        )
        assert assumed_credentials == expected_credentials
