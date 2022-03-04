"""Gcp Cloud Connector."""
from googleapiclient.discovery import build as build_resource
from oauth2client.service_account import ServiceAccountCredentials

from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.enums import ProviderEnum

from .settings import GcpSpecificSettings

SCOPES = ["https://www.googleapis.com/auth/cloud-provider"]


class GcpCloudConnector(CloudConnector):
    """Gcp Cloud Connector."""

    provider = ProviderEnum.GCP
    organization_id: str
    credentials: ServiceAccountCredentials
    provider_settings: GcpSpecificSettings

    def scan_all(self):
        """Scan all Gcp Organizations."""
        provider_settings: list[GcpSpecificSettings] = self.settings.providers.get(
            self.provider, []
        )
        for provider_setting in provider_settings:
            self.provider_settings = provider_setting
            self.organization_id = provider_setting.organization_id
            try:
                self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
                    provider_setting.service_account_json_file, SCOPES
                )
            except ValueError as e:
                self.logger.error(
                    f"Failed to load service account credentials from {provider_setting.service_account_json_file}: {e}"
                )
                continue
            self.security_center_client = build_resource(
                "securitycenter",
                "v1",
                credentials=self.credentials,
                cache_discovery=False,
            )
            self.scan()

    def _format_label(self, asset: dict) -> str:
        """Format Gcp asset label.

        Args:
            asset (dict): Gcp asset.

        Returns:
            str: Formatted asset label.

        Raises:
            ValueError: If asset does not have a display name.
        """
        asset_display_name = asset.get("securityCenterProperties", {}).get(
            "resourceProjectDisplayName"
        )
        if not asset_display_name:
            raise ValueError(f"Asset {asset} has no display name.")
        return f"{self.label_prefix}{self.organization_id}/{asset_display_name}"

    def get_seeds(self):
        """Get Gcp seeds."""
        super().get_seeds()

    def get_cloud_assets(self):
        """Get Gcp cloud assets."""
        super().get_cloud_assets()

    # TODO: Port over existings methods
