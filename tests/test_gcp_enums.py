from typing import Optional
from unittest import TestCase

from parameterized import parameterized

from censys.cloud_connectors.gcp_connector.enums import (
    GcloudCommands,
    GcpApiIds,
    GcpCloudAssetInventoryTypes,
    GcpRoles,
)

TEST_PROJECT_ID = "my-project"
TEST_ORGANIZATION_ID = "my-organization"
TEST_SERVICE_ACCOUNT = "my-service-account"
TEST_SERVICE_ACCOUNT_EMAIL = (
    f"{TEST_SERVICE_ACCOUNT}@{TEST_PROJECT_ID}.iam.gserviceaccount.com"
)


class TestEnums(TestCase):
    @parameterized.expand(
        [
            (GcloudCommands.VERSION, "gcloud version"),
            (GcloudCommands.LOGIN, "gcloud auth login"),
            (GcloudCommands.LIST_ACCOUNTS, "gcloud auth list"),
            (
                GcloudCommands.LIST_ACCOUNTS,
                "gcloud auth list --format json",
                {"format": "json"},
            ),
            (
                GcloudCommands.GET_CONFIG_VALUE,
                "gcloud config get-value project",
                {"key": "project"},
            ),
            (
                GcloudCommands.SET_CONFIG_VALUE,
                "gcloud config set project my-project",
                {"key": "project", "value": TEST_PROJECT_ID},
            ),
            (
                GcloudCommands.ENABLE_SERVICES,
                "gcloud services enable securitycenter.googleapis.com",
                {"service": "securitycenter.googleapis.com"},
            ),
            (
                GcloudCommands.LIST_PROJECTS,
                "gcloud projects list",
            ),
            (
                GcloudCommands.LIST_PROJECTS,
                "gcloud projects list --format json",
                {"format": "json"},
            ),
            (
                GcloudCommands.GET_PROJECT_ANCESTORS,
                "gcloud projects get-ancestors my-project",
                {"project_id": TEST_PROJECT_ID},
            ),
            (
                GcloudCommands.GET_PROJECT_ANCESTORS,
                "gcloud projects get-ancestors my-project --format json",
                {"project_id": TEST_PROJECT_ID, "format": "json"},
            ),
            (
                GcloudCommands.LIST_SERVICE_ACCOUNTS,
                "gcloud iam service-accounts list",
            ),
            (
                GcloudCommands.LIST_SERVICE_ACCOUNTS,
                "gcloud iam service-accounts list --format json",
                {"format": "json"},
            ),
            (
                GcloudCommands.ADD_ORG_IAM_POLICY,
                "gcloud organizations add-iam-policy-binding my-org --member 'user:my-user' --role 'roles/viewer'",
                {
                    "organization_id": "my-org",
                    "member": "user:my-user",
                    "role": "roles/viewer",
                },
            ),
            (
                GcloudCommands.ADD_ORG_IAM_POLICY,
                "gcloud organizations add-iam-policy-binding my-org --member 'user:my-user' --role 'roles/viewer' --quiet",
                {
                    "organization_id": "my-org",
                    "member": "user:my-user",
                    "role": "roles/viewer",
                    "quiet": True,
                },
            ),
            (
                GcloudCommands.CREATE_SERVICE_ACCOUNT,
                "gcloud iam service-accounts create my-service-account --display-name 'My Service Account' --description 'My Service Account Description'",
                {
                    "name": TEST_SERVICE_ACCOUNT,
                    "display_name": "My Service Account",
                    "description": "My Service Account Description",
                },
            ),
            (
                GcloudCommands.CREATE_SERVICE_ACCOUNT,
                "gcloud iam service-accounts create my-service-account --display-name 'My Service Account' --description 'My Service Account Description' --project my-project",
                {
                    "name": TEST_SERVICE_ACCOUNT,
                    "display_name": "My Service Account",
                    "description": "My Service Account Description",
                    "project": TEST_PROJECT_ID,
                },
            ),
            (
                GcloudCommands.ENABLE_SERVICE_ACCOUNT,
                "gcloud iam service-accounts enable my-service-account@my-project.iam.gserviceaccount.com",
                {"service_account_email": TEST_SERVICE_ACCOUNT_EMAIL},
            ),
            (
                GcloudCommands.CREATE_SERVICE_ACCOUNT_KEY,
                "gcloud iam service-accounts keys create my-service-account.json --iam-account my-service-account@my-project.iam.gserviceaccount.com",
                {
                    "key_file": "my-service-account.json",
                    "service_account_email": TEST_SERVICE_ACCOUNT_EMAIL,
                },
            ),
        ]
    )
    def test_gcloud_commands(
        self,
        enum_command: GcloudCommands,
        expected_command: str,
        format_args: Optional[dict] = None,
    ):
        # Test data
        if not format_args:
            format_args = {}

        # Actual call
        actual_command = enum_command.generate(**format_args)

        # Assertions
        assert expected_command == actual_command

    @parameterized.expand(
        [
            (
                GcpApiIds.IAM,
                "https://console.cloud.google.com/flows/enableapi?apiid=iam.googleapis.com",
            ),
            (
                GcpApiIds.CLOUDASSET,
                "https://console.cloud.google.com/flows/enableapi?apiid=cloudasset.googleapis.com",
            ),
        ]
    )
    def test_gcp_api_ids_urls(
        self,
        enum_api_id: GcpApiIds,
        expected_url: str,
    ):
        # Actual call
        actual_url = enum_api_id.enable_url()

        # Assertions
        assert expected_url == actual_url

    @parameterized.expand(
        [
            (
                GcpApiIds.IAM,
                "gcloud services enable iam.googleapis.com --project my-project",
            ),
            (
                GcpApiIds.CLOUDASSET,
                "gcloud services enable cloudasset.googleapis.com --project my-project",
            ),
        ]
    )
    def test_gcp_api_ids_commands(
        self,
        enum_api_id: GcpApiIds,
        expected_command: str,
    ):
        # Actual call
        actual_command = enum_api_id.enable_command(TEST_PROJECT_ID)

        # Assertions
        assert expected_command == actual_command

    @parameterized.expand(
        [
            (
                GcpRoles.SECURITY_REVIEWER,
                "roles/iam.securityReviewer",
            ),
            (
                GcpRoles.FOLDER_VIEWER,
                "roles/resourcemanager.folderViewer",
            ),
            (
                GcpRoles.ORGANIZATION_VIEWER,
                "roles/resourcemanager.organizationViewer",
            ),
            (
                GcpRoles.CAI_ASSETS_VIEWER,
                "roles/cloudasset.viewer",
            ),
        ]
    )
    def test_gcp_roles(
        self,
        enum_role: GcpRoles,
        expected_role: str,
    ):
        # Actual call
        actual_role = str(enum_role)

        # Assertions
        assert expected_role == actual_role

    @parameterized.expand(
        [
            (
                GcpCloudAssetInventoryTypes.COMPUTE_INSTANCE,
                "compute.googleapis.com/Instance",
            ),
            (
                GcpCloudAssetInventoryTypes.COMPUTE_ADDRESS,
                "compute.googleapis.com/Address",
            ),
            (
                GcpCloudAssetInventoryTypes.CONTAINER_CLUSTER,
                "container.googleapis.com/Cluster",
            ),
            (
                GcpCloudAssetInventoryTypes.CLOUD_SQL_INSTANCE,
                "sqladmin.googleapis.com/Instance",
            ),
            (
                GcpCloudAssetInventoryTypes.DNS_ZONE,
                "dns.googleapis.com/ManagedZone",
            ),
            (
                GcpCloudAssetInventoryTypes.STORAGE_BUCKET,
                "storage.googleapis.com/Bucket",
            ),
        ]
    )
    def test_gcp_security_center_resource_types(
        self,
        enum_resource_type: GcpCloudAssetInventoryTypes,
        expected_filter: str,
    ):
        # Actual call
        actual_filter = enum_resource_type

        # Assertions
        assert expected_filter == actual_filter
