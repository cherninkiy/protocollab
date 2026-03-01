"""Composite (user-defined) types built from a TypeDef model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:
    from protocollab.type_system.registry import TypeRegistry

from protocollab.core.models import FieldDef, TypeDef


@dataclass
class ResolvedField:
    """A FieldDef paired with its resolved type object."""

    field_def: FieldDef
    #: None if resolution is deferred (forward reference or dynamic type)
    resolved_type: object = field(default=None)


@dataclass
class CompositeType:
    """A user-defined protocol type declared in the ``types:`` section.

    Attributes
    ----------
    name:
        The type's declared name (matches the key in ``types:``).
    fields:
        Ordered list of :class:`ResolvedField` objects.
    doc:
        Optional documentation string from the spec.
    """

    name: str
    fields: list[ResolvedField] = field(default_factory=list)
    doc: Optional[str] = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_def(
        cls,
        name: str,
        type_def: TypeDef,
        registry: "TypeRegistry",
    ) -> "CompositeType":
        """Build a :class:`CompositeType` from a :class:`~protocollab.core.models.TypeDef`.

        Each field's ``type`` attribute is resolved via *registry*.  If the
        type name is not yet registered (forward reference), ``resolved_type``
        is left as ``None`` and a second pass is needed.

        Parameters
        ----------
        name:
            The composite type name (key in the YAML ``types:`` section).
        type_def:
            Parsed Pydantic model for the type.
        registry:
            The :class:`~protocollab.type_system.registry.TypeRegistry` to use
            for resolving field types.
        """
        resolved_fields: list[ResolvedField] = []
        for fd in type_def.seq:
            try:
                resolved_type = registry.resolve(fd.type) if fd.type else None
            except Exception:  # UnknownTypeError — keep None, validate later
                resolved_type = None
            resolved_fields.append(ResolvedField(field_def=fd, resolved_type=resolved_type))

        return cls(name=name, fields=resolved_fields, doc=type_def.doc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def field_defs(self) -> Sequence[FieldDef]:
        """Flat list of the underlying :class:`FieldDef` objects."""
        return [rf.field_def for rf in self.fields]
