"""Class for performing healthchecks on Cloud Connectors."""
import traceback
from types import TracebackType
from typing import Any, Literal, Optional

import requests

from .logger import get_logger
from .settings import ProviderSpecificSettings, Settings

ErrorCodes = Literal["ABANDONED", "PERMISSIONS"]


class Healthcheck:
    """Healthcheck class for the Cloud Connectors."""

    run_id: Optional[int]

    def __init__(
        self,
        settings: Settings,
        provider_specific_settings: ProviderSpecificSettings,
        provider: Optional[dict] = None,
        exception_map: Optional[dict[Exception, ErrorCodes]] = None,
        **kwargs,
    ) -> None:
        """Initialize the Healthcheck.

        Args:
            settings (Settings): The settings to use.
            provider_specific_settings (ProviderSpecificSettings): The provider-specific settings to use.
            provider (Optional[dict]): Additional provider information to use.
            exception_map (Optional[dict[Exception, ErrorCodes]]): The exception map to use.
            **kwargs: Additional keyword arguments.
        """
        self.settings = settings
        self.provider_specific_settings = provider_specific_settings
        self.provider_payload = provider_specific_settings.get_provider_payload()
        if provider:
            new_provider_payload = self.provider_payload.get(
                self.provider_specific_settings.provider, {}
            )
            new_provider_payload.update(provider)
            self.provider_payload.update(
                {self.provider_specific_settings.provider: new_provider_payload}
            )
        if kwargs:
            self.provider_payload.update(kwargs)
        self.exception_map = exception_map or {}
        self.logger = get_logger(
            log_name="healthcheck",
            level=settings.logging_level,
        )

        # Session
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": settings.censys_user_agent,
                "Censys-Api-Key": settings.censys_api_key,
            }
        )
        self._session.cookies.update(settings.censys_cookies)

        # URLs
        self.base_url = settings.censys_asm_api_base_url
        self.integrations_url = f"{self.base_url}/integrations/beta"
        self.status_url = f"{self.integrations_url}/status"
        self.start_url = f"{self.status_url}/start"
        self.finish_url = self.status_url + "/{run_id}/finish"
        self.fail_url = self.status_url + "/{run_id}/fail"
        self.run_id = None

    def __enter__(self) -> "Healthcheck":
        """Enter the Healthcheck context.

        Returns:
            Healthcheck: The Healthcheck instance.
        """
        if self.settings.healthcheck_enabled:
            self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> None:
        """Exit the Healthcheck context.

        Args:
            exc_type (Optional[type[BaseException]]): The exception type.
            exc_value (Optional[BaseException]): The exception value.
            exc_traceback (Optional[TracebackType]): The traceback.
        """
        if not self.settings.healthcheck_enabled:
            return
        if exc_type is not None:
            error_code = self.exception_map.get(exc_type)  # type: ignore
            self.fail(
                error_code=error_code,
                metadata={
                    "error": str(exc_type),
                    "exception": str(exc_value),
                    "traceback": "".join(traceback.format_tb(exc_traceback)),
                },
            )
        else:
            self.finish()

    def __del__(self) -> None:
        """Delete the Healthcheck."""
        if self.run_id:
            self.finish()
        self._session.close()

    def start(self) -> None:
        """Start the Healthcheck.

        Raises:
            ValueError: If the provider is not set.
        """
        if not self.provider_payload:
            raise ValueError("The provider must be set.")
        self.run_id = self._session.post(
            self.start_url, json={"provider": self.provider_payload}
        ).json()["runId"]
        self.logger.debug(
            f"Starting Run ID: {self.run_id}", extra={"provider": self.provider_payload}
        )

    def finish(self, metadata: Optional[dict] = None) -> None:
        """Finish the Healthcheck.

        Args:
            metadata (Optional[dict]): The metadata to use.

        Raises:
            ValueError: If the run ID is not set.
        """
        if not self.run_id:
            raise ValueError("The run ID must be set.")
        body = {}

        if not self.settings.healthcheck_enabled:
            self.logger.info(
                "Healthcheck not enabled. Skipping submission of healthcheck data."
            )
        else:
            if metadata:
                body["metadata"] = metadata
            self.logger.info("Submitting healthcheck data...")
            self._session.post(self.finish_url.format(run_id=self.run_id), json=body)
            self.logger.debug(
                f"Finished Run ID: {self.run_id}",
                extra={"provider": self.provider_payload},
            )

        self.run_id = None

    def fail(
        self,
        error_code: Optional[ErrorCodes] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Fail the Healthcheck.

        Args:
            error_code (Optional[ErrorCodes]): The error code to use.
            metadata (Optional[dict]): The metadata to use.

        Raises:
            ValueError: If the run ID is not set.
        """
        if not self.run_id:
            raise ValueError("The run ID must be set.")
        data: dict[str, Any] = {}
        if error_code:
            data["errorCode"] = error_code
        if metadata:
            data["metadata"] = metadata

        res = self._session.post(
            self.fail_url.format(run_id=self.run_id),
            json=data,
        )
        if res and res.status_code == 200:
            self.logger.debug(
                f"Failed Run ID: {self.run_id}",
                extra={"provider": self.provider_payload},
            )
        else:
            self.logger.error(res.text)
        self.run_id = None
