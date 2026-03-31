"""jsonscreamer backend for jsonschema_validator.

Uses the ``jsonscreamer`` library for validation.  The ``jsonscreamer``
``Validator`` provides a ``jsonschema``-compatible interface (``iter_errors``,
``absolute_path``, ``message``), making it a drop-in replacement that can be
safely used with untrusted schemas.

This backend is included in the ``auto`` priority list and is preferred over
``jsonschema`` when available, since it offers the same safety guarantees with
improved performance.

This module is an **optional** backend: if ``jsonscreamer`` is not installed,
constructing :class:`JsonscreamerBackend` will raise
:class:`~jsonschema_validator.factory.BackendNotAvailableError`.
"""

from __future__ import annotations

from typing import Any, Dict, List

from jsonschema_validator.backends.base import AbstractSchemaValidator
from jsonschema_validator.models import SchemaValidationError


def _format_path(path: list) -> str:
    """Convert a jsonscreamer absolute_path list to dot-notation string."""
    parts: list[str] = []
    for segment in path:
        if isinstance(segment, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{segment}]"
            else:
                parts.append(f"[{segment}]")
        else:
            parts.append(str(segment))
    return ".".join(parts) if parts else "(root)"


class JsonscreamerBackend(AbstractSchemaValidator):
    """JSON Schema validation backed by the ``jsonscreamer`` library.

    ``jsonscreamer`` provides a ``jsonschema``-compatible interface, making it
    a safe drop-in that can be used with untrusted schemas.  Validators are
    cached per schema object identity when *cache* is ``True`` (default).

    Parameters
    ----------
    cache:
        When ``True`` (default) ``Validator`` instances are cached by schema
        object identity.  Set to ``False`` to always create a fresh instance.

    Raises
    ------
    ImportError
        If ``jsonscreamer`` is not installed.
    """

    def __init__(self, cache: bool = True) -> None:
        try:
            import jsonscreamer  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "The 'jsonscreamer' package is required for the jsonscreamer backend. "
                "Install it with: pip install jsonscreamer"
            ) from exc
        self._jsonscreamer = __import__("jsonscreamer")
        self._cache: dict[int, Any] = {}
        self._cache_enabled = cache

    def validate(
        self,
        schema: Dict[str, Any],
        data: Dict[str, Any],
    ) -> List[SchemaValidationError]:
        """Validate *data* against *schema* using ``jsonscreamer``."""
        validator = self._get_validator(schema)
        errors: List[SchemaValidationError] = []
        for err in validator.iter_errors(data):
            errors.append(
                SchemaValidationError(
                    path=_format_path(list(err.absolute_path)),
                    message=err.message,
                    schema_path="",
                )
            )
        return errors

    def _get_validator(self, schema: Dict[str, Any]) -> Any:
        if not self._cache_enabled:
            return self._jsonscreamer.Validator(schema)
        key = id(schema)
        if key not in self._cache:
            self._cache[key] = self._jsonscreamer.Validator(schema)
        return self._cache[key]
