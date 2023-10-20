"""Exceptions for the Cloud Connectors."""
from typing import Optional


class CensysCloudConnectorException(Exception):
    """Base Exception for Censys Cloud Connectors."""


class CensysCloudProviderException(CensysCloudConnectorException):
    """Base Exception for Censys Cloud Connector Cloud Providers."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        body: Optional[str] = None,
        const: Optional[str] = None,
        details: Optional[str] = None,
    ):
        """Inits CensysCloudProviderException.

        Args:
            message (str): HTTP message.
            status_code (int): Optional; HTTP status code.
            body (str): Optional; HTTP body.
            const (str): Optional; Constant for manual errors.
            details (str): Optional; Additional details.
        """
        self.message = message
        self.status_code = status_code
        self.body = body
        self.const = const
        self.details = details
        super().__init__(self.message)

    def __repr__(self) -> str:
        """Representation of CensysCloudProviderException.

        Returns:
            str: Printable representation.
        """
        return f"{self.message}"

    __str__ = __repr__


class CensysAzureException(CensysCloudProviderException):
    """Azure Exception for Censys Cloud Connectors."""

    def __repr__(self) -> str:
        """Representation of CensysAzureException.

        Returns:
            str: Printable representation.
        """
        return f"{self.message}"

    __str__ = __repr__


class CensysGcpException(CensysCloudProviderException):
    """Gcp Exception for Censys Cloud Connectors."""

    def __repr__(self) -> str:
        """Representation of CensysGcpException.

        Returns:
            str: Printable representation.
        """
        return f"{self.message}"

    __str__ = __repr__


class CensysAwsException(CensysCloudProviderException):
    """Aws Exception for Censys Cloud Connectors."""

    def __repr__(self) -> str:
        """Representation of CensysAwsException.

        Returns:
            str: Printable representation.
        """
        return f"{self.message}"

    __str__ = __repr__
