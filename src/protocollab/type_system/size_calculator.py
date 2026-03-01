"""Calculate the static byte-size of protocol types.

Returns ``None`` for variable-length or dynamically-sized types.
"""

from __future__ import annotations

from typing import Optional

from protocollab.type_system.composite import CompositeType
from protocollab.type_system.primitives import PrimitiveType


def calculate_size(type_obj: object) -> Optional[int]:
    """Return the fixed byte-size of *type_obj*, or ``None`` if dynamic.

    Parameters
    ----------
    type_obj:
        A :class:`PrimitiveType` or :class:`CompositeType`.

    Returns
    -------
    int
        Fixed size in bytes, if every field has a statically known size.
    None
        If any field is variable-length (e.g. ``str``, ``strz``, ``bytes``),
        has an ``if_expr`` condition, or if the type is unknown.

    Examples
    --------
    >>> calculate_size(PRIMITIVE_TYPES["u4"])
    4
    >>> calculate_size(CompositeType("ts", [ResolvedField(FieldDef(id="s", type="u4"), u4_type),
    ...                                     ResolvedField(FieldDef(id="us", type="u4"), u4_type)]))
    8
    """
    if isinstance(type_obj, PrimitiveType):
        return type_obj.size_bytes  # None for str / strz / bytes

    if isinstance(type_obj, CompositeType):
        total = 0
        for rf in type_obj.fields:
            # Conditional fields make size indeterminate
            if rf.field_def.if_expr is not None:
                return None
            # Repeated fields of unknown count make size indeterminate
            if rf.field_def.repeat is not None:
                return None
            if rf.resolved_type is None:
                return None
            field_size = calculate_size(rf.resolved_type)
            if field_size is None:
                return None
            total += field_size
        return total

    return None
