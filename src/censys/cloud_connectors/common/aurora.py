"""Interact with Aurora API."""
from cloudevents.conversion import to_structured

from censys.asm import Seeds


class Aurora(Seeds):
    """Aurora API class."""

    # TODO base_path = "/api/v1/payload/enqueue"
    base_path = "/api/payload/enqueue"

    def emit(self, payload: dict) -> None:
        """Emit a payload to ASM.

        Args:
            payload (dict): Payload to emit.
        """

        # TODO: contact aurora
        # https://github.com/cloudevents/sdk-python#structured-http-cloudevent
        headers, body = to_structured(payload)
        # requests.post("<some-url>", data=body, headers=headers)

        # data = {"payload": payload}
        # censys python is forcing json encoding, whereas we want to send a binary cloud event
        # data_workaround = {"body": payload}
        # return self._post(
        #     self.base_path, data=body, headers=headers
        # )  # , **data_workaround)

        request_kwargs = {"timeout": self.timeout, "data": body, "headers": headers}

        # TODO @backoff_wrapper
        url = f"{self._api_url}{self.base_path}"
        resp = self._call_method(self._session.post, url, request_kwargs)
        # TODO: handle response
        print(f"resp: {resp}")

    def emit_batch(self, payloads) -> None:
        """Emit a payload to ASM.

        Args:
            payload (dict): Payload to emit.
        """

        # TODO: contact aurora
        # https://github.com/cloudevents/sdk-python#structured-http-cloudevent
        # headers, body = to_structured(event)
        # requests.post("<some-url>", data=body, headers=headers)

        data = {"payloads": payloads}
        return self._post(self.base_path, data=data)
