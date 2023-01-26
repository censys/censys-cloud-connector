"""Aws Services."""

import re
from collections.abc import Generator
from logging import Logger

import boto3
from botocore.credentials import ReadOnlyCredentials
from botocore.exceptions import ClientError

from censys.cloud_connectors.common.cli.provider_setup import backoff_wrapper
from censys.cloud_connectors.common.settings import Settings

BACKOFF_MAX_TIME = 20
BACKOFF_TRIES = 3


class AwsSetupService:
    """Service for AWS setup."""

    profile: str = "default"
    logger: Logger
    settings: Settings

    def __init__(self, logger: Logger, settings: Settings) -> None:
        """Initialize the service. These fields are required for backoff.

        Args:
            logger (Logger): Logger.
            settings (Settings): Settings.
        """
        self.logger = logger
        self.settings = settings

    def session(self):
        """Create a boto session using the configured profile.

        Returns:
            botocore.Session: boto session.
        """
        return boto3.Session(profile_name=self.profile)

    def client(self, service_name: str):
        """Create a boto client.

        Args:
            service_name (str): Service name.

        Returns:
            botocore.client.BaseClient: An AWS boto3 client.
        """
        return self.session().client(service_name)

    def get_organization_list_accounts(self, exclude_id: str) -> list[dict]:
        """Get the accounts that are in the organization.

        Args:
            exclude_id (str): Account id to exclude.

        Returns:
            list[dict]: Accounts.
        """
        accounts: dict[str, dict] = {}
        exclude = str(exclude_id)
        for account in self.get_organization_list_accounts_paginated():
            account_id = account["Id"]
            name = account["Name"]
            if account_id == exclude:
                continue

            accounts[account_id] = {
                "name": f"{account_id} - {name}",
                "value": account_id,
            }

        return list(accounts.values())

    def get_organization_list_accounts_paginated(self) -> Generator[dict, None, None]:
        """Use the AWS Organizations API to return all accounts.

        Yields:
            Iterator[list[dict]]: Accounts.
        """
        client = self.client("organizations")
        paginator = client.get_paginator("list_accounts")
        results = paginator.paginate()
        for page in results:
            yield from page.get("Accounts", [])

    def available_profiles(self) -> list[str]:
        """Return a list of available profiles from the user's credential file.

        Returns:
            list[str]: List of available profiles.
        """
        return self.session().available_profiles

    def valid_role_name(self, role: str) -> bool:
        """Validate an AWS IAM Role name.

        Documentation is available at
        https://docs.aws.amazon.com/IAM/latest/APIReference/API_CreateRole.html

        Args:
            role (str): Role name.

        Returns:
            bool: True if valid, False otherwise.
        """
        return bool(re.match(r"^[\w+=,.@-]{1,64}$", role))

    def get_primary_account(self) -> str:
        """Get the primary account id.

        Returns:
            str: Primary account id.
        """
        sts = self.client("sts")
        identity = sts.get_caller_identity()
        return identity.get("Account", "")

    def get_regions(self) -> list[str]:
        """Get AWS regions.

        Returns:
            list[str]: Regions.
        """
        regions = set[str]()
        session = self.session()

        region = session.region_name
        if region:
            regions.update([region])

        if available := session.get_available_regions("sts"):
            regions.update(available)

        region_list = list(regions)
        region_list.sort()
        return region_list

    @backoff_wrapper(
        (ClientError),
        task_description="[blue]Validating credentials...",
        max_time=BACKOFF_MAX_TIME,
        max_tries=BACKOFF_TRIES,
    )
    def validate_account(self, credentials: dict) -> bool:
        """Get the caller identity using the provided credentials.

        This is useful to determine if the credentials are valid.

        Args:
            credentials (dict): Credentials.

        Returns:
            bool: True if valid, False otherwise.
        """
        session = boto3.Session(**credentials)
        client = session.client("sts")

        identity = client.get_caller_identity()
        return bool(identity.get("Account"))

    @backoff_wrapper(
        (ClientError),
        task_description="[blue]Validating credentials...",
        max_time=BACKOFF_MAX_TIME,
        max_tries=BACKOFF_TRIES,
    )
    def validate_assume_role_account(
        self, account_number: str, role: str, credentials: dict
    ) -> bool:
        """Validate the credentials for this assume role are accurate.

        Args:
            account_number (str): Primary account id.
            role (str): Role to assume.
            credentials (dict): Credentials.

        Returns:
            bool: True if valid, False otherwise.
        """
        session = boto3.Session(**credentials)
        client = session.client("sts")

        resp = client.assume_role(
            RoleArn=f"arn:aws:iam::{account_number}:role/{role}",
            RoleSessionName="CensysCloudConnectorSetup",
        )
        temp_creds = resp.get("Credentials")
        if not temp_creds:
            return False

        # validate sts credentials work
        valid = self.validate_account(temp_creds)
        if not valid:
            self.logger.error(
                f"[red]Invalid credentials for account {account_number} and role {role}"
            )
        return False

    def get_frozen_credentials(self) -> ReadOnlyCredentials:
        """Load the frozen credentials from AWS configuration.

        Returns:
            ReadOnlyCredentials
        """
        return self.session().get_credentials().get_frozen_credentials()

    def get_session_credentials(self) -> dict[str, str]:
        """Used to populate the credentials in providers configuration.

        Returns:
            dict[str,str]: Credentials.
        """
        cred = {
            "access_key": "",
            "secret_key": "",
            "token": "",
        }

        try:
            current_credentials: ReadOnlyCredentials = self.get_frozen_credentials()

            cred["access_key"] = current_credentials.access_key
            cred["secret_key"] = current_credentials.secret_key
            cred["token"] = current_credentials.token
        except Exception as e:
            self.logger.error(f"[red]Error getting session credentials: {e}")
            pass

        return cred

    def get_stackset_accounts(self, stack_set_name: str, exclude_id: str) -> list[dict]:
        """Get the accounts that have a stackset.

        Args:
            stack_set_name (str): Stackset name.
            exclude_id (str): Account id to exclude.

        Returns:
            list[dict]: List of account ids.
        """
        accounts: dict[str, dict] = {}
        exclude = exclude_id
        for account in self.get_stackset_accounts_paginated(stack_set_name):
            account_id = account["Account"]
            org = account["OrganizationalUnitId"]
            if account_id == exclude:
                continue

            accounts[account_id] = {
                "name": f"{account_id} (Org: {org})",
                "value": account_id,
            }

        return list(accounts.values())

    def get_stackset_accounts_paginated(
        self, stack_set_name: str
    ) -> Generator[dict, None, None]:
        """Flatten out the paginated StackSet accounts results.

        Args:
            stack_set_name (str): StackSet name.

        Yields:
            Iterator[list[dict]]: Accounts.
        """
        session = self.session()
        region_name = session.region_name or "us-east-1"
        client = session.client("cloudformation", region_name=region_name)

        paginator = client.get_paginator("list_stack_instances")
        results = paginator.paginate(
            StackSetName=stack_set_name,
        )

        for page in results:
            yield from page.get("Summaries", [])
