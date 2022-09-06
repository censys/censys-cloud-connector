"""With-statement Contexts for the Cloud Connectors."""
import contextlib
from collections.abc import Iterable
from typing import Optional

from pydantic import ValidationError

wrapper = contextlib.suppress


class SuppressValidationError(contextlib.suppress):
    """Context manager to suppress validation errors."""

    def __init__(self, exceptions: Optional[Iterable[type[BaseException]]] = None):
        """Initialize the context manager.

        Args:
            exceptions (Optional[Iterable[Type[BaseException]]]): The exceptions to suppress.
        """
        exceptions = exceptions or [ValidationError]
        super().__init__(*exceptions)
