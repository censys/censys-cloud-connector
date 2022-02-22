"""Cloud Asset Objects."""
import json
from typing import Dict

from pydantic import AnyHttpUrl, BaseModel, validator


class CloudAsset(BaseModel):
    """Base class for all cloud assets."""

    type: str
    value: str
    cspLabel: str
    scan_data: dict = {}
    uid: str  # Used as cloudConnectorUid

    def to_dict(self) -> Dict[str, str]:
        """Convert the cloud asset to a dictionary.

        Returns:
            Dictionary representation of the cloud asset.
        """
        return {
            "type": self.type,
            "value": self.value,
            "cspLabel": self.cspLabel,
            "scanData": json.dumps(self.scan_data),
        }


class ObjectStorageAsset(CloudAsset):
    """Object storage asset."""

    type: str = "OBJECT_STORAGE"


class GcpCloudStorageAsset(ObjectStorageAsset):
    """GCP Cloud Storage asset."""

    cspLabel: str = "GCP"
    value: AnyHttpUrl

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
        url_prefix = "https://storage.googleapis.com/"
        if not v.startswith(url_prefix):
            raise ValueError(f"Bucket name must start with {url_prefix}")
        return v


class AzureContainerAsset(ObjectStorageAsset):
    """Azure Container asset."""

    cspLabel: str = "AZURE"
    value: AnyHttpUrl
