from typing import Union
from unittest import TestCase

import pytest
from parameterized import parameterized
from pydantic import ValidationError

from censys.cloud_connectors.common.context import SuppressValidationError
from censys.cloud_connectors.common.seed import (
    AsnSeed,
    CidrSeed,
    DomainSeed,
    IpSeed,
    Seed,
)

TEST_LABEL = "test_label"
TEST_CLOUD_RESOURCE_ID = "test-cloud-resource-id"


class SeedTest(TestCase):
    def test_seed_to_dict(self):
        test_type = "test"
        test_value = "test-seed-value"
        seed = Seed(
            type=test_type,
            value=test_value,
            label=TEST_LABEL,
            cloud_resource_id=TEST_CLOUD_RESOURCE_ID,
        )
        assert seed.to_dict() == {
            "type": test_type,
            "value": test_value,
        }

    def test_asn_seed(self):
        test_value = 123
        seed = AsnSeed(
            value=test_value, label=TEST_LABEL, cloud_resource_id=TEST_CLOUD_RESOURCE_ID
        )
        assert seed.type == "ASN"
        assert seed.value == test_value
        assert seed.label == TEST_LABEL

    @parameterized.expand([("AS123", "value is not a valid integer")])
    def test_asn_seed_validation(self, test_value: str, exception_message: str):
        with pytest.raises(ValidationError, match=exception_message):
            AsnSeed(
                value=test_value,
                label=TEST_LABEL,
                cloud_resource_id=TEST_CLOUD_RESOURCE_ID,
            )

    def test_ip_seed(self):
        test_value = "192.35.168.0"
        seed = IpSeed(
            value=test_value, label=TEST_LABEL, cloud_resource_id=TEST_CLOUD_RESOURCE_ID
        )
        assert seed.type == "IP_ADDRESS"
        assert seed.value == test_value
        assert seed.label == TEST_LABEL

    @parameterized.expand(
        [
            ("192.168.1.1", "IP address is private"),
            ("8.8.8.8", "IP address is in the ignore list"),
        ]
    )
    def test_ip_seed_validation(self, value: str, exception_message: str):
        with pytest.raises(ValidationError, match=exception_message):
            IpSeed(
                value=value, label=TEST_LABEL, cloud_resource_id=TEST_CLOUD_RESOURCE_ID
            )

    @parameterized.expand(
        [
            ("censys.io", "censys.io"),
            ("https://search.censys.io.", "search.censys.io"),
            (
                "111111111111111111111111111111.one.two.three.example.com",
                "111111111111111111111111111111.one.two.three.example.com",
            ),
        ]
    )
    def test_domain_seed(self, test_value: str, expected_value: str):
        seed = DomainSeed(
            value=test_value, label=TEST_LABEL, cloud_resource_id=TEST_CLOUD_RESOURCE_ID
        )
        assert seed.type == "DOMAIN_NAME"
        assert seed.value == expected_value
        assert seed.label == TEST_LABEL

    @parameterized.expand(
        [
            ("notaprotocol://bad.domain/path", "Domain is not valid"),
            ("google.com", "Domain is in the ignore list"),
            ("_bad.domain", "Domain contains an underscore"),
        ]
    )
    def test_domain_seed_validation(self, value: str, exception_message: str):
        with pytest.raises(ValidationError, match=exception_message):
            DomainSeed(
                value=value, label=TEST_LABEL, cloud_resource_id=TEST_CLOUD_RESOURCE_ID
            )

    def test_cidr_seed(self):
        test_value = "192.35.168.0/24"
        seed = CidrSeed(
            value=test_value, label=TEST_LABEL, cloud_resource_id=TEST_CLOUD_RESOURCE_ID
        )
        assert seed.type == "CIDR"
        assert seed.value == test_value
        assert seed.label == TEST_LABEL

    @parameterized.expand(
        [
            ("not.a.ip.address", "CIDR is not valid"),
            ("10.0.0.0/8", "CIDR is private"),
        ]
    )
    def test_cidr_validation(self, value: str, exception_message: str):
        with pytest.raises(ValidationError, match=exception_message):
            CidrSeed(
                value=value, label=TEST_LABEL, cloud_resource_id=TEST_CLOUD_RESOURCE_ID
            )

    @parameterized.expand(
        [
            ("8.8.8.8", IpSeed),
            ("aws.com", DomainSeed),
            ("10.0.0.0/8", CidrSeed),
            ("AS1234", AsnSeed),
        ]
    )
    def test_with_suppress_validation_error(
        self, value: str, seed_cls: type[Union[IpSeed, DomainSeed, CidrSeed, AsnSeed]]
    ):
        seed = None
        with SuppressValidationError():
            seed = seed_cls(
                value=value, label=TEST_LABEL, cloud_resource_id=TEST_CLOUD_RESOURCE_ID
            )
        assert seed is None, "Seed should have failed validation"
