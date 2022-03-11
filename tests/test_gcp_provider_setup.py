from typing import Any
from enum import Enums
import json

import pytest
from parameterized import parameterized
from prompt_toolkit.validation import Document, ValidationError
from pydantic import (
    BaseConfig,
    Field,
    FilePath,
    NegativeFloat,
    NonNegativeFloat,
    NonPositiveInt,
    PositiveInt,
    confloat,
    conint,
    conlist,
    constr,
)
from pydantic.fields import ModelField

from censys.cloud_connectors.common.cli.provider_setup import (
    ProviderSetupCli,
    generate_validation,
    prompt_for_list,
    snake_case_to_english,
)
from censys.cloud_connectors.common.settings import ProviderSpecificSettings, Settings
from censys.cloud_connectors.gcp.enums import GcpRoles, GcpApiId, GcpSecurityCenterResourceTypes
from tests.base_case import BaseTestCase


from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import Seed
from censys.cloud_connectors.common.settings import Settings
from censys.cloud_connectors.gcp.connector import GcpCloudConnector
from censys.cloud_connectors.gcp.enums import GcpSecurityCenterResourceTypes
from censys.cloud_connectors.gcp.settings import GcpSpecificSettings
from tests.base_case import BaseTestCase

failed_import = False
try:
    from google.cloud.securitycenter_v1.types import ListAssetsResponse
except ImportError:
    failed_import = True

## TODO: FIX THIS^

@pytest.mark.skipif(failed_import, reason="Failed to import gcp dependencies")
class TestGcpConnector(BaseTestCase):
    # Test data
        mock_connectors = [
            "test_connector_1",
            "test_connector_2",
        ]

    def setUp(self) -> None:
        super().setUp()
        with open(self.shared_datadir / "test_gcp_responses.json") as f:
            self.data = json.load(f)
        self.settings = Settings(censys_api_key=self.consts["censys_api_key"])
        test_creds = self.data["TEST_CREDS"]
        # Ensure the service account json file exists
        test_creds["service_account_json_file"] = str(
            self.shared_datadir / test_creds["service_account_json_file"]
        )
        self.settings.providers["gcp"] = [GcpSpecificSettings.from_dict(test_creds)]
        self.connector = GcpCloudConnector(self.settings)
        self.connector.organization_id = self.data["TEST_CREDS"]["organization_id"]
        self.connector.credentials = self.mocker.MagicMock()
        self.connector.provider_settings = GcpSpecificSettings.from_dict(
            self.data["TEST_CREDS"]
        )

    def tearDown(self) -> None:
        # Reset the deaultdicts as they are immutable
        for seed_key in list(self.connector.seeds.keys()):
            del self.connector.seeds[seed_key]
        for cloud_asset_key in list(self.connector.cloud_assets.keys()):
            del self.connector.cloud_assets[cloud_asset_key]
    @parameterized.expand(
        [
            "role"
        ]
    )
    def test_generate_role_binding_command(
        self,
        service_account_name: str,
        roles: list[GcpRoles],
        organization_id: str,
        project_id: str,
    ):
        # Actual call
        sp_command = self.setup_cli.generate_create_command(subscriptions)

        # Assertions
        assert sp_command.startswith("az ad sp create-for-rbac")
        assert "--scopes " + partial_command in sp_command
