"""JSON Schema-based structural validator for protocol specifications.

Uses the :mod:`json_schema_validator` facade so that the underlying
JSON Schema backend is swappable without changing this module's API.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from json_schema_validator import ValidatorFactory
from json_schema_validator.backends.base import AbstractSchemaValidator

from protocollab.validator.models import ValidationError

_SCHEMAS_DIR = Path(__file__).parent / "schemas"
_DEFAULT_SCHEMA_PATH = _SCHEMAS_DIR / "base.schema.json"


class SchemaValidator:
    """Validates a protocol data dict against a JSON Schema.

    Parameters
    ----------
    schema_path:
        Path to a custom JSON Schema file.  Defaults to ``base.schema.json``.
    backend:
        JSON Schema backend name passed to
        :meth:`~json_schema_validator.ValidatorFactory.create`.  Defaults to
        ``"auto"`` which selects the safest available backend.
    """

    def __init__(
        self,
        schema_path: Optional[str] = None,
        backend: str = "auto",
    ) -> None:
        path = Path(schema_path) if schema_path else _DEFAULT_SCHEMA_PATH
        with open(path, encoding="utf-8") as fh:
            self._schema: Dict[str, Any] = json.load(fh)
        self._backend: AbstractSchemaValidator = ValidatorFactory.create(backend=backend)

    def validate(self, data: Dict[str, Any]) -> List[ValidationError]:
        """Return a list of :class:`ValidationError` for *data* (empty = valid)."""
        raw_errors = self._backend.validate(self._schema, data)
        return [
            ValidationError(
                path=e.path,
                message=e.message,
                schema_path=e.schema_path,
            )
            for e in raw_errors
        ]
