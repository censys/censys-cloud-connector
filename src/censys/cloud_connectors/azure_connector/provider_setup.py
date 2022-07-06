"""Azure specific setup CLI."""
from typing import Optional

from azure.core.exceptions import ClientAuthenticationError, HttpResponseError
from azure.identity import ClientSecretCredential
from azure.mgmt.network import NetworkManagementClient
from pydantic import validate_arguments

from censys.cloud_connectors.azure_connector.enums import AzureMessages
from censys.cloud_connectors.common.cli.provider_setup import (
    ProviderSetupCli,
    backoff_wrapper,
)
from censys.cloud_connectors.common.enums import ProviderEnum

from .settings import AzureSpecificSettings


class AzureSetupCli(ProviderSetupCli):
    """Azure provider setup cli command."""

    provider = ProviderEnum.AZURE
    provider_specific_settings_class = AzureSpecificSettings

    def get_subscriptions_from_cli(self) -> list[dict[str, str]]:
        """Get subscriptions from the CLI.

        Returns:
            List[Dict[str, str]]: List of subscriptions.
        """
        try:
            from azure.identity import AzureCliCredential
            from azure.identity._exceptions import CredentialUnavailableError
            from azure.mgmt.resource import SubscriptionClient

            credential = AzureCliCredential()
            subscription_client = SubscriptionClient(credential)
            try:
                subscriptions = [
                    s.as_dict() for s in subscription_client.subscriptions.list()
                ]
                return subscriptions
            except CredentialUnavailableError:
                self.print_warning("Unable to get subscriptions from the CLI")
        except ImportError:
            self.print_warning("Please install the Azure SDK for Python")
        return []

    def prompt_select_subscriptions(
        self, subscriptions: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        """Prompt the user to select subscriptions.

        Args:
            subscriptions (List[Dict[str, str]]): List of subscriptions.

        Returns:
            List[Dict[str, str]]: List of selected subscriptions.
        """
        if len(subscriptions) == 1:
            questions = [
                {
                    "type": "confirm",
                    "name": "use_subscription",
                    "message": f"Confirm subscription {subscriptions[0]['display_name']}:",
                    "default": True,
                }
            ]
            answers = self.prompt(questions)
            if not answers.get("use_subscription"):
                return []
            return subscriptions
        questions = [
            {
                "type": "list",
                "name": "subscription_ids",
                "message": "Select subscription(s):",
                "choices": [
                    {
                        "name": s.get("display_name"),
                        "value": s,
                    }
                    for s in subscriptions
                    if s.get("state") == "Enabled"
                ],
                "multiselect": True,
            }
        ]
        answers = self.prompt(questions)
        return answers.get("subscription_ids", [])

    def generate_create_command(
        self,
        subscriptions: list[dict[str, str]],
        service_principal_name: str = "Censys Cloud Connector",
        only_show_errors: bool = True,
    ) -> list[str]:
        """Generate the command to create a service principal.

        Args:
            subscriptions (List[Dict[str, str]]): List of subscriptions.
            service_principal_name (str): Optional; Service principal name. Defaults to "Censys Cloud Connector".
            only_show_errors (bool): Optional; Only show errors. Defaults to True.

        Returns:
            list[str]: Command to create a service principal.
        """
        command = [
            "az",
            "ad",
            "sp",
            "create-for-rbac",
            "--name",
            service_principal_name,
            "--role",
            "Reader",
            "--output",
            "jsonc",
            "--scopes",
        ]
        for subscription in subscriptions:
            if subscription_id := subscription.get("id"):
                command.append(subscription_id)
        if only_show_errors:
            command.append("--only-show-errors")
        return command

    @validate_arguments
    def create_service_principal(self, subscriptions: list[dict]) -> Optional[dict]:
        """Create a service principal.

        Args:
            subscriptions (List[Dict]): List of subscriptions.

        Returns:
            Optional[dict]: Service principal.
        """
        try:
            from azure.cli.core import get_default_cli

            azure_cli = get_default_cli()
        except ImportError:  # pragma: no cover
            self.print_warning("Please install the Azure CLI")
            return None

        command = self.generate_create_command(subscriptions)
        self.print_command(command)
        answers = self.prompt(
            [
                {
                    "type": "confirm",
                    "name": "create_service_principal",
                    "message": "Confirm creation of service principal with above command:",
                    "default": True,
                }
            ]
        )
        if not answers.get("create_service_principal", False):  # pragma: no cover
            self.print_warning(
                "Please manually create a service principal with the role 'Reader'"
            )
            return None

        if command[0] == "az":
            command = command[1:]
        azure_cli.invoke(command)
        result = azure_cli.result
        if not result:
            return None
        if results := result.result:
            return results
        if error := result.error:  # pragma: no cover
            self.print_error(error)
        return None

    @backoff_wrapper(
        (HttpResponseError, ClientAuthenticationError, ValueError),
        task_description="[blue]Verifying service principal...",
    )
    def verify_service_principal(self, provider_setting: AzureSpecificSettings) -> bool:
        """Verify the service principal.

        Args:
            provider_setting (AzureSpecificSettings): Azure specific settings.

        Returns:
            bool: True if valid, exits with error otherwise.
        """
        credential = ClientSecretCredential(
            tenant_id=provider_setting.tenant_id,
            client_id=provider_setting.client_id,
            client_secret=provider_setting.client_secret,
        )
        for subscription_id in provider_setting.subscription_id:
            network_client = NetworkManagementClient(credential, subscription_id)
            res = network_client.public_ip_addresses.list_all()
            next(res)
        return True

    def setup_with_cli(self) -> None:
        """Setup with the Azure CLI."""
        subscriptions = self.get_subscriptions_from_cli()
        if len(subscriptions) == 0:
            self.print_error(AzureMessages.ERROR_NO_SUBSCRIPTIONS_FOUND)
            exit(1)

        selected_subscriptions = self.prompt_select_subscriptions(subscriptions)
        if len(selected_subscriptions) == 0:
            self.print_error(AzureMessages.ERROR_NO_SUBSCRIPTIONS_SELECTED)
            exit(1)

        service_principal = self.create_service_principal(selected_subscriptions)
        if service_principal is None:
            self.print_error(
                "Service principal not created. Please try again or manually create a service principal"
            )
            exit(1)

        # Save the service principal
        provider_settings = self.provider_specific_settings_class(
            subscription_id=[
                subscription_id
                for s in selected_subscriptions
                if s and (subscription_id := s.get("subscription_id"))
            ],
            tenant_id=service_principal.get("tenant"),
            client_id=service_principal.get("appId"),
            client_secret=service_principal.get("password"),
        )
        self.add_provider_specific_settings(provider_settings)

        # Verify the service principal
        if not self.verify_service_principal(provider_settings):
            self.print_error(AzureMessages.ERROR_FAILED_TO_VERIFY_SERVICE_PRINCIPAL)
            exit(1)

        self.print_success("Service principal was successfully created.")

    def setup(self):
        """Setup the Azure provider."""
        choices = {
            "Generate with Azure CLI (Recommended)": self.setup_with_cli,
            "Input existing credentials": super().setup
            # TODO: Add support for InteractiveBrowserCredential
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
