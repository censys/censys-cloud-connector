"""Gcp specific setup CLI."""
# import prompt_toolkit
# from InquirerPy import prompt

from censys.cloud_connectors.common.cli.provider_setup import ProviderSetupCli
from censys.cloud_connectors.common.enums import ProviderEnum

from .settings import GcpSpecificSettings

ENABLE_API_URLS = {
    "iam": "https://console.cloud.google.com/flows/enableapi?apiid=iam.googleapis.com",
    "securitycenter": "https://console.cloud.google.com/flows/enableapi?apiid=securitycenter.googleapis.com",
}
SCOPES = ["https://www.googleapis.com/auth/cloud-provider"]


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
