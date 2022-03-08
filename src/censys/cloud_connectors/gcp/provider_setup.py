"""Gcp specific setup CLI."""
from InquirerPy import prompt

from censys.cloud_connectors.common.cli.provider_setup import ProviderSetupCli
from censys.cloud_connectors.common.enums import ProviderEnum

from .enums import GcpRoles
from .settings import GcpSpecificSettings


class GcpSetupCli(ProviderSetupCli):
    """Gcp provider setup cli command."""

    provider = ProviderEnum.GCP
    provider_specific_settings_class = GcpSpecificSettings

    # TODO: Ensure that the service account has the required APIs enabled.
    # role: roles/iam.securityReviewer
    # role: roles/resourcemanager.folderViewer
    # role: roles/resourcemanager.organizationViewer
    # role: roles/securitycenter.assetsDiscoveryRunner
    # role: roles/securitycenter.assetsViewer

    # TODO: Before you begin:
    # - You'll need to have identified the Google Cloud organization administrator account which will execute scripts that configure the Censys Cloud Connector.
    # - You'll need to have identified the project that will be used to run the Censys Cloud Connector.

    # TODO: Setup steps:
    # - Create a service account with the above roles
    # - Download the JSON key file for the service account

    def generate_set_project_command(self, project_id: str) -> str:
        """Generate set project command.

        Args:
            project_id (str): Project ID.

        Returns:
            str: Set project command.
        """
        return f"gcloud config set project {project_id}"

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

    def generate_role_binding_command(
        self,
        service_account_name: str,
        roles: list[GcpRoles],
        project_id: str,
    ) -> list[str]:
        """Generate role binding commands.

        Args:
            service_account_name (str): Service account name.
            roles (list[GcpRoles]): Roles.
            project_id (str): Project ID.

        Returns:
            list[str]: Role binding command.
        """
        commands = []
        for role in roles:
            commands.append(
                f"gcloud projects add-iam-policy-binding {project_id} --member"
                f" serviceAccount:'{service_account_name}@{project_id}.iam.gserviceaccount.com'"
                f" --role {role} --no-user-output-enabled --quiet"
            )
        return commands

    def setup(self):
        """Setup the GCP provider.

        Raises:
            KeyboardInterrupt: If the user cancels the setup.
        """
        cli_choice = "Generate with CLI"
        input_choice = "Input existing credentials"
        # questions = [
        #     {
        #         "type": "list",
        #         "name": "get_credentials_from",
        #         "message": "Select a method to configure your credentials",
        #         "choices": [cli_choice, input_choice],
        #     }
        # ]
        # answers = prompt(questions)
        # if not answers:  # pragma: no cover
        #     raise KeyboardInterrupt

        # get_credentials_from = answers.get("get_credentials_from")
        get_credentials_from = cli_choice
        if get_credentials_from == input_choice:
            super().setup()
        elif get_credentials_from == cli_choice:
            print("Before you begin you'll need to have identified the following:")
            print(
                "- The Google Cloud organization administrator account which will"
                " execute scripts that configure the Censys Cloud Connector."
            )
            print(
                "- The project that will be used to run the Censys Cloud Connector."
                " Please note that the cloud connector will not be scoped to this"
                " project."
            )
            questions = [
                {
                    "type": "input",
                    "name": "project_id",
                    "message": "Enter the project ID",
                },
                {
                    "type": "input",
                    "name": "service_account_name",
                    "message": "Enter the service account name",
                    "default": "censys-cloud-connector",
                },
            ]
            answers = prompt(questions)
            if not answers:  # pragma: no cover
                raise KeyboardInterrupt
            # Ensure that the APIs are enabled.
            project_id = answers.get("project_id")
            service_account_name = answers.get("service_account_name")
            commands = []
            commands.append(self.generate_set_project_command(project_id))
            commands.append(
                self.generate_create_service_account_command(service_account_name)
            )
            commands.extend(self.generate_role_binding_command())
