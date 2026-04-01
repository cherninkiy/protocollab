"""Unified validation result model for jsonschema_validator."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SchemaValidationError:
    """A single JSON Schema validation error from any backend.

    Attributes
    ----------
    path:
        Location of the error in the validated data using dot-notation, e.g.
        ``"meta.id"`` or ``"seq[0].type"``.  ``"(root)"`` when the error
        applies to the root object.
    message:
        Human-readable description of the validation failure.
    schema_path:
        Path inside the JSON Schema document where the violated rule lives,
        e.g. ``"properties/meta/properties/id/pattern"``.  May be an empty
        string when the backend does not provide this information.
    """

    path: str
    message: str
    schema_path: str = field(default="")

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"
