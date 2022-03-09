from unittest.mock import mock_open

import pytest

from censys.common.exceptions import CensysAsmException, CensysException

from censys.cloud_connectors.common.cloud_asset import CloudAsset
from censys.cloud_connectors.common.connector import CloudConnector
from censys.cloud_connectors.common.enums import ProviderEnum
from censys.cloud_connectors.common.seed import Seed
from censys.cloud_connectors.common.settings import Settings
from tests.base_case import BaseTestCase


class ExampleCloudConnector(CloudConnector):
    provider = ProviderEnum.AWS

    def get_seeds(self):
        return super().get_seeds()

    def get_cloud_assets(self) -> None:
        return super().get_cloud_assets()

    def scan_all(self):
        return super().scan_all()


class TestCloudConnector(BaseTestCase):
    settings: Settings
    connector: CloudConnector

    def setUp(self) -> None:
        super().setUp()
        self.settings = Settings(
            censys_api_key=self.consts["censys_api_key"],
            providers_config_file=str(self.shared_datadir / "test_empty_providers.yml"),
        )
        self.connector = ExampleCloudConnector(self.settings)

    def tearDown(self) -> None:
        # Reset the deaultdicts as they are immutable
        for seed_key in list(self.connector.seeds.keys()):
            del self.connector.seeds[seed_key]
        for cloud_asset_key in list(self.connector.cloud_assets.keys()):
            del self.connector.cloud_assets[cloud_asset_key]

    def test_init(self):
        assert self.connector.provider == ProviderEnum.AWS
        assert self.connector.label_prefix == ProviderEnum.AWS.label() + ": "
        assert self.connector.settings == self.settings
        assert self.connector.logger is not None
        assert self.connector.seeds_api is not None
        assert self.connector.seeds_api._api_key == self.consts["censys_api_key"]
        assert (
            self.connector._add_cloud_asset_path
            == f"{self.settings.censys_beta_url}/cloudConnector/addCloudAssets"
        )
        assert list(self.connector.seeds.keys()) == []
        assert list(self.connector.cloud_assets.keys()) == []

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
            "builtins.open",
            new_callable=mock_open,
            read_data="[DEFAULT]\napi_id =\napi_secret =\nasm_api_key =",
        )

        # Assertions
        with pytest.raises(CensysException, match="No ASM API key configured."):
            ExampleCloudConnector(test_settings)

    def test_add_seed(self):
        seed = Seed(type="TEST", value="test-value", label="test-label")
        self.connector.add_seed(seed)
        test_label = self.connector.label_prefix + "test-label"
        assert self.connector.seeds[test_label][0] == seed
        assert len(self.connector.seeds[test_label]) == 1

    def test_add_cloud_asset(self):
        asset = CloudAsset(
            type="TEST", value="test-value", cspLabel=ProviderEnum.AWS, uid="test-uid"
        )
        self.connector.add_cloud_asset(asset)
        test_uid = self.connector.label_prefix + "test-uid"
        assert self.connector.cloud_assets[test_uid][0] == asset
        assert len(self.connector.cloud_assets[test_uid]) == 1

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
        asset = CloudAsset(
            type="TEST", value="test-value", cspLabel=ProviderEnum.AWS, uid="test-uid"
        )
        self.connector.add_cloud_asset(asset)
        add_cloud_mock = self.mocker.patch.object(self.connector, "_add_cloud_assets")
        self.connector.submit_cloud_assets()
        add_cloud_mock.assert_called_once_with(
            {
                "cloudConnectorUid": self.connector.label_prefix + "test-uid",
                "cloudAssets": [asset.to_dict()],
            }
        )

    def test_fail_submit_cloud_assets(self):
        asset = CloudAsset(
            type="TEST", value="test-value", cspLabel=ProviderEnum.AWS, uid="test-uid"
        )
        self.connector.add_cloud_asset(asset)
        add_cloud_mock = self.mocker.patch.object(self.connector, "_add_cloud_assets")
        add_cloud_mock.side_effect = CensysAsmException(404, "Test Exception")
        logger_mock = self.mocker.patch.object(self.connector.logger, "error")
        self.connector.submit_cloud_assets()
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

    @pytest.mark.skip("Submission Not Implemented (Purposefully)")
    def test_submit(self):
        submit_seeds_mock = self.mocker.patch.object(self.connector, "submit_seeds")
        submit_cloud_assets_mock = self.mocker.patch.object(
            self.connector, "submit_cloud_assets"
        )
        self.connector.submit()
        submit_seeds_mock.assert_called_once()
        submit_cloud_assets_mock.assert_called_once()

    def test_scan(self):
        get_seeds_mock = self.mocker.patch.object(self.connector, "get_seeds")
        get_cloud_assets_mock = self.mocker.patch.object(
            self.connector, "get_cloud_assets"
        )
        submit_mock = self.mocker.patch.object(self.connector, "submit")
        self.connector.scan()
        get_seeds_mock.assert_called_once()
        get_cloud_assets_mock.assert_called_once()
        submit_mock.assert_called_once()
