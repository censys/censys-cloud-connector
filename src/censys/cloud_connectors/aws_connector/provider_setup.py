"""Aws specific setup CLI."""
import os
import re
from typing import Optional

from censys.cloud_connectors.aws_connector.enums import AwsDefaults, AwsMessages
from censys.cloud_connectors.aws_connector.service import AwsSetupService
from censys.cloud_connectors.aws_connector.settings import AwsSpecificSettings
from censys.cloud_connectors.common.cli.provider_setup import ProviderSetupCli
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.settings import Settings

BACKOFF_MAX_TIME = 20
BACKOFF_TRIES = 3

has_boto = False
try:

    # note: boto exceptions are dynamically created; there aren't actual classes to import
    from botocore.exceptions import ClientError

    has_boto = True
except ImportError:
    pass


class AwsSetupCli(ProviderSetupCli):
    """AWS provider setup cli command."""

    provider = ProviderEnum.AWS
    provider_specific_settings_class = AwsSpecificSettings

    def __init__(self, settings: Settings, aws: Optional[AwsSetupService] = None):
        """Initialize the AWS setup CLI.

        Args:
            settings (Settings): Settings.
            aws (AwsSetupService): AWS Setup Service.
        """
        super().__init__(settings)

        self.aws = aws or AwsSetupService(self.logger, settings)

    def ask_role_session_name(self) -> str:
        """Prompt for a Role Session Name name.

        Returns:
            str: Role session name.
        """
        self.print_info(
            "AWS recommends setting 'Role Session Name' to the name or identifier that is associated with the user who is using your application."
        )
        answers = self.prompt(
            {
                "type": "input",
                "name": "answer",
                "message": "Enter role session name to use:",
                "default": AwsDefaults.ROLE_SESSION_NAME.value,
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
                "message": "Enter the StackSet name to use:",
                "default": AwsDefaults.STACK_SET_NAME.value,
                "invalid_message": "StackSet name must be between 1 and 64 characters.",
                "validate": lambda name: len(name) > 1 and len(name) <= 64,
            }
        )
        return str(answers.get("answer"))

    def ask_stackset(self, exclude_id: str) -> list[dict]:
        """Find accounts by stack set.

        Args:
            exclude_id (str): Primary account id.

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
            accounts = []

        if not accounts:
            self.confirm_or_exit(AwsMessages.PROMPT_NO_ACCOUNTS_FOUND.value)
            return []

        questions = [
            {
                "type": "list",
                "name": "accounts",
                "max_height": "70%",
                "message": "Select accounts(s):",
                "instruction": "Use <up> and <down> to scroll, <space> to select, <ctrl>+<r> to select all, <enter> to continue.",
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

    def ask_list_accounts(self, exclude_id: str):
        """Ask for the sub-accounts to use.

        Args:
            exclude_id (str): Id to exclude.

        Returns:
            list(str): Account ids.
        """
        accounts = self.get_account_choices(exclude_id)
        if not accounts:
            self.confirm_or_exit(AwsMessages.PROMPT_NO_ACCOUNTS_FOUND.value)
            return []

        questions = [
            {
                "type": "list",
                "name": "accounts",
                "max_height": "70%",
                "message": "Select accounts(s):",
                "instruction": "Use <up> and <down> to scroll, <space> to select, <ctrl>+<r> to select all, <enter> to continue.",
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

    def ask_account_lookup_method(self, primary_id: str) -> list[str]:
        """Prompt for the account lookup method.

        Args:
            primary_id (str): Primary account id.

        Returns:
            list[str]: Account ids.
        """
        self.print_info("Required permissions:")
        self.print_info("- Organization List Accounts uses Organizations ListAccounts.")
        self.print_info("- StackSet uses CloudFormation ListStackInstances.")

        choices = {
            "Find by Organization List Accounts": self.ask_list_accounts,
            "Find by StackSet": self.ask_stackset,
            "Do not load any accounts": lambda x: [],
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

    def confirm_or_exit(
        self, message: Optional[str] = None, default: bool = False
    ) -> None:
        """Prompt to continue or exit setup.

        Args:
            message (str): Question to ask user.
            default (bool): Pass no to exit.
        """
        if not self.prompt_confirm(message, default=default):
            self.print_info("Exiting...")
            exit(0)

    def get_account_choices(self, exclude_id: str) -> list[dict]:
        """Fetch all available accounts.

        The main focus of this method is to capture any service level errors.

        Args:
            exclude_id: Account id to exclude.

        Returns:
            list[dict]: Account ids.
        """
        try:
            return self.aws.get_organization_list_accounts(exclude_id)
        except ClientError as e:
            if e.response["Error"]["Code"] == "AWSOrganizationsNotInUseException":
                self.print_warning(AwsMessages.ORGANIZATIONS_NOT_IN_USE.value)
                self.confirm_or_exit()
            else:
                self.print_error(f"[red]Get Accounts error: {e}")
                self.confirm_or_exit("Unable to load accounts. Proceed?")
        except Exception as e:
            self.print_error(f"[red]Get Accounts error: {e}")
            self.confirm_or_exit("Unable to load accounts. Proceed?")

        return []

    def ask_role_name(self) -> str:
        """Prompt for a role name.

        Returns:
            str: Role name.
        """
        if not self.prompt_confirm(
            "Do you want to run the Censys Cloud Connector with a specific IAM Role?"
        ):
            return ""

        answers = self.prompt(
            {
                "type": "input",
                "name": "answer",
                "message": "Enter an existing IAM Role name to use:",
                "default": AwsDefaults.ROLE_NAME.value,
                "invalid_message": "Role name must be between 1 and 64 characters. Use alphanumeric and '+=,.@-_' characters.",
                "validate": self.aws.valid_role_name,
            }
        )
        return str(answers.get("answer"))

    def ask_primary_account(self) -> str:
        """Get the primary account id.

        Returns:
            str: Primary account id.
        """
        try:
            primary_id = self.aws.get_primary_account()
        except Exception as e:
            self.print_error(f"[red]Error getting primary account: {e}")
            exit(1)

        if len(primary_id) < 12:
            self.print_error("[red]Unable to find primary account.")
            exit(1)

        self.print_info(
            "A primary account is required to run the Censys Cloud Connector."
        )
        self.confirm_or_exit(f"Confirm your Primary Account ID: {primary_id}", True)
        return primary_id

    def ask_access_key(self, access_key: str) -> str:
        """Ask for the access key.

        Args:
            access_key: Access key.

        Returns:
            str: Primary account id.
        """
        questions = {
            "type": "password",
            "name": "answer",
            "message": "(Optional) Access key:",
            "default": access_key,
        }
        answers = self.prompt(questions)
        return answers.get("answer") or ""

    def ask_secret_key(self, secret_key: str) -> str:
        """Ask for the secret key.

        Args:
            secret_key: Secret key.

        Returns:
            str: Secret key.
        """
        questions = {
            "type": "password",
            "name": "answer",
            "message": "(Optional) Secret key:",
            "default": secret_key,
        }
        answers = self.prompt(questions)
        return answers.get("answer") or ""

    def ask_regions(self) -> list[str]:
        """Ask to confirm region selections.

        Returns:
            list[str]: Regions.
        """
        try:
            regions = self.aws.get_regions()
        except Exception:
            self.print_error(
                "Unable to load regions from AWS. Please check your credentials and try again."
            )
            exit(1)

        questions = [
            {
                "type": "fuzzy",
                "name": "regions",
                "max_height": "70%",
                "message": "Select region(s):",
                "instruction": "Fuzzy search enabled. Use <up> and <down> to scroll, <space> to select, <ctrl>+<r> to select all, <enter> to continue.",
                "choices": regions,
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
        self, ids: list[str], role: str, role_session_name: str
    ) -> list[dict]:
        """Generate the provider settings account data structure.

        Args:
            ids (list[str]): Account ids.
            role (str): Role name.
            role_session_name (str): Role session name.

        Returns:
            list[dict]: Accounts.
        """
        accounts = []
        for id in ids:
            account: dict[str, str] = {
                "account_number": id,
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

    def ask_load_credentials(self, profile: str) -> bool:
        """Ask if the user wants to load credentials from the AWS session.

        Args:
            profile: Profile name.

        Returns:
            bool: True if the user wants to load credentials.
        """
        answer = self.prompt(
            {
                "type": "confirm",
                "name": "answer",
                "message": f"Do you want to run the Cloud Connector using the credentials from profile '{profile}'?",
                "default": False,
            }
        )
        return bool(answer.get("answer"))

    def ask_key_credentials(self, profile: str) -> tuple[str, str]:
        """Ask for credentials.

        Args:
            profile (str): AWS Profile.

        Returns:
            tuple[str, str]: Access key, secret key.
        """
        if self.ask_load_credentials(profile):
            self.print_info(f"Loading access key and secret key from '{profile}'")
            creds = self.aws.get_session_credentials()
            if creds["token"]:
                self.print_error(AwsMessages.TEMPORARY_CREDENTIAL_ERROR.value)
                exit(1)

            return creds["access_key"], creds["secret_key"]
        else:
            # note: keys are still optional; using assume role or deploying an ECS task are keyless examples
            access_key = self.ask_access_key("")
            secret_key = self.ask_secret_key("")
            return access_key, secret_key

    def detect_accounts(self) -> None:
        """Generate providers from the chosen profile."""
        profile = self.select_profile()
        self.aws.profile = profile
        access_key, secret_key = self.ask_key_credentials(profile)

        primary_id = self.ask_primary_account()
        role_name = self.ask_role_name()

        role_session_name = ""
        if role_name:
            self.print_role_creation_instructions(role_name)
            role_session_name = self.ask_role_session_name()

        regions = self.ask_regions()

        ids = []
        if self.prompt_confirm(
            "Would you like to load all accounts within your organization?"
        ):
            ids = self.ask_account_lookup_method(primary_id)

        defaults: dict = {
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
        profile = ""

        try:
            choices = self.get_profile_choices()
            if len(choices) == 1:
                name = choices[0]["name"]
                self.print_info(
                    f"There is only one AWS credential profile called '{name}' available."
                )

            choice = self.prompt_select_one(
                AwsMessages.PROMPT_SELECT_PROFILE.value,
                choices,
                default=os.getenv("AWS_PROFILE"),
            )
            if type(choice) is dict:
                # if there is only 1 choice prompt select one returns a dict, otherwise a string
                profile = choice["value"]
            else:
                profile = choice
        except Exception:
            pass

        if not profile:
            self.print_error("Unable to load your AWS credential profile.")
            exit(1)

        return profile

    def setup(self):
        """Entrypoint for AWS provider setup."""
        self.print_info("Please view our documentation for help with provider setup:")
        self.print_info(AwsMessages.PROVIDER_SETUP_DOC_LINK.value)

        if not has_boto:
            self.print_error("Please install the AWS SDK for Python")
            exit(1)

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
