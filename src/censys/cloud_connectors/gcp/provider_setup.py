"""Gcp specific setup CLI."""
import json
import os.path
from typing import Optional

from pydantic import validate_arguments
from rich.progress import track

from censys.cloud_connectors.common.cli.provider_setup import ProviderSetupCli
from censys.cloud_connectors.common.enums import ProviderEnum

from .enums import GcpRoles
from .settings import GcpSpecificSettings


class GcpSetupCli(ProviderSetupCli):
    """Gcp provider setup cli command."""

    provider = ProviderEnum.GCP
    provider_specific_settings_class = GcpSpecificSettings

    def is_gcloud_installed(self) -> bool:
        """Check if user has gcloud installed locally.

        Returns:
            bool: True if installed, false if not.
        """
        gcloud_version = self.run_command("gcloud version")
        # TODO: Capture version stdout and stderr?
        return gcloud_version.returncode == 0

    def get_accounts_from_cli(self) -> list[dict[str, str]]:
        """Get the credentialed accounts from the CLI.

        Returns:
            list[dict[str, str]]: List of credentialed accounts.
        """
        res = self.run_command("gcloud auth list --format=json")
        if res.returncode != 0:
            self.print_warning("Unable to get list of Credentialed GCP Accounts.")
            return []
        return json.loads(res.stdout)

    def prompt_select_account(self, accounts: list[dict[str, str]]) -> Optional[dict]:
        """Prompt the user to select an account.

        Args:
            accounts (list[dict[str, str]]): List of credentialed accounts.

        Returns:
            dict: Selected account.
        """
        if len(accounts) == 1:
            account_email = accounts[0].get("account")
            questions = [
                {
                    "type": "confirm",
                    "name": "use_account",
                    "message": f"Use {account_email}?",
                    "default": True,
                }
            ]
            answers = self.prompt(questions)
            if not answers.get("use_account"):
                return None
            return accounts[0]

        active_account = None
        choices: list[dict] = []
        for account in accounts:
            account_email = account.get("account")
            if not account_email:
                continue
            choice = {"name": account_email, "value": account}
            if account.get("status") == "ACTIVE":
                # Only one account can be active at a time.
                active_account = account
                choice["name"] += " (Active)"  # type: ignore
                choices.insert(0, choice)
            else:
                choices.append(choice)

        questions = [
            {
                "type": "list",
                "message": "Select a GCP account",
                "name": "selected_account",
                "choices": choices,
                "default": active_account,
            }
        ]
        answers = self.prompt(questions)
        return answers.get("selected_account")

    def get_project_id_from_cli(self) -> Optional[str]:
        """Get the project id from the CLI.

        Returns:
            str: Project id.
        """
        res = self.run_command("gcloud config get-value project")
        if res.returncode != 0:
            self.print_info(
                "If you are unsure of the project id, go to https://console.cloud.google.com/iam-admin/settings."
            )
            return None
        return res.stdout.strip()

    @validate_arguments
    def get_organization_id_from_cli(self, project_id: str) -> Optional[str]:
        """Get the organization id from the CLI.

        Args:
            project_id (str): Project id.

        Returns:
            str: Organization id.
        """
        res = self.run_command(
            f"gcloud projects get-ancestors {project_id} --format=json"
        )
        if res.returncode != 0:
            self.print_warning("Unable to get organization id from CLI.")
            return ""
        project_ancestors = json.loads(res.stdout.strip())
        for ancestor in project_ancestors:
            if ancestor.get("type") == "organization":
                return ancestor.get("id", "")
        return ""

    @validate_arguments
    def switch_active_cli_account(self, account_name: str):
        """Switch the active account.

        Args:
            account_name (str): The account name.
        """
        res = self.run_command(f"gcloud config set account {account_name}")
        if res.returncode != 0:
            self.print_warning("Unable to switch active account.")

    def get_service_accounts_from_cli(
        self, project_id: Optional[str] = None
    ) -> list[dict]:
        """Get the service accounts from the CLI.

        Args:
            project_id (str): Project id.

        Returns:
            list[dict]: List of service accounts.
        """
        command = "gcloud iam service-accounts list --format json"
        if project_id:
            command += f" --project {project_id}"
        res = self.run_command(command)
        if res.returncode != 0:
            self.print_warning("Unable to get service accounts from CLI.")
            return []
        service_accounts = json.loads(res.stdout.strip())
        # Filter out the default service accounts
        return [
            account
            for account in service_accounts
            if "@developer.gserviceaccount.com" not in account.get("email")
        ]

    def prompt_select_service_account(
        self, service_accounts: list[dict]
    ) -> Optional[dict]:
        """Prompt the user to select a service account.

        Args:
            service_accounts (list[dict]): List of service accounts.

        Returns:
            dict: Selected service account.
        """
        if len(service_accounts) == 1:
            service_account_email = service_accounts[0].get("email")
            questions = [
                {
                    "type": "confirm",
                    "name": "use_service_account",
                    "message": f"Use {service_account_email}?",
                    "default": True,
                }
            ]
            answers = self.prompt(questions)
            if not answers.get("use_service_account"):
                return None
            return service_accounts[0]
        questions = [
            {
                "type": "list",
                "message": "Select a service account",
                "name": "service_account",
                "choices": [
                    {"name": service_account.get("email"), "value": service_account}
                    for service_account in service_accounts
                ],
            }
        ]
        answers = self.prompt(questions)
        return answers.get("service_account")

    @staticmethod
    def generate_service_account_email(
        service_account_name: str, project_id: str
    ) -> str:
        """Generate the service account email.

        Args:
            service_account_name (str): Service account name.
            project_id (str): Project id.

        Returns:
            str: Service account email.
        """
        return f"{service_account_name}@{project_id}.iam.gserviceaccount.com"

    @validate_arguments
    def generate_role_binding_command(
        self,
        organization_id: str,
        service_account_email: str,
        roles: list[GcpRoles],
    ) -> list[str]:
        """Generate role binding commands.

        Args:
            organization_id (str): Organization id.
            service_account_email (str): Service account email.
            roles (list[GcpRoles]): Roles.

        Returns:
            list[str]: Role binding commands.
        """
        commands = [
            # Adds a comment about scope
            "# Grants the service account the required roles from the organization level"
        ]
        for role in roles:
            commands.append(
                f"gcloud organizations add-iam-policy-binding {organization_id} --member"
                f" 'serviceAccount:{service_account_email}'"
                f" --role '{role}' --no-user-output-enabled --quiet"
            )
        return commands

    @validate_arguments
    def generate_create_service_account_command(
        self,
        name: str = "censys-cloud-connector",
        display_name: str = "Censys Cloud Connector Service Account",
    ) -> str:
        """Generate create service account command.

        Args:
            name (str): Service account name.
            display_name (str): Service account display name.

        Returns:
            str: Create service account command.
        """
        # TODO: Add service account description (--description flag)
        # TODO: Might be worthwhile to add a --project flag to the command
        return (
            f"gcloud iam service-accounts create {name} --display-name '{display_name}'"
        )

    @validate_arguments
    def generate_create_key_command(
        self, service_account_email: str, key_file_path: str
    ) -> list[str]:
        """Generate create key command.

        Args:
            service_account_email (str): Service account email.
            key_file_path (str): Key file path.

        Returns:
            list[str]: Create key commands.
        """
        return [
            "# Generates and downloads a key for the service account",
            f"gcloud iam service-accounts keys create {key_file_path} --iam-account {service_account_email}",
        ]

    @validate_arguments
    def create_service_account(
        self,
        organization_id: str,
        project_id: str,
        service_account_name: str,
        key_file_path: str,
    ) -> Optional[str]:
        """Create a service account.

        Args:
            organization_id (str): Organization id.
            project_id (str): Project id.
            service_account_name (str): The service account name.
            key_file_path (str): The place to store the key file.

        Returns:
            Optional[str]: The service account key file.
        """
        # TODO: Ensure that the APIs are enabled.
        commands = [self.generate_create_service_account_command(service_account_name)]
        service_account_email = self.generate_service_account_email(
            service_account_name, project_id
        )
        commands.extend(
            self.generate_role_binding_command(
                organization_id,
                service_account_email,
                list(GcpRoles),
            )
        )
        commands.extend(
            self.generate_create_key_command(service_account_email, key_file_path)
        )

        self.print_command("\n".join(commands))
        answers = self.prompt(
            {
                "type": "confirm",
                "name": "create_service_account",
                "message": "Create service account with the above commands?",
                "default": True,
            }
        )
        if not answers.get("create_service_account", False):
            self.print_info(
                "Please login and try again. Or run the above commands in the Google Cloud Console."
            )
            return None

        for command in track(commands, description="Running..."):
            res = self.run_command(command)
            if res.returncode != 0:
                self.print_error(
                    f"Failed to create service account. Error: {res.stderr.strip()}"
                )
                return None

        # Check key_file_path exists
        if not os.path.exists(key_file_path):
            self.print_error(
                f"Failed to create service account. Error: {key_file_path} does not exist"
            )
            return None

        return key_file_path

    def check_correct_permissions(self):
        """Verify that the user has the correct organization role to continue."""
        try:
            from google.api_core import exceptions
            from google.cloud import resourcemanager_v3
        except ImportError:
            self.print_error("Please install the google-cloud-resourcemanager library.")
            return

        # Create a client
        client = resourcemanager_v3.OrganizationsClient()
        # Make the request
        try:
            response = client.get_iam_policy(
                request={"resource": f"organizations/{self.organization_id}"}
            )
        except exceptions.PermissionDenied as e:  # pragma: no cover
            # Thrown when the service account does not have permission to
            # access the securitycenter service or the service is disabled.
            self.print_error(e.message)
            return
        # Handle the response
        print(response)

        # potential error: google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials. Please set GOOGLE_APPLICATION_CREDENTIALS or explicitly create credentials and re-run the application. For more information, please see https://cloud.google.com/docs/authentication/getting-started
        # self.print_warning(
        #     f"You do not have the correct organization permissions.\n \
        #     Your user account {user_account} must be \
        #     granted the role 'roles/resourcemanager.organizationAdmin' \
        #     within your organization {organization_id}. You may need to \
        #     contact your organization administrator or switch user accounts.")

    @validate_arguments
    def generate_enable_service_account_command(
        self, service_account_email: str
    ) -> str:
        """Generate enable service account command.

        Args:
            service_account_email (str): Service account email.

        Returns:
            str: Enable service account command.
        """
        return f"gcloud iam service-accounts enable {service_account_email}"

    @validate_arguments
    def enable_service_account(
        self,
        organization_id: str,
        project_id: str,
        service_account_name: str,
        key_file_path: str,
    ) -> Optional[str]:
        """Enable a service account.

        Args:
            organization_id (str): Organization id.
            project_id (str): Project id.
            service_account_name: The service account name.
            key_file_path: The place to store the key file.

        Returns:
            Optional[str]: The existing service account key file.
        """
        service_account_email = self.generate_service_account_email(
            service_account_name, project_id
        )
        commands = [self.generate_enable_service_account_command(service_account_email)]
        commands.extend(
            self.generate_role_binding_command(
                organization_id,
                service_account_email,
                list(GcpRoles),
            )
        )
        commands.extend(
            self.generate_create_key_command(service_account_email, key_file_path)
        )

        self.print_command("\n".join(commands))
        answers = self.prompt(
            [
                {
                    "type": "confirm",
                    "name": "enable_service_account",
                    "message": "Enable service account with the above commands?",
                    "default": True,
                }
            ]
        )

        # TODO: some type of error checking. does service_account exist? what message to print if not?

        if not answers.get("enable_service_account", False):
            self.print_info(
                "Please login and try again. Or run the above commands in the Google Cloud Console."
            )
            return None

        # TODO: Investigate
        for command in track(commands, description="Running..."):
            # TODO: add role checks here
            res = self.run_command(command)
            if res.returncode != 0:
                self.print_error(
                    f"Failed to create service account. Error: {res.stderr.strip()}"
                )
                return None

        # Check key_file_path exists
        if not os.path.exists(key_file_path):
            self.print_error(
                f"Failed to create service account. Error: {key_file_path} does not exist"
            )
            return None

        return key_file_path

    def setup(self):
        """Setup the GCP provider."""
        cli_choice = "Generate with CLI"
        input_choice = "Input existing credentials"
        questions = [
            {
                "type": "list",
                "name": "get_credentials_from",
                "message": "Select a method to configure your credentials:",
                "choices": [cli_choice, input_choice],
            }
        ]
        answers = self.prompt(questions)

        get_credentials_from = answers.get("get_credentials_from")
        if get_credentials_from == input_choice:
            # Prompt for the credentials
            super().setup()
        elif get_credentials_from == cli_choice:
            self.print_info(
                "Before you begin you'll need to have identified the following:\n  [blue]-[/blue] The Google Cloud organization administrator account which will execute scripts that configure the Censys Cloud Connector.\n  [blue]-[/blue] The project that will be used to run the Censys Cloud Connector. Please note that the cloud connector will be scoped to the organization."
            )
            if not self.is_gcloud_installed():
                self.print_warning(
                    r"Please install the [link=https://cloud.google.com/sdk/docs/downloads-interactive]gcloud SDK[\link] before continuing."
                )
                exit(1)

            accounts = self.get_accounts_from_cli()
            if not accounts:
                self.print_error("No accounts found.")
                exit(1)

            selected_account = self.prompt_select_account(accounts)
            if not selected_account:
                # TODO: Print login instructions
                self.print_error("No account selected.")
                exit(1)

            account_email = selected_account.get("account")
            if selected_account.get("status") != "ACTIVE":
                questions = [
                    {
                        "type": "confirm",
                        "name": "switch_account",
                        "message": f"Switch to {account_email}?",
                        "default": True,
                    }
                ]
                answers = self.prompt(questions)
                if not answers.get("switch_account", False):
                    self.print_error("No account selected.")
                    exit(1)

                self.switch_active_cli_account(account_email)

            # TODO: Get project ids from CLI

            # TODO: Prompt user to select project ID from list

            questions = [
                {
                    "type": "input",
                    "name": "project_id",
                    "message": "Enter the project ID:",
                    "default": self.get_project_id_from_cli(),
                }
            ]
            answers = self.prompt(questions)
            project_id = answers.get("project_id")
            if not project_id:
                self.print_error("No project ID entered.")
                exit(1)

            questions = [
                {
                    "type": "input",
                    "name": "organization_id",
                    "message": "Enter the organization ID:",
                    "default": self.get_organization_id_from_cli(project_id),
                }
            ]
            answers = self.prompt(questions)
            organization_id = answers.get("organization_id")
            if not organization_id:
                self.print_error("No organization ID entered.")
                exit(1)

            questions = [
                {
                    "type": "confirm",
                    "name": "use_existing_service_account",
                    "message": "Use existing service account?",
                    "default": False,
                },
                {
                    "type": "input",
                    "name": "key_file_output_path",
                    "message": "Enter the path to where the key file should be saved:",
                    "default": f"{project_id}-key.json",
                },
            ]
            answers = self.prompt(questions)
            key_file_path = answers.get("key_file_output_path")
            if not key_file_path:
                self.print_error("No key file path entered.")
                exit(1)

            if answers.get("use_existing_service_account", False):
                service_accounts = self.get_service_accounts_from_cli(project_id)
                if service_accounts:
                    service_account = self.prompt_select_service_account(
                        service_accounts
                    )
                    existing_account_email = service_account.get("email")
                    # Only the email is returned in this payload
                    existing_account_name = existing_account_email.split("@")[0]
                else:
                    # Enable existing service account
                    answers = self.prompt(
                        [
                            {
                                "type": "input",
                                "name": "existing_account_name",
                                "message": "Enter the service account name:",
                            }
                        ]
                    )
                    existing_account_name = answers.get("existing_account_name")
                if not self.enable_service_account(
                    organization_id, project_id, existing_account_name, key_file_path
                ):
                    exit(1)
            else:
                # Create service account
                answers = self.prompt(
                    [
                        {
                            "type": "input",
                            "name": "new_account_name",
                            "message": "Enter the service account name:",
                            "default": "censys-cloud-connector",
                        }
                    ]
                )
                new_account_name = answers.get("new_account_name")
                if not self.create_service_account(
                    organization_id, project_id, new_account_name, 682745741246
                ):
                    exit(1)

            if not key_file_path:
                self.print_error(
                    "Failed to create service account key file. Please try again."
                )
                exit(1)

            provider_settings = self.provider_specific_settings_class(
                organization_id=organization_id, service_account_json_file=key_file_path
            )
            self.add_provider_specific_settings(provider_settings)
