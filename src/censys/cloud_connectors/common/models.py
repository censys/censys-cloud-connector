"""Models for the Cloud Connectors."""
from pydantic import BaseModel


class HashableBaseModel(BaseModel):
    """Base class for hashable models."""

    def __hash__(self) -> int:
        """Return the hash of the model.

        Returns:
            int: The hash of the model.
        """
        return hash(
            (type(self),)
            + tuple(
                value.values() if isinstance(value, dict) else value
                for value in self.__dict__.values()
            )
        )
