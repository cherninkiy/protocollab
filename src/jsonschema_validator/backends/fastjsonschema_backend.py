"""fastjsonschema backend for jsonschema_validator.

Uses the ``fastjsonschema`` library for high-performance validation.

.. warning::
   ``fastjsonschema`` compiles a schema to Python source code and evaluates it
   with ``exec``.  This makes it unsuitable for validating **untrusted schemas**.
   Always use the default ``jsonscreamer`` or ``jsonschema`` backend (or
   ``auto``) when the schema originates from an untrusted source.

   This backend is **never** selected by ``auto`` mode; you must opt in
   explicitly by passing ``backend="fastjsonschema"`` to
   :class:`~jsonschema_validator.factory.ValidatorFactory`.

This module is an **optional** backend: if ``fastjsonschema`` is not installed,
constructing :class:`FastjsonschemaBackend` will raise
:class:`~jsonschema_validator.factory.BackendNotAvailableError`.
"""

from __future__ import annotations

from typing import Any, Dict, List

from jsonschema_validator.backends.base import AbstractSchemaValidator
from jsonschema_validator.models import SchemaValidationError


def _build_path(path: list) -> str:
    """Convert a fastjsonschema path list to dot-notation."""
    if not path:
        return "(root)"
    parts: list[str] = []
    for segment in path:
        # fastjsonschema uses "data[N]" or "data['key']" notation
        if isinstance(segment, str) and segment.startswith("data"):
            inner = segment[len("data"):]
            if inner.startswith("[") and inner.endswith("]"):
                key = inner[1:-1].strip("'\"")
                try:
                    idx = int(key)
                    if parts:
                        parts[-1] = f"{parts[-1]}[{idx}]"
                    else:
                        parts.append(f"[{idx}]")
                    continue
                except ValueError:
                    parts.append(key)
                    continue
        parts.append(str(segment))
    return ".".join(parts) if parts else "(root)"


class FastjsonschemaBackend(AbstractSchemaValidator):
    """JSON Schema validation backed by ``fastjsonschema``.

    Compiled validators are cached by schema object identity when *cache* is
    ``True`` (default).

    Parameters
    ----------
    cache:
        Cache compiled validators by schema identity.  Defaults to ``True``.

    Raises
    ------
    ImportError
        If ``fastjsonschema`` is not installed.
    """

    def __init__(self, cache: bool = True) -> None:
        try:
            import fastjsonschema  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "The 'fastjsonschema' package is required for the fastjsonschema backend. "
                "Install it with: pip install fastjsonschema"
            ) from exc
        self._fastjsonschema = __import__("fastjsonschema")
        self._cache: dict[int, Any] = {}
        self._cache_enabled = cache

    def validate(
        self,
        schema: Dict[str, Any],
        data: Dict[str, Any],
    ) -> List[SchemaValidationError]:
        """Validate *data* against *schema* using ``fastjsonschema``."""
        compiled = self._get_compiled(schema)
        try:
            compiled(data)
        except self._fastjsonschema.JsonSchemaValueException as exc:
            path = getattr(exc, "path", [])
            return [
                SchemaValidationError(
                    path=_build_path(list(path) if path else []),
                    message=exc.message,
                    schema_path="",
                )
            ]
        return []

    def _get_compiled(self, schema: Dict[str, Any]) -> Any:
        if not self._cache_enabled:
            return self._fastjsonschema.compile(schema)
        key = id(schema)
        if key not in self._cache:
            self._cache[key] = self._fastjsonschema.compile(schema)
        return self._cache[key]
