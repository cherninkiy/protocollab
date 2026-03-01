"""TypeRegistry — the central type store for a single ProtocolSpec."""

from __future__ import annotations

from typing import Union

from protocollab.core.models import ProtocolSpec
from protocollab.type_system.composite import CompositeType
from protocollab.type_system.primitives import PRIMITIVE_TYPES, PrimitiveType

AnyType = Union[PrimitiveType, CompositeType]


class UnknownTypeError(Exception):
    """Raised when a type name cannot be resolved in the registry.

    Attributes
    ----------
    type_name:
        The unresolvable type name.
    """

    def __init__(self, type_name: str) -> None:
        self.type_name = type_name
        super().__init__(f"Unknown type: {type_name!r}")


class TypeRegistry:
    """Holds all types (primitive + user-defined) for one :class:`ProtocolSpec`.

    Primitive types are always available.  User-defined composite types are
    added via :meth:`register` or, more conveniently, by calling
    :meth:`build` with a :class:`ProtocolSpec`.

    Example
    -------
    >>> from protocollab.core import parse_spec
    >>> spec = parse_spec({"meta": {"id": "p", "endian": "le"},
    ...                    "types": {"hdr": {"seq": [{"id": "len", "type": "u2"}]}}})
    >>> reg = TypeRegistry().build(spec)
    >>> reg.resolve("u2")
    PrimitiveType(name='u2', ...)
    >>> reg.resolve("hdr")
    CompositeType(name='hdr', ...)
    """

    def __init__(self) -> None:
        # Start with a mutable copy of the global primitives table so each
        # registry instance is independent.
        self._types: dict[str, AnyType] = dict(PRIMITIVE_TYPES)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, name: str, type_obj: AnyType) -> None:
        """Register a user-defined composite type under *name*.

        Parameters
        ----------
        name:
            The type name (must match the key in the YAML ``types:`` section).
        type_obj:
            A :class:`CompositeType` (or :class:`PrimitiveType` for extensions).
        """
        self._types[name] = type_obj

    def resolve(self, type_name: str) -> AnyType:
        """Return the type object for *type_name*.

        Parameters
        ----------
        type_name:
            The (possibly aliased) type name to look up.

        Raises
        ------
        UnknownTypeError
            If *type_name* is not registered.
        """
        try:
            return self._types[type_name]
        except KeyError:
            raise UnknownTypeError(type_name)

    def is_known(self, type_name: str) -> bool:
        """Return ``True`` if *type_name* is registered."""
        return type_name in self._types

    def build(self, spec: ProtocolSpec) -> "TypeRegistry":
        """Populate the registry from a :class:`ProtocolSpec`.

        1. Registers all types declared in ``spec.types``.
        2. Recursively registers types from ``spec.resolved_imports``.

        Returns *self* for chaining::

            reg = TypeRegistry().build(spec)

        Parameters
        ----------
        spec:
            A fully-parsed (and optionally import-resolved)
            :class:`ProtocolSpec`.
        """
        # First, register types from resolved imports so that composite types
        # in the main spec can reference them.
        for imported_spec in spec.resolved_imports.values():
            if isinstance(imported_spec, ProtocolSpec):
                self.build(imported_spec)

        # Then register the spec's own types (may reference imported types).
        for name, type_def in spec.types.items():
            composite = CompositeType.from_def(name, type_def, self)
            self.register(name, composite)

        return self

    def all_names(self) -> list[str]:
        """Return sorted list of all registered type names."""
        return sorted(self._types)
