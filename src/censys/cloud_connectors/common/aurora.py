"""Aurora API client."""
from cloudevents.conversion import to_structured
from cloudevents.http import CloudEvent

from censys.asm import Seeds


class Aurora(Seeds):
    """Aurora API client."""

    base_path = "/api"

    # TODO @backoff_wrapper
    def enqueue_payload(self, payload: CloudEvent) -> None:
        """Enqueue a payload for later processing.

        Args:
            payload (CloudEvent): Payload.
        """

        headers, body = to_structured(payload)
        request_kwargs = {"timeout": self.timeout, "data": body, "headers": headers}

        # url = f"{self._api_url}{self.base_path}"
        url = f"{self._api_url}{self.base_path}/payload/enqueue"
        resp = self._call_method(self._session.post, url, request_kwargs)

        # TODO: handle response
        # TODO: read enqueue response `event ID` (for status tracking)
        print(f"TODO resp: {resp}")

        if resp.ok:
            try:
                json_data = resp.json()
                # if "error" not in json_data:
                #     return json_data
                return json_data
            except ValueError:
                return {"code": resp.status_code, "status": resp.reason}

        return {}
