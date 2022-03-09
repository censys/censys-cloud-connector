import pytest
from parameterized import parameterized
from pydantic import ValidationError

from censys.cloud_connectors.common.seed import (
    AsnSeed,
    CidrSeed,
    DomainSeed,
    IpSeed,
    Seed,
)
from tests.base_case import BaseTestCase

TEST_LABEL = "test_label"


class SeedTest(BaseTestCase):
    def test_seed_to_dict(self):
        test_type = "test"
        test_value = "test-seed-value"
        seed = Seed(type=test_type, value=test_value, label=TEST_LABEL)
        assert seed.to_dict() == {
            "type": test_type,
            "value": test_value,
        }

    def test_asn_seed(self):
        test_value = "AS1234"
        seed = AsnSeed(value=test_value, label=TEST_LABEL)
        assert seed.type == "ASN"
        assert seed.value == test_value
        assert seed.label == TEST_LABEL

    def test_asn_seed_validation(self):
        # TODO: implement validation?
        pass

    def test_ip_seed(self):
        test_value = "192.35.168.0"
        seed = IpSeed(value=test_value, label=TEST_LABEL)
        assert seed.type == "IP_ADDRESS"
        assert seed.value == test_value
        assert seed.label == TEST_LABEL

    @parameterized.expand(
        [
            ("192.168.1.1", "IP address is private"),
            ("8.8.8.8", "IP address is in the ignore list"),
        ]
    )
    def test_ip_seed_validation(self, value, exception_message):
        with pytest.raises(ValidationError, match=exception_message):
            IpSeed(value=value, label=TEST_LABEL)

    @parameterized.expand(
        [
            ("censys.io", "censys.io"),
            ("https://search.censys.io.", "search.censys.io"),
        ]
    )
    def test_domain_seed(self, test_value, expected_value):
        seed = DomainSeed(value=test_value, label=TEST_LABEL)
        assert seed.type == "DOMAIN_NAME"
        assert seed.value == expected_value
        assert seed.label == TEST_LABEL

    @parameterized.expand(
        [
            ("notaprotocol://bad.domain/path", "Domain is not valid"),
            ("google.com", "Domain is in the ignore list"),
        ]
    )
    def test_domain_seed_validation(self, value, exception_message):
        with pytest.raises(ValidationError, match=exception_message):
            DomainSeed(value=value, label=TEST_LABEL)

    def test_cidr_seed(self):
        test_value = "192.35.168.0/24"
        seed = CidrSeed(value=test_value, label=TEST_LABEL)
        assert seed.type == "CIDR"
        assert seed.value == test_value
        assert seed.label == TEST_LABEL

    @parameterized.expand(
        [
            ("not.a.ip.address", "CIDR is not valid"),
            ("10.0.0.0/8", "CIDR is private"),
        ]
    )
    def test_cidr_validation(self, value, exception_message):
        with pytest.raises(ValidationError, match=exception_message):
            CidrSeed(value=value, label=TEST_LABEL)
