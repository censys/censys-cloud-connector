"""AWS credentials."""

from typing import Optional, TypedDict

from aiobotocore.session import get_session
from types_aiobotocore_sts.client import STSClient

from .settings import AwsAccount, AwsSpecificSettings


class StsClientKwargs(TypedDict, total=False):
    """STS Client kwargs."""

    aws_access_key_id: Optional[str]
    aws_secret_access_key: Optional[str]
    region_name: Optional[str]


class AwsCredentials(TypedDict, total=False):
    """AWS credentials."""

    aws_access_key_id: Optional[str]
    aws_secret_access_key: Optional[str]
    aws_session_token: Optional[str]
    region_name: Optional[str]


async def get_aws_credentials(
    provider_settings: AwsSpecificSettings,
    account: Optional[AwsAccount] = None,
    region: Optional[str] = None,
) -> AwsCredentials:
    """Get AWS credentials.

    Args:
        provider_settings (AwsSpecificSettings): The provider settings.
        account (Optional[AwsAccount], optional): The account. Defaults to None.
        region (Optional[str], optional): The region. Defaults to None.

    Returns:
        AwsCredentials: The AWS credentials.
    """
    provider_has_credentials = bool(
        provider_settings.access_key and provider_settings.secret_key
    )
    provider_has_role = bool(
        provider_settings.role_name and provider_settings.role_session_name
    )

    # If an account is provided, use it
    if account:
        account_has_credentials = bool(account.access_key and account.secret_key)
        account_has_role = bool(account.role_name and account.role_session_name)

        # If the provider has a role and the account has credentials, assume it using the account credentials
        if provider_has_role and account_has_credentials:
            assert provider_settings.role_name
            assert provider_settings.role_session_name
            return await assume_role(
                account.account_number,
                provider_settings.role_name,
                provider_settings.role_session_name,
                access_key=account.access_key,
                secret_key=account.secret_key,
                region=region,
            )

        # If the account has a role and the provider has credentials, assume it using the provider credentials
        if account_has_role and provider_has_credentials:
            assert account.role_name
            assert account.role_session_name
            return await assume_role(
                account.account_number,
                account.role_name,
                account.role_session_name,
                access_key=provider_settings.access_key,
                secret_key=provider_settings.secret_key,
                region=region,
            )

        # If the provider has a role and credentials, assume it using the provider credentials
        if provider_has_role and provider_has_credentials:
            assert provider_settings.role_name
            assert provider_settings.role_session_name
            return await assume_role(
                account.account_number,
                provider_settings.role_name,
                provider_settings.role_session_name,
                access_key=provider_settings.access_key,
                secret_key=provider_settings.secret_key,
                region=region,
            )

        # If neither the provider nor the account have credentials, but the account has a role, assume it using local credentials
        if account_has_role:
            assert account.role_name
            assert account.role_session_name
            return await assume_role(
                account.account_number,
                account.role_name,
                account.role_session_name,
                region=region,
            )

        # If neither the provider nor the account have credentials, but the provider has a role, assume it using local credentials
        if provider_has_role:
            assert provider_settings.role_name
            assert provider_settings.role_session_name
            return await assume_role(
                account.account_number,
                provider_settings.role_name,
                provider_settings.role_session_name,
                region=region,
            )

        # If the account has credentials, but no role, use them
        if account_has_credentials:
            assert account.access_key
            assert account.secret_key
            return {
                "aws_access_key_id": account.access_key,
                "aws_secret_access_key": account.secret_key,
                "region_name": region,
            }

        # If neither the provider nor the account have credentials or roles, use local credentials
        return {}  # pragma: no cover

    # If the provider has a role and credentials, assume it using the provider credentials
    if provider_has_role and provider_has_credentials:
        assert provider_settings.role_name
        assert provider_settings.role_session_name
        return await assume_role(
            provider_settings.account_number,
            provider_settings.role_name,
            provider_settings.role_session_name,
            access_key=provider_settings.access_key,
            secret_key=provider_settings.secret_key,
            region=region,
        )

    # If the provider has a role, but no credentials, assume it using local credentials
    if provider_has_role:
        assert provider_settings.role_name
        assert provider_settings.role_session_name
        return await assume_role(
            provider_settings.account_number,
            provider_settings.role_name,
            provider_settings.role_session_name,
            region=region,
        )

    credentials: AwsCredentials = {}

    # If there is a region specified, use it
    if region:
        credentials["region_name"] = region

    # If the provider has credentials, but no role, use them
    if provider_has_credentials:
        assert provider_settings.access_key
        assert provider_settings.secret_key
        credentials.update(
            {
                "aws_access_key_id": provider_settings.access_key,
                "aws_secret_access_key": provider_settings.secret_key,
            }
        )

    # If the provider has neither credentials nor a role, use local credentials
    return credentials


async def assume_role(
    account_number: str,
    role_name: str,
    role_session_name: str,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    region: Optional[str] = None,
) -> AwsCredentials:
    """Assume an AWS role.

    Args:
        account_number (str): The account number.
        role_name (str): The role name.
        role_session_name (str): The role session name.
        access_key (str, optional): The access key. Defaults to None.
        secret_key (str, optional): The secret key. Defaults to None.
        region (str, optional): The region. Defaults to None.

    Returns:
        AwsCredentials: The AWS credentials.
    """
    # Format the role arn
    role_arn = f"arn:aws:iam::{account_number}:role/{role_name}"

    # kwargs for the sts client
    client_kwargs: StsClientKwargs = {}

    # Add the access key and secret key if they were provided
    if access_key and secret_key:
        client_kwargs["aws_access_key_id"] = access_key
        client_kwargs["aws_secret_access_key"] = secret_key

    # Add the region if it was provided
    if region:
        client_kwargs["region_name"] = region

    # Create the sts client
    async with get_session().create_client("sts", **client_kwargs) as client:
        client: STSClient  # type: ignore[no-redef]
        # Assume the role
        response = await client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=role_session_name,
        )

    assumed_credentials = response["Credentials"]

    credentials: AwsCredentials = {
        "aws_access_key_id": assumed_credentials["AccessKeyId"],
        "aws_secret_access_key": assumed_credentials["SecretAccessKey"],
        "aws_session_token": assumed_credentials["SessionToken"],
    }

    # Add the region if it was provided
    if region:
        credentials["region_name"] = region

    return credentials
