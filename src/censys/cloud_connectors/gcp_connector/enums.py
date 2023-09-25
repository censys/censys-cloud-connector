"""Enums for GCP."""
from enum import Enum
from typing import Any, Optional


class GcloudCommands(str, Enum):
    """Enum for Gcloud commands."""

    VERSION = "version"
    LOGIN = "auth login"
    LIST_ACCOUNTS = "auth list"
    GET_CONFIG_VALUE = "config get-value {key}"
    SET_CONFIG_VALUE = "config set {key} {value}"
    ENABLE_SERVICES = "services enable {service}"
    LIST_PROJECTS = "projects list"
    DESCRIBE_ORGANIZATION = "organizations describe {organization_id}"
    GET_PROJECT_ANCESTORS = "projects get-ancestors {project_id}"
    LIST_SERVICE_ACCOUNTS = "iam service-accounts list"
    ADD_ORG_IAM_POLICY = "organizations add-iam-policy-binding {organization_id} --member '{member}' --role '{role}' --condition=None"
    CREATE_SERVICE_ACCOUNT = "iam service-accounts create {name} --display-name '{display_name}' --description '{description}'"
    ENABLE_SERVICE_ACCOUNT = "iam service-accounts enable {service_account_email}"
    CREATE_SERVICE_ACCOUNT_KEY = "iam service-accounts keys create {key_file} --iam-account {service_account_email}"

    def __str__(self) -> str:
        """Return the string representation of the command.

        Returns:
            str: The string representation of the command.
        """
        return "gcloud " + self.value

    def generate(
        self,
        format: Optional[str] = None,
        project: Optional[str] = None,
        quiet: bool = False,
        **kwargs: Any,
    ) -> str:
        """Generate the command.

        Args:
            format (str): The format to use.
            project (str): The project to use.
            quiet (bool): Whether to use the quiet flag.
            **kwargs: The keyword arguments to use.

        Returns:
            str: The command.
        """
        cmd = str(self).format(**kwargs)
        if format:
            cmd += f" --format {format}"
        if project:
            cmd += f" --project {project}"
        if quiet:
            cmd += " --quiet"
        return cmd


class GcpApiIds(str, Enum):
    """GCP API IDs."""

    IAM = "iam"
    CLOUDASSET = "cloudasset"

    def __str__(self) -> str:
        """Get the string representation of the enum.

        Returns:
            str: The string representation.
        """
        return f"{self.value}.googleapis.com"

    def enable_url(self) -> str:
        """Get the enable url for the API.

        Returns:
            str: Enable url.
        """
        return f"https://console.cloud.google.com/flows/enableapi?apiid={self}"

    def enable_command(self, project_id: str) -> str:
        """Get the enable command for the API.

        Args:
            project_id (str): Project ID.

        Returns:
            str: Enable command.
        """
        return GcloudCommands.ENABLE_SERVICES.generate(
            service=str(self), project=project_id
        )


class GcpRoles(str, Enum):
    """GCP roles."""

    SECURITY_REVIEWER = "iam.securityReviewer"
    FOLDER_VIEWER = "resourcemanager.folderViewer"
    ORGANIZATION_VIEWER = "resourcemanager.organizationViewer"
    CAI_ASSETS_VIEWER = "cloudasset.viewer"

    def __str__(self) -> str:
        """Gets the string representation of the role.

        Returns:
            str: The string representation of the role.
        """
        return f"roles/{self.value}"


class GcpCloudAssetInventoryTypes(str, Enum):
    """GCP Cloud Asset Inventory asset types."""

    COMPUTE_INSTANCE = "compute.googleapis.com/Instance"
    COMPUTE_ADDRESS = "compute.googleapis.com/Address"
    CONTAINER_CLUSTER = "container.googleapis.com/Cluster"
    CLOUD_SQL_INSTANCE = "sqladmin.googleapis.com/Instance"
    DNS_ZONE = "dns.googleapis.com/ManagedZone"
    STORAGE_BUCKET = "storage.googleapis.com/Bucket"
    PROJECT = "cloudresourcemanager.googleapis.com/Project"

    def __str__(self) -> str:
        """Get the string representation of the resource type.

        Returns:
            str: The string representation of the resource type.
        """
        return self.value


