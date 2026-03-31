"""jsonschema_validator — pluggable JSON Schema validation facade.

Provides a unified, backend-agnostic interface for validating Python objects
against JSON Schema (Draft 7).  Supported backends:

* ``jsonscreamer`` — safe, jsonschema-compatible interface; preferred in
  ``auto`` mode when available.
* ``jsonschema``   — maximum compatibility; safe default fallback.
* ``fastjsonschema`` — high performance; uses ``exec``; requires explicit
  opt-in via ``backend="fastjsonschema"``.

Backend selection
-----------------
Pass ``backend="auto"`` (default) to let the factory pick the safest
available backend.  The auto priority order is:
``["jsonscreamer", "jsonschema"]``.  Because ``fastjsonschema`` relies on
``exec`` it is *never* selected automatically; you must request it explicitly.

Usage example::

    from jsonschema_validator import ValidatorFactory

    validator = ValidatorFactory.create(backend="auto")
    errors = validator.validate(schema, data)
    for err in errors:
        print(err.path, err.message)
"""

from jsonschema_validator.factory import (
    ValidatorFactory,
    BackendNotAvailableError,
    available_backends,
)
from jsonschema_validator.models import SchemaValidationError

__all__ = [
    "ValidatorFactory",
    "BackendNotAvailableError",
    "SchemaValidationError",
    "available_backends",
]
