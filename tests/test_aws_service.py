import json
from unittest import TestCase

import pytest

from censys.cloud_connectors.aws_connector.service import AwsSetupService
from censys.cloud_connectors.common.settings import Settings
from tests.base_case import BaseCase

failed_import = False
try:
    from botocore.credentials import ReadOnlyCredentials
except ImportError:
    failed_import = True


@pytest.mark.skipif(failed_import, reason="AWS SDK not installed")
class TestAwsSetupService(BaseCase, TestCase):
    def setUp(self) -> None:
        super().setUp()
        with open(self.shared_datadir / "test_aws_service_responses.json") as f:
            self.data = json.load(f)
        self.settings = Settings(**self.default_settings)

        self.mocked_logger = self.mocker.MagicMock()
        self.aws = AwsSetupService(self.mocked_logger, self.settings)

    def test_get_session_credentials(self):
        test_access_key = "test-access-key-value"
        test_secret_key = "test-secret-key-value"
        test_token = "test-token-value"
        expected = {
            "access_key": test_access_key,
            "secret_key": test_secret_key,
            "token": test_token,
        }

        creds = ReadOnlyCredentials(test_access_key, test_secret_key, test_token)
        self.mocker.patch.object(self.aws, "get_frozen_credentials", return_value=creds)

        assert self.aws.get_session_credentials() == expected

    def test_get_session_credentials_error(self):
        expected = {"access_key": "", "secret_key": "", "token": ""}
        self.mocker.patch.object(
            self.aws, "get_frozen_credentials", side_effect=Exception()
        )

        assert self.aws.get_session_credentials() == expected

    def test_get_stackset_accounts_prevents_duplicates(self):
        name = "test-stack-set-name"
        exclude_id = "011111111111"
        expected = [{"name": "222222222222 (Org: r-41cr)", "value": "222222222222"}]

        self.mocker.patch.object(
            self.aws,
            "get_stackset_accounts_paginated",
            return_value=self.data["TEST_STACKSET_ACCOUNT_WITH_REGIONS"],
        )
        actual = self.aws.get_stackset_accounts(name, exclude_id)
        assert actual == expected

    def test_get_stackset_accounts_exclude(self):
        name = "test-stack-set-name"
        exclude_id = "222222222222"
        expected = []

        self.mocker.patch.object(
            self.aws,
            "get_stackset_accounts_paginated",
            return_value=self.data["TEST_STACKSET_ACCOUNT_WITH_REGIONS"],
        )
        actual = self.aws.get_stackset_accounts(name, exclude_id)
        assert actual == expected

    def test_get_organization_list_accounts(self):
        self.mocker.patch.object(
            self.aws,
            "get_organization_list_accounts_paginated",
            return_value=self.data["TEST_ORGANIZATION_LIST_ACCOUNTS"],
        )
        exclude_id = "000000111111"
        expected = [
            {"name": "011111111111 - TestParentAccount", "value": "011111111111"},
            {"name": "222222222222 - TestChildAccount", "value": "222222222222"},
        ]
        actual = self.aws.get_organization_list_accounts(exclude_id)
        assert actual == expected

    def test_get_organization_list_accounts_excludes(self):
        self.mocker.patch.object(
            self.aws,
            "get_organization_list_accounts_paginated",
            return_value=self.data["TEST_ORGANIZATION_LIST_ACCOUNTS"],
        )
        exclude_id = "011111111111"
        expected = [
            {"name": "222222222222 - TestChildAccount", "value": "222222222222"}
        ]
        actual = self.aws.get_organization_list_accounts(exclude_id)
        assert actual == expected
