"""Azure platform-specific setup CLI."""
import json
import subprocess
from typing import Dict, List

from PyInquirer import prompt

from censys.cloud_connectors.azure.settings import AzureSpecificSettings
from censys.cloud_connectors.common.cli.platform_setup import PlatformSetupCli
from censys.cloud_connectors.common.settings import Settings


class AzureSetupCli(PlatformSetupCli):
    """Azure platform setup cli command."""

    platform = "azure"
    platform_specific_settings_class = AzureSpecificSettings

    def get_subscriptions_from_cli(self) -> List[Dict[str, str]]:
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
                print("Unable to get subscriptions from the CLI")
        except ImportError:
            print("Please install the Azure SDK for Python")
        return []

    def prompt_select_subscriptions(
        self, subscriptions: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Prompt the user to select subscriptions.

        Args:
            subscriptions (List[Dict[str, str]]): List of subscriptions.

        Returns:
            List[Dict[str, str]]: List of selected subscriptions.

        Raises:
            KeyboardInterrupt: If the user cancels the prompt.
        """
        questions = [
            {
                "type": "checkbox",
                "name": "subscription_ids",
                "message": "Select subscription(s)",
                "choices": [
                    {
                        "name": s.get("display_name"),
                        "value": s.get("subscription_id"),
                        "disabled": "Subscription Disabled"
                        if s.get("state") != "Enabled"
                        else False,
                    }
                    for s in subscriptions
                ],
            }
        ]
        answers = prompt(questions)
        if answers == {}:
            raise KeyboardInterrupt
        selected_subscription_ids = answers.get("subscription_ids", [])
        return [
            s
            for s in subscriptions
            if s.get("subscription_id") in selected_subscription_ids
        ]

    def generate_create_command(self, subscriptions: List[Dict[str, str]]) -> str:
        """Generate the command to create a service principal.

        Args:
            subscriptions (List[Dict[str, str]]): List of subscriptions.

        Returns:
            str: Command to create a service principal.
        """
        command = [
            "az",
            "ad",
            "sp",
            "create-for-rbac",
            "--name",
            '"Censys Cloud Connector"',
            "--role",
            "Reader",
            "--scopes",
        ]
        for subscription in subscriptions:
            subscription_id = subscription.get("id")
            command.append(subscription_id)
        return " ".join(command)

    def create_service_principal(self, subscriptions: List[Dict[str, str]]) -> dict:
        """Create a service principal.

        Args:
            subscriptions (List[Dict[str, str]]): List of subscriptions.

        Returns:
            dict: Service principal.

        Raises:
            KeyboardInterrupt: If the user cancels the prompt.
        """
        command = self.generate_create_command(subscriptions)
        print("$ " + command)
        answers = prompt(
            [
                {
                    "type": "confirm",
                    "name": "create_service_principal",
                    "message": "Create service principal with above command?",
                    "default": True,
                }
            ]
        )
        if answers == {}:
            raise KeyboardInterrupt
        if not answers.get("create_service_principal", False):
            print("Please manually create a service principal with the role 'Reader'")
            return

        res = subprocess.run(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if res.returncode != 0:
            print(f"Error creating service principal: {res.stderr}")
            exit(1)
        print("Service principal successfully created!")
        creds = json.loads(res.stdout)
        return creds

    def setup(self) -> None:
        """Setup the Azure platform.

        Returns:
            None
        """
        subscriptions = self.get_subscriptions_from_cli()
        if len(subscriptions) == 0:
            return super().setup()

        selected_subscriptions = self.prompt_select_subscriptions(subscriptions)
        if len(selected_subscriptions) == 0:
            return super().setup()

        service_principal = self.create_service_principal(selected_subscriptions)
        if service_principal is None:
            return super().setup()

        platform_settings = self.platform_specific_settings_class(
            subscription_id=[s.get("subscription_id") for s in selected_subscriptions],
            tenant_id=service_principal.get("tenant"),
            client_id=service_principal.get("appId"),
            client_secret=service_principal.get("password"),
        )

        self.settings.platforms[self.platform].append(platform_settings)


def main(settings: Settings):
    """Main function.

    Args:
        settings (Settings): Settings object.
    """
    setup_cli = AzureSetupCli(settings)
    setup_cli.setup()


if __name__ == "__main__":
    main()
