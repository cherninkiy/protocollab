"""Abstract base class for all jsonschema_validator backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from jsonschema_validator.models import SchemaValidationError


class AbstractSchemaValidator(ABC):
    """Interface that every validation backend must implement.

    Each backend wraps one JSON Schema library and normalises its error output
    to :class:`~jsonschema_validator.models.SchemaValidationError` instances
    using the dot-notation path format expected by callers.
    """

    @abstractmethod
    def validate(
        self,
        schema: Dict[str, Any],
        data: Dict[str, Any],
    ) -> List[SchemaValidationError]:
        """Validate *data* against *schema*.

        Parameters
        ----------
        schema:
            A JSON Schema document (Draft 7) as a Python dict.
        data:
            The object to validate.

        Returns
        -------
        list[SchemaValidationError]
            Empty list means *data* is valid; otherwise one entry per error.
        """
