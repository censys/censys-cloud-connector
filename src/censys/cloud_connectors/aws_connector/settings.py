"""AWS specific settings."""

from typing import Any, Optional

from pydantic import BaseModel, ConstrainedStr, Field, root_validator

from censys.cloud_connectors.aws_connector.enums import AwsMessages, AwsResourceTypes
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import ProviderSpecificSettings

DEFAULT_IGNORE = ["censys-cloud-connector-ignore"]


class AwsAccountNumber(ConstrainedStr):
    """Account Number."""

    regex = "^[0-9]{12}$"


class AwsAccount(BaseModel):
    """AWS Account."""

    account_number: AwsAccountNumber = Field()
    access_key: Optional[str] = Field(min_length=1)
    secret_key: Optional[str] = Field(min_length=1)
    role_name: Optional[str] = Field(min_length=1)
    role_session_name: Optional[str] = Field(min_length=1)
    ignore_tags: list[str] = Field(description="Tags to ignore", default_factory=list)


class AwsSpecificSettings(ProviderSpecificSettings):
    """AWS specific settings."""

    provider = ProviderEnum.AWS
    ignore: Optional[list[AwsResourceTypes]] = None

    account_number: AwsAccountNumber = Field()
    access_key: Optional[str] = Field(min_length=1)
    secret_key: Optional[str] = Field(min_length=1)
    role_name: Optional[str] = Field(min_length=1)
    role_session_name: Optional[str] = Field(min_length=1)
    ignore_tags: list[str] = Field(description="Tags to ignore", default=DEFAULT_IGNORE)

    session_token: Optional[str] = Field(min_length=1)
    external_id: Optional[str] = Field(min_length=1)

    accounts: Optional[list[AwsAccount]] = None

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
        has_key = values.get("access_key") and values.get("secret_key")
        has_role = values.get("role_name")
        has_none = not has_key and not has_role

        if has_none:
            raise ValueError(AwsMessages.KEY_OR_ROLE_REQUIRED.value)

        return values

    def get_provider_key(self) -> tuple:
        """Get provider key.

        Returns:
            tuple: Provider key.
        """
        return (self.account_number,)

    def get_provider_payload(self) -> dict:
        """Get the provider payload.

        Returns:
            dict: The provider payload.
        """
        return {
            self.provider: {
                "account_number": self.account_number,
            }
        }

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

        for index, account in enumerate(data.get("accounts") or []):
            data["accounts"][index] = AwsAccount(**account)

        return cls(**data)
