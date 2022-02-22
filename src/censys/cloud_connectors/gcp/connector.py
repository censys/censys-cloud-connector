"""Gcp Cloud Connector."""
from typing import List

from googleapiclient.discovery import build as build_resource
from oauth2client.service_account import ServiceAccountCredentials

from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.settings import GcpSpecificSettings, Settings

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class GcpCloudConnector(CloudConnector):
    """Gcp Cloud Connector."""

    platform = "gcp"
    organization_id: str
    credentials: ServiceAccountCredentials
    platform_settings: GcpSpecificSettings

    def __init__(self, settings: Settings):
        """Initialize Gcp Cloud Connector.

        Args:
            settings (Settings): Settings.
        """
        super().__init__(self.platform, settings)

    def scan_all(self):
        """Scan all Gcp Organizations."""
        platform_settings: List[GcpSpecificSettings] = self.settings.platforms.get(
            self.platform, []
        )
        for platform_setting in platform_settings:
            self.platform_settings = platform_setting
            self.organization_id = platform_setting.organization_id
            self.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                platform_setting.service_account_json_file, scopes=SCOPES
            )
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

    # TODO: Port over existings methods
