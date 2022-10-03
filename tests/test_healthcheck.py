from unittest import TestCase

import pytest
import responses

from censys.cloud_connectors.common.healthcheck import Healthcheck
from censys.cloud_connectors.common.settings import ProviderSpecificSettings, Settings

from .base_case import BaseCase

TEST_PROVIDER_PAYLOAD = {"test": "payload"}
TEST_RUN_ID = 100
INTEGRATIONS_API_BASE_URL = "https://app.censys.io/api/integrations/beta"
STATUS_BASE_URL = f"{INTEGRATIONS_API_BASE_URL}/status"
START_BASE_URL = f"{STATUS_BASE_URL}/start"
FINISH_BASE_URL = f"{STATUS_BASE_URL}/{{run_id}}/finish"
FAIL_BASE_URL = f"{STATUS_BASE_URL}/{{run_id}}/fail"


class ExampleProviderSettings(ProviderSpecificSettings):
    provider = "test"

    def get_provider_key(self) -> tuple:
        return super().get_provider_key()

    def get_provider_payload(self) -> dict:
        return TEST_PROVIDER_PAYLOAD


class TestHealthcheck(BaseCase, TestCase):
    def setUp(self):
        super().setUp()
        self.settings = Settings(**self.default_settings)
        self.provider_specific_settings = ExampleProviderSettings()

        self.responses = responses.RequestsMock()
        self.responses.start()

        self.addCleanup(self.responses.stop)
        self.addCleanup(self.responses.reset)

    def test_init(self):
        # Actual call
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)

        # Assertions
        assert healthcheck.settings == self.settings
        assert healthcheck.provider_specific_settings == self.provider_specific_settings
        assert healthcheck.provider_payload == TEST_PROVIDER_PAYLOAD
        assert (
            healthcheck._session.headers.get("User-Agent")
            == self.settings.censys_user_agent
        )
        assert (
            healthcheck._session.headers.get("Censys-Api-Key")
            == self.settings.censys_api_key
        )
        assert healthcheck._session.cookies == self.settings.censys_cookies
        assert healthcheck.run_id is None

    def test_context(self):
        # Test data
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)

        # Mock
        mock_start = self.mocker.patch.object(healthcheck, "start")
        mock_fail = self.mocker.patch.object(healthcheck, "fail")
        mock_finish = self.mocker.patch.object(healthcheck, "finish")

        # Actual call
        with healthcheck as hc:
            hc.run_id = TEST_RUN_ID

        # Assertions
        mock_start.assert_called_once()
        mock_fail.assert_not_called()
        mock_finish.assert_called_once()

    def test_failed_exit(self):
        # Test data
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)
        test_message = "test message"

        # Mock
        mock_start = self.mocker.patch.object(healthcheck, "start")
        mock_fail = self.mocker.patch.object(healthcheck, "fail")
        mock_finish = self.mocker.patch.object(healthcheck, "finish")
        healthcheck.run_id = TEST_RUN_ID

        # Actual call
        with pytest.raises(ValueError, match=test_message), healthcheck:
            raise ValueError(test_message)

        # Assertions
        mock_start.assert_called_once()
        mock_fail.assert_called_once()
        mock_finish.assert_not_called()

    def test_start(self):
        # Setup response
        self.responses.add(
            method="POST",
            url=START_BASE_URL,
            status=200,
            json={"runId": TEST_RUN_ID},
        )

        # Test data
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)

        # Actual call
        healthcheck.start()

        # Assertions
        assert healthcheck.run_id == TEST_RUN_ID

    def test_start_error(self):
        # Test data
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)
        healthcheck.provider_payload = None

        # Actual call
        with pytest.raises(ValueError, match="The provider must be set."):
            healthcheck.start()

    def test_finish(self):
        # Setup response
        self.responses.add(
            method="POST",
            url=FINISH_BASE_URL.format(run_id=TEST_RUN_ID),
            status=200,
        )

        # Test data
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)
        healthcheck.run_id = TEST_RUN_ID

        # Actual call
        healthcheck.finish()

        # Assertions
        assert healthcheck.run_id is None

    def test_finish_error(self):
        # Test data
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)
        healthcheck.run_id = None

        # Actual call
        with pytest.raises(ValueError, match="The run ID must be set."):
            healthcheck.finish()

    def test_fail(self):
        # Setup response
        self.responses.add(
            method="POST",
            url=FAIL_BASE_URL.format(run_id=TEST_RUN_ID),
            status=200,
        )

        # Test data
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)
        healthcheck.run_id = TEST_RUN_ID

        # Actual call
        healthcheck.fail()

        # Assertions
        assert healthcheck.run_id is None

    def test_fail_error(self):
        # Test data
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)
        healthcheck.run_id = None

        # Actual call
        with pytest.raises(ValueError, match="The run ID must be set."):
            healthcheck.fail()

    def test_disabled(self):
        # Test data
        healthcheck = Healthcheck(self.settings, self.provider_specific_settings)
        healthcheck.settings.healthcheck_enabled = False

        # Mock
        mock_start = self.mocker.patch.object(healthcheck, "start")
        mock_fail = self.mocker.patch.object(healthcheck, "fail")
        mock_finish = self.mocker.patch.object(healthcheck, "finish")

        # Actual call
        with healthcheck as hc:
            hc.run_id = TEST_RUN_ID

        # Assertions
        mock_start.assert_not_called()
        mock_fail.assert_not_called()
        mock_finish.assert_not_called()
