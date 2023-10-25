"""Aurora API client."""
from cloudevents.conversion import to_structured
from cloudevents.http import CloudEvent

from censys.asm import Seeds


class Aurora(Seeds):
    """Aurora API client."""

    base_path = "/api/integrations"

    # TODO @_backoff_wrapper
    def enqueue_payload(self, payload: CloudEvent) -> None:
        """Enqueue a payload for later processing.

        Args:
            payload (CloudEvent): Payload.
        """
        headers, body = to_structured(payload)
        request_kwargs = {"timeout": self.timeout, "data": body, "headers": headers}

        url = f"{self._api_url}{self.base_path}/v1/payloads/enqueue"
        resp = self._call_method(self._session.post, url, request_kwargs)

        if resp.ok:
            try:
                json_data = resp.json()
                return json_data
            except ValueError:
                return {"code": resp.status_code, "status": resp.reason}

        raise Exception(f"Invalid response: {resp.text}")
