"""Data models for validation results."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ValidationError:
    """A single schema validation error."""

    path: str        # dot-notation path, e.g. "meta.id" or "seq[0].type"
    message: str     # human-readable description
    schema_path: str # path inside the JSON Schema where the rule is defined


@dataclass
class ValidationResult:
    """Aggregated result of validating a single protocol file."""

    is_valid: bool
    errors: List[ValidationError]
    file_path: str

    def __bool__(self) -> bool:
        return self.is_valid
