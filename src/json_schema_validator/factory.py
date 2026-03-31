"""Factory for creating json_schema_validator backend instances.

The factory hides backend availability probing and instance caching from
callers, providing a single entry point for backend construction.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from json_schema_validator.backends.base import AbstractSchemaValidator


# Registry of known backend names → import path + class name
_BACKEND_REGISTRY: dict[str, tuple[str, str]] = {
    "jsonschema": (
        "json_schema_validator.backends.jsonschema_backend",
        "JsonschemaBackend",
    ),
    "fastjsonschema": (
        "json_schema_validator.backends.fastjsonschema_backend",
        "FastjsonschemaBackend",
    ),
}

# Auto-mode priority list (safe backends only — fastjsonschema excluded)
_AUTO_PRIORITY: list[str] = ["jsonschema"]


class BackendNotAvailableError(Exception):
    """Raised when the requested backend is not available or not installed."""


class ValidatorFactory:
    """Factory that creates and caches :class:`AbstractSchemaValidator` instances.

    Parameters
    ----------
    cache:
        When ``True`` (default) a single backend instance is reused per
        ``(backend_name, cache_validators)`` combination.

    Examples
    --------
    Using the default auto backend::

        factory = ValidatorFactory()
        validator = factory.create()
        errors = validator.validate(schema, data)

    Selecting an explicit backend::

        validator = factory.create(backend="jsonschema")

    Requesting fastjsonschema (explicit opt-in required)::

        validator = factory.create(backend="fastjsonschema")

    Using the class method shortcut::

        validator = ValidatorFactory.create(backend="auto")
    """

    def __init__(self, cache: bool = True) -> None:
        self._cache_validators = cache
        self._instances: Dict[str, AbstractSchemaValidator] = {}

    # ------------------------------------------------------------------
    # Class-level convenience (stateless)
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        backend: str = "auto",
        cache: bool = True,
        **options: Any,
    ) -> AbstractSchemaValidator:
        """Create (or reuse a cached) backend instance.

        Parameters
        ----------
        backend:
            Backend name: ``"auto"``, ``"jsonschema"``, or
            ``"fastjsonschema"``.  ``"auto"`` (default) picks the safest
            available backend using the priority list
            ``jsonschema``.  Because ``fastjsonschema`` relies on ``exec``
            it is never selected automatically.
        cache:
            Pass ``cache=True`` (default) to cache compiled validators inside
            the backend.
        **options:
            Extra keyword arguments forwarded to the backend constructor.

        Returns
        -------
        AbstractSchemaValidator
            A ready-to-use validator instance.

        Raises
        ------
        BackendNotAvailableError
            When the requested backend is not installed or the name is unknown.
        """
        return cls(cache=cache)._get_or_create(backend, **options)

    # ------------------------------------------------------------------
    # Instance-level helpers
    # ------------------------------------------------------------------

    def _get_or_create(
        self,
        backend: str,
        **options: Any,
    ) -> AbstractSchemaValidator:
        resolved = self._resolve_backend_name(backend)
        cache_key = resolved
        if cache_key in self._instances:
            return self._instances[cache_key]
        instance = self._build(resolved, **options)
        self._instances[cache_key] = instance
        return instance

    def _resolve_backend_name(self, backend: str) -> str:
        """Return the concrete backend name for *backend* (resolves ``auto``)."""
        if backend == "auto":
            return self._auto_select()
        if backend not in _BACKEND_REGISTRY:
            raise BackendNotAvailableError(
                f"Unknown backend {backend!r}. "
                f"Available backends: {sorted(_BACKEND_REGISTRY)}"
            )
        return backend

    @staticmethod
    def _auto_select() -> str:
        """Pick the first available backend from the auto priority list."""
        for name in _AUTO_PRIORITY:
            module_path, _ = _BACKEND_REGISTRY[name]
            try:
                __import__(module_path)
                return name
            except ImportError:
                continue
        raise BackendNotAvailableError(
            "No suitable JSON Schema backend is available. "
            "Install at least one of: jsonschema"
        )

    def _build(self, backend: str, **options: Any) -> AbstractSchemaValidator:
        """Instantiate the named backend, propagating *cache* and *options*."""
        module_path, class_name = _BACKEND_REGISTRY[backend]
        try:
            module = __import__(module_path, fromlist=[class_name])
        except ImportError as exc:
            raise BackendNotAvailableError(
                f"Backend {backend!r} is not available: {exc}"
            ) from exc
        cls_obj = getattr(module, class_name)
        try:
            return cls_obj(cache=self._cache_validators, **options)
        except ImportError as exc:
            raise BackendNotAvailableError(
                f"Backend {backend!r} dependency is missing: {exc}"
            ) from exc


def available_backends() -> list[str]:
    """Return the names of all backends that can be imported right now."""
    result: list[str] = []
    for name, (module_path, class_name) in _BACKEND_REGISTRY.items():
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls_obj = getattr(module, class_name)
            cls_obj()  # probe: will raise ImportError if deps missing
            result.append(name)
        except (ImportError, Exception):
            pass
    return result
