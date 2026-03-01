"""Parse a raw YAML data dict into a :class:`ProtocolSpec`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from protocollab.core.models import ProtocolSpec


def parse_spec(
    data: Dict[str, Any],
    base_path: Optional[Path] = None,  # noqa: ARG001 — reserved for future use
) -> ProtocolSpec:
    """Deserialise a raw YAML mapping into a validated :class:`ProtocolSpec`.

    Parameters
    ----------
    data:
        The plain-Python dict returned by the YAML loader.
    base_path:
        Directory that contains the spec file.  Currently unused but accepted
        so callers can pass it for future relative-path resolution inside
        ``types`` / ``seq`` entries.

    Returns
    -------
    ProtocolSpec
        Fully validated Pydantic model.

    Raises
    ------
    pydantic.ValidationError
        If *data* does not conform to the expected schema.
    """
    return ProtocolSpec.model_validate(data)
