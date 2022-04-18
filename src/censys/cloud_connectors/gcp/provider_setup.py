"""Gcp specific setup CLI."""
import json
import os.path
import re
import uuid
from typing import Optional

from InquirerPy.separator import Separator
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
    extra_instructions = {
        "organization_id": "(This is a 12-digit number)",
    }

    def is_gcloud_installed(self) -> bool:
        """Check if user has gcloud installed locally.

        Returns:
            bool: True if installed, false if not.
        """
        gcloud_version = self.run_command("gcloud version")
        return gcloud_version.returncode == 0

    def get_accounts_from_cli(self) -> Optional[list[dict[str, str]]]:
        """Get the credentialed accounts from the CLI.

        Returns:
            list[dict[str, str]]: List of credentialed accounts.
        """
        res = self.run_command("gcloud auth list --format=json")
        if res.returncode != 0:
            return None
        return json.loads(res.stdout)

    def prompt_select_account(
        self, accounts: list[dict[str, str]]
    ) -> Optional[dict[str, str]]:
        """Prompt the user to select an account.

        Args:
            accounts (list[dict[str, str]]): List of credentialed accounts.

        Returns:
            dict: Selected account.
        """
        active_account: Optional[dict] = None
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

        kwargs = {}
        if active_account and (active_email := active_account.get("account")):
            kwargs["default"] = active_email
        return self.prompt_select_one("Select a GCP account:", choices, **kwargs)

    def get_project_ids_from_cli(self) -> Optional[list[dict]]:
        """Get list of active projects which the user has access to from the CLI.

        Returns:
            list[dict]: List of projects.
        """
        res = self.run_command("gcloud projects list --format=json")
        if res.returncode != 0:
            return None
        return json.loads(res.stdout.strip())

    def get_default_project_id_from_cli(self) -> Optional[str]:
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

    def prompt_select_project(
        self, projects: list[dict[str, str]], default_project_id: Optional[str]
    ) -> Optional[dict]:
        """Prompt the user to select a project.

        Args:
            projects (list[dict]): List of projects.
            default_project_id (Optional[str]): Current project.

        Returns:
            Optional[dict]: Selected project.
        """
        default_project: Optional[dict] = None
        kwargs = {}
        choices: list[dict] = []
        for project in projects:
            project_id = project.get("projectId")
            if not project_id:
                continue
            choice = {"name": project_id, "value": project}
            if project.get("projectId") == default_project_id:
                default_project = project
                choices.insert(0, choice)
            else:
                choices.append(choice)

        if default_project and (default_project_id := default_project.get("projectId")):
            kwargs["default"] = default_project_id

        return self.prompt_select_one("Select a project:", choices, **kwargs)

    @validate_arguments
    def get_organization_id_from_cli(self, project_id: str) -> Optional[int]:
        """Get the organization id from the CLI.

        Args:
            project_id (str): Project id.

        Returns:
            int: Organization id.
        """
        res = self.run_command(
            f"gcloud projects get-ancestors {project_id} --format=json"
        )
        if res.returncode != 0:
            self.print_error(res.stderr.strip())
            return None
        project_ancestors = json.loads(res.stdout.strip())
        for ancestor in project_ancestors:
            if ancestor.get("type") == "organization":
                if organization_id := ancestor.get("id"):
                    return int(organization_id)
                return None
        return None

    @validate_arguments
    def switch_active_cli_account(self, account_name: str) -> bool:
        """Switch the active account.

        Args:
            account_name (str): The account name.

        Returns:
            bool: Success.
        """
        res = self.run_command(f"gcloud config set account {account_name}")
        if res.returncode != 0:
            return False
        return True

    def get_service_accounts_from_cli(
        self, project_id: Optional[str] = None
    ) -> Optional[list[dict]]:
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
            return None
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
        return self.prompt_select_one(
            "Select a service account:", service_accounts, "email"
        )

    def get_current_key_file_path(
        self, org_id: int, service_account_email: str
    ) -> Optional[str]:
        """Get the current key file path.

        Args:
            org_id (int): Organization id.
            service_account_email (str): Service account email.

        Returns:
            str: Current key file path.
        """
        current_provider = (org_id, service_account_email)
        current_provider_config: dict[
            tuple, GcpSpecificSettings
        ] = self.settings.providers[
            self.provider
        ]  # type: ignore

        if current_key_file_path := current_provider_config.get(current_provider):
            return str(current_key_file_path.service_account_json_file)

        return None

    def generate_service_account_email(
        self, service_account_name: str, project_id: str
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
        organization_id: int,
        service_account_email: str,
        roles: list[GcpRoles],
    ) -> list[str]:
        """Generate role binding commands.

        Args:
            organization_id (int): Organization id.
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
        project_id: Optional[str] = None,
    ) -> str:
        """Generate create service account command.

        Args:
            name (str): Service account name.
            display_name (str): Service account display name.
            project_id (str): Project ID.

        Returns:
            str: Create service account command.
        """
        # TODO: Add service account description (--description flag)
        command = (
            f"gcloud iam service-accounts create {name} --display-name '{display_name}'"
        )
        if project_id:
            command += f" --project {project_id}"
        return command

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
        organization_id: int,
        project_id: str,
        service_account_name: str,
        key_file_path: str,
    ) -> Optional[str]:
        """Create a service account.

        Args:
            organization_id (int): Organization id.
            project_id (str): Project id.
            service_account_name (str): The service account name.
            key_file_path (str): The place to store the key file.

        Returns:
            Optional[str]: The service account key file.
        """
        commands = [
            self.generate_create_service_account_command(
                service_account_name, project_id=project_id
            )
        ]
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

        for command in track(commands, description="Running...", transient=True):
            res = self.run_command(command)
            if res.returncode != 0:
                self.print_error(
                    f"Failed to create service account. {res.stderr.strip()}"
                )
                return None

        # Check key_file_path exists
        if not os.path.exists(key_file_path):
            self.print_error(
                f"Failed to create service account. Error: {key_file_path} does not exist"
            )
            return None

        return key_file_path

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
        organization_id: int,
        project_id: str,
        service_account_name: str,
        key_file_path: str,
    ) -> Optional[str]:
        """Enable a service account.

        Args:
            organization_id (int): Organization id.
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

        if not answers.get("enable_service_account", False):
            self.print_info(
                "Please login and try again. Or run the above commands in the Google Cloud Console."
            )
            return None

        # TODO: Investigate progress bar
        for command in track(commands, description="Running...", transient=True):
            res = self.run_command(command)
            if res.returncode != 0:
                self.print_error(
                    f"Failed to enable service account. {res.stderr.strip()}"
                )
                return None

        # Check key_file_path exists
        if not os.path.exists(key_file_path):
            self.print_error(
                f"Failed to enable service account. Error: {key_file_path} does not exist"
                # TODO: is this the correct error?
            )
            return None

        return key_file_path

    def prompt_to_create_service_account(
        self, organization_id: int, project_id: str, key_file_path: str
    ) -> str:
        """Prompt to create a service account.

        Args:
            organization_id (int): Organization id.
            project_id (str): Project id.
            key_file_path: The place to store the key file.

        Returns:
            str: The service account email.
        """

        def validate_service_account_name(service_account_name: str) -> bool:
            """Validate service account name.

            Service account name must be between 6 and 30 characters (inclusive), must begin with a
            lowercase letter, and consist of lowercase alphanumeric characters that can be separated by hyphens.

            Args:
                service_account_name (str): Service account name.

            Returns:
                bool: True if valid, False otherwise.
            """
            return bool(re.match(r"^[a-z][a-z0-9-]{5,29}$", service_account_name))

        answers = self.prompt(
            [
                {
                    "type": "input",
                    "name": "new_account_name",
                    "message": "Confirm or name service account:",
                    "default": "censys-cloud-connector",
                    "validate": validate_service_account_name,
                    "invalid_message": "Service account name must be between 6 and 30 characters.",
                    "transformer": lambda name: self.generate_service_account_email(
                        name, project_id
                    ),
                }
            ]
        )
        new_account_name = answers.get("new_account_name")
        if not new_account_name:
            self.print_error("Service account name is required.")
            exit(1)
        if not self.create_service_account(
            organization_id, project_id, new_account_name, key_file_path
        ):
            self.print_error(
                "Failed to create service account key file. Please try again."
                # TODO: "service account key file" or "service account"?
            )
            exit(1)

        return self.generate_service_account_email(new_account_name, project_id)

    def setup_with_cli(self) -> None:
        """Setup with gcloud CLI."""
        self.print_info(
            "Before you begin you'll need to have identified the following:\n  [info]-[/info] The Google Cloud organization administrator account which will execute scripts that configure the Censys Cloud Connector.\n  [info]-[/info] The project that will be used to run the Censys Cloud Connector. Please note that the cloud connector will be scoped to the organization."
        )
        if not self.is_gcloud_installed():
            self.print_warning(
                r"Please install the [link=https://cloud.google.com/sdk/docs/downloads-interactive]gcloud SDK[\link] before continuing."
            )
            exit(1)

        accounts = self.get_accounts_from_cli()
        if accounts is None:
            self.print_error("Unable to get list of Credentialed GCP Accounts.")
            exit(1)
        if not accounts:
            self.print_error("No Credentialed GCP Accounts found.")
            exit(1)

        selected_account = self.prompt_select_account(accounts)
        if selected_account is None:
            # TODO: Print login instructions
            self.print_error("No GCP Account selected.")
            exit(1)

        account_email = selected_account["account"]
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
                self.print_error("No GCP Account selected.")
                exit(1)

            success = self.switch_active_cli_account(account_email)
            if not success:
                self.print_error("Unable to switch active GCP Account.")
                exit(1)

        projects = self.get_project_ids_from_cli()
        if projects is None:
            self.print_error("Unable to get projects from gcloud CLI.")
            # TODO: print gcloud CLI error message
            exit(1)
        if not projects:
            self.print_error(f"No projects found under GCP Account {account_email}.")
            # self.print("Please ensure your account has the correct permissions (resourcemanager.projects.list) to access projects under your organization \
            #             Or create a new project using gcloud projects create")
            # TODO: tell them how to create a project
            exit(1)
        default_project_id: Optional[str] = self.get_default_project_id_from_cli()
        selected_project = self.prompt_select_project(projects, default_project_id)
        if selected_project is None or "projectId" not in selected_project:
            self.print_error("No project selected.")
            exit(1)
        project_id: str = selected_project["projectId"]

        organization_id = self.get_organization_id_from_cli(project_id)
        if not organization_id:
            self.print_error("Unable to get Organization ID from gcloud CLI.")
            exit(1)
        questions = [
            {
                "type": "input",
                "name": "organization_id",
                "message": "Confirm your organization ID:",
                "default": str(organization_id),
            }
        ]
        answers = self.prompt(questions)
        if not answers.get("organization_id"):
            self.print_error("No Organization ID selected.")
            exit(1)

        service_accounts = self.get_service_accounts_from_cli(project_id)
        if service_accounts is None:
            self.print_error(
                f"Unable to get service accounts for project {project_id} from CLI."
            )
            # TODO: tell user to check permissions
            exit(1)

        if len(service_accounts) > 0:
            create_new_service_account = "Create new service account"
            service_account_choices = [acct.get("email") for acct in service_accounts]
            answers = self.prompt(
                {
                    "type": "list",
                    "name": "service_account_action",
                    "message": "Select service account:",
                    "choices": [
                        create_new_service_account,
                        Separator("--- Existing service accounts ---"),
                        *service_account_choices,
                    ],
                },
            )
            service_account_action: Optional[str] = answers.get(
                "service_account_action"
            )
        else:
            service_account_action = create_new_service_account

        service_account_email: Optional[str] = None

        if service_account_action is None:
            self.print_error("No service account selected.")
            exit(1)

        current_key_file_path: Optional[str] = None
        if service_account_action != create_new_service_account:
            service_account_email = service_account_action
            current_key_file_path = self.get_current_key_file_path(
                organization_id, service_account_email
            )
        if current_key_file_path:
            default_path = current_key_file_path
        else:
            random_str = uuid.uuid4().hex.upper()[0:4]
            default_path = f"./secrets/{project_id}-{random_str}-key.json"

        answers = self.prompt(
            {
                "type": "input",
                "name": "key_file_output_path",
                "message": "Confirm or edit key file path:",
                "default": default_path,
            }
        )
        key_file_path = answers.get("key_file_output_path")
        if not key_file_path:
            exit(1)

        if service_account_action == create_new_service_account:
            service_account_email = self.prompt_to_create_service_account(
                organization_id, project_id, key_file_path
            )
        else:
            existing_account_name = service_account_action.split("@")[0]
            service_account_email = service_account_action

            if not self.enable_service_account(
                organization_id,
                project_id,
                existing_account_name,
                key_file_path,
            ):
                self.print_error("Failed to enable service account.")
                exit(1)

        # TODO: Wait until the service account can get a single `google.cloud.resourcemanager.Organization`
        # from the security center API.
        provider_settings = self.provider_specific_settings_class(
            organization_id=organization_id,
            service_account_json_file=key_file_path,
            service_account_email=service_account_email,
        )
        self.add_provider_specific_settings(provider_settings)

    def setup(self):
        """Setup the GCP provider."""
        choices = {
            "Generate with gcloud CLI (Recommended)": self.setup_with_cli,
            "Input existing credentials": super().setup,
        }
        answers = self.prompt(
            {
                "type": "list",
                "name": "get_credentials_from",
                "message": "Select a method to configure your credentials:",
                "choices": list(choices.keys()),
            }
        )

        get_credentials_from = answers.get("get_credentials_from")
        if func := choices.get(get_credentials_from):
            func()