class GcpMessages(str, Enum):
    """GCP messages."""

    INSTALL_GCLOUD_INSTRUCTIONS = "Please install the [link=https://cloud.google.com/sdk/docs/downloads-interactive]gcloud SDK[/link] before continuing."
    LOGIN_INSTRUCTIONS = (
        f"Please login to your GCP account with the command: `{GcloudCommands.LOGIN}`."
    )
    LOGIN_TRY_AGAIN = "Please login and try again. Or run the above commands in the Google Cloud Console."
    SAVING_KEY = "Saving key file into ./secrets/"

    ERROR_UNABLE_TO_GET_ACCOUNTS = "Unable to get list of authenticated GCP Accounts."
    ERROR_NO_ACCOUNTS_FOUND = "No authenticated GCP Accounts found."
    ERROR_NO_ACCOUNT_SELECTED = "No GCP Account selected."
    ERROR_UNABLE_TO_SWITCH_ACCOUNT = "Unable to switch active GCP Account."
    ERROR_UNABLE_TO_GET_PROJECTS = "Unable to get list of GCP Projects."
    ERROR_NO_PROJECTS_FOUND = "No accessible GCP Projects found."
    ERROR_NO_PROJECT_SELECTED = "No GCP Project selected."
    ERROR_UNABLE_TO_GET_ORG_FROM_PROJECT = (
        "Unable to get GCP Organization from Project ancestry."
    )
    ERROR_NO_ORGANIZATION_SELECTED = "No GCP Organization selected."
    ERROR_UNABLE_TO_GET_SERVICE_ACCOUNTS = "Unable to get list of GCP Service Accounts."
    ERROR_NO_KEY_FILE_PATH = "No key file path provided."
    ERROR_NO_SERVICE_ACCOUNT_SELECTED = "No GCP Service Account selected."
    ERROR_FAILED_TO_ENABLE_SERVICE_ACCOUNT = "Failed to enable GCP Service Account."
    ERROR_FAILED_TO_CREATE_SERVICE_ACCOUNT_KEY = (
        "Failed to create service account key file. Please try again."
    )
    ERROR_FAILED_TO_VERIFY_SERVICE_ACCOUNT = "Failed to verify GCP Service Account."

    def __str__(self) -> str:
        """Get the string representation of the message.

        Returns:
            str: The string representation of the message.
        """
        return self.value


class GcpApiVersions(Enum):
    """GCP API versions."""

    SUPPORTED_VERSIONS: dict[GcpCloudAssetInventoryTypes, set[str]] = {
        GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE: {"v1", "beta"},
        GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS: {"v1", "beta"},
        GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER: {"v1"},
        GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE: {"v1", "v1beta4"},
        GcpCloudAssetInventoryTypes.DNS_ZONE: {"v1", "v2"},
        GcpCloudAssetInventoryTypes.STORAGE_BUCKET: {"v1"},
        GcpCloudAssetInventoryTypes.PROJECT: {"v1", "v1beta1", "v3"},
    }

    UNSUPPORTED_VERSIONS: dict[GcpCloudAssetInventoryTypes, set[str]] = {
        GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE: set(),
        GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS: set(),
        GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER: set(),
        GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE: set(),
        GcpCloudAssetInventoryTypes.DNS_ZONE: set(),
        GcpCloudAssetInventoryTypes.STORAGE_BUCKET: set(),
        GcpCloudAssetInventoryTypes.PROJECT: set(),
    }

    def get_versions(self, asset_type: GcpCloudAssetInventoryTypes) -> set[str]:
        """Get the set of supported versions for the asset type.

        Args:
            asset_type (GcpCloudAssetInventoryTypes): The asset type.

        Returns:
            set: The set of supported versions for the asset type.
        """
        return self.value[asset_type]
