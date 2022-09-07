"""Aws specific setup CLI."""
import os
import re
from logging import Logger
from typing import Optional

from censys.cloud_connectors.aws_connector.enums import AwsMessages
from censys.cloud_connectors.aws_connector.settings import AwsSpecificSettings
from censys.cloud_connectors.common.cli.provider_setup import (
    ProviderSetupCli,
    backoff_wrapper,
)
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import Settings

DEFAULT_STACK_SET_NAME = "CensysCloudConnector"
DEFAULT_ROLE = "CensysCloudConnector"
DEFAULT_ROLE_SESSION_NAME = "cloud-connector-session"
BACKOFF_MAX_TIME = 20
BACKOFF_TRIES = 3

has_boto = False
try:
    import boto3

    # note: boto exceptions are dynamically created; there aren't actual classes to import
    from botocore.exceptions import ClientError

    has_boto = True
except ImportError:
    pass


class AwsSetupCli(ProviderSetupCli):
    """AWS provider setup cli command."""

    provider = ProviderEnum.AWS
    provider_specific_settings_class = AwsSpecificSettings

    def get_primary_account(
        self,
    ) -> Optional[int]:  # type: ignore[missing-return-statement]
        """Determine the primary account id.

        Returns:
            int: primary account id
        """
        id = 0
        try:
            id = self.aws.get_primary_account()
        except Exception as e:
            self.print_error(f"Error loading primary account: {e}")
            exit(1)

        return id

    def ask_role_session_name(self) -> str:
        """Prompt for a Role Session Name name.

        Returns:
            str: Role session name.
        """
        answers = self.prompt(
            {
                "type": "input",
                "name": "answer",
                "message": "Enter role session name to use:",
                "default": DEFAULT_ROLE_SESSION_NAME,
                "invalid_message": "Role session name must be between 1 and 64 characters.",
                "validate": lambda name: re.match(r"^[\w+=,.@-]{2,64}$", name),
            }
        )
        return str(answers.get("answer"))

    def ask_stack_set_name(self) -> str:
        """Prompt for a StackSet name.

        Returns:
            str: Role name.
        """
        answers = self.prompt(
            {
                "type": "input",
                "name": "answer",
                "message": "Enter StackSet to use:",
                "default": DEFAULT_STACK_SET_NAME,
                "invalid_message": "StackSet name must be between 1 and 64 characters.",
                "validate": lambda name: len(name) > 1 and len(name) <= 64,
            }
        )
        return str(answers.get("answer"))

    def ask_stackset(self, exclude_id: int) -> list[dict]:
        """Find accounts by stack set.

        Args:
            exclude_id (int): Primary account id.

        Returns:
            list[dict]: Account Ids.
        """
        stack_set_name = self.ask_stack_set_name()
        try:
            accounts = self.aws.get_stackset_accounts(
                stack_set_name=stack_set_name, exclude_id=exclude_id
            )
        except Exception as e:
            self.print_error(f"Error loading stackset accounts: {e}")
            self.confirm_or_exit("Unable to load stackset accounts. Continue?")
            return []

        questions = [
            {
                "type": "list",
                "name": "accounts",
                "max_height": "70%",
                "message": "Select accounts(s):",
                "instruction": "Use <up> and <down> to scroll, <space> to select, <enter> to continue.",
                "choices": accounts,
                "multiselect": True,
                "validate": lambda regions: len(regions) > 0,
                "invalid_message": "You must select at least one account.",
                "keybindings": {
                    "toggle": [
                        {"key": "space"},
                    ],
                },
            }
        ]
        answers = self.prompt(questions)
        return answers.get("accounts", [])

    def ask_list_accounts(self, exclude_id: int):
        """Ask for the sub-accounts to use.

        Args:
            exclude_id (int): Id to exclude.

        Returns:
            list(int): Account ids.
        """
        self.print_info(
            "Setup can build a list of accounts from your organization if you have the Organizations ListAccounts policy."
        )
        accounts = self.get_account_choices(exclude_id)
        if not accounts:
            return []

        questions = [
            {
                "type": "list",
                "name": "accounts",
                "max_height": "70%",
                "message": "Select accounts(s):",
                "instruction": "Use <up> and <down> to scroll, <space> to select, <enter> to continue.",
                "choices": accounts,
                "multiselect": True,
                "validate": lambda regions: len(regions) > 0,
                "invalid_message": "You must select at least one account.",
                "keybindings": {
                    "toggle": [
                        {"key": "space"},
                    ],
                },
            }
        ]
        answers = self.prompt(questions)
        return answers.get("accounts", [])

    def ask_account_lookup_method(self, primary_id: int) -> list[int]:
        """Prompt for the account lookup method.

        Args:
            primary_id (int): Primary account id.

        Returns:
            list[int]: Account ids.
        """
        self.print_info(
            "Note: each account can have an override role name. Please add them in the generated providers.yml."
        )
        choices = {
            "Find by Organization List Accounts": self.ask_list_accounts,
            "Find by StackSet": self.ask_stackset,
        }
        answers = self.prompt(
            {
                "type": "list",
                "name": "answer",
                "message": "Account retrieval method:",
                "choices": list(choices.keys()),
            }
        )
        answer = answers.get("answer")
        if func := choices.get(answer):  # type: ignore
            return func(primary_id)

        return []

    def confirm_or_exit(self, message: Optional[str] = None) -> None:
        """Prompt to continue or exit setup.

        Args:
            message (str): Question to ask user.
        """
        if not self.prompt_confirm(message, default=False):
            self.print_info("Exiting...")
            exit(0)

    def get_account_choices(self, exclude_id: int) -> list[dict]:
        """Fetch all available accounts.

        Args:
            exclude_id: Account id to exclude.

        Returns:
            list[dict]: Account ids.
        """
        try:
            accounts = self.aws.get_organization_list_accounts()
            choices: list[dict] = []
            for account in accounts:
                account_id = account.get("Id")
                if account_id == exclude_id:
                    continue

                choices.append(
                    {
                        "name": account_id + " - " + account.get("Name"),
                        "value": account_id,
                    }
                )
            return choices
        except ClientError as e:
            if e.response["Error"]["Code"] == "AWSOrganizationsNotInUseException":
                self.print_warning(AwsMessages.ORGANIZATIONS_NOT_IN_USE)
                self.confirm_or_exit()
            else:
                self.print_error(f"Get Accounts error: {e}")
                self.confirm_or_exit("Unable to load accounts. Proceed?")
        except Exception as e:
            self.print_error(f"Get Accounts error: {e}")
            self.confirm_or_exit("Unable to load accounts. Proceed?")

        return []

    def ask_role_name(self) -> str:
        """Prompt for a role name.

        Returns:
            str: Role name.
        """
        if not self.prompt_confirm("Will you be using a role?"):
            return ""

        answers = self.prompt(
            {
                "type": "input",
                "name": "answer",
                "message": "Enter role to use:",
                "default": DEFAULT_ROLE,
                "invalid_message": "Role name must be between 1 and 64 characters. Use alphanumeric and '+=,.@-_' characters.",
                "validate": self.aws.valid_role_name,
            }
        )
        return str(answers.get("answer"))

    def ask_primary_account(self) -> int:
        """Get the primary account id.

        Returns:
            int: Primary account id.
        """
        primary_id = self.get_primary_account()
        questions = {
            "type": "input",
            "name": "answer",
            "message": "Primary account id:",
            "default": primary_id,
            "invalid_message": "Primary account id must be a number.",
            "validate": lambda id: id.isnumeric(),
        }
        answers = self.prompt(questions)
        return answers.get("answer", 0)

    def ask_access_key(self, access_key: str) -> Optional[str]:
        """Ask for the access key.

        Args:
            access_key: Access key.

        Returns:
            int: Primary account id.
        """
        questions = {
            "type": "password",
            "name": "answer",
            "message": "(Optional) Access key:",
            "default": access_key,
        }
        answers = self.prompt(questions)
        return answers.get("answer")

    def ask_secret_key(self, secret_key: str) -> Optional[str]:
        """Ask for the secret key.

        Args:
            secret_key: Secret key.

        Returns:
            Optional[str]: Secret key.
        """
        questions = {
            "type": "password",
            "name": "answer",
            "message": "(Optional) Secret key:",
            "default": secret_key,
        }
        answers = self.prompt(questions)
        return answers.get("answer")

    def ask_regions(self) -> list[str]:
        """Ask to confirm region selections.

        Returns:
            list[str]: Regions.
        """
        questions = [
            {
                "type": "fuzzy",
                "name": "regions",
                "max_height": "70%",
                "message": "Select region(s):",
                "instruction": "Fuzzy search enabled. Use <up> and <down> to scroll, <space> to select, <enter> to continue.",
                "choices": self.aws.get_regions(),
                "multiselect": True,
                "validate": lambda regions: len(regions) > 0,
                "invalid_message": "You must select at least one region.",
                "keybindings": {
                    "toggle": [
                        {"key": "space"},
                    ],
                },
            }
        ]
        answers = self.prompt(questions)
        return answers.get("regions", [])

    def provider_accounts(
        self, ids: list[int], role: str, role_session_name: str
    ) -> list[dict]:
        """Generate the provider settings account data structure.

        Args:
            ids (list[dict]): Account ids.
            role (str): Role name.
            role_session_name (str): Role session name.

        Returns:
            list[dict]: Accounts.
        """
        accounts = []
        for id in ids:
            account: dict[str, str] = {
                "account_number": str(id),
            }

            if role:
                account["role_name"] = role

            if role_session_name:
                account["role_session_name"] = role_session_name

            accounts.append(account)
        return accounts

    def verify_settings(self, settings: AwsSpecificSettings) -> bool:
        """Verify settings.

        Args:
            settings: Settings.

        Returns:
            bool: True if settings are valid.
        """
        primary = {
            "aws_access_key_id": settings.access_key,
            "aws_secret_access_key": settings.secret_key,
        }

        if settings.session_token:
            primary["aws_session_token"] = settings.session_token

        try:
            if not self.aws.validate_account(primary):
                self.confirm_or_exit("Unable to validate account. Proceed?")
        except Exception as e:
            self.print_error(f"Unable to verify account: {e}")
            self.confirm_or_exit()

        return True

    def ask_load_credentials(self) -> bool:
        """Ask if the user wants to load credentials from the AWS session.

        Returns:
            bool: True if the user wants to load credentials.
        """
        answer = self.prompt(
            {
                "type": "confirm",
                "name": "answer",
                "message": "Do you want to run the Cloud Connector using the profile credentials?",
                "default": False,
            }
        )
        return bool(answer.get("answer"))

    def detect_accounts(self) -> None:
        """Generate providers from the chosen profile."""
        profile = self.select_profile()
        self.aws.profile = profile

        primary_id = self.ask_primary_account()

        creds = {}
        if self.ask_load_credentials():
            creds = self.aws.get_session_credentials()

        access_key = self.ask_access_key(creds.get("access_key", ""))
        secret_key = self.ask_secret_key(creds.get("secret_key", ""))

        role_name = self.ask_role_name()

        role_session_name = ""
        if role_name:
            role_session_name = self.ask_role_session_name()

        regions = self.ask_regions()

        ids = []
        if self.prompt_confirm("Load all accounts?"):
            ids = self.ask_account_lookup_method(primary_id)

        self.print_role_creation_instructions(role_name)

        defaults = {
            "account_number": primary_id,
            "regions": regions,
        }

        if access_key:
            defaults["access_key"] = access_key

        if secret_key:
            defaults["secret_key"] = secret_key

        if role_name:
            defaults["role_name"] = role_name

        if role_session_name:
            defaults["role_session_name"] = role_session_name

        if ids:
            defaults["accounts"] = self.provider_accounts(
                ids, role_name, role_session_name
            )

        provider_settings = self.provider_specific_settings_class(**defaults)
        self.add_provider_specific_settings(provider_settings)

        if not self.verify_settings(provider_settings):
            self.print_error("Account verification failed.")
            exit(1)

        self.print_success("auto-detect completed")

    def print_role_creation_instructions(self, role: str):
        """Print role creation instructions.

        Args:
            role (str): Role name.
        """
        self.print_info(f"Please ensure the role {role} exists in your account(s).")
        self.print_info("For more information please see the README:")
        self.print_info(
            "https://github.com/censys/censys-cloud-connector/blob/main/README.md#aws-cloud-connector-role"
        )
        self.confirm_or_exit()

    def get_profile_choices(self):
        """Build the profile choices for the profile selection prompt.

        Returns:
            dict: Profile choices.
        """
        choices: list[dict] = []
        for profile in self.aws.available_profiles():
            choices.append({"name": profile, "value": profile})

        return choices

    def select_profile(self):
        """Ask user to select a profile.

        For more information see
        https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#aws-config-file

        Returns:
            str: Profile name.
        """
        choices = self.get_profile_choices()

        default = os.getenv("AWS_PROFILE")
        return self.prompt_select_one("Select a profile:", choices, default=default)

    def create_stackset(self) -> None:
        """Generate providers from a new StackSet."""
        # TODO: show end user exactly what will be ran in their environment
        # command = self.generate_create_command(create-stackset-command)
        # self.print_command(command)
        # - print_create_stackset_instructions()
        self.print_error("Coming soon!")
        exit(1)

    def setup(self):
        """Entrypoint for AWS provider setup."""
        if not has_boto:
            self.print_error("Please install the AWS SDK for Python")
            exit(1)

        self.aws = AwsSetupService(self.logger, self.settings)

        choices = {
            "Generate with AWS CLI (Recommended)": self.detect_accounts,
            "Input existing credentials": super().setup,
        }
        answers = self.prompt(
            {
                "type": "list",
                "name": "answer",
                "message": "Select a method to configure your credentials:",
                "choices": list(choices.keys()),
            }
        )

        answer = answers.get("answer")
        if func := choices.get(answer):
            func()


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

    def get_organization_list_accounts(self) -> list[dict]:
        """Use the AWS Organizations API to return all accounts.

        Returns:
            list: List of account ids.
        """
        # Other exceptions:
        # AccessDeniedException: Missing IAM policy.
        # TooManyRequestsException: Rate limit exceeded.
        #
        # required policies:
        # - organizations:ListAccounts.
        #
        # docs:
        # https://docs.aws.amazon.com/organizations/latest/APIReference/API_ListAccounts.html#API_ListAccounts_Errors
        accounts: list[dict] = []
        client = self.client("organizations")

        paginator = client.get_paginator("list_accounts")
        for page in paginator.paginate():
            for account in page.get("Accounts", {}):
                accounts.append(account)

        return accounts

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

    def get_primary_account(self) -> Optional[int]:
        """Get the primary account id.

        Returns:
            Optional[int]: Primary account id.
        """
        sts = self.client("sts")
        identity = sts.get_caller_identity()
        return identity.get("Account")

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
        self, account_number: int, role: str, credentials: dict
    ) -> bool:
        """Validate the credentials for this assume role are accurate.

        Args:
            account_number (int): Primary account id.
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

    def get_session_credentials(self):
        """Used to populate the credentials in providers configuration.

        Returns:
            dict[str,str]: Credentials.
        """
        credentials = self.session().get_credentials()
        current_credentials = credentials.get_frozen_credentials()
        return {
            "access_key": current_credentials.access_key,
            "secret_key": current_credentials.secret_key,
            "token": current_credentials.token,
        }

    def get_stackset_accounts(self, stack_set_name: str, exclude_id: int) -> list[dict]:
        """Get the accounts that have a stackset.

        Args:
            stack_set_name (str): Stackset name.
            exclude_id (int): Account id to exclude.

        Returns:
            list[dict]: List of account ids.
        """
        accounts: list[dict] = []

        session = self.session()
        region_name = session.region_name or "us-east-1"
        client = session.client("cloudformation", region_name=region_name)

        paginator = client.get_paginator("list_stack_instances")
        results = paginator.paginate(
            StackSetName=stack_set_name,
            Filters=[{"Name": "DRIFT_STATUS", "Values": "CURRENT"}],
        )
        for page in results:
            for account in page.get("Summaries", []):
                account_id = account["Account"]
                if account_id == exclude_id:
                    continue

                accounts.append(
                    {
                        "name": account_id + " - " + account["StackSetId"],
                        "value": account_id,
                    }
                )

        return accounts
