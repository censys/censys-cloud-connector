"""Gcp platform-specific setup CLI."""
# from PyInquirer import prompt

# from censys.cloud_connectors.common.cli.platform_setup import PlatformSetupCli

# from .settings import GcpSpecificSettings

ENABLE_API_URLS = {
    "iam": "https://console.cloud.google.com/flows/enableapi?apiid=iam.googleapis.com",
    "securitycenter": "https://console.cloud.google.com/flows/enableapi?apiid=securitycenter.googleapis.com",
}
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
