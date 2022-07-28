"""AWS specific settings."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field, PositiveInt, root_validator

from censys.cloud_connectors.aws_connector.enums import AwsResourceTypes
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings


class AwsAccountNumber(PositiveInt):
    """Account Number."""

    lt = 10**12


class AwsAccount(BaseModel):
    """AWS Account."""

    account_number: AwsAccountNumber = Field()
    access_key: Optional[str] = Field(min_length=1)
    secret_key: Optional[str] = Field(min_length=1)
    role_name: Optional[str] = Field(min_length=1)
    role_session_name: Optional[str] = Field(min_length=1)


class AwsSpecificSettings(ProviderSpecificSettings):
    """AWS specific settings."""

    provider = ProviderEnum.AWS
    ignore: Optional[List[AwsResourceTypes]] = None

    account_number: Optional[AwsAccountNumber] = Field()
    access_key: Optional[str] = Field(min_length=1)
    secret_key: Optional[str] = Field(min_length=1)
    role_name: Optional[str] = Field(min_length=1)
    role_session_name: Optional[str] = Field(min_length=1)

    session_token: Optional[str] = Field(min_length=1)
    external_id: Optional[str] = Field(min_length=1)

    accounts: Optional[List[AwsAccount]] = None

    regions: list[str] = Field(min_items=1)

    @root_validator
    def validate_account_numbers(cls, values: dict[str, Any]) -> dict:
        """Validate.

        Args:
            values (dict): Settings

        Raises:
            ValueError: Invalid settings.

        Returns:
            dict: Settings
        """
        if values["accounts"] is not None and values["account_number"] is not None:
            raise ValueError("Cannot specify both account_number and accounts")

        return values

    def get_provider_key(self) -> tuple:
        """Get provider key.

        Returns:
            tuple: [str, str]: Provider key.
        """
        accounts = []
        if self.accounts:
            for account in self.accounts:
                accounts.append(str(account.account_number))
        else:
            accounts.append(str(self.account_number))

        return ("_".join(sorted(accounts)), "_".join(self.regions))

    @classmethod
    def from_dict(cls, data: dict):
        """Create a ProviderSpecificSettings object from a dictionary.

        Args:
            data (dict): The dictionary to use.

        Returns:
            ProviderSpecificSettings: The settings.
        """
        if provider_name := data.get("provider"):
            data["provider"] = provider_name.title()

        if "accounts" in data:
            for index, account in enumerate(data["accounts"]):
                data["accounts"][index] = AwsAccount(**account)

        return cls(**data)

    def get_credentials(self):
        """Generator for all configured credentials. Any values within the accounts block will take precedence over the overall values.

        Yields:
            dict[str, Any]
        """
        if self.accounts:
            for account in self.accounts:
                yield {
                    "account_number": (account.account_number or self.account_number),
                    "access_key": (account.access_key or self.access_key),
                    "secret_key": (account.secret_key or self.secret_key),
                    "role_name": (account.role_name or self.role_name),
                    "role_session_name": (
                        account.role_session_name or self.role_session_name
                    ),
                }

        else:
            yield {
                "account_number": self.account_number,
                "access_key": self.access_key,
                "secret_key": self.secret_key,
                "role_name": self.role_name,
                "role_session_name": self.role_session_name,
            }
