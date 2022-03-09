"""Gcp specific setup CLI."""
import json
from typing import Optional

from pydantic import validate_arguments

from censys.cloud_connectors.common.cli.provider_setup import ProviderSetupCli
from censys.cloud_connectors.common.enums import ProviderEnum

from .enums import GcpRoles
from .settings import GcpSpecificSettings


class GcpSetupCli(ProviderSetupCli):
    """Gcp provider setup cli command."""

    provider = ProviderEnum.GCP
    provider_specific_settings_class = GcpSpecificSettings
    logged_in_cli = False

    # TODO: Ensure that the service account has the required APIs enabled.
    # role: roles/iam.securityReviewer
    # role: roles/resourcemanager.folderViewer
    # role: roles/resourcemanager.organizationViewer
    # role: roles/securitycenter.assetsDiscoveryRunner
    # role: roles/securitycenter.assetsViewer

    # TODO: Setup steps:
    # - Create a service account with the above roles
    # - Download the JSON key file for the service account

    def get_ids_from_cli(self) -> Optional[tuple[str, str]]:
        """Get the organization ID and project ID from the CLI.

        Returns:
            Optional[tuple[str, str]]: The organization ID and project ID.
        """
        project_res = self.run_command("gcloud config get-value project")
        if project_res.returncode != 0:
            self.print_warning("Unable to get the current project ID from the CLI")
            return None
        project_id = project_res.stdout.decode("utf-8").strip()
        project_ancestors_res = self.run_command(
            f"gcloud projects get-ancestors {project_id} --format=json"
        )
        if project_ancestors_res.returncode != 0:
            self.print_warning(
                "Unable to get the current project ancestors from the CLI"
            )
            return None
        project_ancestors = json.loads(project_ancestors_res.stdout)
        for ancestor in project_ancestors:
            if ancestor.get("type") == "organization":
                organization_id = ancestor.get("id")
                return organization_id, project_id
        return None

    def create_service_account(
        self, service_account_name: str, project_id: str, organization_id: str
    ) -> Optional[dict]:
        """Create a service account.

        Args:
            service_account_name: The service account name.
            project_id: The project ID.
            organization_id: The organization ID.

        Returns:
            Optional[dict]: The service account.
        """
        # TODO: Ensure that the APIs are enabled.
        commands = [self.generate_create_service_account_command(service_account_name)]
        commands.extend(
            self.generate_role_binding_command(
                service_account_name, list(GcpRoles), organization_id, project_id
            )
        )
        self.print_bash("\n".join(commands))
        answers = self.prompt(
            {
                "type": "confirm",
                "name": "create_service_account",
                "message": "Create service account with the above commands?",
                "default": True,
            }
        )

        if not self.logged_in_cli or not answers.get("create_service_account", False):
            self.print_info(
                "Please login and try again. Or run the above commands in the Google Cloud Console."
            )
            return None
        # TODO: Return service account.
        return {}

    @validate_arguments
    def generate_set_project_command(self, project_id: str) -> str:
        """Generate set project command.

        Args:
            project_id (str): Project ID.

        Returns:
            str: Set project command.
        """
        return f"gcloud config set project {project_id}"

    @validate_arguments
    def generate_create_service_account_command(
        self, name: str = "censys-cloud-connector"
    ) -> str:
        """Generate create service account command.

        Args:
            name (str): Service account name.

        Returns:
            str: Create service account command.
        """
        return (
            f"gcloud iam service-accounts create {name} --display-name 'Censys Cloud"
            " Connector Service Account'"
        )

    @validate_arguments
    def generate_role_binding_command(
        self,
        service_account_name: str,
        roles: list[GcpRoles],
        organization_id: str,
        project_id: str,
    ) -> list[str]:
        """Generate role binding commands.

        Args:
            service_account_name (str): Service account name.
            roles (list[GcpRoles]): Roles.
            organization_id (str): Organization ID.
            project_id (str): Project ID for the serivce account.

        Returns:
            list[str]: Role binding command.
        """
        commands = [
            "# Grant the service account the required roles from the organization level"
        ]
        for role in roles:
            commands.append(
                f"gcloud organizations add-iam-policy-binding {organization_id} --member"
                f" 'serviceAccount:{service_account_name}@{project_id}.iam.gserviceaccount.com'"
                f" --role '{role}' --no-user-output-enabled --quiet"
            )
        return commands

    def setup(self):
        """Setup the GCP provider."""
        cli_choice = "Generate with CLI"
        input_choice = "Input existing credentials"
        questions = [
            {
                "type": "list",
                "name": "get_credentials_from",
                "message": "Select a method to configure your credentials",
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
            questions = [
                {
                    "type": "confirm",
                    "name": "get_from_cli",
                    "message": "Do you want to get the project and organization IDs from the CLI?",
                    "default": True,
                },
                {
                    "type": "input",
                    "name": "project_id",
                    "message": "Enter the project ID",
                    "when": lambda answers: not answers["get_from_cli"],
                },
                {
                    "type": "input",
                    "name": "organization_id",
                    "message": "Enter the organization ID",
                    "when": lambda answers: not answers["get_from_cli"],
                },
            ]
            answers = self.prompt(questions)

            project_id = answers.get("project_id")
            organization_id = answers.get("organization_id")
            if answers.get("get_from_cli"):
                current_ids = self.get_ids_from_cli()
                if not current_ids:
                    self.print_info(
                        "Unable to get the project and organization IDs from the CLI. Please try again."
                    )
                    return
                organization_id, project_id = current_ids
                self.logged_in_cli = True

            self.print_info(f"Using organization ID: {organization_id}.")
            self.print_info(f"Using project ID: '{project_id}'.")

            answers = self.prompt(
                [
                    {
                        "type": "input",
                        "name": "service_account_name",
                        "message": "Enter the service account name",
                        "default": "censys-cloud-connector",
                    }
                ]
            )
            service_account_name = answers.get("service_account_name")

            service_account = self.create_service_account(
                service_account_name, project_id, organization_id
            )
            if service_account is None:
                self.print_error(
                    "Service account not created. Please try again or manually create the service account."
                )
                exit(1)

            GcpSpecificSettings.from_dict(service_account)
