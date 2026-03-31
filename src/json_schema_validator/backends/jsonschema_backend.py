"""jsonschema backend for json_schema_validator.

Uses the ``jsonschema`` library (Draft 7) which is a required dependency of
``protocollab``.  This backend is always available and is the safe default
for validating untrusted schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List

import jsonschema
from jsonschema import Draft7Validator

from json_schema_validator.backends.base import AbstractSchemaValidator
from json_schema_validator.models import SchemaValidationError


def _format_path(error: jsonschema.ValidationError) -> str:
    """Convert a jsonschema error path deque to dot-notation string."""
    parts: list[str] = []
    for segment in error.absolute_path:
        if isinstance(segment, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{segment}]"
            else:
                parts.append(f"[{segment}]")
        else:
            parts.append(str(segment))
    return ".".join(parts) if parts else "(root)"


def _format_schema_path(error: jsonschema.ValidationError) -> str:
    return "/".join(str(s) for s in error.absolute_schema_path)


class JsonschemaBackend(AbstractSchemaValidator):
    """JSON Schema validation backed by the ``jsonschema`` library.

    Validators are compiled once per unique schema object identity and reused
    on subsequent calls when *cache* is ``True`` (default).

    Parameters
    ----------
    cache:
        When ``True`` (default) compiled validators are cached by schema ``id``
        (object identity).  Set to ``False`` to always recompile.
    """

    def __init__(self, cache: bool = True) -> None:
        self._cache: dict[int, Draft7Validator] = {}
        self._cache_enabled = cache

    def validate(
        self,
        schema: Dict[str, Any],
        data: Dict[str, Any],
    ) -> List[SchemaValidationError]:
        """Validate *data* against *schema* using ``jsonschema``."""
        validator = self._get_validator(schema)
        errors: List[SchemaValidationError] = []
        for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
            errors.append(
                SchemaValidationError(
                    path=_format_path(err),
                    message=err.message,
                    schema_path=_format_schema_path(err),
                )
            )
        return errors

    def _get_validator(self, schema: Dict[str, Any]) -> Draft7Validator:
        if not self._cache_enabled:
            return Draft7Validator(schema)
        key = id(schema)
        if key not in self._cache:
            self._cache[key] = Draft7Validator(schema)
        return self._cache[key]
