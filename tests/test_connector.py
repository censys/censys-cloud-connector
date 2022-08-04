from unittest import TestCase

import pytest

from censys.common.exceptions import CensysAsmException, CensysException

from censys.cloud_connectors.common.cloud_asset import CloudAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import Seed
from censys.cloud_connectors.common.settings import Settings
from tests.base_connector_case import BaseConnectorCase


class ExampleCloudConnector(CloudConnector):
    provider = ProviderEnum.GCP

    def get_seeds(self):
        return super().get_seeds()

    def get_cloud_assets(self) -> None:
        return super().get_cloud_assets()

    def scan_all(self):
        return super().scan_all()


class TestCloudConnector(BaseConnectorCase, TestCase):
    connector: ExampleCloudConnector

    def setUp(self) -> None:
        super().setUp()
        self.setUpConnector(ExampleCloudConnector)

    def test_init_fail(self):
        # Mock provider
        self.mocker.patch.object(ExampleCloudConnector, "provider", None)

        # Assertions
        with pytest.raises(ValueError, match="The provider must be set."):
            ExampleCloudConnector(self.settings)

    def test_no_api_key_fail(self):
        # Test data (Ensure that the validation is not triggered)
        test_settings = Settings(censys_api_key=self.consts["censys_api_key"])

        # Mock settings
        self.mocker.patch.object(test_settings, "censys_api_key", None)

        # Mock Censys Config to not grab the API from the config file
        self.mocker.patch(
            "censys.common.config.get_config_path", return_value="not_a_file"
        )

        # Assertions
        with pytest.raises(CensysException, match="No ASM API key configured."):
            ExampleCloudConnector(test_settings)

    def test_add_seed(self):
        seed = Seed(type="TEST", value="test-value", label="test-label")
        self.connector.add_seed(seed)
        test_label = self.connector.label_prefix + "test-label"
        assert len(self.connector.seeds[test_label]) == 1
        assert self.connector.seeds[test_label].pop() == seed

    def test_add_cloud_asset(self):
        asset = CloudAsset(
            type="TEST", value="test-value", csp_label=ProviderEnum.GCP, uid="test-uid"
        )
        self.connector.add_cloud_asset(asset)
        test_uid = self.connector.label_prefix + "test-uid"
        assert len(self.connector.cloud_assets[test_uid]) == 1
        assert self.connector.cloud_assets[test_uid].pop() == asset

    def test_submit_seeds(self):
        seed = Seed(type="TEST", value="test-value", label="test-label")
        self.connector.add_seed(seed)
        replace_seeds_mock = self.mocker.patch.object(
            self.connector.seeds_api, "replace_seeds_by_label"
        )
        self.connector.submit_seeds()
        replace_seeds_mock.assert_called_once_with(
            self.connector.label_prefix + "test-label",
            [seed.to_dict()],
        )

    def test_fail_submit_seeds(self):
        seed = Seed(type="TEST", value="test-value", label="test-label")
        self.connector.add_seed(seed)
        replace_seeds_mock = self.mocker.patch.object(
            self.connector.seeds_api, "replace_seeds_by_label"
        )
        replace_seeds_mock.side_effect = CensysAsmException(404, "Test Exception")
        logger_mock = self.mocker.patch.object(self.connector.logger, "error")
        self.connector.submit_seeds()
        logger_mock.assert_called_once()

    def test_submit_cloud_assets(self):
        # Test data
        asset = CloudAsset(
            type="TEST", value="test-value", csp_label=ProviderEnum.GCP, uid="test-uid"
        )
        self.connector.add_cloud_asset(asset)

        # Mock
        add_cloud_mock = self.mocker.patch.object(self.connector, "_add_cloud_assets")

        # Actual call
        self.connector.submit_cloud_assets()

        # Assertions
        add_cloud_mock.assert_called_once_with(
            {
                "cloudConnectorUid": self.connector.label_prefix + "test-uid",
                "cloudAssets": [asset.to_dict()],
            }
        )

    def test_fail_submit_cloud_assets(self):
        # Test data
        asset = CloudAsset(
            type="TEST", value="test-value", csp_label=ProviderEnum.GCP, uid="test-uid"
        )
        self.connector.add_cloud_asset(asset)

        # Mock
        add_cloud_mock = self.mocker.patch.object(self.connector, "_add_cloud_assets")
        add_cloud_mock.side_effect = CensysAsmException(404, "Test Exception")
        logger_mock = self.mocker.patch.object(self.connector.logger, "error")

        # Actual call
        self.connector.submit_cloud_assets()

        # Assertions
        logger_mock.assert_called_once()

    def test_add_cloud_assets(self):
        # Test data
        test_data = {
            "cloudConnectorUid": "test-uid",
        }

        # Mock
        post_mock = self.mocker.patch.object(self.connector.seeds_api._session, "post")
        post_mock.return_value.json.return_value = {"status": "success"}

        # Actual call
        self.connector._add_cloud_assets(test_data)

        # Assertions
        post_mock.assert_called_once_with(
            self.connector._add_cloud_asset_path, json=test_data
        )

    def test_submit(self):
        # Mock
        submit_seeds_mock = self.mocker.patch.object(self.connector, "submit_seeds")
        submit_cloud_assets_mock = self.mocker.patch.object(
            self.connector, "submit_cloud_assets"
        )
        self.mocker.patch.object(self.connector.settings, "dry_run", False)

        # Actual call
        self.connector.submit()

        # Assertions
        submit_seeds_mock.assert_called_once()
        submit_cloud_assets_mock.assert_called_once()

    def test_scan(self):
        # Mock
        get_seeds_mock = self.mocker.patch.object(self.connector, "get_seeds")
        get_cloud_assets_mock = self.mocker.patch.object(
            self.connector, "get_cloud_assets"
        )
        submit_mock = self.mocker.patch.object(self.connector, "submit")

        # Actual call
        self.connector.scan()

        # Assertions
        get_seeds_mock.assert_called_once()
        get_cloud_assets_mock.assert_called_once()
        submit_mock.assert_called_once()
