"""AWS specific settings."""

from typing import Any, Optional, Union

from pydantic import ConstrainedInt, Field, root_validator, validator

from censys.cloud_connectors.aws_connector.enums import AwsResourceTypes
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings


class AwsAccountNumber(ConstrainedInt):
    """Account Number."""

    gt = 1
    lt = 10**12


class AwsSpecificSettings(ProviderSpecificSettings):
    """AWS specific settings."""

    provider = ProviderEnum.AWS
    ignore: Optional[list[AwsResourceTypes]] = None
    account_number: list[AwsAccountNumber] = Field(min_items=1)

    # User Account Access
    access_key: Optional[str] = Field(min_length=1)
    secret_key: Optional[str] = Field(min_length=1)
    session_token: Optional[str] = Field(min_length=1)

    # Role Account Access
    primary_access_id: Optional[str] = Field(min_length=1)
    primary_access_secret_id: Optional[str] = Field(min_length=1)
    role_to_assume: Optional[str] = Field(min_length=1)

    regions: list[str] = Field(min_items=1)

    role_session_name: Optional[str] = Field(min_length=1)
    external_id: Optional[str] = Field(min_length=1)

    @root_validator
    def validate_one_access_type(cls, values: dict[str, Any]) -> dict:
        """Validate either User or Role access type is used.

        Args:
            values (dict): Settings

        Raises:
            ValueError: only one access type is allowed

        Returns:
            dict: Settings
        """
        has_user = values["access_key"] is not None and values["secret_key"] is not None
        has_role = (
            values["primary_access_id"] is not None
            and values["primary_access_secret_id"] is not None
        )
        if not (has_user or has_role):
            raise ValueError("user or role access type required")

        if has_user and has_role:
            raise ValueError("only one access type is allowed")

        return values

    def get_provider_key(self) -> tuple:
        """Get provider key.

        Returns:
            tuple: [str, str]: Provider key.
        """
        accounts = "_".join(
            [str(account_number) for account_number in sorted(self.account_number)]
        )
        regions = "_".join(self.regions)
        return accounts, regions

    @validator("account_number", pre=True, allow_reuse=True)
    def validate_account_number(cls, v: Union[str, list[str]]) -> list[str]:
        """Validate and ensure account number is a list of strings.

        Args:
            v (Union[str, list[str]]): Value as string or list of strings

        Returns:
            list[str]: Account Numbers
        """
        if not isinstance(v, list):
            return [v]
        return v
