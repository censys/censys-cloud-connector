from unittest import TestCase

import pytest
from parameterized import parameterized
from pytest_mock import MockerFixture

from censys.cloud_connectors.common.cloud_asset import (
    AzureContainerAsset,
    CloudAsset,
    GcpStorageBucketAsset,
    ObjectStorageAsset,
)
from censys.cloud_connectors.common.enums import ProviderEnum

TEST_TYPE = "test_type"
TEST_VALUE = "test_value"
TEST_SCAN_DATA = {"test_scan_data": "test_scan_data"}
TEST_UID = "test_uid"


class CloudAssetTest(TestCase):
    @pytest.fixture(autouse=True)
    def __inject_fixtures(self, mocker: MockerFixture):
        self.mocker = mocker

    def test_cloud_asset_to_dict(self):
        cloud_asset = CloudAsset(
            type=TEST_TYPE,
            value=TEST_VALUE,
            cspLabel=ProviderEnum.AWS,
            scan_data=TEST_SCAN_DATA,
            uid=TEST_UID,
        )
        assert cloud_asset.uid == TEST_UID
        assert cloud_asset.to_dict() == {
            "type": TEST_TYPE,
            "value": TEST_VALUE,
            "cspLabel": ProviderEnum.AWS.label(),
            "scanData": '{"test_scan_data": "test_scan_data"}',
        }

    def test_object_storage_asset(self):
        cloud_asset = ObjectStorageAsset(
            value=TEST_VALUE, cspLabel=ProviderEnum.AWS, uid=TEST_UID
        )
        assert cloud_asset.type == "OBJECT_STORAGE"

    def test_gcp_cloud_storage_asset(self):
        test_object_name = "test-bucket"
        test_value = f"https://storage.googleapis.com/{test_object_name}"
        cloud_asset = GcpStorageBucketAsset(value=test_value, uid=test_object_name)
        assert cloud_asset.type == "OBJECT_STORAGE"
        assert cloud_asset.value == test_value
        assert cloud_asset.cspLabel == ProviderEnum.GCP
        assert cloud_asset.scan_data == {}
        assert cloud_asset.uid == "test-bucket"

    @parameterized.expand(
        [
            (
                "http://not.valid.bucket/url",
                "Bucket name must start with https://storage.googleapis.com/",
            ),
        ]
    )
    def test_gcp_cloud_storage_asset_validation(self, value, expected_error):
        with pytest.raises(ValueError, match=expected_error):
            GcpStorageBucketAsset(value=value, uid=TEST_UID)

    def test_azure_container_asset(self):
        test_object_name = "test-container"
        test_value = f"https://{test_object_name}.blob.core.windows.net"
        cloud_asset = AzureContainerAsset(value=test_value, uid=test_object_name)
        assert cloud_asset.type == "OBJECT_STORAGE"
        assert cloud_asset.value == test_value
        assert cloud_asset.cspLabel == ProviderEnum.AZURE
        assert cloud_asset.scan_data == {}
        assert cloud_asset.uid == "test-container"

    @parameterized.expand(
        [
            (
                "not.valid.bucket/url",
                "Container URL is not valid",
            ),
        ]
    )
    def test_azure_container_asset_validation(self, value, expected_error):
        with pytest.raises(ValueError, match=expected_error):
            AzureContainerAsset(value=value, uid=TEST_UID)
