"""Enums for GCP."""
from enum import Enum
from typing import Optional


class GcpApiId(str, Enum):
    """GCP API IDs."""

    IAM = "iam"
    SECURITYCENTER = "securitycenter"

    def enable_url(self) -> str:
        """Get the enable url for the API.

        Returns:
            str: Enable url.
        """
        return f"https://console.cloud.google.com/flows/enableapi?apiid={self.value}.googleapis.com"

    def enable_command(self, project_id: Optional[str] = None) -> str:
        """Get the enable command for the API.

        Args:
            project_id (Optional[str], optional): Project ID. Defaults to None.

        Returns:
            str: Enable command.
        """
        command = f"gcloud services enable {self.value}.googleapis.com"
        if project_id:
            command += f" --project {project_id}"
        return command


class GcpRoles(str, Enum):
    """GCP roles."""

    SECURITY_REVIEWER = "iam.securityReviewer"
    FOLDER_VIEWER = "resourcemanager.folderViewer"
    ORGANIZATION_VIEWER = "resourcemanager.organizationViewer"
    ASSETS_DISCOVERY_RUNNER = "securitycenter.assetsDiscoveryRunner"
    ASSETS_VIEWER = "securitycenter.assetsViewer"

    def __str__(self) -> str:
        """Gets the string representation of the role.

        Returns:
            str: The string representation of the role.
        """
        return f"roles/{self.value}"


class GcpSecurityCenterResourceTypes(str, Enum):
    """GCP security center resource types."""

    COMPUTE_ADDRESS = "google.compute.Address"
    CONTAINER_CLUSTER = "google.container.Cluster"
    CLOUD_SQL_INSTANCE = "google.cloud.sql.Instance"
    DNS_ZONE = "google.cloud.dns.ManagedZone"
    STORAGE_BUCKET = "google.cloud.storage.Bucket"

    def filter(self) -> str:
        """Get the filter for the resource type.

        Returns:
            str: Filter.
        """
        return f'securityCenterProperties.resource_type : "{self.value}"'
