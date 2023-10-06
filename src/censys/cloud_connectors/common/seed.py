"""Seed Objects."""
from datetime import datetime
from ipaddress import IPv4Address, IPv4Network
from typing import Optional, Union

from pydantic import AnyUrl, parse_obj_as, validator

from .ignore_list import IGNORED_DOMAINS, IGNORED_IPS
from .models import HashableBaseModel


class Seed(HashableBaseModel):
    """Base class for all seeds."""

    type: str
    value: Union[str, int]
    label: str
    cloud_resource_id: str
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Union[str, int]]:
        """Convert the seed to a dictionary.

        Please note that the label should not be included.

        Returns:
            Dictionary representation of the seed.
        """
        return {"type": self.type, "value": self.value}


class AsnSeed(Seed):
    """ASN seed."""

    type: str = "ASN"
    value: int


class IpSeed(Seed):
    """IP seed."""

    type: str = "IP_ADDRESS"

    @validator("value")
    def value_is_public_ip(cls, v: str) -> str:
        """Validate that the IP is both public and not in the ignore list.

        Args:
            v: IP address.

        Returns:
            IP address.

        Raises:
            ValueError: If the IP is not public or in the ignore list.
        """
        ip = IPv4Address(v)
        if ip.is_private:
            raise ValueError("IP address is private")
        if str(ip) in IGNORED_IPS:
            raise ValueError("IP address is in the ignore list")
        return str(ip)


class DomainSeed(Seed):
    """Domain seed."""

    type: str = "DOMAIN_NAME"

    @validator("value")
    def value_is_host(cls, v: str) -> str:
        """Validate that the domain is not in the ignore list.

        Args:
            v: Domain name.

        Returns:
            Domain name.

        Raises:
            ValueError: If the domain is invalid or in the ignore list.
        """
        if v.endswith("."):
            v = v[:-1]
        if not ("http://" in v or "https://" in v):
            v = f"http://{v}"
        try:
            url = parse_obj_as(AnyUrl, v)
        except ValueError:
            raise ValueError("Domain is not valid")
        host = url.host.lower()
        if "_" in host:
            raise ValueError("Domain contains an underscore")
        if host in IGNORED_DOMAINS:
            raise ValueError("Domain is in the ignore list")
        return host


class CidrSeed(Seed):
    """CIDR seed."""

    type: str = "CIDR"

    @validator("value")
    def value_is_valid_cidr(cls, v: str):
        """Validate that the CIDR is both valid and public.

        Args:
            v: CIDR.

        Returns:
            CIDR.

        Raises:
            ValueError: If the CIDR is not valid or public.
        """
        try:
            cidr = IPv4Network(v)
        except ValueError:
            raise ValueError("CIDR is not valid")
        if cidr.is_private:
            raise ValueError("CIDR is private")
        return str(cidr)
