"""Cloud Asset Objects."""
import json

from pydantic import AnyUrl, BaseModel, parse_obj_as, validator

from censys.cloud_connectors.common.enums import ProviderEnum


class CloudAsset(BaseModel):
    """Base class for all cloud assets."""

    type: str
    value: str
    csp_label: ProviderEnum
    scan_data: dict = {}
    uid: str  # Used as cloudConnectorUid

    def to_dict(self) -> dict[str, str]:
        """Convert the cloud asset to a dictionary.

        Returns:
            Dictionary representation of the cloud asset.
        """
        return {
            "type": self.type,
            "value": self.value,
            "cspLabel": self.csp_label.label(),
            "scanData": json.dumps(self.scan_data),
        }


class ObjectStorageAsset(CloudAsset):
    """Object storage asset."""

    type: str = "OBJECT_STORAGE"


class GcpStorageBucketAsset(ObjectStorageAsset):
    """GCP Cloud Storage asset."""

    csp_label = ProviderEnum.GCP

    @validator("value")
    def value_is_valid_bucket_name(cls, v: str) -> str:
        """Validate that the bucket name is valid.

        Args:
            v (str): Bucket name.

        Raises:
            ValueError: If the bucket name is invalid.

        Returns:
            Bucket name.
        """
        # TODO: Should https://www.googleapis.com/storage/v1/b/ (self) links be supported?
        url_prefix = "https://storage.googleapis.com/"
        if not v.startswith(url_prefix):
            raise ValueError(f"Bucket name must start with {url_prefix}")
        return v


class AzureContainerAsset(ObjectStorageAsset):
    """Azure Container asset."""

    csp_label = ProviderEnum.AZURE

    @validator("value")
    def value_is_valid_container_url(cls, v: str) -> str:
        """Validate that the container URL is valid.

        Args:
            v (str): Container URL.

        Raises:
            ValueError: If the container URL is invalid.

        Returns:
            Container URL.
        """
        try:
            url = parse_obj_as(AnyUrl, v)
        except ValueError:
            raise ValueError("Container URL is not valid")
        return str(url)


class AwsStorageBucketAsset(ObjectStorageAsset):
    """AWS Container asset."""

    csp_label = ProviderEnum.AWS

    @validator("value")
    def value_is_valid_bucket_name(cls, v: str) -> str:
        """Validate that the bucket name is valid.

        Args:
            v (str): Bucket name.

        Returns:
            Bucket name.
        """
        return v

    @staticmethod
    def url(bucket: str, region: str = "us-east-1") -> str:
        """Get the URL of the container.

        Args:
            bucket (str): Bucket name.
            region (str): Region name.

        Returns:
            str: Container URL.
        """
        return f"https://{bucket}.s3.{region}.amazonaws.com"
